"""SIM2 bloc 11 : conditions du combat de chaque tranche.

- `solo` (défaut, leveling) : aucun buff, affaiblissement ni consommable ; cible du niveau du personnage ;
- `group` (groupe de donjon) : buffs et affaiblissements du préréglage (rangs au niveau par le correctif des rangs),
  aucun consommable ; cible du niveau du personnage ;
- `raid` : buffs, affaiblissements et consommables du préréglage ; boss de trois niveaux de plus (63 au plus), coups
  écrasants permis (recoupement avec les classements de MythicSim).
Dépôt et simulateur fabriqués : aucune valeur de jeu."""

import pytest
from test_sims_brackets import FROST_STEPS, LevelSim
from test_sims_brackets import _setup as brackets_setup

from forever.errors import InvalidArgumentError
from forever.sims.brackets import run_brackets


def _run(make_deps, tmp_path, conditions, brackets="25"):
    deps = brackets_setup(make_deps, tmp_path)
    sim = LevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets=brackets, steps=FROST_STEPS,
                       picks_at=None, iterations=10, runner=sim, conditions=conditions)  # fmt: skip
    return out, sim.requests[0]


def test_raid_has_buffs_consumables_and_a_boss_three_levels_higher(make_deps, tmp_path):
    out, req = _run(make_deps, tmp_path, "raid")
    assert req["raid"]["buffs"] == {"arcaneBrilliance": True}  # buffs de raid du préréglage fabriqué
    target = req["encounter"]["targets"][0]
    assert target["level"] == 28 and target["canCrush"] is True
    assert out["conditions"] == "raid" and any("raid" in a for a in out["provenance"]["assumptions"])
    _, req60 = _run(make_deps, tmp_path / "b", "raid", brackets="60")
    assert req60["encounter"]["targets"][0]["level"] == 63


def test_group_has_buffs_without_consumables_and_a_target_of_the_level(make_deps, tmp_path):
    out, req = _run(make_deps, tmp_path, "group")
    player = req["raid"]["parties"][0]["players"][0]
    assert req["raid"]["buffs"] == {"arcaneBrilliance": True} and "consumables" not in player
    assert req["encounter"]["targets"][0]["level"] == 25 and out["conditions"] == "group"


def test_solo_is_the_default_and_unknown_conditions_are_refused(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    sim = LevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=FROST_STEPS, picks_at=None,
                       iterations=10, runner=sim)  # fmt: skip
    assert out["conditions"] == "solo" and "buffs" not in sim.requests[0]["raid"]
    with pytest.raises(InvalidArgumentError, match="conditions"):
        run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=[], picks_at=None,
                     iterations=10, runner=sim, conditions="world_buffs")  # fmt: skip
