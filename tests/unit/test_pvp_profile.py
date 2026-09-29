"""Profil PvP en mode forever et builds PvP par contexte (T05, bloc G). Barème du seed (`pvp.profile`, suppose) et
poids des contextes (`pvp.weights` : `bg` = poids du seed, `world` supposé) lus dans `mechanics.json` ; recharges du
client et sorts utilitaires lus dans les données."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.pvp import pvp_score
from forever.engine.talents import check_build, points_available
from forever.optimize.endgame import PVP_CONTEXTS, neighbors, optimize_context, seed_pvp_greedy

BUILD_20 = {"improvedFrostbolt": 5, "frostbite": 3, "elementalPrecision": 2, "iceLance": 1}


def _values():
    return read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]


def test_profile_and_weights_come_from_the_data(game_data):
    v = _values()
    for key in ("pvp.profile", "pvp.weights"):
        assert v[key]["certainty"] == "suppose" and v[key]["registry"] == "I5" and v[key]["source"]
    w = v["pvp.weights"]["value"]
    assert set(w) == {"bg", "world"}
    assert w["bg"] == {"burst": 0.35, "control": 0.25, "survival": 0.25, "sustain": 0.15}  # poids du seed
    for weights in w.values():
        assert sum(weights.values()) == pytest.approx(1.0)
    assert PVP_CONTEXTS == {"pvp-bg": "bg", "pvp-world": "world"}


def test_score_is_the_weighted_capped_sum(game_data):
    v = _values()
    prof = v["pvp.profile"]["value"]
    p = pvp_score(game_data, BUILD_20, 20, "Orc")
    w = v["pvp.weights"]["value"]["bg"]
    comps = {"burst": p.burst, "control": p.control, "survival": p.survival, "sustain": p.sustain}
    expected = sum(w[k] * min(prof["cap"], comps[k] / prof["ref"][k]) for k in w) * prof["scale"]
    assert p.score == pytest.approx(expected, rel=1e-12)
    world = pvp_score(game_data, BUILD_20, 20, "Orc", v["pvp.weights"]["value"]["world"])
    assert (world.burst, world.control) == (p.burst, p.control)


def test_forever_mode_uses_the_client_rules(game_data):
    seed = pvp_score(game_data, BUILD_20, 20, "Orc", rules="seed")
    forever = pvp_score(game_data, BUILD_20, 20, "Orc")
    assert forever.control == seed.control  # contrôle : durées du barème, identiques
    assert forever.burst != seed.burst  # dégâts : coefficients du client, dégâts au niveau du personnage


def test_pvp_context_builds_are_legal_local_optima(game_data):
    for context in ("pvp-bg", "pvp-world"):
        cands = optimize_context(game_data, context, 20, "Orc", shortlist=2, mc_n=40, depth=2)
        assert cands and all(c.stats is None for c in cands)  # modèle déterministe : pas de Monte Carlo
        for c in cands:
            assert check_build(game_data, c.points, 20) == []
            assert sum(c.points.values()) == points_available(game_data, 20)
        best = cands[0]
        weights = _values()["pvp.weights"]["value"][PVP_CONTEXTS[context]]
        assert best.analytic == pytest.approx(pvp_score(game_data, best.points, 20, "Orc", weights).score, rel=1e-12)
        for n in neighbors(game_data, best.points, 20):
            assert pvp_score(game_data, n, 20, "Orc", weights).score <= best.analytic + 1e-9
        assert [c.analytic for c in cands] == sorted((c.analytic for c in cands), reverse=True)


def test_multi_start_beats_the_seed_greedy(game_data):
    """Le glouton du seed rend un build sans point de dégâts ni de contrôle (plan T05, D6) ; les départs multiples et
    la recherche locale doivent faire au moins aussi bien avec le même barème."""
    greedy = seed_pvp_greedy(game_data, 20, "Orc", beam=2, rules="forever")
    best = optimize_context(game_data, "pvp-bg", 20, "Orc", shortlist=2, mc_n=40, depth=2)[0]
    assert best.analytic >= pvp_score(game_data, greedy.points, 20, "Orc").score
    assert best.analytic > pvp_score(game_data, greedy.points, 20, "Orc").score + 1.0
