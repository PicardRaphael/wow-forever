"""Mesures tirées d'un journal : PV des monstres, coûts, intervalles entre instantanés, incantations, critiques,
touchés et ratés. Valeurs relevées sur la fixture anonymisée du 2026-09-27 (voir tests/fixtures/combatlog/)."""

from datetime import datetime

import pytest
from conftest import MINE_GUID, REAL_LOG, SYNTHETIC_LOGS

from forever.pipeline.combatlog import read_log
from forever.pipeline.levels import CasterLevels, LevelTimeline
from forever.pipeline.measure import (
    cast_times,
    crit_ratios,
    find_mine,
    gcd_intervals,
    hit_tally,
    monster_hp,
    spell_costs,
)

# Fenêtre d'enchaînement passée explicitement (paramètre de mesure, pas une règle du jeu) : exclut le trou de 24,9 s
# entre deux instantanés de la fixture.
MAX_GAP_S = 3.0


def events(path=REAL_LOG):
    _, it = read_log(path)
    return list(it)


def test_monster_hp_by_npc_and_level():
    observations, conflicts = monster_hp(events(), log=REAL_LOG.name)
    by_key = {(o["npc_id"], o["level"]): o for o in observations}
    assert set(by_key) == {(3099, 6), (3099, 7), (5951, 1)}
    assert by_key[(3099, 6)]["max_hp"] == 120 and by_key[(3099, 6)]["guids"] == 2
    assert by_key[(3099, 7)]["max_hp"] == 137 and by_key[(3099, 7)]["guids"] == 1
    assert by_key[(5951, 1)]["max_hp"] == 8 and by_key[(5951, 1)]["name"] == "Hare"
    assert by_key[(3099, 6)]["ui_map_id"] == 1411 and by_key[(3099, 6)]["log"] == REAL_LOG.name
    assert conflicts == []


def test_monster_hp_conflict_is_listed_never_averaged():
    observations, conflicts = monster_hp(events(SYNTHETIC_LOGS / "hp_conflict.txt"), log="hp_conflict.txt")
    assert observations == []
    assert conflicts == [{"npc_id": 3099, "level": 6, "values": [120, 125], "log": "hp_conflict.txt"}]


def test_find_mine():
    assert find_mine(events()) == MINE_GUID


def test_spell_costs_read_on_cast_success():
    assert spell_costs(events(), MINE_GUID) == {837: {50}, 145: {65}, 1449: {75}, 2137: {75}}


def test_gcd_intervals_between_chained_instants():
    intervals = gcd_intervals(events(), MINE_GUID, max_gap_s=MAX_GAP_S)
    assert intervals == pytest.approx([1.516, 1.503, 1.590], abs=1e-3)  # ordre chronologique


def test_gcd_intervals_keep_long_gaps_when_window_is_wide():
    assert len(gcd_intervals(events(), MINE_GUID, max_gap_s=60.0)) == 4


def test_cast_times_start_to_success():
    """Chaque START est clos par le SUCCESS suivant du même sort ; un échec qui suit le START (sort déjà en cours)
    ne l'annule pas. Le plan citait deux incantations de Frostbolt : la fixture en contient trois."""
    times = cast_times(events(), MINE_GUID)
    assert set(times) == {837, 145}
    assert times[837] == pytest.approx([1.916, 2.074, 1.982], abs=1e-3)
    assert times[145] == pytest.approx([2.443, 2.472], abs=1e-3)


def test_crit_ratios():
    assert crit_ratios(events(), MINE_GUID) == [(145, pytest.approx(1.5))]


def test_hit_tally_without_caster_level_is_empty_with_assumption():
    tally = hit_tally(events(), MINE_GUID, None)
    assert tally.counts == {}
    assert any("niveau du lanceur" in a for a in tally.assumptions)


def test_hit_tally_grouped_by_school_and_level_gap():
    tally = hit_tally(events(), MINE_GUID, 14)
    got = {k: (v["hits"], v["misses"]) for k, v in tally.counts.items()}
    assert got == {
        ("frost", -8): (3, 0),
        ("fire", -7): (2, 0),
        ("fire", -8): (1, 0),
        ("arcane", -13): (1, 0),
        ("arcane", -8): (2, 0),
    }


def test_gcd_intervals_only_between_gcd_spells():
    """Un sort hors de `gcd_spells` (ici Fire Blast 2137) rompt l'enchaînement : ses deux intervalles disparaissent."""
    intervals = gcd_intervals(events(), MINE_GUID, max_gap_s=MAX_GAP_S, gcd_spells=frozenset({1449}))
    assert intervals == pytest.approx([1.516, 1.590], abs=1e-3)


def test_hit_tally_counts_known_spells_only():
    tally = hit_tally(events(), MINE_GUID, 14, known_spells=frozenset({837}))
    assert {k: (v["hits"], v["misses"]) for k, v in tally.counts.items()} == {("frost", -8): (3, 0)}


def test_hit_tally_follows_a_level_change():
    """Niveau 15 à partir de 14:55:00 : Fire Blast et Arcane Explosion de la fin du journal changent d'écart."""
    levels = CasterLevels(
        (
            LevelTimeline(
                (
                    (datetime.fromisoformat("2026-09-27T14:50:00"), 14),
                    (datetime.fromisoformat("2026-09-27T14:55:00"), 15),
                ),
                "t",
            ),
        )
    )
    tally = hit_tally(events(), MINE_GUID, levels)
    assert {k: v["hits"] for k, v in tally.counts.items()} == {
        ("frost", -8): 3,
        ("fire", -7): 2,
        ("arcane", -13): 1,
        ("fire", -9): 1,
        ("arcane", -9): 2,
    }


def test_hit_tally_notes_casts_before_any_known_level():
    levels = CasterLevels((LevelTimeline(((datetime.fromisoformat("2026-09-27T14:55:00"), 15),), "t"),))
    tally = hit_tally(events(), MINE_GUID, levels)
    assert sum(v["hits"] for v in tally.counts.values()) == 3
    assert any("6 sort(s)" in a and "niveau du lanceur inconnu" in a for a in tally.assumptions)
