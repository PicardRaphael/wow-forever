"""Contrôle de forme de `pets.json` (CH0, bloc A) : `pets_errors` et `forever verify` d'une candidate.

Chaque défaut est posé sur une copie du document décodé des fixtures ; le message nomme ce qui est refusé."""

import copy
import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, isolated_deps, read_json

from forever.manifest import write_manifest
from forever.pipeline.decode import decode_version
from forever.pipeline.pets import PETS_FILE, decode_pets, load_pet_tables, pets_errors
from forever.pipeline.verify import verify_version

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")


@pytest.fixture(scope="module")
def doc():
    return decode_pets(load_pet_tables(WAGO_70124, RULES), RULES, LOCAL_VERSION)


def test_decoded_document_has_no_error(doc):
    assert pets_errors(doc) == []


def test_family_without_ability_is_refused(doc):
    bad = copy.deepcopy(doc)
    bad["families"]["wolf"]["abilities"] = []
    errors = pets_errors(bad)
    assert any("wolf" in e and "capacité" in e for e in errors), errors


def test_rank_without_level_is_refused(doc):
    bad = copy.deepcopy(doc)
    bad["abilities"]["bite"]["ranks"][1]["level"] = None
    errors = pets_errors(bad)
    assert any("bite" in e and "rang 2" in e and "niveau" in e for e in errors), errors


@pytest.mark.parametrize("change", ["trou", "doublon"])
def test_rank_numbering_with_a_gap_or_a_duplicate_is_refused(doc, change):
    bad = copy.deepcopy(doc)
    ranks = bad["abilities"]["bite"]["ranks"]
    if change == "trou":
        del ranks[1]
    else:
        ranks[2]["rank"] = ranks[1]["rank"]
    errors = pets_errors(bad)
    assert any("bite" in e and "rangs" in e for e in errors), errors


def test_ability_unknown_to_the_abilities_table_is_refused(doc):
    bad = copy.deepcopy(doc)
    bad["families"]["wolf"]["abilities"].append("inconnue")
    errors = pets_errors(bad)
    assert any("wolf" in e and "inconnue" in e for e in errors), errors


def test_verify_refuses_a_broken_pets_json_in_a_candidate(tmp_path):
    deps = isolated_deps(tmp_path)
    cand = decode_version(deps, LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand")
    work = tmp_path / "work"
    shutil.copytree(cand.root, work)
    path = work / LOCAL_VERSION / PETS_FILE
    data = read_json(path)
    data["families"]["wolf"]["abilities"] = []
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(work)
    report = verify_version(deps, str(work))
    assert not report["ok"] and any(PETS_FILE in e and "wolf" in e for e in report["errors"]), report["errors"]
