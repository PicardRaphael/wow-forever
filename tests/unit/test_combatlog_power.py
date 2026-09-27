"""Cas relevés dans le second journal réel du 2026-09-27 : ressources multiples, SPELL_ABSORBED variable."""

from conftest import SYNTHETIC_LOGS

from forever.pipeline.combatlog import read_log


def test_multiple_power_types_keep_the_primary_one():
    _, events = read_log(SYNTHETIC_LOGS / "multi_power.txt")
    (cast,) = list(events)
    adv = cast.advanced
    assert (adv.power_type, adv.power, adv.max_power, adv.power_cost) == (3, 46, 100, 35)
    assert adv.level == 9 and adv.ui_map_id == 1413


def test_spell_absorbed_has_a_variable_layout_kept_raw():
    _, events = read_log(SYNTHETIC_LOGS / "absorbed.txt")
    first, second = list(events)
    assert first.source.npc_id == 3268 and first.dest.name == "Joueur1-Royaume"
    assert first.spell is None and first.advanced is None and first.raw[-3:] == ("14", "15", "nil")
    assert second.source.guid == "Player-0000-00000002" and len(second.raw) == 22
