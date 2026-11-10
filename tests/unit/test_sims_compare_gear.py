"""Comparaison entre classes à équipement égal (demande du 2026-11-10 : « corrige tout ») : `gear="gearquest"` donne à
chaque cas les choix de GearQuest au niveau 60 de sa spécialisation et de sa race, mêmes buffs pour tous ; sans
`gear`, l'équipement du préréglage, comme avant.

Dépôt, simulateur et choix d'objets fabriqués : aucune valeur de jeu."""

import json
from pathlib import Path

from test_sims_brackets import _setup as brackets_setup
from test_sims_races_brackets import RaceLevelSim

from forever.sims import brackets
from forever.sims.report import simulate

PICKED = {"items": [{"id": 4242}]}


def test_compare_with_gearquest_gear(make_deps, tmp_path, monkeypatch):
    from forever.pipeline import gitops

    deps = brackets_setup(make_deps, tmp_path)
    sim = RaceLevelSim()
    monkeypatch.setattr(gitops, "subprocess_runner", sim)
    asked = []

    def fake(deps_, preset, race, level):
        asked.append((preset.key, race, level))
        return PICKED, "équipement : choix fabriqués"

    monkeypatch.setattr(brackets, "gearquest_equipment", fake)
    out = simulate(deps, "compare", cases="mage/dps/Fire@Orc", gear="gearquest", iterations=100)
    assert asked == [("mage/dps/Fire", "Orc", 60)]
    assert sim.requests[-1]["raid"]["parties"][0]["players"][0]["equipment"] == PICKED
    assert out["gear"] == "gearquest"
    assert any("choix fabriqués" in a for a in out["provenance"]["assumptions"])
    before = len(sim.requests)
    out = simulate(deps, "compare", cases="mage/dps/Fire@Orc", iterations=100)
    assert len(asked) == 1 and out["gear"] == "preset"  # sans gear : équipement du préréglage, comme avant
    assert sim.requests[before]["raid"]["parties"][0]["players"][0]["equipment"] != PICKED
    assert json.dumps(out["rows"])  # lignes sérialisables
    assert Path(deps.cache_dir).is_dir()


def test_shadow_tree_maps_to_the_gearquest_shadow_spec():
    """Arbre « Shadow Magic » du client (Prêtre) : spécialisation `shadow-priest` de GearQuest, pas
    `shadow_magic-priest` (aucun objet ; vu le 2026-11-10)."""
    from forever.sims.brackets import gearquest_spec

    assert gearquest_spec("priest/dps/testing", "Shadow Magic") == "shadow-priest"


def test_empty_slots_are_not_gear():
    """Équipement aux 17 emplacements vides (aucun choix d'objet) : nu, donc refusé comme un préréglage sans
    équipement (le Prêtre a été simulé nu le 2026-11-10)."""
    import dataclasses

    import pytest
    from wowsims_fakes import BUILD

    from forever.sims.wowsims import Preset, WowsimsError, require_gear

    empty = Preset(key="priest/dps/x", class_token="ClassPriest", spec_field="shadowPriest", talents="",
                   rotation={}, equipment={"items": [{} for _ in range(17)]}, spec_options={})  # fmt: skip
    assert empty.items == 0
    with pytest.raises(WowsimsError, match="sans équipement"):
        require_gear(empty)
    assert dataclasses.replace(empty, equipment={"items": [{}, {"id": 1}]}).items == 1
    assert BUILD  # faux du dépôt importable
