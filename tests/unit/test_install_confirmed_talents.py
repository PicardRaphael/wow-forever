"""Règle de fusion de `forever install` : talent renommé et `tooltip_values` confirmés (installation de 1.60.1.70170).

Le client 1.60.1.70170 renomme Hot Streak en Heating Up (même nœud, même sort, même aura) et passe les charges de
Combustion de 4 à 3 (`tasks/70170-ecarts.md`, décisions de l'utilisateur du 2026-10-02 : changements du client,
clé du dépôt `hotStreak` gardée). Avant cette tranche, la fusion refusait toujours un talent absent de la candidate,
un talent nouveau et tout changement de `tooltip_values`. Un changement listé dans `confirmed_changes.json` passe
désormais ; sans entrée, il reste refusé.

Données synthétiques : deux talents aux valeurs arbitraires, sans lien avec les valeurs du jeu."""

import copy

from forever.pipeline.install import _Merge

VERSION = "1.60.1.70170"
READ_AT = "2026-10-02"


def talent(key, name, ranks, desc, spell=1, name_fr=None):
    return {
        "key": key,
        "name": name,
        "name_fr": name_fr or name,
        "tree": "Fire",
        "tier": 4,
        "col": 3,
        "max": 1,
        "ranks": ranks,
        "tooltip_values": copy.deepcopy(ranks),
        "desc": desc,
        "spellIds": [spell],
        "prereq": None,
        "certainty": "FC-70124",
    }


def doc(*talents):
    return {"trees": [{"name": "Fire", "talents": list(talents)}]}


REPO = doc(
    talent("oldName", "Old Name", [[7, 8, 9]], "Grants Old Name for {0} sec, {1}%, {2} times.", name_fr="Ancien"),
    talent("charges", "Charges", [[1, 5]], "Lasts {1} charges, {0}%."),
)
CAND = doc(
    talent("newName", "New Name", [[7, 8, 9]], "Reduces your next cast within $1d by $1s1%.", name_fr="Nouveau"),
    talent("charges", "Charges", [[1, 6]], "Lasts $n charges, $1s1%."),
)
RENAME = {
    "kind": "talent",
    "key": "oldName",
    "change": "renamed",
    "field": "key",
    "old": "oldName",
    "new": "newName",
    "desc": "Reduces your next cast within {0} sec by {1}%, stacking up to {2} times.",
    "nature": "client",
    "decision": "renommage du client (essai)",
}
RANK = {"kind": "talent", "key": "charges", "change": "modified", "field": "ranks[1]", "old": [1, 5], "new": [1, 6]}
TOOLTIP = {**RANK, "field": "tooltip_values[1]"}
DECISION = {"nature": "client", "decision": "changement du client (essai)"}


def merge(confirmed):
    m = _Merge(VERSION, [{**DECISION, **c} for c in confirmed], READ_AT)
    out = m.talents(copy.deepcopy(REPO), copy.deepcopy(CAND))
    return m, {t["key"]: t for tree in out["trees"] for t in tree["talents"]}


def test_unconfirmed_rename_and_tooltip_values_stay_refused():
    m, _ = merge([RANK])
    refused = {c["path"] for c in m.refused}
    assert {"oldName", "newName", "charges.tooltip_values[1]"} <= refused


def test_confirmed_rename_keeps_the_repository_key_and_takes_the_client_names():
    m, out = merge([RENAME, RANK, TOOLTIP])
    assert m.refused == []
    assert "newName" not in out
    t = out["oldName"]
    assert (t["name"], t["name_fr"]) == ("New Name", "Nouveau")
    assert t["desc"] == RENAME["desc"]
    assert t["source"]["client_key"] == "newName"
    assert t["former_names"] == ["Old Name"]  # l'ancien nom reste trouvable par la recherche
    assert t["source"]["client_spell_ids"] == [1]
    assert t["certainty"] == "FC-70170"
    confirmed = {c["path"]: c for c in m.changes if c["rule"] == "confirmed"}
    assert confirmed["oldName.name"]["after"] == "New Name"
    assert confirmed["oldName.desc"]["after"] == RENAME["desc"]
    assert any(e["change"] == "renamed" for e in m.applied)


def test_confirmed_tooltip_values_change_is_applied():
    m, out = merge([RENAME, RANK, TOOLTIP])
    assert out["charges"]["ranks"] == [[1, 6]]
    assert out["charges"]["tooltip_values"] == [[1, 6]]
    paths = {c["path"] for c in m.changes if c["rule"] == "confirmed"}
    assert {"charges.ranks[1]", "charges.tooltip_values[1]"} <= paths


def test_rename_to_a_key_absent_from_the_candidate_is_refused():
    m, _ = merge([{**RENAME, "new": "elsewhere"}, RANK, TOOLTIP])
    assert {c["path"] for c in m.refused} >= {"oldName", "newName"}


def test_confirmed_rename_is_applied_to_the_mage_tree_of_classes_json():
    """L'arbre du Mage de `classes.json` (décodé du client) prend la clé du dépôt : l'import du profil traduit les
    nœuds de talents par ce fichier, le moteur du Mage ne connaît que la clé de `talents.json`."""
    from forever.pipeline.install import rename_class_talents

    classes = {
        "classes": {
            "Mage": {"trees": [{"talents": [{"key": "newName", "node_id": 1}, {"key": "charges", "node_id": 2}]}]},
            "Rogue": {"trees": [{"talents": [{"key": "newName", "node_id": 3}]}]},
        }
    }
    done = rename_class_talents(classes, [{**DECISION, **RENAME}, {**DECISION, **RANK}])
    mage = classes["classes"]["Mage"]["trees"][0]["talents"]
    assert mage[0] == {"key": "oldName", "node_id": 1, "client_key": "newName"}
    assert mage[1] == {"key": "charges", "node_id": 2}
    assert classes["classes"]["Rogue"]["trees"][0]["talents"][0]["key"] == "newName"
    assert done == [("Mage", "newName", "oldName")]
