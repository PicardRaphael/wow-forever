"""Écriture de `forever update` par le clone dédié et le chemin git (T08d, blocs E et G, décisions 180 et 181).

Git réel dans `tmp_path` : un dépôt nu `origin.git` porte `forever/data` du montage de `test_update_chain.py` (base
`1.60.1.79998` installée depuis l'extrait 70124) ; le passage clone ce dépôt dans `<cache>/update/repo`. `uv`
(`sync`, `tasks.py verify`) et `gh` (CI) sont simulés ; aucune commande ne force une poussée. Les données de la
session ne sont jamais touchées : seule `origin` reçoit la nouvelle version."""

import json
import shutil
import subprocess

import pytest
from test_update_chain import BASE, TARGET, Replay, montage  # noqa: F401 : fixture partagée

from forever.manifest import version_files
from forever.pipeline.gitops import subprocess_runner
from forever.update import UpdateOptions, approve, list_pending, run_update, update_dir

FORBIDDEN = {"--force", "-f", "--force-with-lease", "--force-if-includes"}
COEFFICIENT = ("SpellEffect", "116", "EffectBonusCoefficient")
GAME = UpdateOptions(auto=True, only=frozenset({"jeu"}))


def git(cwd, *args):
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True)
    return out.stdout.strip()


def done(stdout="", code=0, args=("x",)):
    return subprocess.CompletedProcess(list(args), code, stdout, "")


class Recorder:
    """Git réel ; `uv` et `gh` simulés (CI verte sous Ubuntu et Windows, sauf `failing_job`)."""

    def __init__(self, failing_job=None, verify_code=0):
        self.calls = []
        self.failing_job = failing_job
        self.verify_code = verify_code

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        assert not FORBIDDEN & set(args), args
        assert not any(a.startswith(("+", "--force")) for a in args), args
        self.calls.append(args)
        if args[0] == "uv":
            return done(code=self.verify_code if "verify" in args else 0, args=args)
        if args[0] == "gh":
            if args[1:3] == ["run", "list"]:
                branch = args[args.index("--branch") + 1]
                sha = git(cwd, "rev-parse", branch)
                runs = [{"databaseId": 7, "headSha": sha, "status": "completed", "conclusion": "success", "url": "u"}]
                return done(json.dumps(runs), args=args)
            if args[1:3] == ["run", "watch"]:
                return done(args=args)
            if args[1:3] == ["run", "view"]:
                jobs = [
                    {"name": "test (ubuntu-latest)", "conclusion": "success"},
                    {"name": "test (windows-latest)", "conclusion": "failure" if self.failing_job else "success"},
                ]
                return done(json.dumps({"jobs": jobs}), args=args)
            raise AssertionError(f"gh inattendu : {args}")
        assert args[0] == "git", args
        return subprocess_runner(args, cwd, timeout)

    def commits(self):
        return [c for c in self.calls if c[:2] == ["git", "commit"]]

    def pushes(self):
        return [c for c in self.calls if c[:2] == ["git", "push"]]


@pytest.fixture(autouse=True)
def isolated_git(tmp_path, monkeypatch):
    config = tmp_path / "gitconfig"
    config.write_text(
        "[user]\n\tname = Test\n\temail = test@example.invalid\n[init]\n\tdefaultBranch = main\n"
        "[core]\n\tautocrlf = false\n[commit]\n\tgpgsign = false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def origin(tmp_path, montage):  # noqa: F811
    """(fabrique de deps, dépôt nu) : `origin.git` porte les données du montage ; l'URL est gardée dans la
    configuration du passage (aucune lecture du dépôt réel)."""
    deps, _ = montage()
    seed = tmp_path / "seed"
    shutil.copytree(deps.data_dir, seed / "forever" / "data")
    git(seed, "init", "-q")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "montage")
    bare = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(bare))
    config = update_dir(deps.cache_dir) / "config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"repo_url": str(bare)}), encoding="utf-8")
    # garde-fou de la première écriture levé (décision 184) : ces tests portent sur le chemin git
    (config.parent / "state.json").write_text(
        json.dumps({"first_write_approved_at": "2026-10-06T00:00:00Z"}), encoding="utf-8"
    )
    return montage, bare


def test_same_tables_are_installed_through_the_clone(origin):
    montage_, bare = origin
    deps, _ = montage_()
    session = version_files(deps.data_dir / BASE)
    rec = Recorder()
    report = run_update(deps, GAME, runner=rec, replay=Replay())
    assert [v["action"] for v in report["verdicts"]] == ["écrire"]
    (written,) = report["written"]
    assert written["version"] == TARGET and written["branch"] == f"data/{TARGET}-r1"
    # origin/main porte la nouvelle version ; la branche est supprimée en local et à distance
    assert git(bare, "ls-tree", "--name-only", "main", f"forever/data/{TARGET}")
    assert git(bare, "branch", "--list", f"data/{TARGET}-r1") == ""
    message = git(bare, "log", "-1", "--format=%B", "main")
    assert message.startswith(f"Veille : {TARGET} r1 installée par forever update")
    assert "Co-Authored-By" not in message
    revisions = json.loads(git(bare, "show", f"main:forever/data/{TARGET}/revisions.json"))
    last = revisions["revisions"][-1]
    assert last["automated"] is True and last["command"] == "forever update --auto"
    assert git(bare, "ls-tree", "--name-only", "main", f"docs/research/data-{TARGET}-r1.md")
    # la session n'est jamais touchée
    assert version_files(deps.data_dir / BASE) == session and not (deps.data_dir / TARGET).exists()
    assert report["origin_main"] and json.loads((update_dir(deps.cache_dir) / "last.json").read_text("utf-8"))


def test_a_changed_engine_input_is_recorded_and_nothing_is_pushed(origin):
    montage_, bare = origin
    deps, _ = montage_(change=COEFFICIENT)
    head = git(bare, "rev-parse", "main")
    rec = Recorder()
    report = run_update(deps, GAME, runner=rec, replay=Replay())
    assert [v["action"] for v in report["verdicts"]] == ["attente"]
    assert rec.commits() == [] and rec.pushes() == []
    assert git(bare, "rev-parse", "main") == head
    (entry,) = list_pending(deps.cache_dir)
    assert entry["state"] == "en_attente" and entry["base"]["origin_main"] == head


def test_an_approved_entry_is_written_by_the_next_run(origin):
    montage_, bare = origin
    deps, _ = montage_(change=COEFFICIENT)
    rec = Recorder()
    run_update(deps, GAME, runner=rec, replay=Replay())
    (entry,) = list_pending(deps.cache_dir)
    spawned = []
    assert approve(deps, entry["id"], spawn=spawned.append)["state"] == "approuvée"
    assert len(spawned) == 1
    report = run_update(deps, GAME, runner=rec, replay=Replay())  # le passage lancé par l'approbation
    assert [(v["action"], v["approved"]) for v in report["verdicts"]] == [("écrire", True)]
    assert git(bare, "ls-tree", "--name-only", "main", f"forever/data/{TARGET}")
    revisions = json.loads(git(bare, "show", f"main:forever/data/{TARGET}/revisions.json"))
    assert revisions["revisions"][-1]["approval"] == entry["id"]
    assert list_pending(deps.cache_dir)[0]["state"] == "faite"


def test_a_red_windows_job_merges_nothing_and_keeps_the_branch(origin):
    montage_, bare = origin
    deps, _ = montage_()
    head = git(bare, "rev-parse", "main")
    report = run_update(deps, GAME, runner=Recorder(failing_job="windows"), replay=Replay())
    step = next(s for s in report["steps"] if s["name"] == "nouvelle_version")
    assert step["status"] == "arrêt" and "CI" in step["detail"]
    assert git(bare, "rev-parse", "main") == head
    assert git(bare, "branch", "--list", f"data/{TARGET}-r1")
    assert report["written"] == []


def test_a_red_verify_in_the_clone_leaves_it_clean(origin):
    montage_, _bare = origin
    deps, _ = montage_()
    rec = Recorder(verify_code=1)
    report = run_update(deps, GAME, runner=rec, replay=Replay())
    step = next(s for s in report["steps"] if s["name"] == "nouvelle_version")
    assert step["status"] == "arrêt" and "verify" in step["detail"]
    assert rec.commits() == [] and rec.pushes() == []
    clone = update_dir(deps.cache_dir) / "repo"
    assert git(clone, "status", "--porcelain") == ""


def clone_checks(rec):
    return [c for c in rec.calls if c[0] == "uv" and "verify" in c]


def test_the_clone_runs_the_data_verify_without_engine_tests(origin):
    """Seules les données changent dans le clone : vérification des données, pas la suite complète ; aucun moteur
    aux entrées changées, aucun test de moteur. La CI complète de la branche reste le juge avant la fusion."""
    montage_, _bare = origin
    deps, _ = montage_()
    rec = Recorder()
    run_update(deps, GAME, runner=rec, replay=Replay())
    assert clone_checks(rec) == [["uv", "run", "--frozen", "--offline", "tasks.py", "verify", "--data", "--engines="]]


def test_the_clone_checks_the_engines_whose_inputs_changed(origin):
    montage_, _bare = origin
    deps, _ = montage_(change=COEFFICIENT)
    rec = Recorder()
    run_update(deps, GAME, runner=rec, replay=Replay())
    (entry,) = list_pending(deps.cache_dir)
    approve(deps, entry["id"], spawn=lambda *a: None)
    run_update(deps, GAME, runner=rec, replay=Replay())
    (check,) = clone_checks(rec)
    engines = check[-1].removeprefix("--engines=").split(",")
    assert check[-2:-1] == ["--data"] and "mage_build" in engines and "pvp_dr" not in engines


def test_a_version_installed_by_the_other_pc_only_advances_the_clone(origin, tmp_path):
    montage_, _bare = origin
    deps, _ = montage_()
    rec = Recorder()
    run_update(deps, GAME, runner=rec, replay=Replay())  # premier PC : installe 79999
    other = make_other_cache(deps, tmp_path)
    rec2 = Recorder()
    report = run_update(other, GAME, runner=rec2, replay=Replay())  # second PC : clone neuf, déjà à jour
    game = next(s for s in report["steps"] if s["name"] == "jeu")
    assert game["status"] == "rien" and TARGET in game["detail"]
    assert rec2.commits() == [] and rec2.pushes() == []


def make_other_cache(deps, tmp_path):
    import dataclasses

    other = tmp_path / "autre-cache"
    (other / "update").mkdir(parents=True)
    shutil.copyfile(update_dir(deps.cache_dir) / "config.json", other / "update" / "config.json")
    return dataclasses.replace(deps, cache_dir=other)
