"""Nœuds garés hors du canevas (décision 211, demande de l'utilisateur du 2026-10-08) : la règle du zéro en trop ne
replace plus jamais un nœud en silence. Un nœud dont une coordonnée vaut dix fois une valeur de la grille n'est
replacé que si Talents Forever le confirme à la position corrigée (même arbre, même sort, même rangée, même colonne) ;
sinon il est garé, écarté (`dropped_nodes`), listé dans `parked_nodes` avec la question à ouvrir, et une question
ouverte (`docs/OPEN_QUESTIONS.md`) ou un relevé en jeu (`observed_absent`, `observed_positions`) doit y répondre.

Cas réel : Improved Serpent Sting (Chasseur), ordonnée dix fois la grille dans le client, absent de Talents Forever
0.37.1 (`tests/fixtures/talents_forever/layout.json`) et de l'arbre en jeu (relevé du 2026-10-08). Positions lues
dans la fixture wago et `decode_rules.json`, jamais écrites dans le test ; addon synthétique dans `tmp_path`."""

import copy
import csv

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, REPO_ROOT, WAGO_70124, read_json
from talents_forever_data import write_addon

from forever.errors import DataSchemaError
from forever.pipeline.decode import check_mage_not_parked, decode_classes
from forever.pipeline.talents_forever import tf_positions

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"
KEY = "improvedSerpentSting"


def node_row(node_id):
    with (WAGO_70124 / "enUS" / "TraitNode.csv").open(encoding="utf-8", newline="") as f:
        return next(r for r in csv.DictReader(f) if int(r["ID"]) == node_id)


def talents_of(c):
    return {t["key"]: t for tree in c["trees"] for t in tree["talents"]}


@pytest.fixture(scope="module")
def iss(decode_rules):
    return decode_rules["observed_absent"]["Hunter"][KEY]


@pytest.fixture(scope="module")
def corrected(decode_rules, iss):
    """(arbre, rangée, colonne, sort) d'Improved Serpent Sting une fois le zéro en trop retiré."""
    geo = decode_rules["talent_geometry"]
    row = node_row(iss["node_id"])
    x, y = int(row["PosX"]), int(row["PosY"])
    assert (y - geo["row_base"]) % geo["row_step"] and y % geo["extra_zero_divisor"] == 0  # prémisse : garé
    origins = geo["tab_origins"]
    tab = max(i for i, o in enumerate(origins) if o <= x)
    tier = (y // geo["extra_zero_divisor"] - geo["row_base"]) // geo["row_step"] + 1
    col = (x - origins[tab]) // geo["col_step"] + 1
    return tab, tier, col, y


@pytest.fixture
def rules(decode_rules):
    """Règles installées sans la réponse du relevé en jeu : la règle des nœuds garés seule."""
    out = copy.deepcopy(decode_rules)
    del out["observed_absent"]["Hunter"]
    return out


@pytest.fixture
def tf(tmp_path):
    """Positions de Talents Forever 0.37.1 (disposition relevée de l'addon réel, sans Improved Serpent Sting)."""
    folder = write_addon(tmp_path / "wow", CLASSES)
    return tf_positions(folder / "Data.lua")


def spell_of(class_tables, node_id):
    link = next(r for r in class_tables["TraitNodeXTraitNodeEntry"] if int(r["TraitNodeID"]) == node_id)
    entry = next(r for r in class_tables["TraitNodeEntry"] if int(r["ID"]) == int(link["TraitNodeEntryID"]))
    definition = next(r for r in class_tables["TraitDefinition"] if int(r["ID"]) == int(entry["TraitDefinitionID"]))
    return int(definition["SpellID"])


def parked_entry(c, node_id):
    return next(p for p in c["parked_nodes"] if p["node_id"] == node_id)


def test_installed_rules_enable_the_parked_rule(decode_rules):
    assert decode_rules["parked_nodes"] == "talents_forever"


def test_real_case_not_in_talents_forever_is_parked(class_tables, rules, tf, iss, corrected):
    hunter = decode_classes(class_tables, rules, LOCAL_VERSION, tf=tf)["classes"]["Hunter"]
    assert KEY not in talents_of(hunter)
    p = parked_entry(hunter, iss["node_id"])
    assert p["key"] == KEY and p["status"] == "garé" and p["answered"] is None
    assert (p["pos_y"], p["tier"], p["col"]) == (corrected[3], corrected[1], corrected[2])
    assert "0.37.1" in p["talents_forever"]
    assert "Improved Serpent Sting" in p["question"] and "en jeu" in p["question"]
    dropped = {d["node_id"]: d for d in hunter["dropped_nodes"]}
    assert "garé" in dropped[iss["node_id"]]["reason"] and dropped[iss["node_id"]]["kept_node"] is None


def test_confirmed_by_talents_forever_is_placed(class_tables, rules, tf, iss, corrected):
    tab, tier, col, _ = corrected
    tf = copy.deepcopy(tf)
    tf["classes"]["HUNTER"][tab].append([spell_of(class_tables, iss["node_id"]), tier, col])
    hunter = decode_classes(class_tables, rules, LOCAL_VERSION, tf=tf)["classes"]["Hunter"]
    t = talents_of(hunter)[KEY]
    assert (t["tier"], t["col"]) == (tier, col)
    assert "Talents Forever" in t["position"]["source"] and t["position"]["certainty"] == "probable"
    assert parked_entry(hunter, iss["node_id"])["status"] == "confirmé"
    assert iss["node_id"] not in {d["node_id"] for d in hunter["dropped_nodes"]}


@pytest.mark.parametrize("shift", [(0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 1)])
def test_any_other_position_is_not_a_confirmation(class_tables, rules, tf, iss, corrected, shift):
    tab, tier, col, _ = corrected
    dt, dr, dc, ds = shift  # autre arbre, autre rangée, autre colonne, autre sort
    tf = copy.deepcopy(tf)
    other = (tab + dt) % len(tf["classes"]["HUNTER"])
    tf["classes"]["HUNTER"][other].append([spell_of(class_tables, iss["node_id"]) + ds, tier + dr, col + dc])
    hunter = decode_classes(class_tables, rules, LOCAL_VERSION, tf=tf)["classes"]["Hunter"]
    assert KEY not in talents_of(hunter)
    assert parked_entry(hunter, iss["node_id"])["status"] == "garé"


def test_without_talents_forever_the_node_is_parked(class_tables, rules, iss):
    hunter = decode_classes(class_tables, rules, LOCAL_VERSION)["classes"]["Hunter"]
    p = parked_entry(hunter, iss["node_id"])
    assert p["status"] == "garé" and "absent" in p["talents_forever"]
    assert KEY not in talents_of(hunter)


def test_in_game_answers_close_the_question(class_tables, decode_rules, tf, iss, corrected):
    hunter = decode_classes(class_tables, decode_rules, LOCAL_VERSION, tf=tf)["classes"]["Hunter"]
    p = parked_entry(hunter, iss["node_id"])
    assert p["status"] == "garé" and p["answered"] == iss["source"]
    reason = {d["node_id"]: d for d in hunter["dropped_nodes"]}[iss["node_id"]]["reason"]
    assert "garé" in reason and "absent de l'arbre en jeu" in reason
    rules = copy.deepcopy(decode_rules)
    del rules["observed_absent"]["Hunter"]
    _, tier, col, _ = corrected
    seen = {"tier": tier, "col": col, "source": "relevé de test", "certainty": "certain"}
    rules["observed_positions"]["Hunter"] = {KEY: seen}
    hunter = decode_classes(class_tables, rules, LOCAL_VERSION, tf=tf)["classes"]["Hunter"]
    t = talents_of(hunter)[KEY]
    assert (t["tier"], t["col"]) == (tier, col) and t["position"]["source"] == "relevé de test"
    assert parked_entry(hunter, iss["node_id"])["answered"] == "relevé de test"


def test_rules_without_the_parked_rule_keep_the_old_behaviour(class_tables, rules, iss, corrected):
    del rules["parked_nodes"]  # règles d'une version antérieure : décodage reproductible
    hunter = decode_classes(class_tables, rules, LOCAL_VERSION)["classes"]["Hunter"]
    t = talents_of(hunter)[KEY]
    assert (t["tier"], t["col"]) == (corrected[1], corrected[2])
    assert hunter["parked_nodes"] == []


def test_installed_data_lists_the_parked_node_and_its_answer(iss):
    hunter = read_json(CLASSES)["classes"]["Hunter"]
    p = parked_entry(hunter, iss["node_id"])
    assert p["status"] == "garé" and p["answered"] == iss["source"]


def test_every_parked_node_has_an_open_question_or_an_in_game_answer():
    questions = (REPO_ROOT / "docs" / "OPEN_QUESTIONS.md").read_text(encoding="utf-8")
    for cls, c in read_json(CLASSES)["classes"].items():
        for p in c["parked_nodes"]:
            if p["status"] == "garé" and p["answered"] is None:
                assert p["key"] in questions or p["name"] in questions, (cls, p["key"], p["question"])


def test_tf_positions_reads_tree_spell_row_col(tf):
    hunter = tf["classes"]["HUNTER"]
    assert len(hunter) == 3 and all(len(p) == 3 for tree in hunter for p in tree)
    assert "0.37.1" in tf["label"] and tf["label"].count("empreinte") == 1


def test_mage_talent_on_a_parked_node_stops_the_decode():
    classes = {"classes": {"Mage": {"parked_nodes": [{"spell_id": 1, "status": "garé", "key": "x"}]}}}
    talents = {"trees": [{"talents": [{"key": "x", "spellIds": [1]}]}]}
    with pytest.raises(DataSchemaError):
        check_mage_not_parked(talents, classes)
    classes["classes"]["Mage"]["parked_nodes"][0]["status"] = "confirmé"
    check_mage_not_parked(talents, classes)
