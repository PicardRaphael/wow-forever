"""1.60.1.70450, bloc B : Fire Power et Heating Up refondus (note du 15 octobre, tables du client).

- Fire Power (marqueur `per_fire_effect`) : +x % de dégâts de Feu par effet de Feu du Mage sur la cible, au plus le
  plafond du client (deuxième variable) ; les sorts de deux écoles (Frostfire Bolt) en profitent sans en donner.
  Nombre d'effets : celui que suit le simulateur (buff `fire_effects`) ; sans lui (calcul analytique), le nombre moyen
  de la rotation en régime établi (DoT de Fireball, Ignite selon le critique), `suppose`. Sans marqueur : ancien sens
  (bonus plat).
- Heating Up (règle du serveur de la note, `mechanics.json`) : Fire Blast donne toujours une charge de plus, deux sur
  un critique.

Talents fabriqués ici (variables à la forme de celles du client) ; aucun chiffre de jeu."""

import pytest

from forever.engine.buffs import hot_streak_gain
from forever.engine.damage import dmg_mult, fire_effects_steady
from forever.engine.model import Talent

FP_ROWS = ((1, 4), (2, 8), (3, 12))  # % par effet, plafond (fabriqués à la forme du client)


def with_fire_power(gd):
    from dataclasses import replace

    fp = Talent("firePower", "Fire Power", "Fire", 6, 1, 3, FP_ROWS, None, model="per_fire_effect")
    return replace(gd, talents={**gd.talents, "firePower": fp})


def test_bonus_per_fire_effect_up_to_the_cap(game_data):
    gd, pts = with_fire_power(game_data), {"firePower": 3}
    base = dmg_mult(game_data, "fire", {}, None, key="fireball")
    assert dmg_mult(gd, "fire", pts, {"fire_effects": 2}, key="fireball") == pytest.approx(base * 1.06)
    assert dmg_mult(gd, "fire", pts, {"fire_effects": 9}, key="fireball") == pytest.approx(base * 1.12)  # plafond
    assert dmg_mult(gd, "frostfire", pts, {"fire_effects": 2}, key="frostfire_bolt") > dmg_mult(
        gd, "frostfire", {}, {"fire_effects": 2}, key="frostfire_bolt"
    )  # deux écoles : en profite
    assert dmg_mult(gd, "frost", pts, {"fire_effects": 2}, key="frostbolt") == pytest.approx(
        dmg_mult(game_data, "frost", {}, None, key="frostbolt")
    )


def test_steady_count_grows_with_crit_and_ignite(game_data):
    low = fire_effects_steady(game_data, {"ignite": 5}, crit=0.05)
    high = fire_effects_steady(game_data, {"ignite": 5}, crit=0.30)
    without = fire_effects_steady(game_data, {}, crit=0.30)
    assert high > low > without >= 1.0  # DoT de Fireball, puis Ignite


def test_old_meaning_without_the_marker(game_data):
    pts = {"firePower": 2}
    base = dmg_mult(game_data, "fire", {}, None, key="fireball")
    assert dmg_mult(game_data, "fire", pts, {"fire_effects": 3}, key="fireball") == pytest.approx(
        dmg_mult(game_data, "fire", pts, None, key="fireball")
    )
    assert dmg_mult(game_data, "fire", pts, None, key="fireball") > base


def test_heating_up_fire_blast_extra_charge(game_data):
    from dataclasses import replace

    gd = replace(game_data, constants=replace(game_data.constants, hot_streak_fire_blast_extra=1))
    assert hot_streak_gain(gd, "fire_blast", crit=False) == 1
    assert hot_streak_gain(gd, "fire_blast", crit=True) == 2
    assert hot_streak_gain(gd, "fireball", crit=True) == 1 and hot_streak_gain(gd, "fireball", crit=False) == 0
    assert hot_streak_gain(game_data, "fire_blast", crit=False) == 0  # sans la règle : ancien sens
