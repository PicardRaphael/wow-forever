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
