"""SIM2 bloc 13 : ordre de priorité des statistiques par tranche (demande du 2026-11-08) : `stats="auto"` prend
toutes les statistiques d'équipement connues de l'outil et du proto épinglé ; chaque tranche rend `priority`, les
statistiques du plus grand au plus petit gain par point. Simulateur fabriqué : aucune valeur de jeu."""

from test_sims_bracket_weights import WeightLevelSim, _deps

from forever.sims.report import simulate


def test_auto_stats_give_the_priority_order_of_each_bracket(make_deps, tmp_path, monkeypatch):
    deps = _deps(make_deps, tmp_path)
    sim = WeightLevelSim()
    from forever.pipeline import gitops

    monkeypatch.setattr(gitops, "subprocess_runner", sim)
    out = simulate(deps, "brackets", preset="mage/dps/Fire", race="Human", brackets="25", path="none", gear="none",
                   stats="auto")  # fmt: skip
    weights = out["rows"][0]["weights"]
    assert weights["priority"] == ["StatIntellect", "StatSpellDamage", "StatStrength"]  # gains fabriqués 2, 0,5, 0
    assert set(weights["per_point"]) == {"StatStrength", "StatIntellect", "StatSpellDamage"}
