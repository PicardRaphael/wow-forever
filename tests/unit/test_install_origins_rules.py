"""Les règles d'origine nouvelles d'une tranche (`origins.json` modifié dans le dépôt, porté par la candidate) sont
installées par l'installation elle-même, comme les règles de lecture (T04f, décision 263).

Candidate décodée des fixtures 1.60.1.70124 ; installation sur une copie des données ramenée à cette version."""

import json

import pytest
from conftest import CLASS_FIXTURE_VERSION as LOCAL_VERSION  # version des extraits, pas la version installée
from conftest import WAGO_70124, isolated_deps, read_json

from forever.errors import DataIntegrityError
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install, plan_install
from forever.store import ensure_integrity

ORIGINS = "origins.json"
RULE = {
    "file": "meta.json",
    "paths": ["/t04f_test"],
    "origin": "manuel",
    "source": "règle d'origine de test",
    "reason": "test de l'installation des règles d'une tranche",
}


def add_origin_rule(data_dir, rule):
    path = data_dir / LOCAL_VERSION / ORIGINS
    doc = read_json(path)
    doc["rules"].append(rule)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


@pytest.fixture
def pending(data_at_class_fixture_version, tmp_path):
    data = data_at_class_fixture_version
    add_origin_rule(data, RULE)
    cand = decode_version(
        isolated_deps(tmp_path, data_dir=data), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand"
    )
    return data, cand


def test_new_origin_rules_are_listed_and_installed(pending, make_deps):
    data, cand = pending
    plan = plan_install(make_deps(data_dir=data), str(cand.root))
    assert [c["file"] for c in plan["changes"] if c["rule"] == "rules"] == [ORIGINS] and not plan["refused"]
    apply_install(make_deps(data_dir=data), str(cand.root), motif="test")
    ensure_integrity(data)
    assert RULE in read_json(data / LOCAL_VERSION / ORIGINS)["rules"]


def test_origin_rules_changed_after_the_decode_are_refused(pending, make_deps):
    data, cand = pending
    add_origin_rule(data, {**RULE, "paths": ["/t04f_autre"]})
    with pytest.raises(DataIntegrityError) as err:
        plan_install(make_deps(data_dir=data), str(cand.root))
    assert ORIGINS in err.value.message
