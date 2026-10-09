"""Départage final de la recommandation au Monte Carlo (MAG19, décision 219, demande de l'utilisateur du 2026-10-09).

Sur 1.60.1.70291, le build de leveling 20 retenu par le chemin analytique était plus lent au Monte Carlo que le build
Givre projeté du joueur et que sa propre alternative. Avant de rendre la recommandation, le rapport départage au Monte
Carlo apparié le build du chemin, ses meilleurs voisins analytiques et le build actuel : aucun candidat ne doit battre
significativement le build recommandé. Tests de la fonction pure (comparaisons injectées) puis du rapport (comparaison
truquée pour désigner un gagnant, et données réelles sans truquage). Aucune valeur de jeu n'est affirmée."""

import pytest
from conftest import isolated_deps

import forever.build as build_module
from forever.build import build_report
from forever.engine.talents import check_build
from forever.optimize.decide import Gap, departage


def scored(values, threshold):
    """Comparaison déterministe : valeur plus basse meilleure, significative au-delà du seuil."""

    def compare(a, b):
        d = values[a] - values[b]
        return Gap(d, d, d, 0.95, abs(d) >= threshold), "monte_carlo", d < 0

    return compare


def test_a_significant_gain_switches_the_champion():
    champion, rows = departage(["A", "B", "C"], scored({"A": 10, "B": 9, "C": 7}, 2))
    assert champion == "C"
    assert {r["candidate"] for r in rows} == {"A", "B"}


def test_a_tie_keeps_the_first_candidate():
    champion, _ = departage(["A", "B"], scored({"A": 10, "B": 9.5}, 2))
    assert champion == "A"


@pytest.mark.parametrize("threshold", [0.5, 1, 2, 3])
def test_no_candidate_beats_the_champion_significantly(threshold):
    values = {"A": 10, "B": 8.6, "C": 9.1, "D": 7.9, "E": 12}
    compare = scored(values, threshold)
    champion, rows = departage(list(values), compare)
    for c in values:
        if c != champion:
            gap, _, better = compare(c, champion)
            assert not (gap.significant and better), (c, champion)
    assert all(not (r["significant"] and r["better"]) for r in rows)


# --- Rapport -----------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("departage"))


def first_neighbor(cands):
    """Premier candidat voisin du build de l'optimiseur (un point déplacé)."""
    base = cands[0]
    keys = set(base) | {k for c in cands for k in c}
    return next(c for c in cands[1:] if sum(abs(c.get(k, 0) - base.get(k, 0)) for k in keys) == 2)


def rigged(monkeypatch, pick):
    """Comparaison truquée : le candidat désigné par `pick(candidats)` bat tous les autres, les autres sont à égalité."""
    chosen = {}
    real = build_module._departage_candidates

    def capture(*args, **kwargs):
        cands = real(*args, **kwargs)
        chosen["target"] = pick(cands)
        return cands

    def compare(self, a, b, seed):
        target = chosen.get("target")
        conf = self.gd.build.confidence
        if target is not None and a == target and b != target:
            return Gap(-1.0, -2.0, -0.5, conf, True), "monte_carlo", True
        if target is not None and b == target and a != target:
            return Gap(1.0, 0.5, 2.0, conf, True), "monte_carlo", False
        return Gap(0.0, -1.0, 1.0, conf, False), "analytique", True

    monkeypatch.setattr(build_module, "_departage_candidates", capture)
    monkeypatch.setattr(build_module._Metric, "compare", compare)
    return chosen


def assert_order_is_legal(gd, rep):
    acc = {}
    for step in rep["order"]:
        if step["talent"]:
            acc[step["talent"]] = acc.get(step["talent"], 0) + 1
            assert check_build(gd, acc, step["level"]) == [], step
    assert acc == rep["talents"]


def test_a_neighbor_that_wins_at_monte_carlo_is_recommended(deps, monkeypatch):
    chosen = rigged(monkeypatch, first_neighbor)
    rep = build_report(deps, "dungeon", 20, preset="rapide", sensitivity=False)
    assert rep["talents"] == chosen["target"]
    assert rep["departage"]["switched"] is True and rep["departage"]["chosen"] == "voisin"
    assert not (rep["alternative"]["better"] == "alternative" and not rep["alternative"]["tie"])


CURRENT_20 = {"arcaneFocus": 5, "arcaneConcentration": 5, "arcaneBlast": 1}


def test_the_current_build_that_wins_a_dungeon_is_recommended(deps, monkeypatch):
    chosen = rigged(monkeypatch, lambda cands: cands[-1])
    rep = build_report(deps, "dungeon", 20, preset="rapide", current=CURRENT_20, sensitivity=False)
    assert rep["departage"]["chosen"] == "build actuel"
    assert rep["talents"] == chosen["target"] == CURRENT_20


def test_the_current_build_enters_the_departage_of_a_dungeon(deps, monkeypatch):
    seen = {}
    real = build_module._departage_candidates

    def capture(*args, **kwargs):
        cands = real(*args, **kwargs)
        seen["cands"] = cands
        return cands

    monkeypatch.setattr(build_module, "_departage_candidates", capture)
    rep = build_report(deps, "dungeon", 20, preset="rapide", current=CURRENT_20, sensitivity=False)
    assert CURRENT_20 in seen["cands"]
    assert "niveau 20" in rep["departage"]["criterion"]


def test_real_data_never_recommend_a_dungeon_build_slower_than_a_candidate(deps):
    rep = build_report(deps, "dungeon", 20, preset="rapide", current=CURRENT_20, sensitivity=False)
    dep = rep["departage"]
    assert {"criterion", "candidates", "chosen", "switched", "mc_runs"} <= set(dep)
    assert all(not (c["significant"] and c["better"]) for c in dep["candidates"] if not c["champion"])
    assert not (rep["alternative"]["better"] == "alternative" and not rep["alternative"]["tie"])
    assert dep["mc_runs"] >= 1  # nombre de Monte Carlo lancés (le temps se mesure hors du rapport, déterministe)


def test_leveling_path_ends_are_ranked_by_cumulative_time(deps, monkeypatch, game_data):
    """Décision 220 : en leveling, les fins de faisceau se départagent au temps cumulé du chemin (heures
    équivalentes), pas au niveau demandé seul ; le chemin le plus court est retenu, avec son ordre."""
    seen = {}
    real_paths = build_module.leveling_paths

    def capture(*args, **kwargs):
        paths = real_paths(*args, **kwargs)
        seen["paths"] = paths
        return paths

    monkeypatch.setattr(build_module, "leveling_paths", capture)
    rep = build_report(deps, "leveling", 14, preset="rapide", sensitivity=False)
    dep = rep["departage"]
    assert "cumulé" in dep["criterion"]
    best = min(seen["paths"], key=lambda q: q.hours_equiv)
    assert rep["talents"] == {k: best.points[k] for k in game_data.talents if best.points.get(k, 0) > 0}
    hours = [c["hours"] for c in dep["candidates"]]
    assert min(hours) == next(c["hours"] for c in dep["candidates"] if c["champion"])
    assert_order_is_legal(game_data, rep)
