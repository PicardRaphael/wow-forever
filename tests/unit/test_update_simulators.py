"""La veille tient wowsims/forever à jour (plan des simulateurs §3 et §7, étape 5) : étape `simulateurs` de
`forever update`, après `guides`. Seulement si wowsims a déjà été compilé une fois (`forever sims update`), jamais en
simulation ni hors réseau. Au nouveau commit : recompilation épinglée, cas de référence rejoués (chaque préréglage,
même graine), écarts avec le passage précédent notés dans un rapport (`<cache>/third_party/wowsims/veille.json`). Un
échec (réseau, compilation) garde le binaire épinglé et ne bloque pas le passage. Compilation et combats simulés."""

import json

from wowsims_fakes import Sim, clone

from forever import update
from forever.update import STEPS, UpdateOptions


def _run(deps, **options):
    return update._Run(deps, UpdateOptions(**options), None, None, None, deps.data_dir)


def test_step_follows_guides_and_can_be_asked_alone():
    assert STEPS.index("simulateurs") == STEPS.index("guides") + 1 and "simulateurs" in update.ONLY


def test_never_built_means_nothing_to_do(make_deps, tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr("forever.pipeline.wowsims_build.update_wowsims", lambda *a, **k: called.append(1))
    step = update._step_simulators(_run(make_deps(cache_dir=tmp_path)))
    assert step.status == "rien" and "forever sims update" in step.detail and not called


def test_dry_run_offline_or_not_asked(make_deps, tmp_path, monkeypatch):
    clone(tmp_path)
    called = []
    monkeypatch.setattr("forever.pipeline.wowsims_build.update_wowsims", lambda *a, **k: called.append(1))
    for options in ({"dry_run": True}, {"network": False}, {"only": frozenset({"addons"})}):
        assert update._step_simulators(_run(make_deps(cache_dir=tmp_path), **options)).status == "rien", options
    assert not called


def test_new_commit_replays_the_reference_cases_and_reports_gaps(make_deps, tmp_path, monkeypatch):
    from forever.pipeline import gitops, wowsims_build

    root = clone(tmp_path)
    sim = Sim()
    monkeypatch.setattr(gitops, "subprocess_runner", sim)
    pin = wowsims_build.pinned(tmp_path)
    monkeypatch.setattr(
        "forever.pipeline.wowsims_build.update_wowsims", lambda cache_dir, **_: {**pin, "status": "compilé"}
    )
    (root / "veille.json").write_text(
        json.dumps({"commit": "0" * 40, "cases": {"mage/dps/Fire": 50.0, "shaman/elemental/testing": 90.0}}),
        encoding="utf-8",
    )
    step = update._step_simulators(_run(make_deps(cache_dir=tmp_path)))
    assert step.status == "fait" and pin["commit"][:12] in step.detail
    report = json.loads((root / "veille.json").read_text(encoding="utf-8"))
    assert report["commit"] == pin["commit"] and report["previous_commit"] == "0" * 40
    assert report["cases"]["mage/dps/Fire"] > 0
    gaps = {g["case"]: g for g in report["gaps"]}
    assert "mage/dps/Fire" in gaps and "shaman/elemental/testing" not in gaps  # écart au-delà du seuil seulement
    assert len({r["simOptions"]["randomSeed"] for r in sim.requests}) == 1


def test_same_commit_does_not_replay(make_deps, tmp_path, monkeypatch):
    from forever.pipeline import wowsims_build

    clone(tmp_path)
    pin = wowsims_build.pinned(tmp_path)
    monkeypatch.setattr(
        "forever.pipeline.wowsims_build.update_wowsims", lambda cache_dir, **_: {**pin, "status": "à jour"}
    )
    step = update._step_simulators(_run(make_deps(cache_dir=tmp_path)))
    assert step.status == "rien" and "à jour" in step.detail


def test_failure_keeps_the_pin_and_is_noted_without_waiting(make_deps, tmp_path, monkeypatch):
    from forever.pipeline.gitops import GitOpsError

    clone(tmp_path)

    def broken(cache_dir, **_):
        raise GitOpsError("`go build` a échoué (1) : erreur simulée")

    monkeypatch.setattr("forever.pipeline.wowsims_build.update_wowsims", broken)
    step = update._step_simulators(_run(make_deps(cache_dir=tmp_path)))
    assert step.status == "rien" and "passage suivant" in step.detail and "injoignable" in step.detail
