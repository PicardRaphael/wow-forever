"""Manifeste des empreintes : vérification, détection d'altération, déterminisme (critère 3)."""

import json
import re
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, MANIFEST_CORRUPTIONS, corrupt_manifest, tamper

from forever.manifest import compute_manifest, data_sha, verify, write_manifest


def test_repository_manifest_is_up_to_date():
    report = verify(DATA_DIR)
    assert report.manifest_found
    assert (report.mismatched, report.missing, report.unexpected) == ([], [], [])
    assert report.ok


def test_tampered_file_is_detected(data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    report = verify(data_copy)
    assert not report.ok
    assert report.mismatched == [f"{LOCAL_VERSION}/spells.json"]
    assert report.missing == [] and report.unexpected == []


def test_deleted_file_is_missing(data_copy):
    (data_copy / LOCAL_VERSION / "respec.json").unlink()
    report = verify(data_copy)
    assert not report.ok
    assert report.missing == [f"{LOCAL_VERSION}/respec.json"]


def test_added_file_is_unexpected(data_copy):
    (data_copy / LOCAL_VERSION / "extra.json").write_bytes(b"{}\n")
    report = verify(data_copy)
    assert not report.ok
    assert report.unexpected == [f"{LOCAL_VERSION}/extra.json"]


def test_missing_manifest_is_reported(data_copy):
    (data_copy / "manifest.json").unlink(missing_ok=True)
    report = verify(data_copy)
    assert not report.manifest_found
    assert not report.ok


@pytest.mark.parametrize("kind", MANIFEST_CORRUPTIONS)
def test_corrupt_manifest_is_reported_not_missing(data_copy, kind):
    corrupt_manifest(data_copy, kind)
    report = verify(data_copy)
    assert report.manifest_found
    assert report.manifest_error
    assert not report.ok


def test_valid_manifest_has_no_error():
    assert verify(DATA_DIR).manifest_error is None


def test_write_manifest_is_idempotent(data_copy):
    path = write_manifest(data_copy)
    first = path.read_bytes()
    write_manifest(data_copy)
    assert path.read_bytes() == first
    assert first.endswith(b"\n") and b"\r\n" not in first
    assert verify(data_copy).ok


def test_repository_manifest_matches_fresh_generation(data_copy):
    assert write_manifest(data_copy).read_bytes() == (DATA_DIR / "manifest.json").read_bytes()


def test_manifest_content():
    m = compute_manifest(DATA_DIR)
    assert m["schema_version"] == 1
    assert m["game_version"] == LOCAL_VERSION
    v = m["versions"][LOCAL_VERSION]
    assert v["product"] == "wow_classic_beta"
    assert v["version_prefix"] == "1.60."
    assert v["collected_at"] == "2026-09-26"
    assert v["hotfixes"] == []
    assert re.fullmatch(r"[0-9a-f]{12}", v["data_sha"])
    assert re.fullmatch(r"[0-9a-f]{64}", v["data_sha256"])
    assert v["data_sha256"].startswith(v["data_sha"])
    assert len(v["files"]) == 12 and {"mechanics.json", "decode_rules.json", "confirmed_changes.json"} <= set(
        v["files"]
    )


def test_data_sha_is_short_and_changes_with_content(data_copy):
    before = compute_manifest(data_copy)["versions"][LOCAL_VERSION]["data_sha"]
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    after = compute_manifest(data_copy)["versions"][LOCAL_VERSION]["data_sha"]
    assert re.fullmatch(r"[0-9a-f]{12}", before) and re.fullmatch(r"[0-9a-f]{12}", after)
    assert before != after
    assert data_sha({"a.json": "0" * 64}) != data_sha({"a.json": "1" * 64})


def test_game_version_is_highest_version_dir(data_copy):
    # Faux dossier de version plus récente (copie de 1.60.1.70009) et un dossier parasite.
    shutil.copytree(data_copy / LOCAL_VERSION, data_copy / "1.60.1.70150")
    (data_copy / "__pycache__").mkdir()
    m = compute_manifest(data_copy)
    assert m["game_version"] == "1.60.1.70150"
    assert set(m["versions"]) == {LOCAL_VERSION, "1.60.1.70150"}


def test_manifest_json_is_sorted_and_parsable():
    text = (DATA_DIR / "manifest.json").read_text(encoding="utf-8")
    data = json.loads(text)
    assert text == json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
