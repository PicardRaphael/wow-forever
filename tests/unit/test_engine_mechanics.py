"""Les 30 contrôles de mécaniques du seed (critère 1), avec les mêmes expressions et les mêmes égalités exactes.

Source des contrôles et de leurs valeurs : seed/forever-mage/tests/run_all.py, test `couverture_mecaniques`
(personnage de référence : niveau 60, Orc, 500 de puissance des sorts, 10 % de critique)."""

import pytest
from conftest import REGISTRY_PATH

from forever.engine import MECHANICS, character, coefficient, expected_cast
from forever.registry import COVERED_STATUSES, load

L = 60
THIS_FILE = "tests/unit/test_engine_mechanics.py"


def ch_ref(gd, **extra):
    return character(gd, 60, "Orc", {"sp": 500, "spell_crit": 0.10, **extra})


def E(gd, key, pts=None, *, ch=None, diff=0, **kw):
    return expected_cast(gd, key, L, pts or {}, ch or ch_ref(gd), diff, **kw)


def fb(gd):
    return E(gd, "frostbolt")


def fi(gd):
    return E(gd, "fireball")


CHECKS = {
    "toucher/écart de niveau": lambda gd: E(gd, "frostbolt", diff=3)["hit"] < fb(gd)["hit"],
    "plafond de toucher": lambda gd: E(gd, "frostbolt", {"elementalPrecision": 5})["hit"] == 0.99,
    "Elemental Precision": lambda gd: E(gd, "frostbolt", {"elementalPrecision": 2})["hit"] > fb(gd)["hit"],
    "Arcane Focus": lambda gd: E(gd, "arcane_missiles", {"arcaneFocus": 2})["hit"] > E(gd, "arcane_missiles")["hit"],
    "critique Int/niveau": lambda gd: character(gd, 30).crit > 0.002,
    "critique d'équipement": lambda gd: character(gd, 60, "Orc", {"crit_gear": 0.03}).crit > character(gd, 60).crit,
    "critique épée Humain": lambda gd: (
        character(gd, 60, "Human", {"sword": True}).crit > character(gd, 60, "Human").crit
    ),
    "Arcane Instability": lambda gd: E(gd, "frostbolt", {"arcaneInstability": 3})["crit"] > fb(gd)["crit"],
    "Critical Mass": lambda gd: E(gd, "fireball", {"criticalMass": 3})["crit"] > fi(gd)["crit"],
    "Arcane Impact": lambda gd: (
        E(gd, "arcane_missiles", {"arcaneImpact": 3})["crit"] > E(gd, "arcane_missiles")["crit"]
    ),
    "Incineration": lambda gd: E(gd, "fire_blast", {"incineration": 3})["crit"] > E(gd, "fire_blast")["crit"],
    "Shatter (gelé)": lambda gd: E(gd, "frostbolt", {"shatter": 3}, frozen=True)["crit"] > fb(gd)["crit"],
    "Winter's Chill": lambda gd: E(gd, "frostbolt", wc_stacks=5)["crit"] > fb(gd)["crit"],
    "multiplicateur de critique": lambda gd: fb(gd)["crit_mult"] == 1.5,
    "Ice Shards": lambda gd: E(gd, "frostbolt", {"iceShards": 5})["crit_mult"] == 2.0,
    "Arcane Mind": lambda gd: E(gd, "arcane_missiles", {"arcaneMind": 5})["crit_mult"] == 2.0,
    "DoT qui critiquent": lambda gd: fi(gd)["dot"] > gd.spells["fireball"].ranks[-1].dot_total,
    "Ignite": lambda gd: E(gd, "fireball", {"ignite": 5})["ignite"] > 0,
    "Piercing Ice": lambda gd: E(gd, "frostbolt", {"piercingIce": 3})["dmg"] > fb(gd)["dmg"],
    "Fire Power": lambda gd: E(gd, "fireball", {"firePower": 5})["dmg"] > fi(gd)["dmg"],
    # contrôles de la formule du seed (T04e : rules="seed" ; coefficients du client : test_client_coefficients.py)
    "coefficients": lambda gd: (
        coefficient(gd, "frostbolt", gd.spells["frostbolt"].ranks[-1], rules="seed") == 3.0 / 3.5 * 0.95
    ),
    "pénalité < 20": lambda gd: (
        coefficient(gd, "frostbolt", gd.spells["frostbolt"].ranks[1], rules="seed") < 1.8 / 3.5 * 0.95
    ),
    "Improved Frostbolt": lambda gd: E(gd, "frostbolt", {"improvedFrostbolt": 5})["cast_s"] == 2.5,
    "Improved Fireball": lambda gd: E(gd, "fireball", {"improvedFireball": 5})["cast_s"] == 3.0,
    "hâte": lambda gd: E(gd, "frostbolt", ch=ch_ref(gd, haste=0.1))["cast_s"] < fb(gd)["cast_s"],
    "temps de recharge global": lambda gd: E(gd, "fire_blast")["cast_s"] == 1.5,
    "Frost Channeling": lambda gd: E(gd, "frostbolt", {"frostChanneling": 3})["mana"] < fb(gd)["mana"],
    "Master of Elements": lambda gd: E(gd, "fireball", {"masterOfElements": 3})["mana"] < fi(gd)["mana"],
    "Arcane Concentration": lambda gd: E(gd, "frostbolt", {"arcaneConcentration": 5})["mana"] < fb(gd)["mana"],
    "sorts en % du mana de base": lambda gd: (
        abs(E(gd, "arcane_blast", {"arcaneBlast": 1})["mana"] - 0.15 * ch_ref(gd).base_mana) < 1e-6
    ),
}


@pytest.mark.parametrize("label", CHECKS)
def test_mechanic_check(label, game_data):
    assert CHECKS[label](game_data), f"mécanique inopérante : {label}"


def test_inventory_matches_checks():
    assert len(CHECKS) == 30
    assert set(MECHANICS) == set(CHECKS)


def test_inventory_ids_are_tested_in_registry():
    entries = {m.id: m for m in load(REGISTRY_PATH)}
    for label, mechanic_id in MECHANICS.items():
        assert mechanic_id in entries, (label, mechanic_id)
        entry = entries[mechanic_id]
        assert entry.status in COVERED_STATUSES, (label, mechanic_id, entry.status)  # B1 : valide-journal (T04b)
        assert any(t.startswith(f"{THIS_FILE}::") for t in entry.tests), (label, mechanic_id)
