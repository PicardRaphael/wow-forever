"""Poids de l'équipement au niveau 60 calculés par wowsims/forever (plan des simulateurs, étape 4 ; décisions 293 et
294) : gain de dégâts par seconde par point de chaque statistique (tirages appariés, binaire épinglé), en clés de
Forever Guide. Unités vérifiées le 2026-10-21 : mêmes points chez Guide et chez wowsims (toucher, critique, puissance
des sorts, Intelligence…) ; wowsims n'a qu'un toucher et qu'un critique, appliqués aussi au toucher et au critique des
sorts de Guide (`shit`, `scrit`). Sous le 60, ou sans préréglage pour la spécialisation, les poids d'avant restent.

Dépôt et simulateur fabriqués (`wowsims_fakes`) ; poids inventés."""

from wowsims_fakes import PROTO_STATS, WeightSim, clone

from forever.gear import _weights_for


def setup(tmp_path, monkeypatch):
    from forever.pipeline import gitops

    root = clone(tmp_path)
    (root / "forever" / "proto").mkdir(parents=True, exist_ok=True)
    (root / "forever" / "proto" / "common.proto").write_text(PROTO_STATS, encoding="utf-8")
    sim = WeightSim()
    monkeypatch.setattr(gitops, "subprocess_runner", sim)
    return sim


def test_level_60_weights_come_from_wowsims(tmp_path, make_deps, monkeypatch):
    sim = setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path, wow_dir=tmp_path)
    weights, source = _weights_for(deps, tmp_path / "AddOns", "MAGE", level=60, race="Gnome", spec="fire-mage")
    assert weights == {"int": 0.4, "sp": 0.8}  # gain par point du simulateur (StatIntellect, StatSpellDamage)
    assert "wowsims/forever" in source and "aaaaaaaaaaaa" in source and "mage/dps/Fire" in source
    races = {r["raid"]["parties"][0]["players"][0]["race"] for r in sim.requests}
    assert races == {"RaceGnome"}


def test_results_are_kept_per_commit(tmp_path, make_deps, monkeypatch):
    sim = setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path, wow_dir=tmp_path)
    _weights_for(deps, tmp_path / "AddOns", "MAGE", level=60, race="Gnome", spec="fire-mage")
    before = len(sim.requests)
    _weights_for(deps, tmp_path / "AddOns", "MAGE", level=60, race="Gnome", spec="fire-mage")
    assert len(sim.requests) == before  # même commit, même préréglage, même race : aucun nouveau calcul


def test_below_60_or_without_preset_the_previous_weights_stay(tmp_path, make_deps, monkeypatch):
    sim = setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path, wow_dir=tmp_path)
    _, source = _weights_for(deps, tmp_path / "AddOns", "DRUID", level=60, race="Tauren", spec="restoration-druid")
    assert "wowsims" not in source  # soigneur : aucun préréglage de wowsims
    _, source = _weights_for(deps, tmp_path / "AddOns", "WARRIOR", level=40, race="Orc", spec="fury-warrior")
    assert "wowsims" not in source and not sim.requests


def test_weights_action_exports_the_same_wowsims_weights_at_60(tmp_path, make_deps, monkeypatch):
    """L'action `weights` (lignes à importer dans Naowh et dans Forever Companion) vient du même calcul que le
    classement de l'équipement : wowsims au niveau 60, toutes classes de dégâts."""
    from forever.exports.naowh import read_naowh_weights
    from forever.exports.pawn import read_pawn_scale
    from forever.gear import gear_report

    setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path, wow_dir=tmp_path)
    (tmp_path / "Interface" / "AddOns").mkdir(parents=True)
    out = gear_report(deps, "weights", class_name="Mage", level=60, race="Gnome", spec="fire-mage")
    assert out["weights"] == {"int": 0.4, "sp": 0.8} and "wowsims/forever" in out["weights_source"]
    spec, naowh = read_naowh_weights(out["naowh"])
    assert spec == "fire-mage" and naowh == {"int": 0.4, "spell": 0.8}
    _name, cls, pawn = read_pawn_scale(out["pawn"])
    assert cls == "Mage" and pawn == {"Intellect": 0.4, "SpellPower": 0.8}
    assert "wowsims/forever" in " ".join(out["provenance"]["assumptions"])
