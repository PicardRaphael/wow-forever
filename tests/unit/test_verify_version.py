"""`forever verify` : intégrité, schéma et cohérence d'une version (dépôt ou candidate), un défaut par test."""

import json

import pytest
from conftest import LOCAL_VERSION, read_json, tamper

from forever.errors import DataIntegrityError
from forever.manifest import write_manifest
from forever.pipeline.decode import INHERITED_FILES
from forever.pipeline.verify import verify_version
from forever.provenance import validate_provenance


def write_json(path, doc):
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def edit(data_copy, name, change):
    path = data_copy / LOCAL_VERSION / name
    doc = read_json(path)
    change(doc)
    write_json(path, doc)
    write_manifest(data_copy)


def talent(doc, key):
    return next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == key)


def test_repository_version_is_ok(make_deps):
    r = verify_version(make_deps())
    assert r["ok"] and r["errors"] == [] and r["version"] == LOCAL_VERSION
    assert validate_provenance(r["provenance"]) == []


def test_candidate_is_ok_and_lists_inherited_files(make_deps, candidate):
    r = verify_version(make_deps(), str(candidate.root))
    assert r["ok"], r["errors"]
    assert set(r["inherited"]) == set(INHERITED_FILES)
    assert any("hérité" in a for a in r["provenance"]["assumptions"])


def failing(make_deps, data_copy, name, change):
    edit(data_copy, name, change)
    r = verify_version(make_deps(data_dir=data_copy))
    assert not r["ok"]
    return " ".join(r["errors"])


def test_ranks_shorter_than_max(make_deps, data_copy):
    errors = failing(make_deps, data_copy, "talents.json", lambda d: talent(d, "arcaneFocus")["ranks"].pop())
    assert "arcaneFocus" in errors


def test_prerequisite_on_empty_cell(make_deps, data_copy):
    errors = failing(
        make_deps, data_copy, "talents.json", lambda d: talent(d, "arcanePower").update(prereq={"tier": 6, "col": 4})
    )
    assert "arcanePower" in errors


def test_two_talents_at_same_position(make_deps, data_copy):
    def move(doc):
        talent(doc, "arcaneFocus").update(tier=1, col=1)

    errors = failing(make_deps, data_copy, "talents.json", move)
    assert "arcaneFocus" in errors and "wandSpecialization" in errors


def test_spell_rank_too_short(make_deps, data_copy):
    errors = failing(make_deps, data_copy, "spells.json", lambda d: d["spells"]["frostbolt"]["ranks"][0].pop())
    assert "spells.json" in errors


def test_spell_levels_must_not_decrease(make_deps, data_copy):
    def swap(doc):
        ranks = doc["spells"]["scorch"]["ranks"]
        ranks[0], ranks[1] = ranks[1], ranks[0]

    assert "scorch" in failing(make_deps, data_copy, "spells.json", swap)


def test_file_missing_from_sources(make_deps, data_copy):
    errors = failing(make_deps, data_copy, "sources.json", lambda d: d["files"].pop("respec.json"))
    assert "respec.json" in errors


def test_unknown_certainty(make_deps, data_copy):
    errors = failing(
        make_deps, data_copy, "sources.json", lambda d: d["files"]["respec.json"].update(certainty="peut-etre")
    )
    assert "respec.json" in errors


def test_altered_data_is_integrity_error(make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    with pytest.raises(DataIntegrityError):
        verify_version(make_deps(data_dir=data_copy))
