"""Faisceaux du leveling calculés en parallèle (décision 230, point 2) : chaque départ (faisceau libre, un par arbre)
est indépendant et tiré avec sa graine ; calculés dans plusieurs processus, ils rendent exactement les mêmes chemins
qu'en séquentiel. Désactivé par défaut (un seul processus) : seul le rejeu de `forever update` l'active."""

import pytest

from forever.optimize import leveling


def test_parallel_beams_are_off_by_default():
    assert leveling.beam_workers() == 1


@pytest.mark.slow
def test_parallel_beams_give_the_sequential_paths(game_data):
    common = {
        "beam": 2,
        "depth": 1,
        "shortlist": 2,
        "mc_n": 20,
        "seed": 12345,
        "rules": "forever",
        "start": {},
        "over": None,
        "talented_bonus": 0,
    }
    sequential = leveling.leveling_paths(game_data, "Orc", 10, 13, **common)
    leveling.set_beam_workers(4)
    try:
        parallel = leveling.leveling_paths(game_data, "Orc", 10, 13, **common)
    finally:
        leveling.set_beam_workers(1)
    assert len(parallel) == len(sequential) > 1
    assert parallel == sequential
