"""Une révision installe tous les fichiers décodés (T08b, bloc C) : `spell_scaling.json` et `character_scaling.json`
compris, avec la liste de leurs valeurs changées dans le plan, le rapport et `revisions.json` (sans blocage).

Candidate décodée des fixtures 1.60.1.70124, copiée puis modifiée (un coefficient) ; installation sur une copie des
données."""

import json
import shutil

import pytest
from conftest import LOCAL_VERSION, WAGO_70124, isolated_deps, read_json

from forever.manifest import write_manifest
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install, plan_install, render_install_report

SCALING, CHARACTER = "spell_scaling.json", "character_scaling.json"


@pytest.fixture(scope="module")
def decoded(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rev")
    return decode_version(isolated_deps(tmp), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp / "candidate")


@pytest.fixture
def cand(decoded, tmp_path):
    root = tmp_path / "cand"
    shutil.copytree(decoded.root, root)
    path = root / LOCAL_VERSION / SCALING
    doc = read_json(path)
    comp = doc["spells"]["frostbolt"][0]["components"][0]
    comp["bonus_coefficient"] = comp["bonus_coefficient"] * 2
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(root)
    return root


def test_plan_lists_changed_values_of_decoded_files(data_copy, cand, make_deps):
    plan = plan_install(make_deps(data_dir=data_copy), str(cand))
    values = [c for c in plan["changes"] if c["rule"] == "value"]
    assert any(c["file"] == SCALING and "frostbolt" in c["path"] and "bonus_coefficient" in c["path"] for c in values)
    assert not plan["refused"]
    added = [c for c in plan["changes"] if c["rule"] == "added_file"]
    assert [c["file"] for c in added] == [CHARACTER]
    report = render_install_report(plan)
    assert "bonus_coefficient" in report and CHARACTER in report


def test_revision_installs_spell_scaling_and_character_file(data_copy, cand, make_deps):
    deps = make_deps(data_dir=data_copy)
    apply_install(deps, str(cand), motif="test")
    vdir = data_copy / LOCAL_VERSION
    assert read_json(vdir / SCALING) == read_json(cand / LOCAL_VERSION / SCALING)
    assert read_json(vdir / CHARACTER) == read_json(cand / LOCAL_VERSION / CHARACTER)
    last = read_json(vdir / "revisions.json")["revisions"][-1]
    assert any(c["rule"] == "value" and c["file"] == SCALING for c in last["changes"])
    assert CHARACTER in read_json(vdir / "sources.json")["files"]
