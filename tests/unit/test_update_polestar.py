"""La veille automatique met à jour le clone des guides de Polestar (plan « Sources d'abord », reste de l'étape d ;
décision 289) : étape `guides` de `forever update`, après les addons. Le clone n'est mis à jour que s'il existe
(créé une première fois par `forever route polestar`, à la main) ; jamais en simulation ni hors réseau ; un échec du
réseau garde la copie existante et réessaie au passage suivant, sans bloquer le passage. git simulé, aucun réseau."""

import subprocess

from forever import update
from forever.compare import polestar_clone
from forever.pipeline.polestar_fetch import REPO
from forever.update import STEPS, UpdateOptions

COMMIT = "a" * 40


class Git:
    def __init__(self, code: int = 0) -> None:
        self.calls: list[tuple[list[str], object]] = []
        self.code = code

    def __call__(self, args, cwd, timeout=None):
        self.calls.append((list(args), cwd))
        return subprocess.CompletedProcess(list(args), self.code, "", "fatal: unable to access" if self.code else "")


def _run(deps, git, **options):
    return update._Run(deps, UpdateOptions(**options), git, None, None, deps.data_dir)


def _clone(cache_dir):
    clone = polestar_clone(cache_dir)
    (clone / ".git").mkdir(parents=True)
    (clone / ".git" / "HEAD").write_text(COMMIT + "\n", encoding="utf-8")
    return clone


def test_guides_step_follows_addons_and_can_be_asked_alone():
    assert STEPS.index("guides") == STEPS.index("addons") + 1 and "guides" in update.ONLY


def test_existing_clone_is_brought_to_the_last_commit(make_deps, tmp_path):
    deps = make_deps(cache_dir=tmp_path)
    clone = _clone(tmp_path)
    git = Git()
    step = update._step_guides(_run(deps, git))
    assert [c[0][:2] for c in git.calls] == [["git", "fetch"], ["git", "reset"]]
    assert all(c[1] == clone for c in git.calls) and not any("push" in c[0] for c in git.calls)
    assert step.name == "guides" and step.status == "fait" and COMMIT[:12] in step.detail


def test_no_clone_no_network_call(make_deps, tmp_path):
    deps = make_deps(cache_dir=tmp_path)
    git = Git()
    step = update._step_guides(_run(deps, git))
    assert step.status == "rien" and "forever route polestar" in step.detail and not git.calls
    assert REPO not in str(git.calls)


def test_dry_run_offline_or_not_asked_touch_nothing(make_deps, tmp_path):
    deps = make_deps(cache_dir=tmp_path)
    _clone(tmp_path)
    for options in ({"dry_run": True}, {"network": False}, {"only": frozenset({"addons"})}):
        git = Git()
        assert update._step_guides(_run(deps, git, **options)).status == "rien", options
        assert not git.calls, options


def test_network_failure_keeps_the_copy_and_does_not_fail_the_pass(make_deps, tmp_path):
    deps = make_deps(cache_dir=tmp_path)
    _clone(tmp_path)
    step = update._step_guides(_run(deps, Git(code=128)))
    assert step.status == "rien" and COMMIT[:12] in step.detail and "passage suivant" in step.detail
    assert "injoignable" in step.detail and step.data["unreachable"] is True
