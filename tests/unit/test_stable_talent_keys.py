"""Clés de talent stables d'une version à l'autre, pour les 9 classes (demande de l'utilisateur du 2026-10-09).

Un talent renommé par le client (même nœud, même sort : Predatory Instincts devenu Natural Instinct dans
1.60.1.70291) garde sa clé ; le nouveau nom est affiché, l'ancien gardé en alias (`former_names`), la clé du client
dans `client_key`. Un nœud qui porte un autre sort est un autre talent (King of the Jungle remplacé par Shifting
Power) : il prend sa propre clé. Données synthétiques, sauf l'invariant sur les deux dernières versions installées."""

import copy

from conftest import DATA_DIR, INSTALLED_VERSIONS, LOCAL_VERSION, read_json

from forever.pipeline.install import stable_talent_keys


def doc(*talents, spells=None):
    return {"classes": {"Druid": {"trees": [{"talents": list(talents)}], "spells": spells or {}}}}


def talent(key, name, node, spell, **extra):
    return {"key": key, "name": name, "node_id": node, "spell_id": spell, **extra}


def test_a_talent_renamed_by_the_client_keeps_its_key():
    previous = doc(talent("predatoryInstincts", "Predatory Instincts", 1, 10))
    current = doc(
        talent("naturalInstinct", "Natural Instinct", 1, 10),
        spells={"x": {"talent": {"node_id": 1, "key": "naturalInstinct"}}},
    )
    renamed = stable_talent_keys(previous, current)
    (t,) = current["classes"]["Druid"]["trees"][0]["talents"]
    assert (t["key"], t["name"], t["client_key"], t["former_names"]) == (
        "predatoryInstincts",
        "Natural Instinct",
        "naturalInstinct",
        ["Predatory Instincts"],
    )
    assert current["classes"]["Druid"]["spells"]["x"]["talent"]["key"] == "predatoryInstincts"
    assert renamed == [("Druid", "naturalInstinct", "predatoryInstincts")]


def test_aliases_and_key_are_carried_to_the_next_version():
    previous = doc(
        talent(
            "predatoryInstincts",
            "Natural Instinct",
            1,
            10,
            client_key="naturalInstinct",
            former_names=["Predatory Instincts"],
        )
    )
    current = doc(talent("naturalInstinct", "Natural Instinct", 1, 10))
    stable_talent_keys(previous, current)
    (t,) = current["classes"]["Druid"]["trees"][0]["talents"]
    assert (t["key"], t["former_names"]) == ("predatoryInstincts", ["Predatory Instincts"])


def test_a_second_rename_appends_the_alias_once():
    previous = doc(talent("a", "B", 1, 10, client_key="b", former_names=["A"]))
    current = doc(talent("c", "C", 1, 10))
    stable_talent_keys(previous, current)
    (t,) = current["classes"]["Druid"]["trees"][0]["talents"]
    assert (t["key"], t["name"], t["client_key"], t["former_names"]) == ("a", "C", "c", ["A", "B"])


def test_a_node_with_another_spell_is_another_talent():
    previous = doc(talent("kingOfTheJungle", "King of the Jungle", 1, 10))
    current = doc(talent("shiftingPower", "Shifting Power", 1, 99))
    before = copy.deepcopy(current)
    assert stable_talent_keys(previous, current) == []
    assert current == before


def test_a_key_taken_by_another_node_is_not_reused():
    previous = doc(talent("a", "A", 1, 10))
    current = doc(talent("b", "B", 1, 10), talent("a", "A2", 2, 20))
    assert stable_talent_keys(previous, current) == []
    assert [t["key"] for t in current["classes"]["Druid"]["trees"][0]["talents"]] == ["b", "a"]


def test_installed_keys_are_stable_from_the_previous_version():
    """Même nœud et même sort entre la version installée et la précédente : même clé, ancien nom en alias."""
    previous_version = INSTALLED_VERSIONS[INSTALLED_VERSIONS.index(LOCAL_VERSION) - 1]
    before = read_json(DATA_DIR / previous_version / "classes.json")["classes"]
    after = read_json(DATA_DIR / LOCAL_VERSION / "classes.json")["classes"]
    checked = 0
    for name, cls in after.items():
        old = {t["node_id"]: t for tree in before.get(name, {}).get("trees", []) for t in tree["talents"]}
        for tree in cls["trees"]:
            for t in tree["talents"]:
                p = old.get(t["node_id"])
                if p is None or p["spell_id"] != t["spell_id"]:
                    continue
                checked += 1
                assert t["key"] == p["key"], (name, t["key"], p["key"])
                if t["name"] != p["name"]:
                    assert p["name"] in t.get("former_names", []), (name, t["key"])
    assert checked > 0
