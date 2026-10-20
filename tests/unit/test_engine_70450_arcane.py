"""1.60.1.70450, bloc B : la rotation des Arcanes refondue (note du 15 octobre, tables du client).

- Arcane Blast (marqueur `intellect_spell_power`) : chaque cumul donne une part de l'Intelligence en puissance des
  sorts à **tous** les sorts, Arcane Blast compris ; l'aura dure depuis sa **première** application (jamais relancée)
  et n'est plus consommée par les autres sorts ; le coût monte toujours par cumul. Sans marqueur : l'ancien sens.
- Missile Barrage (marqueur `missile_hits`) : chance sur Arcane Blast, sur **chaque projectile** d'Arcane Missiles,
  sur Arcane Wrath, Fireball, Frostbolt et Frostfire Bolt ; canalisation raccourcie et coût réduit (positions du
  client).
- Arcane Wrath : puissance des sorts en plus égale à une part du mana maximum, sur lui seul.
- Cycle analytique : Arcane Blast jusqu'à `ab_stacks`, puis la décharge jusqu'à la fin de l'aura.

Talents et sorts fabriqués ici (variables à la forme de celles du client) ; aucun chiffre de jeu."""

import random
from dataclasses import replace

import pytest

from forever.engine import character
from forever.engine.buffs import (
    ArcaneBlastAura,
    arcane_blast_after_cast,
    arcane_blast_after_spell,
    arcane_blast_bonus,
    arcane_wrath_bonus,
    missile_barrage_buffs,
    missile_barrage_chance,
)
from forever.engine.model import Talent
from forever.sim.leveling_analytic import arcane_cycle
from forever.sim.leveling_mc import kill_mc

L = 40
AB_ROW = (30, 34, 15, 175, 4, 15)  # min, max, % d'Intelligence par cumul, hausse du coût, cumuls, durée (fabriqués)
MB_ROWS = ((20, 5, 10, 50, 100, 0.5), (40, 10, 20, 50, 100, 0.5))  # AB, projectile, autres, canalisation, coût, rythme
AW_ROW = (108, 132, 5)  # min, max, % du mana maximum en puissance des sorts


def talent(key, tree, tier, rows, model=None):
    return Talent(key, key, tree, tier, 1, len(rows), tuple(rows), None, model=model)


def redesigned(gd):
    talents = {
        **gd.talents,
        "arcaneBlast": talent("arcaneBlast", "Arcane", 3, [AB_ROW], "intellect_spell_power"),
        "missileBarrage": talent("missileBarrage", "Arcane", 1, MB_ROWS, "missile_hits"),
        "arcaneWrath": talent("arcaneWrath", "Arcane", 4, [AW_ROW]),
    }
    fb = gd.spells["fireball"]
    wrath = replace(fb, key="arcane_wrath", school="arcane", talent="arcaneWrath",
                    ranks=(fb.ranks[3]._replace(position=1, level=1, cast_time_s=3.5, cooldown_s=6.0),))  # fmt: skip
    return replace(
        gd,
        talents=talents,
        spells={**gd.spells, "arcane_wrath": wrath},
        scaling={**gd.scaling, "arcane_wrath": (gd.scaling["fireball"][3],)},
    )


def test_aura_keeps_its_first_timer_and_is_not_consumed(game_data):
    gd, pts = redesigned(game_data), {"arcaneBlast": 1}
    aura = arcane_blast_after_cast(gd, pts, None, 0.0)
    assert aura == ArcaneBlastAura(1, AB_ROW[5])
    aura = arcane_blast_after_cast(gd, pts, aura, 3.0)
    assert aura == ArcaneBlastAura(2, AB_ROW[5])  # durée depuis la première application
    assert arcane_blast_after_spell(gd, pts, aura, 4.0, "arcane_missiles") == aura  # jamais consommée
    assert arcane_blast_after_cast(gd, pts, aura, AB_ROW[5] + 1).stacks == 1  # expirée : nouvelle aura


def test_bonus_is_spell_power_for_every_spell(game_data):
    gd, pts = redesigned(game_data), {"arcaneBlast": 1}
    ch = character(gd, L, "Orc")
    want = 2 * AB_ROW[2] / 100 * ch.intellect
    assert arcane_blast_bonus(gd, pts, 2, for_spell="arcane_blast", ch=ch) == {"sp_flat": pytest.approx(want)}
    assert arcane_blast_bonus(gd, pts, 2, for_spell="frostbolt", ch=ch) == {"sp_flat": pytest.approx(want)}


def test_old_meaning_without_the_marker(game_data):
    pts = {"arcaneBlast": 1}
    aura = arcane_blast_after_cast(game_data, pts, None, 0.0)
    assert arcane_blast_after_spell(game_data, pts, aura, 1.0, "frostbolt") is None  # consommée
    assert "dmg" in arcane_blast_bonus(game_data, pts, 1, for_spell="frostbolt")


def test_missile_barrage_per_missile(game_data):
    gd = redesigned(game_data)
    pts = {"missileBarrage": 2}
    assert missile_barrage_chance(gd, pts, "arcane_blast") == pytest.approx(MB_ROWS[1][0] / 100)
    assert missile_barrage_chance(gd, pts, "arcane_wrath") == pytest.approx(MB_ROWS[1][2] / 100)
    assert missile_barrage_chance(gd, pts, "fireball") == pytest.approx(MB_ROWS[1][2] / 100)
    per_missile = MB_ROWS[1][1] / 100
    assert missile_barrage_chance(gd, pts, "arcane_missiles", missiles=5) == pytest.approx(1 - (1 - per_missile) ** 5)
    assert missile_barrage_buffs(gd, pts) == {
        "cast_reduction": pytest.approx(MB_ROWS[1][3] / 100),
        "cost": pytest.approx(-MB_ROWS[1][4] / 100),
    }


def test_arcane_wrath_spell_power_from_max_mana(game_data):
    gd = redesigned(game_data)
    ch = character(gd, L, "Orc")
    assert arcane_wrath_bonus(gd, {"arcaneWrath": 1}, ch) == {"sp_flat": pytest.approx(ch.mana * AW_ROW[2] / 100)}
    assert arcane_wrath_bonus(gd, {}, ch) == {}


def test_cycle_lasts_the_aura_and_stacks_pay_off(game_data):
    gd, pts = redesigned(game_data), {"arcaneBlast": 1}
    ch = character(gd, L, "Orc", {"sp": 200})
    full = arcane_cycle(gd, L, pts, ch, ab_stacks=4, ab_dump="frostbolt")
    none = arcane_cycle(gd, L, pts, ch, ab_stacks=0, ab_dump="frostbolt")
    assert full["time_s"] == pytest.approx(AB_ROW[5], rel=0.15)  # cycle de la durée de l'aura
    assert full["casts"] > full["ab_casts"] + 1  # plusieurs décharges sous l'aura
    assert full["dmg"] / full["time_s"] > none["dmg"] / none["time_s"]


def test_arcane_rotation_with_wrath_simulates(game_data):
    gd = redesigned(game_data)
    pts = {"arcaneBlast": 1, "missileBarrage": 2, "arcaneWrath": 1}
    result = kill_mc(gd, L, pts, character(gd, L, "Orc"), "arcane", random.Random(3), ab_dump="arcane_missiles")
    assert result["total"] > 0
