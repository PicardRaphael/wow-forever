"""1.60.1.70450, bloc B, socle (`tasks/70450-plan.md`, décision 285) :

- raciaux du Mage lus par leur sort : Ruthless et Savage au critique avec toute arme, Wind Blessed à la hâte, Eureka!
  (racial à activer : coût réduit et dégâts en plus pendant sa durée, toutes les recharges) compté en temps d'effet
  moyen (durée / recharge, `suppose`) ;
- marqueur de modèle d'un talent (`talents.json`) lu par le moteur ; absent : ancien sens ;
- Winter's Chill selon la sorte de son aura : critique avant 70450, plus de critique quand l'aura renforce Cone of Cold ;
- coups directs des simulations Monte Carlo : la puissance des sorts des buffs comptée (Arcane Blast et Arcane Wrath de
  70450 en donnent).

Données installées pour le reste ; raciaux et auras fabriqués ici. Aucun chiffre de jeu ici."""

from dataclasses import replace

import pytest

from forever.engine import character, expected_cast
from forever.engine.damage import roll_base_damage
from forever.engine.mana import mana_cost
from forever.engine.model import Racials
from forever.engine.spells import best_rank
from forever.engine.talents import talent_model
from forever.gamedata import _client_mechanics, _talents

L = 60
EUREKA = {"dmg": 0.1, "cost": -0.1, "duration": 8.0, "cooldown": 120.0}  # valeurs fabriquées


def with_racials(gd, **tables):
    base = {"sword_crit": {}, "spirit_pct": {}, "mana_pct": {}}
    return replace(gd, racials=Racials(**{**base, **tables}))


def test_ruthless_and_savage_count_with_any_weapon(game_data):
    gd = with_racials(game_data, crit={"Human": 0.02, "Orc": 0.01})
    plain = character(game_data, L, "Gnome").crit
    assert character(gd, L, "Human").crit == pytest.approx(plain + 0.02)
    assert character(gd, L, "Orc").crit == pytest.approx(character(game_data, L, "Orc").crit + 0.01)


def test_wind_blessed_haste(game_data):
    gd = with_racials(game_data, haste={"High Order Skyborne": 0.03})
    assert character(gd, L, "High Order Skyborne").haste == pytest.approx(0.03)
    assert character(gd, L, "High Order Skyborne", {"haste": 0.02}).haste == pytest.approx(0.05)


def test_eureka_average_uptime(game_data):
    gd = with_racials(
        game_data,
        eureka_dmg={"Gnome": EUREKA["dmg"]},
        eureka_cost={"Gnome": EUREKA["cost"]},
        eureka_duration_s={"Gnome": EUREKA["duration"]},
        eureka_cooldown_s={"Gnome": EUREKA["cooldown"]},
    )
    uptime = EUREKA["duration"] / EUREKA["cooldown"]
    ch_g, ch_o = character(gd, L, "Gnome", {"sp": 500}), character(gd, L, "Orc", {"sp": 500})
    assert ch_g.racial_dmg == pytest.approx(EUREKA["dmg"] * uptime) and ch_o.racial_dmg == 0
    gnome = expected_cast(gd, "frostbolt", L, {}, replace(ch_g, crit=ch_o.crit))
    orc = expected_cast(gd, "frostbolt", L, {}, ch_o)
    assert gnome["dmg_mult"] == pytest.approx(orc["dmg_mult"] * (1 + EUREKA["dmg"] * uptime))
    rank = best_rank(gd, "frostbolt", L, {})
    assert mana_cost(gd, "frostbolt", rank, {}, ch_g) == pytest.approx(
        mana_cost(gd, "frostbolt", rank, {}, ch_o) * (1 + EUREKA["cost"] * uptime)
    )


def test_talent_model_marker(game_data):
    raw = {"trees": [{"name": "Arcane", "talents": [
        {"key": "arcaneBlast", "name": "Arcane Blast", "tree": "Arcane", "tier": 3, "col": 1, "max": 1,
         "ranks": [[1, 2]], "model": "intellect_spell_power"},
        {"key": "arcaneFocus", "name": "Arcane Focus", "tree": "Arcane", "tier": 1, "col": 2, "max": 1,
         "ranks": [[1]]},
    ]}]}  # fmt: skip
    talents, _ = _talents(raw)
    gd = replace(game_data, talents=talents)
    assert talent_model(gd, "arcaneBlast") == "intellect_spell_power"
    assert talent_model(gd, "arcaneFocus") is None and talent_model(gd, "absent") is None


def test_winters_chill_crit_only_with_the_crit_aura(game_data):
    lv = game_data.leveling
    crit = {"auras": {"winters_chill": {"pct_per_stack": 2, "max_stacks": 5, "duration_ms": 15000}}}
    cone = {"auras": {"winters_chill": {"pct_per_stack": 40, "max_stacks": 5, "duration_ms": 15000,
                                        "kind": "cone_of_cold"}}}  # fmt: skip
    c1, _ = _client_mechanics(crit, game_data.constants, lv)
    c2, _ = _client_mechanics(cone, game_data.constants, lv)
    assert c1.crit_per_winters_chill_stack == pytest.approx(0.02) and c1.cone_of_cold_per_winters_chill_stack == 0
    assert c2.crit_per_winters_chill_stack == 0 and c2.cone_of_cold_per_winters_chill_stack == pytest.approx(0.40)


def test_monte_carlo_direct_hit_counts_spell_power_buffs(game_data):
    ch = character(game_data, L, "Orc", {"sp": 500})
    rank = best_rank(game_data, "frostbolt", L, {})
    plain = roll_base_damage(game_data, "frostbolt", rank, ch, 0.5)
    buffed = roll_base_damage(game_data, "frostbolt", rank, ch, 0.5, buffs={"sp_flat": 100.0})
    assert buffed > plain
