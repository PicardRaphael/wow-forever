"""Écriture de `forever update` arrêtée en route : `verify` rouge dans le clone, passage tué sur la branche de données
(demandes de l'utilisateur du 2026-10-06, réponses 2 et 3).

Cas réel : le passage au premier plan du 2026-10-06 (13:54) a trouvé `tasks.py verify` rouge dans le clone ; il a rendu
le code 0, « 0 attente(s) », et la sortie du `verify` n'était gardée nulle part. Un passage tué pendant l'attente de
la CI (jusqu'à 60 min) laissait le clone sur `data/<version>-r<N>`, et le passage suivant s'arrêtait (« main
attendue »).

Git réel sur un dépôt nu local, `uv` et `gh` simulés (`Recorder` de `test_update_publish.py`) ; un passage tué est
simulé par une exception levée à la commande choisie (ni `ForeverError` ni `OSError` : elle traverse les étapes)."""

import subprocess
from pathlib import Path

import pytest
from test_update_chain import TARGET, Replay, montage, step  # noqa: F401 : fixture partagée
from test_update_publish import GAME, Recorder, git, isolated_git, origin  # noqa: F401 : fixtures partagées

from forever.cli import main
from forever.errors import EXIT_PENDING
from forever.hooks import update_line
from forever.update import exit_code, list_pending, run_update, update_dir, update_summary

BRANCH = f"data/{TARGET}-r1"
VERIFY_OUT = "FAILED tests/unit/test_exemple.py::test_version_figee - AssertionError\n"
VERIFY_ERR = "trace sur la sortie d'erreur\n"


class RedVerify(Recorder):
    """`tasks.py verify` rouge dans le clone, avec une sortie."""

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        if args[0] == "uv" and "verify" in args:
            self.calls.append(args)
            return subprocess.CompletedProcess(args, 1, VERIFY_OUT, VERIFY_ERR)
        return super().__call__(args, cwd, timeout)


class Killed(RuntimeError):
    pass


class KillAt(Recorder):
    """Passage tué à la première commande qui commence par `prefix`."""

    def __init__(self, prefix, **kwargs):
        super().__init__(**kwargs)
        self.prefix = list(prefix)

    def __call__(self, args, cwd, timeout=None):
        if list(args)[: len(self.prefix)] == self.prefix:
            raise Killed(" ".join(args))
        return super().__call__(args, cwd, timeout)


def verify_calls(rec):
    return [c for c in rec.calls if c[0] == "uv" and "verify" in c]


def clone_of(deps):
    return update_dir(deps.cache_dir) / "repo"


def head_branch(path):
    return git(path, "rev-parse", "--abbrev-ref", "HEAD")


def advance_main(bare, tmp_path):
    """L'autre PC pousse un commit sur `main` (hors des données)."""
    work = tmp_path / "autre-pc"
    git(tmp_path, "clone", "-q", str(bare), str(work))
    (work / "NOTES.md").write_text("autre PC\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "autre PC")
    git(work, "push", "-q", "origin", "main")


class SameHead:
    """Exécuteur de `update_line` : le dépôt de la session est à `origin_main` (aucun `git pull` à proposer)."""

    def __init__(self, sha):
        self.sha = sha

    def __call__(self, args, cwd, timeout=None):
        return subprocess.CompletedProcess(list(args), 0, self.sha + "\n", "")


# --- Sixième défaut : verify rouge dans le clone ------------------------------------------------------------------


def test_a_red_verify_in_the_clone_is_a_blocked_wait_with_its_output(origin, capsys):  # noqa: F811
    montage_, _bare = origin
    deps, _ = montage_()
    report = run_update(deps, GAME, runner=RedVerify(), replay=Replay())
    assert exit_code(report) == EXIT_PENDING
    (entry,) = report["pending"]
    assert (entry["kind"], entry["action"], entry["version"]) == ("install_version", "bloqué", TARGET)
    log = Path(entry["log"])
    assert log.parent == update_dir(deps.cache_dir) and log.is_file()
    text = log.read_text(encoding="utf-8")
    assert VERIFY_OUT.strip() in text and VERIFY_ERR.strip() in text
    assert any(log.name in r for r in entry["reasons"])
    assert log.name in step(report, "nouvelle_version")["detail"]
    # enregistrée, visible dans `forever update status` et dans la ligne de démarrage
    assert [e["id"] for e in list_pending(deps.cache_dir)] == [entry["id"]]
    assert [p["id"] for p in update_summary(deps.cache_dir, deps.now())["pending"]] == [entry["id"]]
    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr().out
    assert entry["id"] in out and "bloqué" in out and log.name in out
    line = update_line(deps, Path("."), SameHead(report["origin_main"]))
    assert line is not None and "session nécessaire" in line


@pytest.mark.slow
def test_a_blocked_verify_is_not_run_again_until_main_moves(origin, tmp_path):  # noqa: F811
    montage_, bare = origin
    deps, _ = montage_()
    run_update(deps, GAME, runner=RedVerify(), replay=Replay())
    again = RedVerify()
    report = run_update(deps, GAME, runner=again, replay=Replay())
    assert verify_calls(again) == []  # pas 13 min de verify toutes les 6 h sur le même main
    assert step(report, "nouvelle_version")["status"] == "arrêt"
    assert exit_code(report) == EXIT_PENDING and [p["action"] for p in report["pending"]] == ["bloqué"]
    advance_main(bare, tmp_path)  # une correction arrive sur main : nouvel essai
    green = Recorder()
    report = run_update(deps, GAME, runner=green, replay=Replay())
    assert len(verify_calls(green)) == 1
    assert [w["version"] for w in report["written"]] == [TARGET]


# --- Branche de données laissée par un passage tué ----------------------------------------------------------------


@pytest.mark.slow
def test_a_pass_killed_during_the_ci_wait_is_resumed_by_the_next_one(origin):  # noqa: F811
    montage_, bare = origin
    deps, _ = montage_()
    with pytest.raises(Killed):
        run_update(deps, GAME, runner=KillAt(["gh", "run", "list"]), replay=Replay())
    clone = clone_of(deps)
    assert head_branch(clone) == BRANCH and git(bare, "branch", "--list", BRANCH)  # poussée, CI non attendue
    rec = Recorder()
    report = run_update(deps, GAME, runner=rec, replay=Replay())
    cloned = step(report, "clone")
    assert cloned["status"] == "fait" and "reprise" in cloned["detail"], cloned
    assert verify_calls(rec) == []  # rien n'est refait : CI attendue, puis fusion
    assert any(c[:3] == ["gh", "run", "list"] for c in rec.calls)
    assert [(w["version"], w.get("resumed")) for w in report["written"]] == [(TARGET, True)]
    assert git(bare, "ls-tree", "--name-only", "main", f"forever/data/{TARGET}")
    assert git(bare, "branch", "--list", BRANCH) == "" and head_branch(clone) == "main"
    assert git(clone, "branch", "--list", BRANCH) == ""
    assert step(report, "jeu")["status"] == "rien"  # installée : le passage continue sur main


@pytest.mark.slow
def test_a_pass_killed_after_the_merge_only_cleans_up(origin):  # noqa: F811
    montage_, bare = origin
    deps, _ = montage_()
    with pytest.raises(Killed):
        run_update(deps, GAME, runner=KillAt(["git", "switch", "main"]), replay=Replay())
    assert git(bare, "ls-tree", "--name-only", "main", f"forever/data/{TARGET}")  # déjà fusionnée
    clone = clone_of(deps)
    assert head_branch(clone) == BRANCH
    rec = Recorder()
    report = run_update(deps, GAME, runner=rec, replay=Replay())
    assert "fusionnée" in step(report, "clone")["detail"]
    assert not any(c[0] in ("uv", "gh") for c in rec.calls)
    assert [w["version"] for w in report["written"]] == [TARGET]
    assert head_branch(clone) == "main" and git(bare, "branch", "--list", BRANCH) == ""


@pytest.mark.slow
def test_a_pass_killed_before_the_push_returns_to_main_and_writes_again(origin):  # noqa: F811
    montage_, bare = origin
    deps, _ = montage_()
    with pytest.raises(Killed):
        run_update(deps, GAME, runner=KillAt(["git", "push", "-u"]), replay=Replay())
    clone = clone_of(deps)
    assert head_branch(clone) == BRANCH and git(bare, "branch", "--list", BRANCH) == ""  # jamais poussée
    rec = Recorder()
    report = run_update(deps, GAME, runner=rec, replay=Replay())
    cloned = step(report, "clone")
    assert cloned["status"] == "fait" and "abandonnée" in cloned["detail"], cloned
    assert [w["version"] for w in report["written"]] == [TARGET]  # écrite de nouveau, depuis main
    assert git(bare, "ls-tree", "--name-only", "main", f"forever/data/{TARGET}")
    assert head_branch(clone) == "main" and git(clone, "branch", "--list", BRANCH) == ""


@pytest.mark.slow
def test_a_red_ci_found_on_resume_returns_to_main_and_blocks(origin, tmp_path):  # noqa: F811
    montage_, bare = origin
    deps, _ = montage_()
    head = git(bare, "rev-parse", "main")
    with pytest.raises(Killed):
        run_update(deps, GAME, runner=KillAt(["gh", "run", "list"]), replay=Replay())
    rec = Recorder(failing_job="windows")
    report = run_update(deps, GAME, runner=rec, replay=Replay())
    clone = clone_of(deps)
    assert step(report, "clone")["status"] == "fait" and head_branch(clone) == "main"
    assert git(bare, "rev-parse", "main") == head and report["written"] == []
    assert git(bare, "branch", "--list", BRANCH)  # gardée pour l'examen de la CI
    (entry,) = report["pending"]
    assert (entry["kind"], entry["action"], entry["version"]) == ("install_version", "bloqué", TARGET)
    assert any("CI" in r for r in entry["reasons"]) and exit_code(report) == EXIT_PENDING
    assert verify_calls(rec) == []  # même main : pas de nouvel essai dans le même passage
    advance_main(bare, tmp_path)
    report = run_update(deps, GAME, runner=Recorder(), replay=Replay())
    assert [w["version"] for w in report["written"]] == [TARGET]  # branche périmée remplacée, puis fusion
    assert git(bare, "branch", "--list", BRANCH) == ""


@pytest.mark.slow
def test_a_red_ci_in_the_pass_returns_the_clone_to_main_and_blocks(origin):  # noqa: F811
    montage_, bare = origin
    deps, _ = montage_()
    report = run_update(deps, GAME, runner=Recorder(failing_job="windows"), replay=Replay())
    assert head_branch(clone_of(deps)) == "main"
    assert git(bare, "branch", "--list", BRANCH)  # gardée pour l'examen de la CI
    (entry,) = report["pending"]
    assert entry["action"] == "bloqué" and entry.get("ci")
    again = Recorder()
    report = run_update(deps, GAME, runner=again, replay=Replay())
    assert verify_calls(again) == [] and report["written"] == []


# --- Fichier dérivé de la version installée -------------------------------------------------------------------------


@pytest.mark.slow
def test_the_written_version_carries_its_manual_values_inventory(origin):  # noqa: F811
    """`docs/research/valeurs-ecrites-a-la-main.md` est le rendu de `forever origins inventory` pour la version
    courante : l'écriture d'une nouvelle version le rend de nouveau (relevé par le bout en bout, décision 192)."""
    montage_, bare = origin
    deps, _ = montage_()
    report = run_update(deps, GAME, runner=Recorder(), replay=Replay())
    assert [w["version"] for w in report["written"]] == [TARGET]
    doc = git(bare, "show", "main:docs/research/valeurs-ecrites-a-la-main.md")
    assert f"forever/data/{TARGET}/" in doc
