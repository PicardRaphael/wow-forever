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
    assert entry["start_recovery_ms"] == 1500  # SpellCooldowns.StartRecoveryTime (recharge globale déclenchée)


def test_max_level_zero_is_resolved_to_the_cap_at_decode(client_tables, decode_rules):
    doc = decode_scaling(client_tables, decode_rules, LOCAL_VERSION)
    levels = [e["max_level"] for ranks in doc["spells"].values() for e in ranks]
    assert all(0 < m <= decode_rules["levels"]["level_cap"] for m in levels)


def test_start_recovery_of_every_rank(game_data):
    """Chaque rang décodé porte `start_recovery_ms` ; les sorts suivis déclenchent tous la recharge globale."""
    values = {r.start_recovery_ms for ranks in game_data.scaling.values() for r in ranks}
    assert values == {1500}


def test_decode_reproduces_installed_spell_scaling(candidate):
    assert read_json(candidate.root / LOCAL_VERSION / "spell_scaling.json") == read_json(
        DATA_DIR / LOCAL_VERSION / "spell_scaling.json"
    )


# --- T04e : coefficients et périodes du client (schéma 2) ------------------------------------------
# Valeurs lues dans tests/fixtures/wago/1.60.1.70009/enUS/SpellEffect.csv (DifficultyID 0) : EffectBonusCoefficient
# de l'effet de dégâts ; période = EffectAuraPeriod de l'effet d'aura du sort parent (0 pour un coup direct).
CLIENT_COMPONENTS = [
    # (sort, rang, indice du composant, sort porteur, type, coefficient, période en ms)
    ("frostbolt", 1, 0, 116, "direct", 0.40700000525, 0),
    ("frostbolt", 11, 0, 25304, "direct", 0.81400001049, 0),
    ("pyroblast", 8, 0, 18809, "direct", 1.0, 0),
    ("pyroblast", 8, 1, 18809, "dot", 0.15000000596, 3000),
    ("frostfire_bolt", 3, 1, 1237313, "dot", 0.0, 3000),
    ("fireball", 12, 1, 25306, "dot", 0.0, 2000),
    ("arcane_missiles", 8, 0, 25346, "channel", 0.28600001335, 1000),  # sort déclenché ; période de 25345
    ("blizzard", 6, 0, 1279949, "channel", 0.04199999943, 1000),  # sort déclenché ; période de 10187 (aura 226)
    ("flamestrike", 6, 0, 10216, "direct", 0.15700000525, 0),
    ("flamestrike", 6, 1, 1279990, "dot", 0.03200000152, 2000),  # sort déclenché ; période de 10216 (aura 226)
    ("ice_lance", 6, 0, 1240047, "direct", 0.0, 0),
]


@pytest.mark.parametrize(("key", "rank", "i", "spell_id", "kind", "coef", "period"), CLIENT_COMPONENTS)
def test_decoded_component_carries_client_coefficient_and_period(
    client_tables, decode_rules, key, rank, i, spell_id, kind, coef, period
):
    doc = decode_scaling(client_tables, decode_rules, LOCAL_VERSION)
    c = doc["spells"][key][rank - 1]["components"][i]
    assert (c["spell_id"], c["kind"]) == (spell_id, kind)
    assert c["bonus_coefficient"] == coef
    assert c["period_ms"] == period


@pytest.mark.parametrize(("key", "rank", "i", "spell_id", "kind", "coef", "period"), CLIENT_COMPONENTS)
def test_loaded_component_carries_client_coefficient_and_period(game_data, key, rank, i, spell_id, kind, coef, period):
    c = game_data.scaling[key][rank - 1].components[i]
    assert (c.spell_id, c.kind, c.bonus_coefficient, c.period_ms) == (spell_id, kind, coef, period)


def test_every_component_has_coefficient_and_period(game_data):
    """Chaque composant porte un coefficient du client ; seuls les coups directs ont une période nulle."""
    for key, ranks in game_data.scaling.items():
        for r in ranks:
            for c in r.components:
                assert c.bonus_coefficient >= 0, (key, r.rank)
                assert (c.period_ms == 0) == (c.kind == "direct"), (key, r.rank, c.kind)


def test_spell_scaling_schema_version_2(client_tables, decode_rules):
    assert decode_scaling(client_tables, decode_rules, LOCAL_VERSION)["schema_version"] == 2
    assert read_json(DATA_DIR / LOCAL_VERSION / "spell_scaling.json")["schema_version"] == 2


def test_fire_vulnerability_decoded_from_improved_scorch(client_tables, decode_rules):
    """Aura posée par Improved Scorch (11095, EffectTriggerSpell 22959) : SpellEffect aura 270, 3 par cumul, masque
    d'école 4 (feu) ; SpellAuraOptions.CumulativeAura 5 ; SpellMisc.DurationIndex 9 -> SpellDuration 30 000 ms."""
    doc = decode_scaling(client_tables, decode_rules, LOCAL_VERSION)
    fv = doc["auras"]["fire_vulnerability"]
    assert fv == {
        "spell_id": 22959,
        "source_spell_id": 11095,
        "talent": "improvedScorch",
        "pct_per_stack": 3,
        "max_stacks": 5,
        "duration_ms": 30000,
        "schools": ["fire"],
    }


def test_fire_vulnerability_loaded(game_data):
    fv = game_data.fire_vulnerability
    assert (fv.spell_id, fv.pct_per_stack, fv.max_stacks, fv.duration_s, fv.schools) == (22959, 3, 5, 30, ("fire",))
