"""1.60.1.70450, bloc B : Frost Blast (note du 15 octobre : appris au niveau 24, 1,5 s, ralentit, « profite de tous
les talents de Frostbolt »). Le moteur lui applique les talents de Frostbolt (Improved Frostbolt, Permafrost, Arctic
Reach, Frostbite, Fingers of Frost, Winter's Chill) avec son propre ralentissement ; en leveling il est **proposé**
comme rotation (sort principal) dès qu'il est appris, comparé par le simulateur, jamais imposé.

Frost Blast fabriqué ici à partir de Frostbolt dans les données installées (niveau, incantation, ralentissement
fabriqués) ; aucun chiffre de jeu."""

import random
from dataclasses import replace

import pytest

from forever.engine import character
from forever.engine.casting import cast_time
from forever.engine.movement import chill_duration, frostbolt_slow
from forever.engine.spells import FROSTBOLT_LIKE, best_rank
from forever.optimize.leveling import build_choices
from forever.sim.leveling_mc import kill_mc

LEARNED = 24  # niveau d'apprentissage fabriqué
SLOW = 0.5  # ralentissement fabriqué, différent de celui de Frostbolt


def with_frost_blast(gd):
    fb = gd.spells["frostbolt"]
    rank = replace(fb.ranks[3], position=1, level=LEARNED, cast_time_s=2.5)  # au-dessus du temps de recharge global
    blast = replace(fb, key="frost_blast", ranks=(rank,), slow=SLOW, slow_dur=(fb.slow_dur or (5,))[:1])
    scaling = (gd.scaling["frostbolt"][3],)
    return replace(gd, spells={**gd.spells, "frost_blast": blast}, scaling={**gd.scaling, "frost_blast": scaling})


def test_frost_blast_takes_the_frostbolt_talents(game_data):
    gd = with_frost_blast(game_data)
    assert "frost_blast" in FROSTBOLT_LIKE
    ch = character(gd, 40, "Orc")
    rank = best_rank(gd, "frost_blast", 40, {})
    plain = cast_time(gd, "frost_blast", rank, {}, ch)
    talented = cast_time(gd, "frost_blast", rank, {"improvedFrostbolt": 5}, ch)
    assert talented < plain


def test_frost_blast_has_its_own_slow(game_data):
    gd = with_frost_blast(game_data)
    assert frostbolt_slow(gd, {}, "frost_blast") == pytest.approx(SLOW)
    assert frostbolt_slow(gd, {}) == pytest.approx(gd.spells["frostbolt"].slow)
    rank = best_rank(gd, "frost_blast", 40, {})
    assert chill_duration(gd, rank, {}, "frost_blast") > 0


def test_frost_blast_is_offered_once_learned(game_data):
    gd = with_frost_blast(game_data)
    before = {c.rotation for c in build_choices(gd, LEARNED - 1, {})}
    after = {c.rotation for c in build_choices(gd, LEARNED, {})}
    assert "frost_blast" not in before and "frost_blast" in after and "frost" in after  # comparé, jamais imposé


def test_frost_blast_rotation_simulates(game_data):
    gd = with_frost_blast(game_data)
    result = kill_mc(gd, 30, {}, character(gd, 30, "Orc"), "frost_blast", random.Random(1))
    assert result["total"] > 0
