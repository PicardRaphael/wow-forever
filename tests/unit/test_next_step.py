"""Recommandations départagées (T06b, bloc E, décision D7) : à égalité statistique (intervalle apparié qui contient
zéro), un talent modélisé passe devant un non modélisé ; sinon « choix non départagé par le calcul ».

La règle se teste sur des échantillons construits (`tie_break`, déterministe) ; le faisceau et `next_step` se testent
sur leur structure. Modélisé : talent absent de tout angle mort `absent` du registre (`modeled_talents`)."""

import math

import pytest
from conftest import REGISTRY_PATH, isolated_deps

from forever.build import build_report
from forever.engine.blind_spots import modeled_talents
from forever.engine.talents import check_build, legal_additions
from forever.optimize.decide import DECIDED_BY, tie_break
from forever.optimize.leveling import optimize_leveling
from forever.registry import blind_spot_rules, load
from forever.sim.leveling_mc import McStats

CONF = 0.95
# Build de Givre légal au niveau 21 (12 points = 21 − 9).
FROST_21 = {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceShards": 1}


def stats(totals):
    n = len(totals)
    mean = sum(totals) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in totals) / (n - 1))
    return McStats(mean, sd, sd / math.sqrt(n), n, tuple(totals))


BASE = [30.0 + (i % 7) * 0.5 for i in range(40)]
SAME = stats(BASE)  # échantillons identiques : écart apparié nul, jamais significatif
NEAR = stats([x + (0.01 if i % 2 else -0.01) for i, x in enumerate(BASE)])  # écart moyen nul, dispersion faible
FASTER = stats([x - 2.0 for x in BASE])  # 2 s de moins à chaque combat : significatif


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("next-step"))


@pytest.fixture(scope="module")
def modeled(game_data):
    return modeled_talents(game_data, blind_spot_rules(load(REGISTRY_PATH)))


def test_modeled_talents_follow_the_absent_blind_spots(game_data, modeled):
    rules = blind_spot_rules(load(REGISTRY_PATH))
    absent = {t for r in rules if r.status == "absent" for t in r.talents}
    assert modeled == frozenset(game_data.talents) - absent
    assert "improvedFrostbolt" in modeled and "arcaneSubtlety" not in modeled and "wandSpecialization" not in modeled


def test_tie_prefers_the_modeled_talent():
    # Le non modélisé vient d'abord et a la plus petite moyenne : sans la règle, il serait choisi.
    d = tie_break([("wandSpecialization", SAME), ("frostWarding", NEAR)], frozenset({"frostWarding"}), CONF)
    assert d["choice"] == "frostWarding" and d["decided_by"] == "modelise"
    assert d["runner_up"] == "wandSpecialization"
    assert not d["gap"]["significant"] and d["gap"]["low"] <= 0 <= d["gap"]["high"]
    rows = {r["talent"]: r for r in d["rows"]}
    assert rows["frostWarding"]["modeled"] and not rows["wandSpecialization"]["modeled"]


def test_two_unmodeled_talents_are_not_decided():
    d = tie_break([("wandSpecialization", SAME), ("magicAbsorption", SAME)], frozenset(), CONF)
    assert d["decided_by"] == "non_departage" and d["choice"] == "wandSpecialization"
    assert d["gap"]["mean"] == 0.0 and d["gap"]["significant"] is False


def test_two_modeled_talents_in_a_tie_are_not_decided():
    d = tie_break([("a", SAME), ("b", NEAR)], frozenset({"a", "b"}), CONF)
    assert d["decided_by"] == "non_departage"


def test_significant_gap_is_decided_by_monte_carlo():
    # Le modélisé est significativement plus lent : le non modélisé plus rapide ne peut pas perdre… et l'inverse.
    d = tie_break([("slow", SAME), ("fast", FASTER)], frozenset({"slow"}), CONF)
    assert d["choice"] == "fast" and d["decided_by"] == "monte_carlo" and d["gap"]["significant"]
    assert d["gap"]["mean"] == pytest.approx(-2.0, rel=1e-12)  # choix − second : 2 s de moins par monstre
    assert d["gap"]["advantage"] == pytest.approx(2.0, rel=1e-12)


def test_single_candidate():
    d = tie_break([("only", SAME)], frozenset(), CONF)
    assert (d["choice"], d["decided_by"], d["runner_up"], d["gap"]) == ("only", "seul_candidat", None, None)


def test_higher_is_better_orientation():
    d = tie_break([("slow", SAME), ("fast", FASTER)], frozenset({"slow", "fast"}), CONF, lower_is_better=False)
    assert d["choice"] == "slow" and d["decided_by"] == "monte_carlo"


def test_next_step_lists_every_legal_candidate(deps, game_data, modeled):
    assert check_build(game_data, FROST_21, 21) == []
    rep = build_report(deps, "leveling", 22, current=FROST_21, preset="rapide", sensitivity=False)
    ns = rep["next_step"]
    assert ns["level"] == 22 and ns["from"] == FROST_21
    legal = legal_additions(game_data, FROST_21, 22)
    assert sorted(r["talent"] for r in ns["candidates"]) == sorted(legal)
    assert ns["choice"] in legal and ns["decided_by"] in DECIDED_BY
    best = min(ns["candidates"], key=lambda r: r["mean"])
    for r in ns["candidates"]:
        assert r["modeled"] == (r["talent"] in modeled)
        assert r["n"] == ns["n"] > 0
        g = r["gap"]
        assert g["low"] <= g["mean"] <= g["high"] and g["significant"] == (g["low"] > 0 or g["high"] < 0)
        if r["talent"] == best["talent"]:
            assert g["mean"] == 0.0
    if ns["decided_by"] == "monte_carlo":
        assert ns["choice"] == best["talent"]
    if not modeled.issuperset({best["talent"]}) and any(
        r["modeled"] and not r["gap"]["significant"] for r in ns["candidates"]
    ):
        assert ns["choice"] in modeled  # jamais un non modélisé à la place d'un modélisé à égalité


def test_next_step_needs_a_current_build_legal_one_level_below(deps):
    assert build_report(deps, "leveling", 22, preset="rapide", sensitivity=False)["next_step"] is None
    over = {**FROST_21, "iceShards": 2}  # 13 points : légal au niveau 22, pas au niveau 21
    assert build_report(deps, "leveling", 22, current=over, preset="rapide", sensitivity=False)["next_step"] is None
    assert build_report(deps, "dungeon", 22, current=FROST_21, preset="rapide", sensitivity=False)["next_step"] is None


def test_order_steps_carry_the_decision(deps, game_data):
    rep = build_report(deps, "leveling", 14, preset="rapide", sensitivity=False)
    for step in rep["order"]:
        assert step["decided_by"] in DECIDED_BY, step
        assert isinstance(step["modeled"], bool)
        if step["decided_by"] in ("seul_candidat", "analytique"):
            continue
        assert step["runner_up"] in game_data.talents
        g = step["gap"]
        assert g["significant"] == step["significant"] == (g["low"] > 0 or g["high"] < 0)


def test_forever_path_never_prefers_an_unmodeled_talent_in_a_tie(game_data, modeled):
    path = optimize_leveling(game_data, "Orc", 10, 16, beam=2, depth=2, shortlist=3, mc_n=40, modeled=modeled)
    for s in path.steps:
        assert s.decided_by in DECIDED_BY
        if s.talent is not None and s.talent not in modeled and s.runner_up in modeled and not s.significant:
            assert s.decided_by == "passage_palier", s


def test_seed_path_carries_no_decision(seed_game_data):
    path = optimize_leveling(
        seed_game_data, "Orc", 10, 12, beam=2, depth=2, mc_n=40, rules="seed", mob_source="seed", spell_level="rank"
    )
    assert all(s.decided_by is None and s.runner_up is None for s in path.steps)
