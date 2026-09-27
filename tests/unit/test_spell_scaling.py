"""Points de base des sorts au niveau du personnage (`spell_scaling.json`, `rank_values_at_level`).

Valeurs des fixtures wago 1.60.1.70009 : Frostbolt rang 3 (837) a 46 points au niveau 14, +0,9 par niveau jusqu'à
18, variance 0,111 ; Arcane Explosion rang 1 (1449) 32 points +0,4 par niveau de 14 à 19."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.spells import RankValues, rank_values_at_level
from forever.pipeline.decode import decode_scaling


def test_frostbolt_rank3_by_level(game_data):
    assert rank_values_at_level(game_data, "frostbolt", 3, 14) == RankValues(43, 49, 0)
    assert rank_values_at_level(game_data, "frostbolt", 3, 18) == RankValues(47, 52, 0)
    assert rank_values_at_level(game_data, "frostbolt", 3, 40) == RankValues(47, 52, 0)  # plafond MaxLevel
    assert rank_values_at_level(game_data, "frostbolt", 3, 10) == RankValues(43, 49, 0)  # sous le niveau de base


def test_arcane_explosion_rank1_at_19(game_data):
    assert rank_values_at_level(game_data, "arcane_explosion", 1, 19) == RankValues(32, 36, 0)


def test_reproduces_decoded_ranks_at_capped_max_level(game_data, candidate, decode_rules):
    """Au plafond de niveau, chaque sort (et chaque sort déclenché) est évalué à min(MaxLevel, plafond) : les 99
    rangs décodés du client (min, max, dot_total) sont reproduits."""
    decoded = read_json(candidate.root / LOCAL_VERSION / "spells.json")["spells"]
    cap = decode_rules["levels"]["level_cap"]
    checked = 0
    for key, spell in decoded.items():
        for position, row in enumerate(spell["ranks"], start=1):
            got = rank_values_at_level(game_data, key, position, cap)
            assert (got.damage_min, got.damage_max, got.dot_total) == (row[1], row[2], row[3]), (key, position)
            checked += 1
    assert checked == 99


def test_scaling_entry_of_frostbolt_rank3(client_tables, decode_rules):
    doc = decode_scaling(client_tables, decode_rules, LOCAL_VERSION)
    entry = doc["spells"]["frostbolt"][2]
    assert (entry["rank"], entry["spell_id"], entry["base_level"], entry["spell_level"], entry["max_level"]) == (
        3,
        837,
        14,
        14,
        18,
    )
    (component,) = entry["components"]
    assert (component["spell_id"], component["index"], component["kind"], component["ticks"]) == (837, 1, "direct", 1)
    assert component["base_points"] == 46
    assert component["points_per_level"] == pytest.approx(0.9)
    assert component["variance"] == pytest.approx(0.111111, abs=1e-6)


def test_max_level_zero_is_resolved_to_the_cap_at_decode(client_tables, decode_rules):
    doc = decode_scaling(client_tables, decode_rules, LOCAL_VERSION)
    levels = [e["max_level"] for ranks in doc["spells"].values() for e in ranks]
    assert all(0 < m <= decode_rules["levels"]["level_cap"] for m in levels)


def test_decode_reproduces_installed_spell_scaling(candidate):
    assert read_json(candidate.root / LOCAL_VERSION / "spell_scaling.json") == read_json(
        DATA_DIR / LOCAL_VERSION / "spell_scaling.json"
    )
