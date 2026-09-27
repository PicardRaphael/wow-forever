"""Rapport Markdown d'un changement de données (version fictive 1.60.1.70010, modifications inventées)."""

import json
import shutil

from conftest import LOCAL_VERSION, read_json

from forever.manifest import write_manifest
from forever.pipeline.diff import diff_versions
from forever.pipeline.report import render_report
from forever.pipeline.verify import verify_version

NEXT = "1.60.1.70010"


def make_next(data_copy):
    shutil.copytree(data_copy / LOCAL_VERSION, data_copy / NEXT)
    path = data_copy / NEXT / "talents.json"
    doc = read_json(path)
    next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == "improvedFrostbolt")["ranks"][0] = [0.15]
    path.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    path = data_copy / NEXT / "spells.json"
    doc = read_json(path)
    doc["spells"]["arcane_barrage"] = dict(doc["spells"]["arcane_blast"])
    path.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    write_manifest(data_copy)


def test_report_sections_and_provenance(make_deps, data_copy):
    make_next(data_copy)
    deps = make_deps(data_dir=data_copy)
    text = render_report(diff_versions(deps, LOCAL_VERSION, NEXT), verify_version(deps, NEXT))
    lines = text.rstrip("\n").splitlines()
    assert lines[0] == f"# data: {LOCAL_VERSION} → {NEXT}"
    assert "## Talents" in lines and "## Sorts" in lines
    assert sum("improvedFrostbolt" in line for line in lines) == 1
    assert sum("arcane_barrage" in line for line in lines) == 1
    assert any("2 changement" in line for line in lines)
    assert lines[-1].startswith("Provenance")


def test_report_is_deterministic(make_deps, data_copy):
    make_next(data_copy)
    deps = make_deps(data_dir=data_copy)
    first = render_report(diff_versions(deps, LOCAL_VERSION, NEXT), verify_version(deps, NEXT))
    second = render_report(diff_versions(deps, LOCAL_VERSION, NEXT), verify_version(deps, NEXT))
    assert first == second


def test_empty_diff(make_deps):
    deps = make_deps()
    text = render_report(diff_versions(deps, LOCAL_VERSION, LOCAL_VERSION))
    assert "Aucun changement" in text
    assert text.rstrip("\n").splitlines()[-1].startswith("Provenance")
