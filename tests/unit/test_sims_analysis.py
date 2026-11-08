"""SIM2 bloc 15 : analyse complète gardée, pour répondre aux questions sans recalculer (demande du 2026-11-08 :
« analyse tous les équipements, BiS, talents dans l'ordre, tout, pour que je puisse te poser des questions »).

Pour une spécialisation (préréglage) et une race, à chaque tranche : talents dans l'ordre de prise jusqu'au niveau,
meilleure rotation, dégâts par seconde, priorité des statistiques, meilleurs objets par emplacement. Le résultat est
écrit dans le cache, par version des données et commit de wowsims ; une analyse déjà faite n'est pas refaite ; la
lecture rend le résultat gardé avec sa provenance. Calculs fabriqués (fonctions injectées) : aucune valeur de jeu."""

import json

from forever.sims.analysis import analyse_spec, analysis_path, read_analysis


def _fake_brackets(**kw):
    rows = [{"bracket": "20-29", "level": 25, "dps": 50.0, "rotation": "mage/dps/Fire", "talents": {"a": 1},
             "weights": {"priority": ["StatIntellect"], "normalised": {"StatIntellect": 1.0}}}]  # fmt: skip
    return {"preset": kw["preset"], "race": "RaceHuman", "rows": rows,
            "provenance": {"assumptions": ["calcul fabriqué"]}}  # fmt: skip


def _fake_gear(**kw):
    return {"level": kw["level"], "by_slot": {"Head": {"equipped": [1], "best": [{"item": 2, "gain": 3.0}]}}}


STEPS = [{"level": 10, "key": "a", "rank": 1}, {"level": 30, "key": "b", "rank": 1}]


def test_analysis_is_computed_written_and_read_back(make_deps):
    deps = make_deps()
    calls = []

    def brackets(**kw):
        calls.append("brackets")
        return _fake_brackets(**kw)

    doc = analyse_spec(deps, preset="mage/dps/Fire", race="Human", brackets="20-29", run=brackets, gear=_fake_gear,
                       steps=lambda: (STEPS, "plan fabriqué"))  # fmt: skip
    row = doc["brackets"][0]
    assert row["level"] == 25 and row["dps"] == 50.0 and row["rotation"] == "mage/dps/Fire"
    assert row["talent_order"] == [{"level": 10, "key": "a", "rank": 1}]  # étapes jusqu'au niveau de la tranche
    assert row["stat_priority"] == ["StatIntellect"] and row["gear"]["Head"]["best"][0]["item"] == 2
    path = analysis_path(deps, "mage/dps/Fire", "Human")
    assert path.is_file() and json.loads(path.read_text(encoding="utf-8"))["preset"] == "mage/dps/Fire"
    again = analyse_spec(deps, preset="mage/dps/Fire", race="Human", brackets="20-29", run=brackets,
                         gear=_fake_gear, steps=lambda: (STEPS, "plan fabriqué"))  # fmt: skip
    assert calls == ["brackets"] and again == doc  # déjà faite : relue, pas recalculée
    read = read_analysis(deps, "mage/dps/Fire", "Human")
    assert read["brackets"][0]["dps"] == 50.0 and read["provenance"]["certainty"] == "suppose"
    assert read_analysis(deps, "mage/dps/Frost", "Human") is None
