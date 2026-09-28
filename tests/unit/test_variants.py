"""Hypothèses incertaines pilotées par les données et leurs variantes (T05, bloc B ; décision 81).

Chaque hypothèse vit dans une clé de `mechanics.json` qui porte sa plage (`range`, valeur des données en premier) ;
`with_assumption` rend une copie des données où elle seule change. Les valeurs attendues sont calculées par le moteur
sur les données du dépôt (aucun chiffre de jeu ici) ; la seule constante citée, 0,1429 (Ice Lance), est lue dans
`coefficient.fixed.ice_lance` de `mechanics.json`.

Ignite (registre A18) : notes de développement de Blizzard du 24/09/2026 (Kaivax,
https://us.forums.blizzard.com/en/wow/t/2360696/1, « Today, we updated the WoW Forever Beta with a new build ») :
« Ignite no longer double dips on % damage increase modifiers ». Le build 1.60.1.70009 est publié le 2026-09-24 à
22:02 UTC (`forever builds`, wago.tools), le jour du message, et aucun build ne le suit : les notes s'appliquent à
70009. Ignite se prend donc une seule fois sur les bonus en pourcentage (part du critique final, tics non
remultipliés)."""

import dataclasses

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, REPO_ROOT, read_json

from forever.engine.armor import worn_armor
from forever.engine.cast import expected_cast
from forever.engine.character import character
from forever.engine.damage import dmg_mult, ignite_damage, roll_base_damage
from forever.engine.hit import hit_chance
from forever.engine.mana import in_combat_regen_fraction
from forever.engine.spells import best_rank, coefficient
from forever.engine.talents import talent_value
from forever.engine.variants import ASSUMPTIONS, assumption_range, current_value, with_assumption
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import mc

NAMES = ("a3_miss", "ignite_rule", "mob_hp", "regen_stacking", "low_level_penalty", "bonus_stacking", "ice_lance_coef")
OTHER = {
    "a3_miss": 0.0,
    "ignite_rule": "independent",
    "mob_hp": "seed",
    "regen_stacking": "max",
    "low_level_penalty": False,
    "bonus_stacking": "additive",
    "ice_lance_coef": "seed",
}
FIRE_IGNITE = {"improvedFireball": 5, "ignite": 5}
HIGH_CRIT = {"spell_crit": 0.5}  # critique relevé sur la fiche (valeur de test) : chevauchements d'Ignite fréquents
SEED_MODE = {"mob_source": "seed", "spell_level": "rank", "rules": "seed"}
BLIZZARD_NOTES = "https://us.forums.blizzard.com/en/wow/t/2360696/1"


def test_the_seven_assumptions():
    assert tuple(ASSUMPTIONS) == NAMES


@pytest.mark.parametrize("name", NAMES)
def test_every_assumption_has_a_range_in_the_data(game_data, name):
    entry = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"][ASSUMPTIONS[name]]
    assert entry["certainty"] in ("probable", "suppose")
    assert entry["range"][0]["value"] == entry["value"]
    assert all(v["source"] for v in entry["range"])
    rng = assumption_range(game_data, name)
    assert len(rng) >= 2
    assert rng[0].value == current_value(game_data, name) == entry["value"]
    assert OTHER[name] in [v.value for v in rng]


def test_unknown_assumption_or_value_is_refused(game_data):
    with pytest.raises(ValueError, match="hypothèse inconnue"):
        with_assumption(game_data, "haste_cap", 1)
    with pytest.raises(ValueError, match="hors de la plage"):
        with_assumption(game_data, "regen_stacking", "product")
    with pytest.raises(ValueError, match="hypothèse inconnue"):
        assumption_range(game_data, "haste_cap")


@pytest.mark.parametrize("name", NAMES)
def test_variant_is_a_copy(game_data, name):
    before = dataclasses.asdict(game_data.constants), game_data.leveling
    v = with_assumption(game_data, name, OTHER[name])
    assert current_value(v, name) == OTHER[name]
    assert current_value(game_data, name) != OTHER[name]
    assert (dataclasses.asdict(game_data.constants), game_data.leveling) == before
    assert with_assumption(game_data, name, current_value(game_data, name)) == game_data


def test_a3_variant_misses_as_at_level_diff_zero(game_data):
    ch = character(game_data, 20, "Orc")
    v = with_assumption(game_data, "a3_miss", 0.0)
    assert hit_chance(v, "frost", -3, {}, ch) == hit_chance(v, "frost", 0, {}, ch)
    assert hit_chance(game_data, "frost", -3, {}, ch) > hit_chance(game_data, "frost", 0, {}, ch)


def test_ice_lance_variant_uses_the_seed_coefficient(game_data):
    pts = {"iceLance": 1}
    rank = best_rank(game_data, "ice_lance", 20, pts)
    ch = character(game_data, 20, "Orc", {"sp": 100})
    v = with_assumption(game_data, "ice_lance_coef", "seed")
    seed_coef = game_data.constants.coefficients.fixed["ice_lance"].value
    assert coefficient(game_data, "ice_lance", rank) == 0.0
    assert coefficient(v, "ice_lance", rank) == pytest.approx(seed_coef, rel=1e-12)
    gain = roll_base_damage(v, "ice_lance", rank, ch, 0.5) - roll_base_damage(game_data, "ice_lance", rank, ch, 0.5)
    assert gain == pytest.approx(seed_coef * ch.sp, rel=1e-12)
    # le coefficient des autres sorts ne bouge pas
    fb = best_rank(game_data, "frostbolt", 20, {})
    assert coefficient(v, "frostbolt", fb) == coefficient(game_data, "frostbolt", fb)


def test_bonus_stacking_variant_adds_like_the_seed(game_data):
    buffs = {"dmg": 0.2, "dmg_sources": (0.3,)}
    pts = {"arcaneInstability": 3}
    v = with_assumption(game_data, "bonus_stacking", "additive")
    seed = dmg_mult(game_data, "arcane", pts, buffs, rules="seed")
    assert dmg_mult(v, "arcane", pts, buffs) == pytest.approx(seed, rel=1e-12)
    assert dmg_mult(game_data, "arcane", pts, buffs) != pytest.approx(seed, rel=1e-6)
    assert dmg_mult(v, "arcane", pts, buffs, rules="seed") == seed


def test_regen_stacking_variant_keeps_the_best_source(game_data):
    pts = {"arcaneMeditation": 1}
    am = talent_value(game_data, pts, "arcaneMeditation") / 100
    armor = worn_armor(game_data, 40, "mage").regen_while_casting
    assert am > 0 and armor > 0
    v = with_assumption(game_data, "regen_stacking", "max")
    assert in_combat_regen_fraction(game_data, pts, 40, armor="mage") == pytest.approx(min(1.0, am + armor))
    assert in_combat_regen_fraction(v, pts, 40, armor="mage") == pytest.approx(max(am, armor))
    seed = in_combat_regen_fraction(game_data, pts, 40, rules="seed")
    assert in_combat_regen_fraction(v, pts, 40, rules="seed") == seed


def test_low_level_penalty_variant_is_the_option(game_data):
    rank = game_data.spells["frostbolt"].ranks[0]
    v = with_assumption(game_data, "low_level_penalty", False)
    assert coefficient(v, "frostbolt", rank) == coefficient(game_data, "frostbolt", rank, low_level_penalty=False)
    assert coefficient(v, "frostbolt", rank) > coefficient(game_data, "frostbolt", rank)


def test_mob_hp_variant_is_the_seed_source(game_data):
    pts = {"improvedFrostbolt": 3}
    v = with_assumption(game_data, "mob_hp", "seed")
    assert kill_analytic(v, 12, pts) == kill_analytic(game_data, 12, pts, mob_source="seed")
    assert kill_analytic(v, 12, pts) != kill_analytic(game_data, 12, pts)
    assert kill_analytic(v, 12, pts, mob_source="measured") == kill_analytic(game_data, 12, pts)


def test_independent_ignite_variant_is_the_seed_rule(game_data):
    """Au niveau 16, Fireball seule : forever et seed ne diffèrent que par Ignite (test_engine_ignite) ; la variante
    `independent` (un Ignite par critique, tics fixes) rend donc le Monte Carlo du seed à l'identique."""
    v = with_assumption(game_data, "ignite_rule", "independent")
    seed = mc(game_data, 16, FIRE_IGNITE, "Orc", "fire", 150, seed=11, over=HIGH_CRIT, rules="seed")
    assert mc(v, 16, FIRE_IGNITE, "Orc", "fire", 150, seed=11, over=HIGH_CRIT) == seed
    assert mc(game_data, 16, FIRE_IGNITE, "Orc", "fire", 150, seed=11, over=HIGH_CRIT) != seed


@pytest.mark.parametrize("name", NAMES)
def test_seed_mode_ignores_every_variant(game_data, name):
    v = with_assumption(game_data, name, OTHER[name])
    frost = {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceLance": 1, "arcaneMeditation": 3}
    for level, rotation, pts in ((16, "fire", FIRE_IGNITE), (40, "frost", frost)):
        base = mc(game_data, level, pts, "Orc", rotation, 60, seed=3, over=HIGH_CRIT, **SEED_MODE)
        assert mc(v, level, pts, "Orc", rotation, 60, seed=3, over=HIGH_CRIT, **SEED_MODE) == base
        assert kill_analytic(v, level, pts, "Orc", rotation, **SEED_MODE) == kill_analytic(
            game_data, level, pts, "Orc", rotation, **SEED_MODE
        )


# --- Ignite ne prend les bonus en pourcentage qu'une fois (notes du 24/09/2026, build 70009) -----------------------


def test_ignite_takes_percentage_bonuses_once(game_data):
    """Fire Power multiplie le critique ; l'Ignite qui en découle grandit dans le même rapport (une fois), pas au
    carré (double prise, règle antérieure au 24/09)."""
    ch = character(game_data, 30, "Orc")
    plain = {"improvedFireball": 5, "ignite": 5}
    power = {**plain, "firePower": 5}
    a = expected_cast(game_data, "fireball", 30, power, ch, 0)
    b = expected_cast(game_data, "fireball", 30, plain, ch, 0)
    ratio = a["dmg_mult"] / b["dmg_mult"]
    assert ratio > 1
    assert a["ignite"] / b["ignite"] == pytest.approx(ratio, rel=1e-12)
    assert a["ignite"] / b["ignite"] != pytest.approx(ratio**2, rel=1e-6)


def test_ignite_amount_is_the_talent_share_of_the_final_crit(game_data):
    pts = {"ignite": 5, "firePower": 5}
    share = talent_value(game_data, pts, "ignite") / 100
    assert ignite_damage(game_data, pts, 1000.0) == pytest.approx(share * 1000.0, rel=1e-12)


def test_ignite_rule_cites_the_blizzard_notes():
    entry = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["leveling.ignite_rule"]
    assert BLIZZARD_NOTES in entry["source"]
    registry = (REPO_ROOT / "docs" / "MECHANICS_REGISTRY.yaml").read_text(encoding="utf-8")
    a18 = registry[registry.index("  - id: A18") : registry.index("  - id: A19")]
    assert BLIZZARD_NOTES in a18
    assert "test_ignite_takes_percentage_bonuses_once" in a18
