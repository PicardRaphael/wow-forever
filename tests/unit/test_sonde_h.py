"""Retours de la sonde en jeu H du 2026-10-10 (P06b, décision 238) :
- rejeu parallèle : l'empreinte du code est fixée par le passage et transmise au processus du rejeu, qui refuse de
  calculer si le code de forever a changé entre-temps (cause de « leveling-60 absent du cache après le calcul » : code
  modifié pendant le passage de 12:42) ;
- passage de `forever update` borné : au-delà de la durée maximale, il s'arrête proprement (verrou rendu) et laisse
  une attente « erreur » visible, levée par le passage réussi suivant ; l'étape en cours porte son détail (« CI
  attendue … ») ;
- messages des commits de la conversation « addons » lus en UTF-8 ;
- fraîcheur : une dernière version observée plus ancienne que les données locales n'est jamais « plus récente » ;
- consignes de la conversation « jeu » : parler comme à un joueur, ni nom de tranche, ni champ, ni outil interne ;
  faute de frappe interprétée d'après la conversation, question de précision en cas de doute ; critère « jargon
  interne » du banc ;
- dernier export SimulationCraft réel (sonde H) en fixture."""

import json
import os
import shutil
import subprocess
import threading

import pytest
from conftest import FIXTURES

from forever import replay
from forever.update import list_pending, record_pending, update_dir

# --- 9. Rejeu parallèle ----------------------------------------------------------------------------------------------


def test_worker_writes_the_code_of_the_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "build_case", lambda case, data_dir: {"talents": {"a": 1}})
    monkeypatch.setattr(replay, "code_fingerprint", lambda: "code-du-processus")
    path = tmp_path / "leveling-60.json"
    replay._worker("leveling-60", str(tmp_path), str(path), 1, "code-du-passage")
    assert json.loads(path.read_text(encoding="utf-8"))["code"] == "code-du-passage"


def test_child_refuses_a_code_changed_since_the_pass_started(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(replay, "code_fingerprint", lambda: "nouveau")
    request = tmp_path / "demande.json"
    request.write_text(json.dumps({"workers": 1, "code": "ancien", "jobs": []}), encoding="utf-8")
    assert replay.main([str(request)]) == replay.CODE_CHANGED_EXIT
    assert "code de forever a changé pendant le passage" in capsys.readouterr().err


def test_parent_names_a_code_change(tmp_path, monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, replay.CODE_CHANGED_EXIT, stdout="",
                                           stderr="le code de forever a changé pendant le passage")  # fmt: skip

    monkeypatch.setattr(replay.subprocess, "run", fake_run)
    with pytest.raises(replay.ReplayFailedError, match="code de forever a changé pendant le passage"):
        replay._run_child({"workers": 2, "code": "x", "jobs": []}, tmp_path)


def test_parent_sends_its_fingerprint(tmp_path, monkeypatch):
    seen = {}

    def fake_child(request, cache_dir):
        seen.update(request)
        for _case, _data, path, _beams in request["jobs"]:
            replay._write(replay.Path(path), {"talents": {}}, 1.0, code=request["code"])
        return []

    monkeypatch.setattr(replay, "_run_child", fake_child)
    monkeypatch.setattr(replay, "code_fingerprint", lambda: "empreinte-du-passage")
    out = replay.replay_cases([("leveling-20", tmp_path), ("dungeon-20", tmp_path)], tmp_path / "cache", workers=4)
    assert seen["code"] == "empreinte-du-passage" and len(out) == 2


def quiet_steps(monkeypatch, update, **overrides):
    """Étapes du passage remplacées par des étapes vides (aucun réseau, aucun clone), sauf `overrides`."""
    names = {"archivage": "_step_archive", "clone": "_step_clone", "nouvelle_version": "_step_new_version",
             "correctifs": "_step_hotfixes", "journaux": "_step_logs", "addons": "_step_addons"}  # fmt: skip
    for step, fn in names.items():
        monkeypatch.setattr(
            update, fn, overrides.get(step) or (lambda *a, step=step: update.Step(step, "rien", "simulé"))
        )
    monkeypatch.setattr(
        update, "_step_game", overrides.get("jeu") or (lambda run: (update.Step("jeu", "rien", "simulé"), None))
    )


# --- 9. Passage borné ------------------------------------------------------------------------------------------------


def test_a_pass_over_its_limit_stops_and_leaves_an_error(make_deps, monkeypatch):
    from forever import update

    deps = make_deps()
    stuck = threading.Event()
    released = threading.Event()
    stopped: list[int] = []

    def blocking_clone(run):
        stuck.set()
        released.wait(5)
        return update.Step("clone", "fait", "débloqué")

    quiet_steps(monkeypatch, update, clone=blocking_clone)

    def on_timeout(code):
        stopped.append(code)
        released.set()

    worker = threading.Thread(
        target=lambda: update.run_update(deps, update.UpdateOptions(auto=True), max_seconds=0.3, on_timeout=on_timeout)
    )
    worker.start()
    assert stuck.wait(5)
    worker.join(10)
    assert stopped == [update.PASS_TIMEOUT_EXIT]
    errors = [e for e in list_pending(deps.cache_dir) if e["kind"] == "pass_error"]
    assert len(errors) == 1 and errors[0]["action"] == "bloqué" and errors[0]["state"] == "en_attente"
    assert "étape clone" in errors[0]["reasons"][0]
    assert (
        not (update_dir(deps.cache_dir) / "lock").exists()
        or json.loads((update_dir(deps.cache_dir) / "lock").read_text(encoding="utf-8")).get("pid") != os.getpid()
    )


def test_next_good_pass_clears_the_error(make_deps):
    from forever import update

    deps = make_deps()
    record_pending(deps.cache_dir, {"id": "pass-error-x", "kind": "pass_error", "action": "bloqué", "version": None,
                                    "reasons": ["passage arrêté"], "commands": [], "created_at": "2026-09-27T10:00:00Z"})  # fmt: skip
    update.close_pass_errors(deps.cache_dir, "2026-09-27T12:00:00Z")
    (entry,) = list_pending(deps.cache_dir)
    assert entry["state"] == "faite"


def test_error_card_and_status_line():
    from forever.bridge.actions import approvable
    from forever.bridge.cards import update_cards
    from forever.bridge.status import status_line

    entry = {"id": "pass-error-x", "kind": "pass_error", "action": "bloqué", "state": "en_attente", "version": None,
             "reasons": ["passage arrêté au bout de 120 min, à l'étape journaux"], "commands": ["forever update status"]}  # fmt: skip
    (card,) = update_cards([entry])
    assert card["title"] == "Passage de forever update en erreur" and not approvable(entry)
    assert card["lines"][0].startswith("passage arrêté") and [b["key"] for b in card["buttons"]] == ["explain"]
    line = status_line({"version": "1.60.1.70338", "freshness": "fresh", "pass_error": True})
    assert "dernier passage en erreur" in line


def lock_with(cache_dir, **fields):
    lock = update_dir(cache_dir) / "lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    doc = {"pid": os.getpid(), "started_at": "2026-09-27T11:50:00Z", **fields}
    lock.write_text(json.dumps(doc), encoding="utf-8")
    return lock


def test_running_step_shows_the_real_activity_and_its_duration(make_deps):
    from forever.bridge.status import status_line
    from forever.update import update_summary

    deps = make_deps()  # horloge des tests : 2026-09-27T12:00:00Z
    lock_with(deps.cache_dir, step="journaux", step_at="2026-09-27T11:52:00Z",
              detail="CI attendue sur data/1.60.1.70338-r2 (df3a6dfd535b, jusqu'à 60 min)",
              detail_at="2026-09-27T11:51:00Z")  # fmt: skip
    summary = update_summary(deps.cache_dir, deps.now())
    assert summary["running_activity"] == "attente de la CI" and summary["running_minutes"] == 9
    assert summary["running_detail"].startswith("CI attendue sur data/1.60.1.70338-r2")
    update = {"running": True, "step": "journaux", "activity": "attente de la CI", "minutes": 9}
    line = status_line({"version": "1.60.1.70338", "freshness": "fresh", "running": True, "update": update})
    assert "mise à jour en cours (journaux : attente de la CI, 9 min)" in line


def test_update_status_shows_the_activity_and_the_last_line(make_deps, capsys):
    from forever.cli import main

    deps = make_deps()
    lock_with(deps.cache_dir, step="clone", step_at="2026-09-27T11:55:00Z",
              detail="reprise de data/1.60.1.70338-r2 (df3a6dfd535b), CI attendue", detail_at="2026-09-27T11:55:00Z")  # fmt: skip
    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr()[0]
    assert "en cours : clone · attente de la CI depuis 5 min" in out
    assert "dernière ligne : reprise de data/1.60.1.70338-r2 (df3a6dfd535b), CI attendue" in out


def test_pass_log_lines_update_the_lock_detail(make_deps):
    from forever import update

    deps = make_deps()
    lock = lock_with(deps.cache_dir, step="journaux")
    run = update._Run(deps, update.UpdateOptions(auto=True), None, None, None, deps.data_dir)
    run.say("journaux : CI attendue sur data/x (abc, jusqu'à 60 min)")
    doc = json.loads(lock.read_text(encoding="utf-8"))
    assert (
        doc["detail"] == "CI attendue sur data/x (abc, jusqu'à 60 min)" and doc["detail_at"] == "2026-09-27T12:00:00Z"
    )
    run.say("clone : en cours")  # début d'étape : pas un détail
    assert json.loads(lock.read_text(encoding="utf-8"))["detail"] == "CI attendue sur data/x (abc, jusqu'à 60 min)"


# --- Mise à jour en arrière-plan : fenêtres, invites, délais (message de l'utilisateur du 2026-10-10) ----------------


def subprocess_calls(path):
    """Appels `subprocess.run` et `subprocess.Popen` d'un module, avec leurs arguments nommés."""
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id == "subprocess" and node.func.attr in ("run", "Popen"):
                out.append({k.arg for k in node.keywords})
    return out


def test_no_background_subprocess_opens_a_window():
    from conftest import REPO_ROOT

    package = REPO_ROOT / "forever"
    for path in sorted(package.rglob("*.py")):
        for keywords in subprocess_calls(path):
            assert "creationflags" in keywords or "start_new_session" in keywords, path
            assert "stdin" in keywords or "input" in keywords, path  # jamais l'entrée du terminal


def test_git_and_gh_never_prompt(monkeypatch, tmp_path):
    from forever.pipeline import gitops

    seen = {}

    def fake(args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(gitops.subprocess, "run", fake)
    gitops.subprocess_runner(["gh", "run", "list"], tmp_path)
    env = seen["env"]
    assert env["GH_PROMPT_DISABLED"] == "1" and env["GIT_TERMINAL_PROMPT"] == "0"
    assert seen["stdin"] is subprocess.DEVNULL and seen["creationflags"] == gitops.NO_WINDOW


def test_expired_gh_login_is_a_clear_error(tmp_path):
    from forever.pipeline import gitops

    def runner(args, cwd, timeout=None):
        return subprocess.CompletedProcess(
            args, 4, stdout="", stderr="To get started with GitHub CLI, please run:  gh auth login"
        )

    with pytest.raises(gitops.GitOpsError) as err:
        gitops._run(runner, ["gh", "run", "list"], tmp_path)
    assert "authentification de gh expirée" in err.value.message and "gh auth login" in err.value.action


def test_an_error_step_leaves_a_visible_error(make_deps, monkeypatch):
    from forever import update
    from forever.pipeline.gitops import GitOpsError

    deps = make_deps()

    def failing_clone(run):
        raise GitOpsError("`gh run list` a échoué (4) : authentification de gh expirée", "lancer gh auth login")

    quiet_steps(monkeypatch, update, clone=failing_clone)
    update.run_update(deps, update.UpdateOptions(auto=True))
    errors = [e for e in list_pending(deps.cache_dir) if e["kind"] == "pass_error"]
    assert len(errors) == 1 and "clone" in errors[0]["reasons"][0] and "gh" in errors[0]["reasons"][0]
    assert errors[0]["commands"] == ["lancer gh auth login"]


def test_every_step_has_a_limit():
    from forever import update

    assert set(update.STEP_LIMITS_S) >= {"archivage", "clone", "jeu", "nouvelle_version", "correctifs", "journaux",
                                         "addons"}  # fmt: skip
    ci_wait_s = 60 * 60
    for step in ("clone", "nouvelle_version", "journaux", "addons"):
        assert update.STEP_LIMITS_S[step] > ci_wait_s  # l'attente de la CI tient dans le délai de l'étape


def test_live_logs_lists_processes_without_a_window(monkeypatch):
    from forever.pipeline import live_logs

    seen = {}

    def fake(command, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(live_logs.subprocess, "run", fake)
    live_logs.detect_game_running(None)
    assert "creationflags" in seen and seen["stdin"] is subprocess.DEVNULL


# --- 12. Accents des commits ------------------------------------------------------------------------------------------


def test_git_output_is_read_as_utf8(tmp_path):
    from forever.bridge.addons import git

    seen = {}

    def fake(argv, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    git(tmp_path, "log", run=fake)
    assert seen.get("encoding") == "utf-8" and "text" not in seen


@pytest.mark.skipif(shutil.which("git") is None, reason="git absent")
def test_real_git_log_keeps_the_accents(tmp_path):
    from forever.bridge.addons import AddonsConfig, commit, git

    (tmp_path / "Core.lua").write_text("-- coeur\n", encoding="utf-8")
    info = commit(AddonsConfig(tmp_path), "Conversation addons : commentaire en tête de Core.lua")
    assert info is not None
    log = git(tmp_path, "log", "--format=%s", "-n", "1").stdout
    assert log.strip() == "Conversation addons : commentaire en tête de Core.lua"


# --- 13. Fraîcheur --------------------------------------------------------------------------------------------------


def test_an_older_observed_version_is_never_newer(make_deps):
    from forever.freshness import CACHE_NAME, CACHE_SCHEMA_VERSION, check_freshness

    deps = make_deps(offline=True)
    deps.cache_dir.mkdir(parents=True, exist_ok=True)
    doc = {"schema_version": CACHE_SCHEMA_VERSION, "freshness": "fresh", "computed_at": "2026-09-27T11:00:00Z",
           "local_version": "1.60.1.70338", "fetched_at": "2026-09-27T11:00:00Z", "product": "wow_classic_beta",
           "latest": {"version": "1.60.1.70245", "created_at": "2026-09-27T05:00:00Z"}}  # fmt: skip
    (deps.cache_dir / CACHE_NAME).write_text(json.dumps(doc), encoding="utf-8")
    result = check_freshness(deps, "1.60.1.70338", product="wow_classic_beta", prefix="1.60.1.", allow_network=False)
    assert result["newer_available"] is False
    assert any("antérieure aux données locales" in a for a in result["assumptions"])
    assert result["freshness"] != "stale"


def test_a_newer_observed_version_is_flagged(make_deps):
    from forever.freshness import CACHE_NAME, CACHE_SCHEMA_VERSION, check_freshness

    deps = make_deps(offline=True)
    deps.cache_dir.mkdir(parents=True, exist_ok=True)
    doc = {"schema_version": CACHE_SCHEMA_VERSION, "freshness": "stale", "computed_at": "2026-09-27T11:00:00Z",
           "local_version": "1.60.1.70245", "fetched_at": "2026-09-27T11:00:00Z", "product": "wow_classic_beta",
           "latest": {"version": "1.60.1.70338", "created_at": "2026-09-27T05:00:00Z"}}  # fmt: skip
    (deps.cache_dir / CACHE_NAME).write_text(json.dumps(doc), encoding="utf-8")
    result = check_freshness(deps, "1.60.1.70245", product="wow_classic_beta", prefix="1.60.1.", allow_network=False)
    assert result["newer_available"] is True


# --- 10. Consignes de la conversation « jeu » ------------------------------------------------------------------------


def test_game_prompt_speaks_to_a_player():
    from forever.bridge.prompt import SYSTEM_PROMPT

    for rule in (
        "comme à un joueur",
        "jamais de nom de tranche",
        "faute de frappe",
        "question de précision",
    ):
        assert rule in SYSTEM_PROMPT, rule


@pytest.mark.parametrize(
    ("text", "jargon"),
    [
        ("Il manque la tranche T10a pour l'équipement.", True),
        ("Le champ next_step est vide.", True),
        ("J'ai appelé forever_build pour ton build.", True),
        ("Ton prochain talent : Frostbite, au niveau 20.", False),
        ("Rotation **Givre**, avec Frost Armor.", False),
    ],
)
def test_internal_jargon_criterion(text, jargon):
    from forever.bridge.jargon import internal_jargon

    assert bool(internal_jargon(text)) is jargon


def test_bench_has_the_typo_follow_up():
    from forever.bridge.speed import BENCH_QUESTIONS

    keys = [q[0] for q in BENCH_QUESTIONS]
    assert "suite-faute" in keys
    (case,) = [q for q in BENCH_QUESTIONS if q[0] == "suite-faute"]
    assert case[2] == "Pour toi le projet step c'est quoi ?"
    assert keys.index("suite-faute") == keys.index("talents") + 1  # juste après une question sur le build


def test_quality_flags_jargon():
    from forever.bridge.agent import AgentResult
    from forever.bridge.speed import quality_failures

    result = AgentResult(text="Je ne sais pas : il manque T04d et le champ next_step.", session_id="s")
    assert "jargon interne" in quality_failures(result, None, None)


def test_eval_case_for_the_typo_question():
    from conftest import REPO_ROOT

    case = REPO_ROOT / "plugin" / "evals" / "pont-question-de-suite-faute"
    prompt = (case / "prompt.md").read_text(encoding="utf-8")
    assert "Pour toi le projet step c'est quoi ?" in prompt
    graders = "".join(p.read_text(encoding="utf-8") for p in (case / "graders").glob("*.md"))
    assert "nom de tranche" in graders and "question de précision" in graders


# --- Relevé de la sonde H ---------------------------------------------------------------------------------------------


def test_second_real_export():
    from forever.simc import checksum_ok, parse_simc

    text = (FIXTURES / "simc" / "mage19_sonde_h.txt").read_text(encoding="utf-8")
    assert checksum_ok(text) is True and parse_simc(text).level == 19
