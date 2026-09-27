"""Bloc avancé à plusieurs ressources (« 3|4 ») : relevé dans le second journal du 2026-09-27 (voleur voisin)."""

from conftest import SYNTHETIC_LOGS

from forever.pipeline.combatlog import read_log


def test_multiple_power_types_keep_the_primary_one():
    _, events = read_log(SYNTHETIC_LOGS / "multi_power.txt")
    (cast,) = list(events)
    adv = cast.advanced
    assert (adv.power_type, adv.power, adv.max_power, adv.power_cost) == (3, 46, 100, 35)
    assert adv.level == 9 and adv.ui_map_id == 1413
