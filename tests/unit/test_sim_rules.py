"""Règles des simulateurs (T04c) : `rules="forever"` (défaut, corrections de T04c) ou `"seed"` (parité avec le
seed), armure portée (`armor`, paramètre de build), régénération cumulée (B7), recharge de Fire Blast dans
l'analytique (B13).

Les effets testés ici sont déterministes (analytique) ou vérifiés par différence (Monte Carlo à graine fixe) : aucun
sens n'est imposé à un écart plus petit que le bruit du Monte Carlo. Valeur de parité : L16, 5 Improved Frostbolt,
n = 200, graine 1 -> 30.435373555182213 (seed, test_sim_leveling.py)."""

import json

import pytest

from forever.cli import main
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import mc, options_with_defaults

SEED_MODE = {"mob_source": "seed", "spell_level": "rank", "rules": "seed"}
IF5 = {"improvedFrostbolt": 5}
AM3 = {"arcaneMeditation": 3}
NO_SP = {"sp": 0}  # puissance des sorts neutralisée : forever et seed ne diffèrent alors que par les autres règles


def run_json(capsys, argv, deps):
    code = main([*argv, "--json"], deps)
    return code, json.loads(capsys.readouterr().out)


def test_default_rules_are_forever_with_auto_armor(game_data):
    o = options_with_defaults(game_data, "frost", {})
    assert (o["rules"], o["armor"]) == ("forever", "auto")


def test_seed_rules_keep_the_seed_value(seed_game_data):
    assert mc(seed_game_data, 16, IF5, n=200, seed=1, **SEED_MODE)["total"] == pytest.approx(
        30.435373555182213, rel=1e-12
    )


@pytest.mark.parametrize(
    ("options", "match"),
    [
        ({"rules": "classic"}, "rules"),
        ({"armor": "molten"}, "armor"),
        ({"rules": "seed", "armor": "mage"}, "armor"),
    ],
)
def test_invalid_rules_or_armor_are_refused(game_data, options, match):
    with pytest.raises(ValueError, match=match):
        mc(game_data, 40, {}, n=5, **options)
    with pytest.raises(ValueError, match=match):
        kill_analytic(game_data, 40, {}, **options)


def test_mage_armor_below_its_level_is_refused_by_both_simulators(game_data):
    with pytest.raises(ValueError, match="Mage Armor"):
        mc(game_data, 30, {}, n=5, armor="mage")
    with pytest.raises(ValueError, match="Mage Armor"):
        kill_analytic(game_data, 30, {}, armor="mage")


def test_mage_armor_removes_the_attacker_slow_in_the_analytic_model(game_data):
    """Sous Mage Armor, plus de ralenti des coups du monstre : plus de dégâts subis que sous Ice Armor (L40)."""
    mage = kill_analytic(game_data, 40, {}, armor="mage")
    frost = kill_analytic(game_data, 40, {}, armor="frost")
    assert mage != frost  # le paramètre est lu
    assert mage["combat"] > frost["combat"]  # coups plus fréquents : plus de recul d'incantation
    assert mage["taken"] > frost["taken"]
    auto = kill_analytic(game_data, 40, {})
    assert auto == mage  # auto : Mage Armor dès son niveau d'apprentissage


def test_seed_rules_keep_the_frost_armor_slow(game_data):
    """Le seed garde le ralenti de Frost Armor à tout niveau : mêmes dégâts subis que sous Ice Armor forcée.
    Puissance des sorts neutralisée (`sp` 0, T04e) : les coefficients du client ne changent que ce terme."""
    seed = kill_analytic(game_data, 40, {}, over=NO_SP, rules="seed")
    frost = kill_analytic(game_data, 40, {}, over=NO_SP, armor="frost")
    assert seed["taken"] == frost["taken"]
    assert seed["taken"] < kill_analytic(game_data, 40, {}, over=NO_SP)["taken"]


def test_mage_armor_changes_the_monte_carlo(game_data):
    mage = mc(game_data, 40, {}, n=60, seed=5, armor="mage")
    frost = mc(game_data, 40, {}, n=60, seed=5, armor="frost")
    assert mage != frost
    assert mc(game_data, 40, {}, n=60, seed=5) == mage


def test_arcane_meditation_adds_to_mage_armor(game_data):
    """Règle Classic (B7, suppose) : Arcane Meditation et Mage Armor s'additionnent ; le seed prend le maximum."""
    with_am = kill_analytic(game_data, 40, AM3, armor="mage")
    without = kill_analytic(game_data, 40, {}, armor="mage")
    assert with_am["combat"] == without["combat"]
    assert with_am["mana"] < without["mana"]
    seed_with = kill_analytic(game_data, 40, AM3, rules="seed")
    seed_without = kill_analytic(game_data, 40, {}, rules="seed")
    assert seed_with["mana"] == seed_without["mana"]  # max(AM 50 %, Mage Armor 50 %) = 50 %


def test_monte_carlo_uses_the_cumulated_regen(game_data):
    with_am = mc(game_data, 40, AM3, n=40, seed=9, armor="mage")
    without = mc(game_data, 40, {}, n=40, seed=9, armor="mage")
    assert with_am["combat"] == without["combat"]  # aucun tirage changé
    assert with_am["mana"] < without["mana"]


def test_analytic_fire_blast_cooldown_includes_wake_of_fire(game_data):
    """B13 : en `forever`, le cycle de feu prend la recharge de Fire Blast réduite par Wake of Fire. Égalité sans
    Wake of Fire à puissance des sorts neutralisée (`sp` 0, T04e : seul terme changé par les coefficients du client)."""
    pts = {"improvedFireball": 5, "wakeOfFire": 2}
    forever = kill_analytic(game_data, 20, pts, rotation="fire")
    seed = kill_analytic(game_data, 20, pts, rotation="fire", rules="seed")
    assert forever["combat"] < seed["combat"]
    plain = {"improvedFireball": 5}
    assert kill_analytic(game_data, 20, plain, rotation="fire", over=NO_SP) == kill_analytic(
        game_data, 20, plain, rotation="fire", over=NO_SP, rules="seed"
    )


def test_cli_armor_and_rules(capsys, make_deps):
    code, out = run_json(capsys, ["sim", "leveling", "--level", "40", "--n", "10", "--armor", "mage"], make_deps())
    assert code == 0 and (out["options"]["armor"], out["options"]["rules"]) == ("mage", "forever")
    assert any("armor mage" in a for a in out["provenance"]["assumptions"])
    code, out = run_json(capsys, ["sim", "leveling", "--level", "12", "--n", "10", "--rules", "seed"], make_deps())
    assert code == 0 and out["options"]["rules"] == "seed"


def test_cli_mage_armor_below_its_level_is_refused(capsys, make_deps):
    code, out = run_json(capsys, ["sim", "leveling", "--level", "30", "--n", "10", "--armor", "mage"], make_deps())
    assert code == 2 and out["error"]["code"] == "invalid_argument" and "Mage Armor" in out["error"]["message"]


# --- T04e : pénalité des sorts de bas niveau, coefficients du client dans les simulateurs --------------------------


def test_low_level_penalty_option_changes_the_forever_result(game_data):
    """Niveau 12, frost : Frostbolt r2 (niveau 8) porte la pénalité (× 0,55, suppose) ; sans elle, le combat est plus
    court (effet déterministe sur l'analytique) et le Monte Carlo change ; `True` vaut le défaut des données."""
    default = kill_analytic(game_data, 12, {})
    off = kill_analytic(game_data, 12, {}, low_level_penalty=False)
    assert off["combat"] < default["combat"]
    assert kill_analytic(game_data, 12, {}, low_level_penalty=True) == default
    assert mc(game_data, 12, {}, n=40, seed=2, low_level_penalty=False) != mc(game_data, 12, {}, n=40, seed=2)


def test_low_level_penalty_option_is_checked(game_data):
    assert options_with_defaults(game_data, "frost", {})["low_level_penalty"] is None
    with pytest.raises(ValueError, match="low_level_penalty"):
        options_with_defaults(game_data, "frost", {"rules": "seed", "low_level_penalty": False})
    with pytest.raises(ValueError, match="low_level_penalty"):
        options_with_defaults(game_data, "frost", {"low_level_penalty": "non"})
    assert options_with_defaults(game_data, "frost", {"rules": "seed", "low_level_penalty": True})["rules"] == "seed"


def test_ice_lance_damage_does_not_depend_on_spell_power(game_data):
    """Ice Lance au niveau 24 : coefficient du client nul (probable, test en jeu E4) : mêmes dégâts à 0 et à 100 de
    puissance des sorts en forever ; en seed (0,1429), les dégâts suivent la puissance."""
    from forever.engine import character, expected_cast

    pts = {"iceLance": 1}

    def lance(sp, **kw):
        ch = character(game_data, 24, "Orc", {"sp": sp})
        return expected_cast(game_data, "ice_lance", 24, pts, ch, frozen=True, **kw)["direct_per_hit"]

    assert lance(0) == lance(100)
    assert lance(0, rules="seed") < lance(100, rules="seed")
