"""Bonus d'XP du moteur (T04f, bloc B) : facteur des auras d'XP, cumul (addition, variante produit), repos sur l'XP
majorée, perk Legacy, tente. Valeurs lues dans les données de la version du dépôt (`xp_bonuses.json`,
`mechanics.json`, `character_scaling.json`), jamais écrites dans le test ; les identifiants désignent des sorts."""

from dataclasses import replace

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.xp import (
    ActiveAura,
    QuestXpInput,
    XpBonusState,
    mob_kill_xp,
    quest_xp,
    rested_cap,
    rested_gain,
    sleeping_bag_state,
    tent_rested,
    xp_bonus_data,
    xp_multiplier,
)

WELL_RESTED, FOOD_XP, LEGACY_RESTED, NO_SOURCE = 429959, 1243969, 1225478, 436412
CERTAINTIES = {"certain", "probable", "suppose"}


def doc():
    return read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")


def aura(spell):
    return next(a for a in doc()["auras"] if a["spell_id"] == spell)


def pct(spell, key):
    return next(e["base_points"] for e in aura(spell)["effects"] if e["key"] == key) / 100


def rule(key):
    return read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"][key]


def kill(level):
    return read_json(DATA_DIR / LOCAL_VERSION / "character_scaling.json")["kill_xp"][level - 1]


def level_xp(game_data, level):
    return game_data.xp_to_next[level - 1]


WR3 = XpBonusState(auras=(ActiveAura(WELL_RESTED, aura(WELL_RESTED)["max_stacks"]),))
WR3_FOOD = replace(WR3, food=True)


def test_bonus_data_is_read_from_the_client_file(game_data):
    data = xp_bonus_data(game_data)
    assert set(data.auras) == {a["spell_id"] for a in doc()["auras"]}
    assert data.stacking == rule("xp.bonus_stacking")["value"]["mode"] == "additive"
    assert data.rested_after is rule("xp.bonus_stacking")["value"]["rested_after"] is True
    assert data.sleeping_bag is not None and data.sleeping_bag.aura == WELL_RESTED


def test_kill_factor_adds_well_rested_and_food(game_data):
    stacks = aura(WELL_RESTED)["max_stacks"]
    expected = 1 + pct(WELL_RESTED, "kill_xp_pct") * stacks + pct(FOOD_XP, "kill_xp_pct")
    factor, terms = xp_multiplier(game_data, WR3_FOOD, source="kill")
    assert factor == pytest.approx(expected, rel=1e-12)
    assert {t.rule for t in terms} >= {f"xp_bonus.{WELL_RESTED}", f"xp_bonus.{FOOD_XP}", "xp.bonus_stacking"}
    for t in terms:
        assert t.certainty in CERTAINTIES and t.source


def test_multiplicative_variant_is_the_product(game_data):
    stacks = aura(WELL_RESTED)["max_stacks"]
    expected = (1 + pct(WELL_RESTED, "kill_xp_pct") * stacks) * (1 + pct(FOOD_XP, "kill_xp_pct"))
    assert rule("xp.bonus_stacking")["value"]["variants"] == ["additive", "multiplicative"]
    factor, _ = xp_multiplier(game_data, WR3_FOOD, source="kill", mode="multiplicative")
    assert factor == pytest.approx(expected, rel=1e-12)


def test_food_bonus_does_not_touch_quests(game_data):
    assert xp_multiplier(game_data, XpBonusState(food=True), source="quest")[0] == 1.0
    stacks = aura(WELL_RESTED)["max_stacks"]
    factor, _ = xp_multiplier(game_data, WR3_FOOD, source="quest")
    assert factor == pytest.approx(1 + pct(WELL_RESTED, "quest_xp_pct") * stacks, rel=1e-12)


def test_stacks_are_capped_at_the_client_maximum(game_data):
    over = XpBonusState(auras=(ActiveAura(WELL_RESTED, aura(WELL_RESTED)["max_stacks"] + 5),))
    assert xp_multiplier(game_data, over, source="kill")[0] == xp_multiplier(game_data, WR3, source="kill")[0]


def test_bonus_without_a_player_source_is_never_applied(game_data):
    state = XpBonusState(auras=(ActiveAura(NO_SOURCE, 1),))
    factor, terms = xp_multiplier(game_data, state, source="kill")
    assert factor == 1.0 and not any(str(NO_SOURCE) in t.rule for t in terms)


@pytest.mark.parametrize(("player", "mob"), [(10, 10), (20, 18), (30, 32)])
def test_without_bonuses_the_xp_is_unchanged(game_data, player, mob):
    before = mob_kill_xp(game_data, player, mob, rested_pool=1000.0)
    assert mob_kill_xp(game_data, player, mob, rested_pool=1000.0, bonuses=None) == before
    assert mob_kill_xp(game_data, player, mob, rested_pool=1000.0, bonuses=XpBonusState()).xp == before.xp


def test_rested_applies_to_the_boosted_xp(game_data):
    level = 20
    factor, _ = xp_multiplier(game_data, WR3_FOOD, source="kill")
    rested = rule("xp.rested")["value"]
    rested_factor = game_data.xp.rested_factor
    assert rested["factor"] and rested_factor
    result = mob_kill_xp(game_data, level, level, rested_pool=1e9, bonuses=WR3_FOOD)
    assert result.xp == pytest.approx(kill(level) * factor * rested_factor, rel=1e-12)
    assert result.rested_used == pytest.approx(kill(level) * factor * (rested_factor - 1), rel=1e-12)


def test_quest_xp_gets_the_quest_bonus_and_never_rested(game_data):
    quest = QuestXpInput(level=20, base_xp=1000.0, source="test", certainty="certain")
    base = quest_xp(game_data, 20, quest)
    boosted = quest_xp(game_data, 20, quest, bonuses=WR3_FOOD)
    factor, _ = xp_multiplier(game_data, WR3_FOOD, source="quest")
    assert boosted.xp == pytest.approx(base.xp * factor, rel=1e-12) and boosted.rested_used == 0.0


@pytest.mark.parametrize("rank", [1, 3, 5])
def test_legacy_well_rested_multiplies_gain_and_cap(game_data, rank):
    level = 20
    ranks = aura(LEGACY_RESTED)["legacy"]["ranks"]
    effects = {e["key"]: str(e["index"]) for e in aura(LEGACY_RESTED)["effects"]}
    rate = ranks[effects["rested_rate_pct"]][rank - 1] / 100
    cap = ranks[effects["rested_cap_pct"]][rank - 1] / 100
    assert rested_gain(game_data, level, 8, inn=True, legacy_rank=rank) == pytest.approx(
        rested_gain(game_data, level, 8, inn=True) * (1 + rate), rel=1e-12
    )
    assert rested_cap(game_data, level, rank) == pytest.approx(rested_cap(game_data, level) * (1 + cap), rel=1e-12)
    assert rested_cap(game_data, level) == pytest.approx(
        rule("xp.rested")["value"]["cap_levels"] * level_xp(game_data, level), rel=1e-12
    )
    huge = rested_gain(game_data, level, 10_000, inn=True, legacy_rank=rank)
    assert huge == pytest.approx(rested_cap(game_data, level, rank), rel=1e-12)


def test_tent_raises_the_pool_to_its_threshold_only(game_data):
    level = 20
    threshold = doc()["camp"]["tent"]["threshold_pct_of_level"] / 100 * level_xp(game_data, level)
    assert tent_rested(game_data, level, 0.0) == pytest.approx(threshold, rel=1e-12)
    assert tent_rested(game_data, level, threshold * 2) == threshold * 2


def test_sleeping_bag_state_is_well_rested_at_full_stacks_and_duration(game_data):
    state = sleeping_bag_state(game_data)
    (active,) = state.auras
    assert active.spell_id == WELL_RESTED and active.stacks == aura(WELL_RESTED)["max_stacks"]
    assert active.remaining_s == aura(WELL_RESTED)["duration_ms"] / 1000
    assert sleeping_bag_state(game_data, 1).auras[0].stacks == 1


def test_registry_entries_of_the_xp_bonuses():
    from conftest import REGISTRY_PATH

    from forever.registry import load

    entries = {m.id: m for m in load(REGISTRY_PATH)}
    for mid in ("D5", "D7", "D9", "D10", "E3"):
        assert entries[mid].status == "teste", mid
        assert any("test_engine_xp_bonuses.py::" in t or "test_session_xp.py::" in t for t in entries[mid].tests), mid
    assert entries["D10"].certainty == "suppose"
