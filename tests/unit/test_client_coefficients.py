"""Coefficients de puissance des sorts lus dans le client (T04e, registre G4).

Sources : tests/fixtures/wago/1.60.1.70009/enUS/SpellEffect.csv (EffectBonusCoefficient, DifficultyID 0) ; niveaux
des rangs : forever/data/1.60.1.70009/spells.json ; pénalité des sorts de bas niveau : mechanics.json
(`coefficient.low_level`, `coefficient.low_level_default`). Personnage de référence du seed : niveau 60, Orc, 500 de
puissance des sorts, 10 % de critique (seed/forever-mage/tests/run_all.py)."""

import csv
import json

import pytest
from conftest import LOCAL_VERSION, WAGO_70009

from forever.engine import character, coefficient, expected_cast
from forever.engine.damage import roll_base_damage
from forever.gamedata import load_game_data
from forever.manifest import write_manifest

SPELLS = (
    "frostbolt",
    "fireball",
    "fire_blast",
    "scorch",
    "pyroblast",
    "frostfire_bolt",
    "ice_lance",
    "arcane_blast",
    "arcane_missiles",
    "arcane_explosion",
    "frost_nova",
    "cone_of_cold",
    "blast_wave",
    "blizzard",
    "flamestrike",
)


def approx(x):
    return pytest.approx(x, rel=1e-12, abs=1e-15)


def client_coefficients():
    """(sort, indice d'effet) -> EffectBonusCoefficient, lu directement dans la fixture du client."""
    with open(WAGO_70009 / "enUS" / "SpellEffect.csv", encoding="utf-8", newline="") as f:
        return {
            (int(r["SpellID"]), int(r["EffectIndex"])): float(r["EffectBonusCoefficient"])
            for r in csv.DictReader(f)
            if r["DifficultyID"] == "0"
        }


@pytest.fixture
def ch(game_data):
    return character(game_data, 60, "Orc", {"sp": 500, "spell_crit": 0.10})


def edit_version_file(data_dir, name, change):
    path = data_dir / LOCAL_VERSION / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    write_manifest(data_dir)  # modification voulue : l'intégrité reste valide


def test_coefficient_matches_client_table(game_data):
    """Pour chaque rang des 15 sorts : coups directs + éclairs canalisés × tics, coefficients lus dans SpellEffect.csv
    (Frost Nova 0,029 ; Cone of Cold et Blast Wave 0,129 ; Ice Lance 0 ; Blizzard 8 × 0,042 ; Arcane Missiles r8
    5 × 0,286), sans pénalité des sorts de bas niveau."""
    table = client_coefficients()
    checked = 0
    for key in SPELLS:
        for rank, scaling in zip(game_data.spells[key].ranks, game_data.scaling[key], strict=True):
            expected = sum(
                table[(c.spell_id, c.index)] * (c.ticks if c.kind == "channel" else 1)
                for c in scaling.components
                if c.kind in ("direct", "channel")
            )
            assert coefficient(game_data, key, rank, low_level_penalty=False) == approx(expected), (key, rank.position)
            checked += 1
    assert checked == 99
    last = {key: game_data.spells[key].ranks[-1] for key in SPELLS}
    assert coefficient(game_data, "frost_nova", last["frost_nova"]) == 0.02899999917
    assert coefficient(game_data, "cone_of_cold", last["cone_of_cold"]) == 0.12899999321
    assert coefficient(game_data, "blast_wave", last["blast_wave"]) == 0.12899999321
    assert coefficient(game_data, "blizzard", last["blizzard"]) == approx(8 * 0.04199999943)
    assert coefficient(game_data, "arcane_missiles", last["arcane_missiles"]) == approx(5 * 0.28600001335)


def test_low_level_penalty_applies_to_client_coefficient(game_data):
    """Frostbolt r1 (niveau 4) : 0,407 × (1 - 0,0375 × (20 - 4)) par défaut (clé des données à vrai), 0,407 sans
    pénalité ; à partir du rang 4 (niveau 20), la pénalité est sans effet."""
    ranks = game_data.spells["frostbolt"].ranks
    assert coefficient(game_data, "frostbolt", ranks[0]) == approx(0.40700000525 * (1 - 0.0375 * 16))
    assert coefficient(game_data, "frostbolt", ranks[0], low_level_penalty=True) == approx(0.1628000021)
    assert coefficient(game_data, "frostbolt", ranks[0], low_level_penalty=False) == 0.40700000525
    for r in ranks[3:]:
        assert coefficient(game_data, "frostbolt", r) == coefficient(game_data, "frostbolt", r, low_level_penalty=False)


def test_low_level_default_comes_from_data(make_deps, data_copy):
    edit_version_file(
        data_copy, "mechanics.json", lambda d: d["values"]["coefficient.low_level_default"].update(value=False)
    )
    gd = load_game_data(make_deps(data_dir=data_copy))
    assert coefficient(gd, "frostbolt", gd.spells["frostbolt"].ranks[0]) == 0.40700000525


def test_client_coefficient_reads_data(make_deps, data_copy):
    """Preuve que le coefficient vient de spell_scaling.json : le changer change le coefficient."""
    edit_version_file(
        data_copy,
        "spell_scaling.json",
        lambda d: d["spells"]["frostbolt"][10]["components"][0].update(bonus_coefficient=0.5),
    )
    gd = load_game_data(make_deps(data_dir=data_copy))
    assert coefficient(gd, "frostbolt", gd.spells["frostbolt"].ranks[10]) == 0.5


def test_ice_lance_coefficient(game_data):
    """Ice Lance : 0 dans le client (six rangs, probable, test en jeu E4) ; 0,1429 en mode seed (estimation)."""
    for r in game_data.spells["ice_lance"].ranks:
        assert coefficient(game_data, "ice_lance", r) == 0.0
    assert coefficient(game_data, "ice_lance", game_data.spells["ice_lance"].ranks[-1], rules="seed") == 0.1429


def test_seed_rules_keep_the_seed_formula(game_data):
    ranks = game_data.spells["frostbolt"].ranks
    assert coefficient(game_data, "frostbolt", ranks[1], rules="seed") == approx(0.26871428571428574)
    assert coefficient(game_data, "frostbolt", ranks[10], rules="seed") == approx(0.8142857142857142)


def test_unknown_rules_and_seed_without_penalty_are_refused(game_data):
    rank = game_data.spells["frostbolt"].ranks[0]
    with pytest.raises(ValueError, match="rules"):
        coefficient(game_data, "frostbolt", rank, rules="classic")
    with pytest.raises(ValueError, match="low_level_penalty"):
        coefficient(game_data, "frostbolt", rank, rules="seed", low_level_penalty=False)
    assert coefficient(game_data, "frostbolt", rank, rules="seed", low_level_penalty=True) == coefficient(
        game_data, "frostbolt", rank, rules="seed"
    )


def test_frostbolt_forever_values(game_data, ch):
    """Frostbolt r11 (457-493) à 500 de puissance des sorts : (475 + 0,814 × 500) × (1 + 0,1 × 0,5), toucher 0,96."""
    e = expected_cast(game_data, "frostbolt", 60, {}, ch)
    assert e["direct_per_hit"] == approx((475 + 0.81400001049 * 500) * 1.05)
    assert e["direct_per_hit"] == approx(926.1000055072501)
    assert e["dmg"] == approx(889.05600528696)
    seed = expected_cast(game_data, "frostbolt", 60, {}, ch, rules="seed")
    assert seed["direct_per_hit"] == approx(926.25)


def test_fireball_rank12_is_the_same_in_both_modes(game_data, ch):
    """Fireball r12 : coefficient 1 dans le client comme dans la formule (3,5 s / 3,5), DoT sans puissance."""
    assert expected_cast(game_data, "fireball", 60, {}, ch) == expected_cast(
        game_data, "fireball", 60, {}, ch, rules="seed"
    )


def test_roll_base_damage_uses_the_rules(game_data, ch):
    r = game_data.spells["frostbolt"].ranks[10]
    assert roll_base_damage(game_data, "frostbolt", r, ch, 0.0) == approx(457 + 0.81400001049 * 500)
    assert roll_base_damage(game_data, "frostbolt", r, ch, 0.0, rules="seed") == approx(457 + 0.8142857142857142 * 500)
