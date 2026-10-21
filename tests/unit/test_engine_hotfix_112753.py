"""Correctif du serveur 112753 de 1.60.1.70450 (2026-10-20, lu dans un cache vérifié de Raidbots, décision 290) :
Missile Barrage perd sa chance par projectile d'Arcane Missiles et nomme ses sorts (Arcane Wrath, Fireball,
Frostbolt, Frost Blast, Frostfire Bolt), variables de nouveau dans l'ordre d'avant 70450 (Arcane Blast, autres sorts,
canalisation, coût, rythme). Marqueur `listed_spells` tiré de la description du client ; sans lui, jamais le sens
« projectiles » sur des variables décalées.

Rangs fabriqués ici (même forme que le client) ; aucun chiffre de jeu."""

from dataclasses import replace

import pytest

from forever.engine.buffs import missile_barrage_buffs, missile_barrage_chance
from forever.engine.model import Talent
from forever.pipeline.decode import talent_model

ROWS = ((20, 10, 50, 100, 0.5), (40, 20, 50, 100, 0.5))  # AB, autres sorts, canalisation, coût, rythme (fabriqués)
TEXT = (
    "Gives your Arcane Blast spell a $m1% chance, and your Arcane Wrath, Fireball, Frostbolt, Frost Blast, and "
    "Frostfire Bolt spells a ${$m1/2}% chance to reduce the channeled duration of your next Arcane Missiles spell"
)
RULES = {
    "missileBarrage": [
        {"contains": "Arcane Missile hits", "model": "missile_hits"},
        {"contains": "Frost Blast, and Frostfire Bolt", "model": "listed_spells"},
    ]
}


def hotfixed(gd):
    mb = Talent("missileBarrage", "Missile Barrage", "Arcane", 1, 1, 2, ROWS, None, model="listed_spells")
    return replace(gd, talents={**gd.talents, "missileBarrage": mb})


def test_model_read_from_the_hotfixed_description():
    assert talent_model(RULES, "missileBarrage", TEXT) == "listed_spells"


def test_listed_spells_trigger_and_missiles_do_not(game_data):
    gd, pts = hotfixed(game_data), {"missileBarrage": 2}
    assert missile_barrage_chance(gd, pts, "arcane_blast") == pytest.approx(ROWS[1][0] / 100)
    for key in ("arcane_wrath", "fireball", "frostbolt", "frost_blast", "frostfire_bolt"):
        assert missile_barrage_chance(gd, pts, key) == pytest.approx(ROWS[1][1] / 100), key
    assert missile_barrage_chance(gd, pts, "arcane_missiles", missiles=5) == 0.0
    assert missile_barrage_chance(gd, pts, "scorch") == 0.0
    assert missile_barrage_buffs(gd, pts) == {
        "cast_reduction": pytest.approx(ROWS[1][2] / 100),
        "cost": pytest.approx(-ROWS[1][3] / 100),
    }
