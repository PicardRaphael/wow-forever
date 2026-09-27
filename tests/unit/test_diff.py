"""Critère 3 : comparaison de deux versions de données (copie du dépôt avec une version fictive 1.60.1.70010).

Les modifications de la version fictive sont inventées pour le test ; les valeurs de départ viennent de
forever/data/1.60.1.70009/."""

import json
import shutil

import pytest
from conftest import LOCAL_VERSION, read_json, tamper

from forever.errors import DataIntegrityError, UnknownVersionError
from forever.manifest import write_manifest
from forever.pipeline.diff import diff_versions
from forever.provenance import validate_provenance

NEXT = "1.60.1.70010"


def write_json(path, doc):
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def talent(doc, key):
    return next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == key)


@pytest.fixture
def next_version(data_copy):
    """Copie de 70009 en 70010 ; `edit(fichier, fonction)` modifie un fichier puis régénère le manifeste."""
    shutil.copytree(data_copy / LOCAL_VERSION, data_copy / NEXT)

    def edit(name, change):
        path = data_copy / NEXT / name
        doc = read_json(path)
        change(doc)
        write_json(path, doc)
        write_manifest(data_copy)

    write_manifest(data_copy)
    return edit


def only(changes, **match):
    found = [c for c in changes if all(c[k] == v for k, v in match.items())]
    assert len(found) == 1, (match, changes)
    return found[0]


def test_talent_rank_change(make_deps, data_copy, next_version):
    next_version("talents.json", lambda d: talent(d, "improvedFrostbolt")["ranks"].__setitem__(0, [0.15]))
    d = diff_versions(make_deps(data_dir=data_copy), LOCAL_VERSION, NEXT)
    c = only(d["changes"], kind="talent", key="improvedFrostbolt")
    assert c == {
        "kind": "talent",
        "key": "improvedFrostbolt",
        "change": "modified",
        "field": "ranks[1]",
        "old": [0.1],
        "new": [0.15],
    }


def test_spell_added(make_deps, data_copy, next_version):
    def add(doc):
        doc["spells"]["arcane_barrage"] = dict(doc["spells"]["arcane_blast"])

    next_version("spells.json", add)
    d = diff_versions(make_deps(data_dir=data_copy), LOCAL_VERSION, NEXT)
    c = only(d["changes"], kind="spell", key="arcane_barrage")
    assert (c["change"], c["field"]) == ("added", None)
    assert d["counts"]["spell"] == 1


def test_talent_removed_and_max_changed(make_deps, data_copy, next_version):
    def change(doc):
        for tree in doc["trees"]:
            tree["talents"] = [t for t in tree["talents"] if t["key"] != "coldSnap"]
        focus = talent(doc, "arcaneFocus")
        focus["max"] = 4
        focus["ranks"] = focus["ranks"][:4]

    next_version("talents.json", change)
    changes = diff_versions(make_deps(data_dir=data_copy), LOCAL_VERSION, NEXT)["changes"]
    assert only(changes, key="coldSnap")["change"] == "removed"
    assert only(changes, key="arcaneFocus", field="max") | {} == {
        "kind": "talent",
        "key": "arcaneFocus",
        "change": "modified",
        "field": "max",
        "old": 5,
        "new": 4,
    }
    rank = only(changes, key="arcaneFocus", field="ranks[5]")
    assert (rank["change"], rank["old"], rank["new"]) == ("removed", [5], None)


def test_spell_rank_field_and_rank_count(make_deps, data_copy, next_version):
    def change(doc):
        ranks = doc["spells"]["frostbolt"]["ranks"]
        ranks[0][6] = 26  # mana du rang 1 : 25 -> 26
        ranks.append(list(ranks[-1]))

    next_version("spells.json", change)
    changes = diff_versions(make_deps(data_dir=data_copy), LOCAL_VERSION, NEXT)["changes"]
    mana = only(changes, key="frostbolt", field="ranks[1].mana")
    assert (mana["change"], mana["old"], mana["new"]) == ("modified", 25, 26)
    extra = only(changes, key="frostbolt", field="ranks[12]")
    assert extra["change"] == "added" and extra["old"] is None


def test_identical_versions_have_no_change(make_deps, data_copy, next_version):
    d = diff_versions(make_deps(data_dir=data_copy), LOCAL_VERSION, NEXT)
    assert d["changes"] == [] and d["counts"] == {"talent": 0, "spell": 0, "file": 0}
    assert (d["a"], d["b"]) == (LOCAL_VERSION, NEXT)
    assert validate_provenance(d["provenance"]) == []


def test_unknown_version(make_deps):
    with pytest.raises(UnknownVersionError) as info:
        diff_versions(make_deps(), LOCAL_VERSION, "1.60.1.99999")
    assert info.value.code == "unknown_version" and info.value.exit_code == 4


def test_integrity_is_required(make_deps, data_copy, next_version):
    tamper(data_copy / NEXT / "spells.json")
    with pytest.raises(DataIntegrityError):
        diff_versions(make_deps(data_dir=data_copy), LOCAL_VERSION, NEXT)


def test_repository_against_candidate_path(make_deps, candidate):
    d = diff_versions(make_deps(), LOCAL_VERSION, str(candidate.root))
    files = {(c["key"], c["change"]) for c in d["changes"] if c["kind"] == "file"}
    assert files == {("_source_gunba_mage_tree.json", "removed"), ("confirmed_changes.json", "removed")}
    assert d["b"] == str(candidate.root)
    assert not any(c["kind"] == "talent" and c["field"] in ("tier", "col", "prereq") for c in d["changes"])


def test_candidate_integrity_is_required(make_deps, candidate, tmp_path):
    copy = tmp_path / "cand"
    shutil.copytree(candidate.root, copy)
    tamper(copy / LOCAL_VERSION / "talents.json")
    with pytest.raises(DataIntegrityError):
        diff_versions(make_deps(), LOCAL_VERSION, str(copy))
