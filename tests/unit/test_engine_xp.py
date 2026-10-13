"""Modèle d'XP (T04d, bloc C) : chaque règle est lue dans les données de la version du dépôt (`mechanics.json`, clés
`xp.*` ; `character_scaling.json`, `kill_xp`, `rested` et `xp_to_next`), jamais écrite dans le test."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine import leveling
from forever.engine.monsters import mob_xp
from forever.engine.xp import Party, QuestXpInput, gray_level, mob_kill_xp, quest_xp, rested_gain

CERTAINTIES = {"certain", "probable", "suppose"}


def rule(key: str):
    return read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"][key]


def char():
    return read_json(DATA_DIR / LOCAL_VERSION / "character_scaling.json")


def kill(level: int) -> float:
    return char()["kill_xp"][level - 1]


def zero_difference(level: int) -> int:
    return next(zd for top, zd in rule("xp.mob_level_difference")["value"]["zero_difference"] if level <= top)


@pytest.mark.parametrize("level", [1, 10, 30, 60])
def test_same_level_is_the_client_per_kill_and_mob_xp_delegates(game_data, level):
    result = mob_kill_xp(game_data, level, level)
    assert result.xp == kill(level)
    assert mob_xp(game_data, level) == kill(level)
    assert result.terms[0].certainty == "certain"


def test_higher_level_mob_gains_per_level_up_to_the_cap(game_data):
    diff = rule("xp.mob_level_difference")["value"]
    player = 20
    assert mob_kill_xp(game_data, player, player + 2).xp == pytest.approx(
        kill(player) * (1 + diff["higher_per_level"] * 2), rel=1e-12
    )
    far = player + diff["higher_max_diff"] + 3
    assert mob_kill_xp(game_data, player, far).xp == pytest.approx(
        kill(player) * (1 + diff["higher_per_level"] * diff["higher_max_diff"]), rel=1e-12
    )


@pytest.mark.parametrize(("player", "mob"), [(20, 15), (12, 10), (40, 36)])
def test_lower_level_mob_follows_zero_difference(game_data, player, mob):
    assert mob > gray_level(game_data, player)
    # xp.lower_mob_base (relevés du joueur, accord du 2026-10-13) : XP de base au niveau du monstre, ou du joueur
    base = kill(mob) if rule("xp.lower_mob_base")["value"] == "mob" else kill(player)
    expected = base * (1 - (player - mob) / zero_difference(player))
    assert mob_kill_xp(game_data, player, mob).xp == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("player", [5, 10, 20, 40, 60])
def test_gray_mob_gives_nothing(game_data, player):
    gray = gray_level(game_data, player)
    assert gray == leveling.gray_level(game_data, player)  # même règle que les quêtes grises (I7)
    if gray > 0:
        assert mob_kill_xp(game_data, player, gray).xp == 0
        assert mob_kill_xp(game_data, player, gray + 1).xp > 0


def test_elite_and_dungeon_multiply(game_data):
    elite = rule("xp.elite_factor")["value"]
    bonus = rule("xp.dungeon_kill_bonus")["value"]
    base = kill(15)
    assert mob_kill_xp(game_data, 15, 15, elite=True).xp == pytest.approx(base * elite, rel=1e-12)
    assert mob_kill_xp(game_data, 15, 15, dungeon=True).xp == pytest.approx(base * (1 + bonus), rel=1e-12)
    both = mob_kill_xp(game_data, 15, 15, elite=True, dungeon=True)
    assert both.xp == pytest.approx(base * elite * (1 + bonus), rel=1e-12)
    dungeon = next(t for t in both.terms if t.rule == "xp.dungeon_kill_bonus")
    assert dungeon.certainty == rule("xp.dungeon_kill_bonus")["certainty"]


def test_group_share_is_computed_on_each_member_level(game_data):
    rates = rule("xp.group")["value"]["rates"]
    solo = mob_kill_xp(game_data, 20, 20)
    assert mob_kill_xp(game_data, 20, 20, party=Party((20,))).xp == solo.xp
    pair = mob_kill_xp(game_data, 20, 20, party=Party((20, 20)))
    assert pair.xp == pytest.approx(kill(20) * rates[1] * 20 / 40, rel=1e-12)
    mixed = mob_kill_xp(game_data, 18, 20, party=Party((18, 22, 20, 20, 20)))
    own = mob_kill_xp(game_data, 18, 20).xp  # XP du monstre au niveau du joueur (règle individual)
    assert mixed.xp == pytest.approx(own * rates[4] * 18 / 100, rel=1e-12)
    assert any(t.rule == "xp.group" for t in mixed.terms)


def test_rested_doubles_while_the_pool_lasts(game_data):
    factor = char_rested_factor()
    base = kill(12)
    full = mob_kill_xp(game_data, 12, 12, rested_pool=10 * base)
    assert full.xp == pytest.approx(base * factor, rel=1e-12)
    assert full.rested_used == pytest.approx(base * (factor - 1), rel=1e-12)
    partial = mob_kill_xp(game_data, 12, 12, rested_pool=base / 4)
    assert partial.xp == pytest.approx(base + base / 4, rel=1e-12)
    assert partial.rested_used == pytest.approx(base / 4, rel=1e-12)
    none = mob_kill_xp(game_data, 12, 12)
    assert none.rested_used == 0 and not any(t.rule == "xp.rested" for t in none.terms)


def char_rested_factor() -> float:
    return next(r["factor"] for r in char()["rested"] if r["name"] == "Rested")


def test_quest_xp_by_level_difference(game_data):
    q = rule("xp.quest_level_difference")["value"]
    quest = QuestXpInput(level=10, base_xp=840.0, source="fixture", certainty="probable")  # 6083 : QuestXP[10][5]
    assert quest_xp(game_data, 10 + q["full_diff"], quest).xp == 840.0
    assert quest_xp(game_data, 10 + q["full_diff"] + 1, quest).xp == pytest.approx(840.0 * q["reduction"][0])
    assert quest_xp(game_data, 10 + q["full_diff"] + 30, quest).xp == pytest.approx(840.0 * q["reduction"][-1])
    result = quest_xp(game_data, 10, quest)
    assert result.rested_used == 0
    assert result.terms[0].certainty == "probable" and result.terms[0].source == "fixture"


def test_every_term_carries_a_known_certainty_and_a_source(game_data):
    result = mob_kill_xp(game_data, 20, 22, elite=True, dungeon=True, party=Party((20, 20)), rested_pool=1000)
    assert {t.rule for t in result.terms} >= {"xp.mob_level_difference", "xp.elite_factor", "xp.group", "xp.rested"}
    for term in result.terms:
        assert term.certainty in CERTAINTIES and term.source, term


def test_rested_gain_in_the_inn_outside_and_capped(game_data):
    spec = rule("xp.rested")["value"]
    level = 10
    period = next(r["inn_hours"] for r in char()["rested"] if r["name"] == "Rested")
    level_xp = char()["xp_to_next"][level - 1]
    inn = rested_gain(game_data, level, period, inn=True)
    assert inn == pytest.approx(spec["gain_per_period"] * level_xp, rel=1e-12)
    outside = rested_gain(game_data, level, period, inn=False)
    assert outside == pytest.approx(inn * spec["outdoor_ratio"], rel=1e-12)
    assert rested_gain(game_data, level, 10_000, inn=True) == pytest.approx(spec["cap_levels"] * level_xp)
    assert rested_gain(game_data, level, period, inn=True, pool=inn) == pytest.approx(2 * inn, rel=1e-12)
