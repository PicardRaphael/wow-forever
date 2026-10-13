"""Les règles de lecture nouvelles d'une tranche (`decode_rules.json` modifié dans le dépôt, lu par `forever decode`)
sont installées par l'installation elle-même (T04f, décision 263) : changement `rules` listé, manifeste réécrit,
aucune copie à la main. Seul `decode_rules.json` peut différer du manifeste, et seulement s'il est identique aux règles
portées par la candidate.

Candidate décodée des fixtures 1.60.1.70124 ; installation sur une copie des données ramenée à cette version."""

import json

import pytest
from conftest import CLASS_FIXTURE_VERSION as LOCAL_VERSION  # version des extraits, pas la version installée
from conftest import WAGO_70124, isolated_deps, read_json

from forever.errors import DataIntegrityError
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install, plan_install, render_install_report
from forever.store import ensure_integrity

RULES = "decode_rules.json"
NEW_KEY = "t04f_test_rule"


def add_rule(data_dir, key=NEW_KEY, value=None):
    path = data_dir / LOCAL_VERSION / RULES
    doc = read_json(path)
    doc[key] = value or {"note": "règle de lecture de test"}
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


@pytest.fixture
def pending(data_at_class_fixture_version, tmp_path):
    """Copie des données dont les règles portent une clé nouvelle (manifeste non réécrit), et la candidate décodée
    avec ces règles."""
    data = data_at_class_fixture_version
    add_rule(data)
    cand = decode_version(
        isolated_deps(tmp_path, data_dir=data), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand"
    )
    return data, cand


def rules_changes(plan_or_revision):
    return [c for c in plan_or_revision["changes"] if c["rule"] == "rules"]


def test_plan_lists_the_new_rules(pending, make_deps):
    data, cand = pending
    plan = plan_install(make_deps(data_dir=data), str(cand.root))
    assert [c["path"] for c in rules_changes(plan)] == [NEW_KEY] and not plan["refused"]
    assert plan["counts"]["rules"] == 1
    assert "règles de lecture" in render_install_report(plan)


def test_install_takes_the_new_rules_and_rewrites_the_manifest(pending, make_deps):
    data, cand = pending
    revision = apply_install(make_deps(data_dir=data), str(cand.root), motif="test")
    assert [c["path"] for c in rules_changes(revision)] == [NEW_KEY]
    ensure_integrity(data)  # manifeste réécrit par l'installation : plus aucun écart
    installed = read_json(data / LOCAL_VERSION / RULES)
    assert installed[NEW_KEY] == {"note": "règle de lecture de test"} and "inherited_from" not in installed
    history = read_json(data / LOCAL_VERSION / "revisions.json")["revisions"]
    assert rules_changes(history[-1])


def test_rules_changed_after_the_decode_are_refused(pending, make_deps):
    data, cand = pending
    add_rule(data, NEW_KEY, {"note": "autre règle"})
    with pytest.raises(DataIntegrityError) as err:
        plan_install(make_deps(data_dir=data), str(cand.root))
    assert RULES in err.value.message and "forever decode" in err.value.action


def test_another_modified_file_is_still_refused(pending, make_deps):
    data, cand = pending
    path = data / LOCAL_VERSION / "mechanics.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(DataIntegrityError):
        plan_install(make_deps(data_dir=data), str(cand.root))


def test_without_pending_rules_nothing_is_listed(data_at_class_fixture_version, tmp_path, make_deps):
    data = data_at_class_fixture_version
    cand = decode_version(
        isolated_deps(tmp_path, data_dir=data), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / "cand"
    )
    assert rules_changes(plan_install(make_deps(data_dir=data), str(cand.root))) == []
