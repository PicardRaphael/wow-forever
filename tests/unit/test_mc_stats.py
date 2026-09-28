"""Statistiques du Monte Carlo et décision entre builds (T05, bloc D ; décision 85).

`mc_stats` rejoue exactement les combats de `mc()` (même graine) et en donne la dispersion ; `paired_gap` compare
deux builds combat par combat ; `decide` retient le gagnant si l'intervalle exclut 0, sinon l'analytique départage ;
`stability` rejoue la décision sur plusieurs graines. Écart de référence : Improved Frostbolt 5/5 contre 0/5 au
niveau 20 (Givre), mesuré avant ce test à ~28 erreurs standard de la moyenne sur les graines 1 à 5 (n = 400)."""

import math

import pytest

from forever.optimize.decide import decide, paired_gap, stability
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


def test_identical_builds_have_no_gap(game_data):
    a = mc_stats(game_data, 20, IF5, "Orc", "frost", 80, seed=1)
    g = paired_gap(a, a, 0.95)
    assert (g.mean, g.low, g.high, g.significant) == (0.0, 0.0, 0.0, False)
    # talent que le simulateur ne lit pas : mêmes combats, aucun écart
    b = mc_stats(game_data, 20, {**IF5, "frostWarding": 2}, "Orc", "frost", 80, seed=1)
    assert paired_gap(a, b, 0.95).significant is False


def test_known_gap_is_significant_on_five_seeds(game_data):
    for seed in range(1, 6):
        a = mc_stats(game_data, 20, IF0, "Orc", "frost", 400, seed=seed)
        b = mc_stats(game_data, 20, IF5, "Orc", "frost", 400, seed=seed)
        g = paired_gap(a, b, 0.95)
        assert g.significant and g.low > 0, (seed, g)
        assert g.mean == pytest.approx(a.mean - b.mean, rel=1e-9)
        assert g.low < g.mean < g.high
        back = paired_gap(b, a, 0.95)
        assert (back.mean, back.low, back.high) == pytest.approx((-g.mean, -g.high, -g.low), rel=1e-12)


def test_interval_width_follows_confidence(game_data):
    a = mc_stats(game_data, 20, IF0, "Orc", "frost", 100, seed=2)
    b = mc_stats(game_data, 20, IF5, "Orc", "frost", 100, seed=2)
    narrow, wide = paired_gap(a, b, 0.80), paired_gap(a, b, 0.99)
    assert wide.high - wide.low > narrow.high - narrow.low
    assert narrow.mean == wide.mean
    assert (narrow.confidence, wide.confidence) == (0.80, 0.99)


def test_gap_needs_the_same_number_of_fights(game_data):
    a = mc_stats(game_data, 20, IF0, "Orc", "frost", 10, seed=2)
    b = mc_stats(game_data, 20, IF5, "Orc", "frost", 12, seed=2)
    with pytest.raises(ValueError, match="combats"):
        paired_gap(a, b, 0.95)


def _stats(values):
    n = len(values)
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    return McStats(mean, sd, sd / math.sqrt(n), n, tuple(values))


def test_decide_takes_the_monte_carlo_winner_when_the_gap_is_significant():
    table = {"a": _stats([10.0, 11.0, 12.0, 10.5]), "b": _stats([20.0, 21.0, 19.0, 20.5])}
    d = decide(
        ["a", "b"],
        lambda c, s: table[c],
        lambda c: {"a": 2.0, "b": 1.0}[c],
        seed=1,
        confidence=0.95,
        lower_is_better=True,
    )
    assert (d.winner, d.runner_up, d.decided_by) == ("a", "b", "monte_carlo")
    assert d.gap.significant and d.gap.mean < 0  # gagnant - second : temps plus court
    up = decide(["a", "b"], lambda c, s: table[c], lambda c: 0.0, seed=1, confidence=0.95, lower_is_better=False)
    assert up.winner == "b"  # dégâts : plus grand vaut mieux


def test_decide_falls_back_on_the_analytic_model_on_a_tie():
    table = {"a": _stats([10.0, 12.0, 11.0, 13.0]), "b": _stats([10.2, 11.9, 11.1, 12.9])}
    d = decide(
        ["a", "b"],
        lambda c, s: table[c],
        lambda c: {"a": 5.0, "b": 4.0}[c],
        seed=1,
        confidence=0.95,
        lower_is_better=True,
    )
    assert d.decided_by == "analytique" and not d.gap.significant
    assert d.winner == "b"  # meilleure analytique (temps plus court)


def test_stability_over_seeds():
    good = {"a": _stats([10.0, 11.0, 12.0, 10.5]), "b": _stats([20.0, 21.0, 19.0, 20.5])}
    s = stability(["a", "b"], lambda c, seed: good[c], lambda c: 0.0, [1, 2, 3], confidence=0.95, lower_is_better=True)
    assert s.stable and s.winners == ("a", "a", "a") and s.seeds == (1, 2, 3)
    flip = {1: good, 2: {"a": good["b"], "b": good["a"]}}
    s2 = stability(
        ["a", "b"], lambda c, seed: flip[seed][c], lambda c: 0.0, [1, 2], confidence=0.95, lower_is_better=True
    )
    assert not s2.stable and s2.winners == ("a", "b")


def test_decide_needs_two_finalists():
    with pytest.raises(ValueError, match="finalistes"):
        decide(["a"], lambda c, s: _stats([1.0, 2.0]), lambda c: 0.0, seed=1, confidence=0.95, lower_is_better=True)
