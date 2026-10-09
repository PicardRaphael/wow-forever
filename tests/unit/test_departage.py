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


def test_a_neighbor_that_wins_at_monte_carlo_is_recommended_with_a_legal_order(deps, monkeypatch, game_data):
    chosen = rigged(monkeypatch, lambda cands: cands[1])
    rep = build_report(deps, "leveling", 14, preset="rapide", sensitivity=False)
    assert rep["talents"] == chosen["target"]
    assert rep["departage"]["switched"] is True and rep["departage"]["chosen"] == "voisin"
    assert_order_is_legal(game_data, rep)
    assert not (rep["alternative"]["better"] == "alternative" and not rep["alternative"]["tie"])


def test_the_current_build_that_wins_is_recommended_and_kept(deps, monkeypatch, game_data):
    chosen = rigged(monkeypatch, lambda cands: cands[-1])
    rep = build_report(
        deps,
        "leveling",
        14,
        preset="rapide",
        current={"improvedFrostbolt": 3, "elementalPrecision": 1},
        sensitivity=False,
    )
    assert rep["departage"]["chosen"] == "build actuel"
    assert rep["talents"] == chosen["target"] == rep["respec"]["projected"]["talents"]
    assert rep["respec"]["verdict"] == "garder"
    assert rep["respec"]["versus_optimal"]["current_better"] is False
    assert "retenu" in rep["respec"]["reason"]
    assert_order_is_legal(game_data, rep)


def test_the_current_build_enters_the_departage_of_a_dungeon(deps, monkeypatch):
    seen = {}
    real = build_module._departage_candidates

    def capture(*args, **kwargs):
        cands = real(*args, **kwargs)
        seen["cands"] = cands
        return cands

    monkeypatch.setattr(build_module, "_departage_candidates", capture)
    current = {"arcaneFocus": 5, "arcaneConcentration": 5, "arcaneBlast": 1}
    rep = build_report(deps, "dungeon", 20, preset="rapide", current=current, sensitivity=False)
    assert current in seen["cands"]
    assert rep["departage"]["criterion"]


def test_real_data_never_recommend_a_build_slower_than_a_candidate(deps):
    rep = build_report(
        deps,
        "leveling",
        12,
        preset="rapide",
        current={"improvedFrostbolt": 2, "elementalPrecision": 1},
        sensitivity=False,
    )
    dep = rep["departage"]
    assert {"criterion", "candidates", "chosen", "switched", "mc_runs"} <= set(dep)
    assert all(not (c["significant"] and c["better"]) for c in dep["candidates"] if not c["champion"])
    assert not (rep["alternative"]["better"] == "alternative" and not rep["alternative"]["tie"])
    assert rep["respec"]["versus_optimal"]["current_better"] is False
    assert dep["mc_runs"] >= 1  # nombre de Monte Carlo lancés (le temps se mesure hors du rapport, déterministe)


def test_the_end_of_every_tree_path_enters_the_departage(deps, monkeypatch, game_data):
    """Relevé au leveling 20 de 1.60.1.70291 : le chemin Givre finit sur un build meilleur au niveau demandé, même en
    analytique, mais perd au cumul d'heures des niveaux précédents ; non voisin du build retenu, il n'entrait pas au
    départage. La fin de chaque faisceau (libre et par arbre) est candidate ; gagnante, son ordre est le sien."""
    seen = {}
    real_paths = build_module.leveling_paths

    def capture(*args, **kwargs):
        paths = real_paths(*args, **kwargs)
        seen["ends"] = [{k: v for k, v in p.points.items() if v > 0} for p in paths]
        return paths

    monkeypatch.setattr(build_module, "leveling_paths", capture)
    rep = build_report(deps, "leveling", 14, preset="rapide", sensitivity=False)
    talents = [c["talents"] for c in rep["departage"]["candidates"]]
    assert len(seen["ends"]) > 1
    for end in seen["ends"]:
        assert {k: end[k] for k in game_data.talents if end.get(k, 0) > 0} in talents
    assert all(not (c["significant"] and c["better"]) for c in rep["departage"]["candidates"] if not c["champion"])
    assert_order_is_legal(game_data, rep)
