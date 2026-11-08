"""SIM2 bloc 12 : meilleurs objets par emplacement (« les 5 ou 6 meilleurs », demande du 2026-11-08) à partir des
essais de l'optimisation : candidats regroupés par emplacement (bagues et bijoux sous `Finger` et `Trinket`), triés
par gain, au plus `top` par emplacement, objet porté indiqué. Lignes fabriquées : aucune valeur de jeu."""

from forever.sims.brackets import rank_by_slot

ROWS = [
    {"item": 1, "slot": "Head", "replaces": 9, "gain": 5.0, "verdict": "meilleur"},
    {"item": 2, "slot": "Head", "replaces": 9, "gain": 12.0, "verdict": "meilleur"},
    {"item": 3, "slot": "Head", "replaces": 9, "gain": -1.0, "verdict": "non départagé"},
    {"item": 4, "slot": "Finger2", "replaces": 8, "gain": 3.0, "verdict": "meilleur"},
    {"item": 5, "slot": "Finger1", "replaces": 7, "gain": 4.0, "verdict": "meilleur"},
    {"item": 6, "slot": "Trinket1", "replaces": None, "gain": 9.0, "verdict": "meilleur"},
]


def test_candidates_are_grouped_by_slot_and_ranked():
    ranked = rank_by_slot(ROWS, {"Head": 9, "Finger1": 7, "Finger2": 8}, top=2)
    assert [r["item"] for r in ranked["Head"]["best"]] == [2, 1]  # au plus deux, du plus grand gain au plus petit
    assert ranked["Head"]["equipped"] == [9]
    assert [r["item"] for r in ranked["Finger"]["best"]] == [5, 4] and ranked["Finger"]["equipped"] == [7, 8]
    assert ranked["Trinket"]["best"][0]["item"] == 6 and ranked["Trinket"]["equipped"] == []
    assert list(ranked) == ["Head", "Finger", "Trinket"]  # ordre des emplacements de wowsims
