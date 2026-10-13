"""Objectifs de leveling (T04d, bloc F) : une quête grise ou rouge pour le niveau du personnage n'entre pas dans le
calcul (couleurs de `leveling.quest_band` des données du dépôt)."""

from forever.sim.objectives import _eligible


def quest(level, min_level=1, faction="both"):
    fields = {"level": level, "min_level": min_level, "faction": faction, "xp": 100.0}
    return {"fields": {k: {"value": v, "source": "test", "certainty": "suppose"} for k, v in fields.items()}}


def test_gray_and_red_quests_are_left_out(game_data):
    band = game_data.leveling.quest_band
    from forever.engine.leveling import gray_level

    level = 20
    gray, red = gray_level(game_data, level), band.red_min_diff
    assert _eligible(quest(level), "hunter", "horde", level, gray, red)
    assert not _eligible(quest(gray), "hunter", "horde", level, gray, red)
    assert not _eligible(quest(level + red), "hunter", "horde", level, gray, red)
    assert _eligible(quest(level + red - 1), "hunter", "horde", level, gray, red)
    assert not _eligible(quest(level, faction="alliance"), "hunter", "horde", level, gray, red)
    assert not _eligible(quest(level, min_level=level + 1), "hunter", "horde", level, gray, red)
