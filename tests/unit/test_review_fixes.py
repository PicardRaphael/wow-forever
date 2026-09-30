"""Corrections issues de la relecture de T03 : suppression sûre avec --force, refus d'écrire dans les données,
comparaison de `tooltip_values`, code de sortie de `report`, provenance de `decode`, version validée."""

import json
import shutil

import pytest
from conftest import PREVIOUS_VERSION, WAGO_70009, read_json

from forever.cli import main
from forever.errors import CandidateExistsError, InvalidArgumentError
from forever.manifest import compute_manifest, write_manifest
from forever.pipeline.decode import decode_version
from forever.pipeline.diff import diff_versions
from forever.store import current_identity


def test_force_refuses_a_data_dir_that_is_not_a_candidate(make_deps, data_copy):
    before = compute_manifest(data_copy)
    with pytest.raises(CandidateExistsError):
        decode_version(make_deps(), PREVIOUS_VERSION, csv_dir=WAGO_70009, out=data_copy, force=True)
    assert compute_manifest(data_copy) == before


def test_force_refuses_a_folder_without_manifest(make_deps, tmp_path):
    out = tmp_path / "autre"
    out.mkdir()
    (out / "notes.txt").write_bytes(b"a garder")
    with pytest.raises(CandidateExistsError):
        decode_version(make_deps(), PREVIOUS_VERSION, csv_dir=WAGO_70009, out=out, force=True)
    assert (out / "notes.txt").read_bytes() == b"a garder"


def test_never_writes_inside_the_data_dir(make_deps, data_copy):
    with pytest.raises(InvalidArgumentError):
        decode_version(make_deps(data_dir=data_copy), PREVIOUS_VERSION, csv_dir=WAGO_70009, out=data_copy / "cand")
    assert not (data_copy / "cand").exists()


def test_malformed_version_is_refused(capsys, make_deps):
    code = main(["decode", "--version", "1.60.x", "--csv-dir", str(WAGO_70009), "--json"], make_deps())
    assert code == 2 and json.loads(capsys.readouterr().out)["error"]["code"] == "invalid_argument"


def test_diff_compares_tooltip_values_when_both_sides_have_them(make_deps, candidate, tmp_path):
    copy = tmp_path / "cand"
    shutil.copytree(candidate.root, copy)
    path = copy / PREVIOUS_VERSION / "talents.json"
    doc = read_json(path)
    ignite = next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == "ignite")
    ignite["tooltip_values"][0] = [ignite["tooltip_values"][0][0], ignite["tooltip_values"][0][1] + 1]
    path.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    write_manifest(copy)
    changes = diff_versions(make_deps(), str(candidate.root), str(copy))["changes"]
    assert [(c["key"], c["field"]) for c in changes] == [("ignite", "tooltip_values[1]")]
    repo = diff_versions(make_deps(), PREVIOUS_VERSION, str(candidate.root))["changes"]
    assert not any(str(c["field"]).startswith("tooltip_values") for c in repo)


def test_report_fails_when_verification_fails(capsys, make_deps, data_copy):
    shutil.copytree(data_copy / PREVIOUS_VERSION, data_copy / "1.60.1.70010")
    path = data_copy / "1.60.1.70010" / "talents.json"
    doc = read_json(path)
    doc["trees"][0]["talents"][0]["ranks"].pop()
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    write_manifest(data_copy)
    code = main(["report", PREVIOUS_VERSION, "1.60.1.70010", "--json"], make_deps(data_dir=data_copy))
    payload = json.loads(capsys.readouterr().out)
    assert code == 3 and payload["verify"]["ok"] is False


def test_decode_provenance_describes_the_candidate(capsys, make_deps, tmp_path):
    out = tmp_path / "c"
    code = main(
        ["decode", "--version", PREVIOUS_VERSION, "--csv-dir", str(WAGO_70009), "--out", str(out), "--json"],
        make_deps(),
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0 and payload["provenance"]["data_sha"] == current_identity(out).data_sha
