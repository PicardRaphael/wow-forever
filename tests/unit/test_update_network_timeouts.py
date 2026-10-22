"""Délai maximal de chaque accès réseau de la veille (passage du 22 octobre, demande de l'utilisateur) : Raidbots
(caches vérifiés), wowsims/forever (git, puis modules Go et compilation) et Polestar (git). Une source qui dépasse son
délai est notée « injoignable » dans le détail de son étape, sans attente ni erreur de passage, et les étapes
suivantes tournent. git et HTTP simulés : aucun réseau."""

import subprocess

from conftest import RAIDBOTS_VERIFIED, FakeHttp
from wowsims_fakes import clone as wowsims_clone

from forever import update
from forever.compare import polestar_clone
from forever.pipeline import gitops, wowsims_build
from forever.update import UpdateOptions, dbcache_for_build, list_pending, run_update


class Slow:
    """Exécuteur dont chaque commande dépasse son délai ; garde (commande, délai)."""

    def __init__(self):
        self.calls = []

    def __call__(self, args, cwd, timeout=None):
        self.calls.append((list(args), timeout))
        raise subprocess.TimeoutExpired(list(args), timeout or 0)


def polestar(cache_dir):
    folder = polestar_clone(cache_dir)
    (folder / ".git").mkdir(parents=True)
    (folder / ".git" / "HEAD").write_text("a" * 40 + "\n", encoding="utf-8")


def test_a_git_command_past_its_delay_is_a_named_failure(tmp_path):
    try:
        gitops._run(Slow(), ["git", "fetch"], tmp_path, timeout=300)
    except gitops.GitOpsError as exc:
        assert "délai de 300 s dépassé" in exc.message and "git fetch" in exc.message
    else:
        raise AssertionError("GitOpsError attendue")


def test_polestar_past_its_delay_is_noted_unreachable(make_deps, tmp_path):
    deps = make_deps(cache_dir=tmp_path)
    polestar(tmp_path)
    slow = Slow()
    step = update._step_guides(update._Run(deps, UpdateOptions(), slow, None, None, deps.data_dir))
    assert step.status == "rien" and "injoignable" in step.detail and step.data["unreachable"] is True
    assert [t for _, t in slow.calls] == [update.STEP_GIT_TIMEOUT_S]


def test_wowsims_git_has_its_own_short_delay(tmp_path):
    assert wowsims_build.GIT_TIMEOUT_S < wowsims_build.TIMEOUT_S
    (wowsims_build.wowsims_dir(tmp_path) / "forever" / ".git").mkdir(parents=True)
    slow = Slow()
    try:
        wowsims_build.update_wowsims(tmp_path, runner=slow)
    except gitops.GitOpsError as exc:
        assert "délai" in exc.message
    else:
        raise AssertionError("GitOpsError attendue")
    assert slow.calls == [(["git", "fetch", "--depth", "1", "origin"], wowsims_build.GIT_TIMEOUT_S)]


def test_raidbots_past_its_delay_is_noted_unreachable(make_deps):
    deps = make_deps(http=FakeHttp(routes={RAIDBOTS_VERIFIED: TimeoutError("timed out")}))
    notes: list[str] = []
    assert dbcache_for_build(deps, 70450, "wow_classic_beta", None, notes=notes) is None
    assert len(notes) == 1 and notes[0].startswith("Raidbots injoignable")


def test_unreachable_sources_do_not_stop_the_next_steps(make_deps, tmp_path, monkeypatch):
    deps = make_deps(cache_dir=tmp_path)
    polestar(tmp_path)
    wowsims_clone(tmp_path)  # wowsims déjà compilé une fois

    def slow_wowsims(cache_dir, **_):
        raise gitops.GitOpsError("`git fetch --depth 1 origin` : délai de 120 s dépassé (source injoignable ?)")

    monkeypatch.setattr("forever.pipeline.wowsims_build.update_wowsims", slow_wowsims)
    # clone dédié hors sujet ici (il a son propre test) : laissé de côté
    monkeypatch.setattr(update, "_step_clone", lambda run: update.Step("clone", "rien", "non touché", {}))
    report = run_update(deps, UpdateOptions(only=frozenset({"guides", "simulateurs"})), runner=Slow())
    steps = {s["name"]: s for s in report["steps"]}
    assert steps["guides"]["status"] == "rien" and "injoignable" in steps["guides"]["detail"]
    assert steps["simulateurs"]["status"] == "rien" and "injoignable" in steps["simulateurs"]["detail"]
    assert steps["fin"]["status"] == "fait" and report["pending"] == []
    assert not [e for e in list_pending(tmp_path) if e.get("kind") == "pass_error"]
