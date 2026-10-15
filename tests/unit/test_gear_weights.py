"""CJ1, bloc 4 (décision 276, registre I3) : poids des statistiques du Mage calculés par notre moteur (effet d'un point
de chaque statistique sur l'XP par heure du leveling, différences finies sur la fiche du personnage), normalisés
(Intelligence = 1) et exportés vers Naowh Forever (`NFSW1:`, points de pourcentage pour toucher et critique) et Forever
Companion (échelle Pawn v1).

Valeurs : fonction jouet ici ; données de la version du dépôt pour le Mage. Aucun chiffre de jeu ici."""

import re

from forever.engine.weights import normalize_weights, stat_weights
from forever.exports.naowh import read_naowh_weights
from forever.exports.pawn import pawn_scale, read_pawn_scale
from forever.gear import mage_weights, naowh_weight_line, pawn_line


def test_stat_weights_are_finite_differences():
    def metric(over):
        return 1000.0 + 3.0 * over.get("sp", 0.0) + 0.5 * over.get("intellect", 10.0)

    w = stat_weights(metric, {"intellect": 10.0}, {"sp": 2.0, "intellect": 4.0})
    assert round(w["sp"], 9) == 3.0 and round(w["intellect"], 9) == 0.5


def test_normalize_on_intellect_and_drop_negatives():
    out = normalize_weights({"intellect": 0.5, "sp": 1.5, "spirit": -0.1}, reference="intellect")
    assert out == {"intellect": 1.0, "sp": 3.0, "spirit": 0.0}


def test_pawn_scale_round_trip():
    text = pawn_scale(
        "Forever · Bob · leveling", "MAGE", {"Intellect": 1.0, "SpellPower": 2.5, "SpellCritRating": 12.0}
    )
    assert text.startswith('( Pawn: v1: "Forever · Bob · leveling": Class=Mage, ')
    assert read_pawn_scale(text) == ("Forever · Bob · leveling", "Mage", {"Intellect": 1.0, "SpellPower": 2.5,
                                                                          "SpellCritRating": 12.0})  # fmt: skip
    assert not re.search(r"\de[+-]?\d", text)  # jamais d'écriture exponentielle


def test_mage_weights_from_the_engine(make_deps):
    report = mage_weights(make_deps(), level=20, race="Gnome")
    w = report["weights"]
    assert w["intellect"] == 1.0 and w["sp"] > 0 and all(v >= 0 for v in w.values())
    assert report["provenance"]["certainty"] in ("probable", "suppose")
    spec, weights = read_naowh_weights(naowh_weight_line(report, spec="frost-mage"))
    assert spec == "frost-mage" and weights["int"] == 1.0 and weights["spell"] == w["sp"]
    pawn = pawn_line(report, label="Forever · Bob · leveling")
    assert "Class=Mage" in pawn and "Intellect=1" in pawn
