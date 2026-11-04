"""Recherche de builds au niveau 60 par les simulateurs (MS1, décision 301) : échange d'un point à la fois (un point
retiré parmi les moins utiles, un point ajouté là où il rapporte le plus) tant que le gain est positif, légalité de
chaque build sur les arbres du client, tirages appariés (même graine) ; confirmation : un gain sous le seuil de bruit
(deux fois l'écart type de la différence des moyennes) est rendu « non départagé ».

Évaluation injectée (dégâts fabriqués), aucun simulateur lancé."""

import math

from forever.sims.builds import climb, decide


def _eval(gains):
    def evaluate(talents):
        return 100.0 + sum(gains.get(k, 0.0) * v for k, v in talents.items()), 10.0

    return evaluate


def test_climb_swaps_a_point_while_it_gains():
    out = climb({"a": 2}, _eval({"a": 1.0, "b": 3.0}), lambda t: True, ["a", "b"], max_steps=10)
    assert out["talents"] == {"a": 0, "b": 2}
    assert [(s["remove"], s["add"]) for s in out["steps"]] == [("a", "b"), ("a", "b")]
    assert out["steps"][0]["before"] == 102.0 and out["steps"][0]["after"] == 104.0
    assert out["stopped"] == "aucun échange gagnant"


def test_climb_stops_on_zero_gain():
    out = climb({"a": 1}, _eval({"a": 1.0, "b": 1.0}), lambda t: True, ["a", "b"], max_steps=10)
    assert out["talents"] == {"a": 1} and out["steps"] == []
    assert out["stopped"] == "aucun échange gagnant"


def test_climb_keeps_every_build_legal_and_caps_the_steps():
    legal = lambda t: t.get("b", 0) <= 1
    out = climb({"a": 3}, _eval({"a": 1.0, "b": 3.0, "c": 2.0}), legal, ["a", "b", "c"], max_steps=10)
    assert out["talents"]["b"] == 1 and out["talents"]["c"] == 2
    capped = climb({"a": 3}, _eval({"a": 1.0, "b": 3.0, "c": 2.0}), lambda t: True, ["a", "b", "c"], max_steps=1)
    assert len(capped["steps"]) == 1 and capped["stopped"] == "plafond d'échanges atteint"


def test_gain_under_the_noise_is_not_decided():
    start = {"dps": 1000.0, "stdev": 100.0, "iterations": 10000}
    threshold = 2 * math.sqrt(2 * (100.0 / math.sqrt(10000)) ** 2)
    close = decide(start, {"dps": 1000.0 + threshold / 2, "stdev": 100.0, "iterations": 10000})
    assert close["verdict"] == "non départagé" and close["threshold"] == threshold
    far = decide(start, {"dps": 1000.0 + threshold * 2, "stdev": 100.0, "iterations": 10000})
    assert far["verdict"] == "meilleur" and far["gain"] == threshold * 2
