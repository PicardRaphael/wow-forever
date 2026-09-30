"""Décodage des 9 classes (PV1, bloc B ; décision 31) : arbres de talents, nœuds, nœuds hors grille.

Fixture : `tests/fixtures/wago/1.60.1.70124/` (`scripts/extract_class_fixtures.py`, arbres des 9 classes en entier).
Valeurs attendues lues dans la fixture (CSV du client), dans `decode_rules.json` ou dans `talents.json` des données,
jamais écrites dans le test."""

import csv
from functools import cache

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, read_json

from forever.pipeline.decode import decode_classes, fetch_list

# PV1, D3 : tables téléchargées sur accord de l'utilisateur (2026-09-30), plus ChrClasses et SkillLine déjà en cache.
APPROVED_CLASS_TABLES = {
    "ChrClasses",
    "SkillLine",
    "SpellRange",
    "SpellCategories",
    "SpellCategory",
    "SpellMechanic",
    "SpellDispelType",
    "SpellInterrupts",
    "SpellClassOptions",
    "SpellAuraRestrictions",
    "SpellShapeshift",
    "ChrRaces",
    "CharBaseInfo",
    "SkillRaceClassInfo",
    "Item",
    "ItemSparse",
    "ItemEffect",
    "ItemXItemEffect",
}


@cache
def csv_rows(name: str) -> tuple[dict[str, str], ...]:
    with (WAGO_70124 / "enUS" / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return tuple(csv.DictReader(f))


@pytest.fixture(scope="module")
def doc(class_tables, decode_rules):
    return decode_classes(class_tables, decode_rules, LOCAL_VERSION)


def talents_of(c):
    return [t for tree in c["trees"] for t in tree["talents"]]


def class_tree(decode_rules, cls):
    lines = {str(i) for i in decode_rules["classes"][cls]["skill_lines"]}
    (tree,) = {r["TraitTreeID"] for r in csv_rows("SkillLineXTraitTree") if r["SkillLineID"] in lines}
    return tree


def on_grid(value, origins, step):
    return any(value >= o and (value - o) % step == 0 for o in origins)


def placed(value, origins, step, divisor):
    """Position lisible sur la grille, directement ou après la règle du zéro en trop."""
    return on_grid(value, origins, step) or (value % divisor == 0 and on_grid(value // divisor, origins, step))


def test_fetch_list_is_the_approved_one(decode_rules):
    tables, localized = fetch_list(decode_rules)
    assert set(decode_rules["class_tables"]) == APPROVED_CLASS_TABLES  # toute table ajoutée fait échouer ce test
    assert tables == list(dict.fromkeys([*decode_rules["tables"], *decode_rules["class_tables"]]))
    assert localized == {"frFR": ["SpellName", "ChrRaces"]}


def test_nine_classes_have_three_named_trees(doc, decode_rules):
    skill = {r["ID"]: r["DisplayName_lang"] for r in csv_rows("SkillLine")}
    client = {r["Name_lang"]: r for r in csv_rows("ChrClasses")}
    assert list(doc["classes"]) == list(decode_rules["classes"])
    assert set(doc["classes"]) == set(client)  # les neuf classes du client
    for cls, c in doc["classes"].items():
        lines = decode_rules["classes"][cls]["skill_lines"]
        assert [t["name"] for t in c["trees"]] == [skill[str(i)] for i in lines]
        assert [t["skill_line"] for t in c["trees"]] == lines
        assert (c["id"], c["file"]) == (int(client[cls]["ID"]), client[cls]["Filename"])
        assert c["trait_tree"] == int(class_tree(decode_rules, cls))
        # onglet = ligne de compétence majoritaire des sorts de ses talents (SkillLineAbility)
        assert [ch["skill_line"] for ch in c["tree_checks"]] == lines
        assert all(ch["majority"] == ch["skill_line"] for ch in c["tree_checks"])


def test_every_talent_has_a_node_id(doc, decode_rules):
    nodes = {int(r["ID"]): r for r in csv_rows("TraitNode")}
    for cls, c in doc["classes"].items():
        tree = class_tree(decode_rules, cls)
        talents = talents_of(c)
        assert talents
        for t in talents:
            assert isinstance(t["node_id"], int) and nodes[t["node_id"]]["TraitTreeID"] == tree
        kept = {t["node_id"] for t in talents}
        dropped = {d["node_id"] for d in c["dropped_nodes"]}
        assert not kept & dropped
        assert kept | dropped == {n for n, r in nodes.items() if r["TraitTreeID"] == tree}  # chaque nœud traité
        keys = [t["key"] for t in talents]
        assert len(keys) == len(set(keys))
        for t in talents:
            if t["prereq"] is not None:
                assert t["prereq"]["node_id"] in kept


def test_mage_part_matches_talents_json(doc):
    reference = read_json(DATA_DIR / LOCAL_VERSION / "talents.json")
    mage = doc["classes"]["Mage"]
    assert [t["name"] for t in mage["trees"]] == [t["name"] for t in reference["trees"]]
    for ref_tree, tree in zip(reference["trees"], mage["trees"], strict=True):
        got = {t["key"]: t for t in tree["talents"]}
        assert set(got) == {t["key"] for t in ref_tree["talents"]}
        for r in ref_tree["talents"]:
            g = got[r["key"]]
            assert (g["name"], g["name_fr"], g["tier"], g["col"], g["max"], g["desc"]) == (
                r["name"],
                r["name_fr"],
                r["tier"],
                r["col"],
                r["max"],
                r["source"]["client_desc"],
            )
            assert g["spell_id"] == r["source"]["client_spell_ids"][0]
            prereq = None if g["prereq"] is None else {"tier": g["prereq"]["tier"], "col": g["prereq"]["col"]}
            assert prereq == r["prereq"]
    assert mage["unresolved_nodes"] == []


def test_extra_zero_node_is_placed(doc, decode_rules):
    geo = decode_rules["talent_geometry"]
    div, rows = geo["extra_zero_divisor"], [geo["row_base"]]
    nodes = {int(r["ID"]): r for r in csv_rows("TraitNode")}
    corrected = 0
    for c in doc["classes"].values():
        for t in talents_of(c):
            y = int(nodes[t["node_id"]]["PosY"])
            if not on_grid(y, rows, geo["row_step"]) and y % div == 0 and on_grid(y // div, rows, geo["row_step"]):
                assert t["tier"] == (y // div - geo["row_base"]) // geo["row_step"] + 1
                corrected += 1
    assert corrected >= 1  # prémisse : la fixture porte un nœud au zéro en trop


def test_off_grid_nodes_are_listed_unresolved(doc, decode_rules):
    geo = decode_rules["talent_geometry"]
    origins, div = geo["tab_origins"], geo["extra_zero_divisor"]
    nodes = {int(r["ID"]): r for r in csv_rows("TraitNode")}
    with_unresolved = set()
    for cls, c in doc["classes"].items():
        expected = {}
        for t in talents_of(c):
            x, y = int(nodes[t["node_id"]]["PosX"]), int(nodes[t["node_id"]]["PosY"])
            bad_x = not placed(x, origins, geo["col_step"], div)
            bad_y = not placed(y, [geo["row_base"]], geo["row_step"], div)
            if bad_x or bad_y:
                expected[t["node_id"]] = (bad_x, bad_y)
                assert (t["col"] is None, t["tier"] is None) == (bad_x, bad_y)  # jamais arrondi
                assert t["unresolved"]
            else:
                assert "unresolved" not in t or not t["unresolved"]
        listed = {u["node_id"]: u for u in c["unresolved_nodes"]}
        assert set(listed) == set(expected)
        for node_id, u in listed.items():
            assert (u["pos_x"], u["pos_y"]) == (int(nodes[node_id]["PosX"]), int(nodes[node_id]["PosY"]))
            assert u["reason"]
        if expected:
            with_unresolved.add(cls)
    assert "Paladin" in with_unresolved  # plan de PV1 : écart relevé sur l'arbre du Paladin


def test_stale_duplicate_nodes_are_dropped_for_the_newer_node(doc, decode_rules):
    nodes = {int(r["ID"]): r for r in csv_rows("TraitNode")}
    link = {int(r["TraitNodeID"]): int(r["TraitNodeEntryID"]) for r in csv_rows("TraitNodeXTraitNodeEntry")}
    entry = {int(r["ID"]): int(r["TraitDefinitionID"]) for r in csv_rows("TraitNodeEntry")}
    spell = {int(r["ID"]): int(r["SpellID"]) for r in csv_rows("TraitDefinition")}

    def spell_of(node_id):
        return spell[entry[link[node_id]]]

    geo = decode_rules["talent_geometry"]
    dropped_off_grid = set()
    for cls, c in doc["classes"].items():
        kept = {t["node_id"]: t for t in talents_of(c)}
        for d in c["dropped_nodes"]:
            assert d["kept_node"] in kept and d["kept_node"] > d["node_id"]  # le nœud le plus récent l'emporte
            assert spell_of(d["node_id"]) == spell_of(d["kept_node"]) == kept[d["kept_node"]]["spell_id"]
            x, y = int(nodes[d["node_id"]]["PosX"]), int(nodes[d["node_id"]]["PosY"])
            if not (on_grid(x, geo["tab_origins"], geo["col_step"]) and on_grid(y, [geo["row_base"]], geo["row_step"])):
                dropped_off_grid.add(cls)
    assert "Priest" in dropped_off_grid  # l'écart du Prêtre relevé au plan est un doublon périmé
