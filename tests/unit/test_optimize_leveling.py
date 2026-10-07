"""Optimiseur de leveling en mode forever (T05, bloc F ; décision 84) : ordre légal à chaque niveau, choix du build
(rotation, armure, `ab_stacks`, `ab_dump`, `hs_stacks`) cherchés avec les talents, bonus Legacy « Talented »,
build de départ, déterminisme. Préréglages lus dans `mechanics.json` (`build.presets`)."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.armor import worn_armor
from forever.engine.buffs import arcane_blast_max_stacks, hot_streak_rules
from forever.engine.talents import check_build, points_available
from forever.optimize.leveling import BuildChoice, best_choice, build_choices, level_weight, optimize_leveling
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import AB_DUMPS, ROTATIONS

ARC40 = {
    "arcaneFocus": 5,
    "improvedChanneling": 1,
    "arcaneConcentration": 5,
    "arcaneSubtlety": 2,
    "arcaneImpact": 3,
    "arcaneBlast": 1,
    "arcaneGeometry": 1,
    "arcaneMeditation": 3,
    "missileBarrage": 1,
    "presenceOfMind": 1,
    "arcaneMind": 4,
    "arcaneInstability": 3,
    "arcanePower": 1,
}
FIRE25 = {"improvedFireball": 5, "wakeOfFire": 2, "ignite": 5, "flameThrowing": 2, "pyroblast": 1, "hotStreak": 1}


def _run(gd, lfrom=10, lto=20, **kw):
    p = gd.build.presets["rapide"]
    return optimize_leveling(
        gd, "Orc", lfrom, lto, beam=p.beam, depth=p.depth, shortlist=p.shortlist, mc_n=p.mc_n, **kw
    )


@pytest.fixture(scope="module")
def path(game_data):
    return _run(game_data)


def _points_by_level(path, start=None):
    pts = dict(start or {})
    for s in path.steps:
        if s.talent:
            pts[s.talent] = pts.get(s.talent, 0) + 1
        yield s, dict(pts)


def test_presets_come_from_the_data(game_data):
    entry = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["build.presets"]
    assert entry["certainty"] == "certain" and entry["registry"] == "I5"
    fast, full = game_data.build.presets["rapide"], game_data.build.presets["complet"]
    for key in ("beam", "depth", "shortlist", "mc_n"):
        assert getattr(fast, key) == entry["value"]["rapide"][key]
        assert getattr(fast, key) <= getattr(full, key)


def test_contexts_come_from_the_data(game_data):
    assert dict(game_data.build.contexts) == {"dungeon": ("dungeon_boss", "dungeon_pack"), "raid": ("raid_boss",)}


def test_order_is_legal_and_spends_every_point(game_data, path):
    assert [s.level for s in path.steps] == list(range(10, 21))
    for s, pts in _points_by_level(path):
        assert check_build(game_data, pts, s.level) == [], s
        assert sum(pts.values()) == points_available(game_data, s.level), s
    assert path.points == pts


def test_choices_are_legal(game_data, path):
    for s, pts in _points_by_level(path):
        c = s.choice
        assert c.rotation in ROTATIONS and c.rotation == s.rotation
        worn_armor(game_data, s.level, c.armor)  # Mage Armor jamais sous son niveau (ValueError sinon)
        if c.ab_stacks is not None:
            assert c.rotation == "arcane" and 0 <= c.ab_stacks <= arcane_blast_max_stacks(game_data, pts)
        if c.ab_dump is not None:
            assert c.rotation == "arcane" and c.ab_dump in AB_DUMPS
        if c.hs_stacks is not None:
            assert c.rotation == "fire" and hot_streak_rules(game_data, pts) is not None
        kill_analytic(game_data, s.level, pts, "Orc", c.rotation, **c.options())  # combinaison acceptée


@pytest.mark.slow
def test_optimizer_is_deterministic(game_data, path):
    assert _run(game_data) == path


def test_talented_bonus_adds_legal_points(game_data):
    bonus = _run(game_data, 10, 13, talented_bonus=3)
    by_level = {s.level: pts for s, pts in _points_by_level(bonus)}  # build de fin de chaque niveau
    assert list(by_level) == [10, 11, 12, 13]
    for level, pts in by_level.items():
        assert sum(pts.values()) == points_available(game_data, level, 3)
        assert check_build(game_data, pts, level, 3) == []
        assert check_build(game_data, pts, level) != []  # illégal sans le bonus


def test_start_build_is_kept(game_data):
    start = {"improvedFrostbolt": 1}
    kept = _run(game_data, 11, 13, start=start)
    for _, pts in _points_by_level(kept, start):
        assert pts.get("improvedFrostbolt", 0) >= 1
    with pytest.raises(ValueError, match="illégal"):
        _run(game_data, 11, 12, start={"iceLance": 1})


def test_level_weight_is_zero_at_the_cap(game_data):
    assert level_weight(game_data, game_data.level_cap) == 0.0
    assert level_weight(game_data, 10) > 0


def test_build_choices(game_data):
    assert build_choices(game_data, 20, {}, rules="seed") == [BuildChoice("frost"), BuildChoice("fire")]
    quick = build_choices(game_data, 40, ARC40)
    assert {c.rotation for c in quick} == {"frost", "fire", "arcane"}
    assert all(c.options() == {} for c in quick)
    full = build_choices(game_data, 40, ARC40, full=True)
    arcane = {(c.ab_stacks, c.ab_dump) for c in full if c.rotation == "arcane"}
    assert arcane == {(n, d) for n in range(arcane_blast_max_stacks(game_data, ARC40) + 1) for d in AB_DUMPS}
    assert {c.armor for c in full} == {"frost", "mage"}
    assert not any(c.armor == "mage" for c in build_choices(game_data, 30, {}, full=True))
    fire = {c.hs_stacks for c in build_choices(game_data, 25, FIRE25, full=True) if c.rotation == "fire"}
    assert fire == {1, 2, 3}


def test_best_choice_is_the_fastest(game_data):
    t, c = best_choice(game_data, 40, ARC40, full=True)
    times = [
        kill_analytic(game_data, 40, ARC40, "Orc", x.rotation, **x.options())["total"]
        for x in build_choices(game_data, 40, ARC40, full=True)
    ]
    assert t == min(times)
    assert kill_analytic(game_data, 40, ARC40, "Orc", c.rotation, **c.options())["total"] == t
