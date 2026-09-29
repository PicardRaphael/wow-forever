"""Optimiseur de contexte (donjon, raid ; T05, bloc F ; décision 84) : builds légaux, optimum local de la recherche,
métrique d'un contexte à plusieurs scénarios (dégâts totaux / durée totale), déterminisme. Niveau 30 (21 points) et
préréglage rapide pour tenir le temps des tests ; niveau 60 (51 points) marqué lent."""

import pytest

from forever.engine.talents import check_build, points_available
from forever.optimize.endgame import context_analytic, context_mc, context_scenarios, neighbors, optimize_context
from forever.sim.encounter import ENCOUNTER_ROTATIONS, encounter_analytic, encounter_mc


def _run(gd, context, level, **kw):
    p = gd.build.presets["rapide"]
    return optimize_context(gd, context, level, "Orc", shortlist=p.shortlist, mc_n=p.mc_n, depth=p.depth, **kw)


@pytest.fixture(scope="module")
def raid30(game_data):
    return _run(game_data, "raid", 30)


def test_context_scenarios(game_data):
    assert context_scenarios(game_data, "dungeon") == ("dungeon_boss", "dungeon_pack")
    assert context_scenarios(game_data, "raid") == ("raid_boss",)
    with pytest.raises(ValueError, match="contexte inconnu"):
        context_scenarios(game_data, "arena")


def test_candidates_are_legal_and_ranked(game_data, raid30):
    assert len(raid30) >= 2
    for c in raid30:
        assert check_build(game_data, c.points, 30) == []
        assert sum(c.points.values()) == points_available(game_data, 30)
        assert set(c.choices) == {"raid_boss"}
        assert c.choices["raid_boss"].rotation in ENCOUNTER_ROTATIONS
    assert raid30[0].stats is not None and raid30[1].stats is not None
    assert len({tuple(sorted(c.points.items())) for c in raid30}) == len(raid30)


def test_every_candidate_is_a_local_optimum(game_data, raid30):
    for c in raid30:
        for n in neighbors(game_data, c.points, 30):
            assert context_analytic(game_data, "raid", 30, n)[0] <= c.analytic + 1e-9


def test_neighbors_move_one_point_and_stay_legal(game_data, raid30):
    pts = raid30[0].points
    ns = neighbors(game_data, pts, 30)
    assert ns
    for n in ns:
        assert sum(n.values()) == sum(pts.values())
        assert check_build(game_data, n, 30) == []
        moved = sum(abs(n.get(k, 0) - pts.get(k, 0)) for k in set(n) | set(pts))
        assert moved == 2
    assert ns == neighbors(game_data, pts, 30)


def test_optimizer_is_deterministic(game_data, raid30):
    assert _run(game_data, "raid", 30) == raid30


def test_single_scenario_context_is_the_scenario(game_data, raid30):
    c = raid30[0]
    choice = c.choices["raid_boss"]
    a = encounter_analytic(game_data, "raid_boss", 30, c.points, "Orc", choice.rotation, **choice.options())
    assert context_analytic(game_data, "raid", 30, c.points)[0] == pytest.approx(a["dps"], rel=1e-12)
    m = context_mc(game_data, "raid", 30, c.points, c.choices, "Orc", 30, seed=3)
    e = encounter_mc(game_data, "raid_boss", 30, c.points, "Orc", choice.rotation, 30, seed=3, **choice.options())
    assert m == e


def test_dungeon_combines_boss_and_pack(game_data):
    pts = {"improvedFrostbolt": 5, "elementalPrecision": 3, "iceShards": 5, "frostbite": 3, "iceLance": 1}
    value, choices = context_analytic(game_data, "dungeon", 30, pts)
    assert set(choices) == {"dungeon_boss", "dungeon_pack"}
    parts = [
        encounter_analytic(game_data, s, 30, pts, "Orc", choices[s].rotation, **choices[s].options())
        for s in ("dungeon_boss", "dungeon_pack")
    ]
    assert value == pytest.approx(sum(p["dmg"] for p in parts) / sum(p["duration_s"] for p in parts), rel=1e-12)
    m = context_mc(game_data, "dungeon", 30, pts, choices, "Orc", 10, seed=2)
    assert m.n == 10 and len(m.totals) == 10 and m.mean > 0


@pytest.mark.slow
def test_level_60_raid_build_is_legal(game_data):
    best = _run(game_data, "raid", 60)[0]
    assert check_build(game_data, best.points, 60) == []
    assert sum(best.points.values()) == points_available(game_data, 60) == 51
