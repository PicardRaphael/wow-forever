"""Positions de talents relevées en jeu (PV1, bloc B1 ; relevé de l'utilisateur du 2026-09-30, certitude certain).

`decode_rules.json`, `observed_positions` : palier et colonne observés dans la fenêtre des talents ; ils placent les
nœuds hors grille du client, après contrôle de concordance avec ce que le client dit déjà. Valeurs attendues lues
dans les règles, jamais écrites dans le test."""

import copy

import pytest
from conftest import LOCAL_VERSION

from forever.errors import DataSchemaError
from forever.pipeline.decode import decode_classes


@pytest.fixture(scope="module")
def doc(class_tables, decode_rules):
    return decode_classes(class_tables, decode_rules, LOCAL_VERSION)


def observed(decode_rules):
    return {cls: spec for cls, spec in decode_rules["observed_positions"].items() if isinstance(spec, dict)}


def test_observed_positions_place_off_grid_nodes(doc, decode_rules):
    placed = 0
    for cls, spec in observed(decode_rules).items():
        c = doc["classes"][cls]
        talents = {t["key"]: t for tree in c["trees"] for t in tree["talents"]}
        for key, pos in spec.items():
            t = talents[key]
            assert (t["tier"], t["col"]) == (pos["tier"], pos["col"])
            assert "unresolved" not in t
            assert t["position"] == {"source": pos["source"], "certainty": pos["certainty"]}
            assert key not in {u["key"] for u in c["unresolved_nodes"]}
            assert key in {o["key"] for o in c["observed_nodes"]}
            placed += 1
    assert placed >= 2  # prémisse : les deux nœuds du Paladin


def test_prerequisite_carries_the_observed_column(doc, decode_rules):
    for cls, spec in observed(decode_rules).items():
        talents = {t["key"]: t for tree in doc["classes"][cls]["trees"] for t in tree["talents"]}
        by_node = {t["node_id"]: t for t in talents.values()}
        for t in talents.values():
            for p in t["prereqs"]:
                source = by_node[p["node_id"]]
                if source["key"] in spec:
                    assert (p["tier"], p["col"]) == (source["tier"], source["col"])


def test_observation_disagreeing_with_the_client_stops_the_decode(class_tables, decode_rules):
    rules = copy.deepcopy(decode_rules)
    spec = next(iter(observed(rules).values()))
    key = next(iter(spec))
    spec[key]["tier"] += 1  # palier décodé du client différent du relevé
    with pytest.raises(DataSchemaError):
        decode_classes(class_tables, rules, LOCAL_VERSION)
