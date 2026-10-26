"""Statistiques du Monte Carlo et décision entre builds (T05, bloc D ; décision 85).

`mc_stats` rejoue exactement les combats de `mc()` (même graine) et en donne la dispersion ; `paired_gap` compare
deux builds combat par combat ; `decide` retient le gagnant si l'intervalle exclut 0, sinon l'analytique départage ;
`stability` rejoue la décision sur plusieurs graines. Écart de référence : Improved Frostbolt 5/5 contre 0/5 au
niveau 20 (Givre), mesuré avant ce test à ~28 erreurs standard de la moyenne sur les graines 1 à 5 (n = 400)."""

import math

import pytest

from forever.sim.leveling_mc import McStats, mc, mc_stats

IF0, IF5 = {}, {"improvedFrostbolt": 5}


def test_mc_stats_matches_mc(game_data):
    s = mc_stats(game_data, 16, IF5, "Orc", "frost", 120, seed=9)
    assert s.mean == mc(game_data, 16, IF5, "Orc", "frost", 120, seed=9)["total"]
    assert s.n == 120 and len(s.totals) == 120
    assert s.se == pytest.approx(s.sd / math.sqrt(120), rel=1e-12)
    assert s.sd > 0


def test_mc_stats_needs_two_fights(game_data):
    with pytest.raises(ValueError, match="n"):
        mc_stats(game_data, 16, IF5, "Orc", "frost", 1)


def test_mc_stats_follows_options(game_data):
    seed_mode = {"mob_source": "seed", "spell_level": "rank", "rules": "seed"}
    s = mc_stats(game_data, 16, IF5, "Orc", "frost", 50, seed=3, **seed_mode)
    assert s.mean == mc(game_data, 16, IF5, "Orc", "frost", 50, seed=3, **seed_mode)["total"]


def _stats(values):
    n = len(values)
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    return McStats(mean, sd, sd / math.sqrt(n), n, tuple(values))
