"""Point de passage vers un palier (T06b, décision D7, `passage_palier`) : cas construits sur les données, sans
Monte Carlo. Un point ouvre un palier quand il porte les points de son arbre au seuil du palier
(`tier_points_required`) et que l'anticipation prend un talent modélisé de ce palier."""

from forever.engine.talents import tier_points_required
from forever.optimize.leveling import _opens_tier


def frost(game_data, tier):
    return [k for k, t in game_data.talents.items() if t.tree == "Frost" and t.tier == tier]


def test_point_that_reaches_the_tier_threshold_opens_it(game_data):
    need = tier_points_required(game_data, 2)
    tier1, tier2 = frost(game_data, 1), frost(game_data, 2)
    filler, key = tier1[0], tier1[1]
    pts = {filler: need - 1}
    target = tier2[0]
    assert _opens_tier(game_data, pts, key, (target,), frozenset({target}))


def test_no_opening_below_the_threshold_or_without_a_modeled_pick(game_data):
    need = tier_points_required(game_data, 2)
    tier1, tier2 = frost(game_data, 1), frost(game_data, 2)
    filler, key, target = tier1[0], tier1[1], tier2[0]
    assert not _opens_tier(game_data, {filler: need - 2}, key, (target,), frozenset({target}))  # seuil non atteint
    assert not _opens_tier(game_data, {filler: need - 1}, key, (target,), frozenset())  # palier sans modélisé pris
    assert not _opens_tier(game_data, {filler: need - 1}, key, (), frozenset({target}))  # anticipation vide
    other = next(k for k, t in game_data.talents.items() if t.tree == "Fire" and t.tier == 2)
    assert not _opens_tier(game_data, {filler: need - 1}, key, (other,), frozenset({other}))  # autre arbre
