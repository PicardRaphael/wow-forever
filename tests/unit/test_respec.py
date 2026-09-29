"""Conseil de respec en mode forever (T05, bloc H ; décision 87) : coût et sa certitude, bilan en or, niveau conseillé,
verdict. Barème lu dans `respec.json`, or par heure et trajet dans `mechanics.json` (`respec.*`, suppose)."""

import pytest

from forever.engine.respec import gold_per_hour, respec_balance, respec_cost, respec_cost_certainty
from forever.optimize.leveling import LevelingPath
from forever.optimize.respec import advise_respec

# Build de niveau 30 sans aucun talent lu par les simulateurs (légal : paliers 1 à 4 des Arcanes).
USELESS_30 = {
    "wandSpecialization": 2,
    "improvedChanneling": 5,
    "arcaneSubtlety": 2,
    "magicAbsorption": 2,
    "arcaneResilience": 2,
    "arcaneGeometry": 2,
    "arcaneShielding": 2,
    "improvedCounterspell": 2,
    "arcaneFocus": 2,
}


def test_cost_certainty(game_data):
    observed = game_data.respec.beta_observed_resets
    assert [respec_cost_certainty(game_data, i) for i in range(observed + 2)] == ["probable"] * observed + [
        "suppose"
    ] * 2


def test_balance_formula():
    assert respec_balance(2.0, 5.0, 9.0, 6.0) == pytest.approx(2.0 * 9.0 - 5.0 - 6.0 / 60 * 9.0, rel=1e-12)
    assert respec_balance(0.0, 1.0, 4.0, 6.0) < 0


@pytest.fixture(scope="module")
def bad(game_data):
    return advise_respec(game_data, 30, USELESS_30, 40, "Orc", preset=game_data.build.presets["rapide"])


def test_useless_build_is_reset(game_data, bad):
    assert sum(USELESS_30.values()) == 21
    assert bad.verdict == "réinitialiser"
    assert bad.level is not None and 30 <= bad.level <= 40
    assert bad.balance_gold > 0 and bad.gain_hours > 0
    assert bad.cost_gold == respec_cost(game_data, 0) and bad.cost_certainty == "probable"
    assert isinstance(bad.keep, LevelingPath) and isinstance(bad.free, LevelingPath)


def test_advised_level_is_the_best_balance(game_data, bad):
    levels = [row[0] for row in bad.by_level]
    assert levels == list(range(30, 41))
    for level, gain, balance in bad.by_level:
        gph = gold_per_hour(game_data, level)
        assert balance == pytest.approx(
            respec_balance(gain, bad.cost_gold, gph, game_data.respec.trip_minutes), rel=1e-12
        )
    best = max(bad.by_level, key=lambda r: (r[2], -r[0]))
    assert (bad.level, bad.gain_hours, bad.balance_gold) == best
    assert bad.gold_per_hour == gold_per_hour(game_data, bad.level)


def test_optimal_build_is_kept(game_data, bad):
    """Le build du chemin libre au niveau actuel : rien à gagner (moins que le coût et le trajet)."""
    pts: dict[str, int] = {}
    for s in bad.free.steps:
        if s.level > 30:
            break
        if s.talent:
            pts[s.talent] = pts.get(s.talent, 0) + 1
    good = advise_respec(game_data, 30, pts, 40, "Orc", preset=game_data.build.presets["rapide"])
    assert good.verdict == "garder" and good.level is None
    assert good.balance_gold <= 0


def test_more_resets_cost_more(game_data):
    a = advise_respec(game_data, 30, USELESS_30, 32, "Orc", preset=game_data.build.presets["rapide"], n_previous=5)
    assert a.cost_gold == respec_cost(game_data, 5) and a.cost_certainty == "suppose"


def test_illegal_current_build_is_refused(game_data):
    with pytest.raises(ValueError, match="illégal"):
        advise_respec(game_data, 30, {"iceLance": 1}, 35, "Orc", preset=game_data.build.presets["rapide"])
