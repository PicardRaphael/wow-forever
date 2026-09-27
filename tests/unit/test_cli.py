"""CLI : rendu texte français, --json, codes de sortie (0 succès, 2 usage, 3 intégrité, 4 introuvable)."""

import json

import pytest
from conftest import LOCAL_VERSION, MANIFEST_CORRUPTIONS, FakeHttp, corrupt_manifest, tamper

from forever.cli import main
from forever.manifest import compute_manifest


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def test_lookup_text(capsys, make_deps):
    code, out, _ = run(capsys, ["lookup", "spell", "frostbolt", "--rank", "2"], make_deps())
    assert code == 0
    for fragment in [
        "Frostbolt",
        "rang 2/11",
        "niveau 8",
        "34-38 dégâts",
        "1,8 s",
        "35 mana",
        "portée 30 m",
        "1.60.1.70009",
        "certitude certain",
    ]:
        assert fragment in out, fragment
    assert out.rstrip("\n").splitlines()[-1].startswith("Provenance")


def test_lookup_json(capsys, make_deps):
    code, out, _ = run(capsys, ["lookup", "spell", "frostbolt", "--rank", "2", "--json"], make_deps())
    assert code == 0
    data = json.loads(out)
    rank = data["ranks"][0]
    assert (rank["damage_min"], rank["damage_max"], rank["cast_time_s"], rank["mana"]) == (34, 38, 1.8, 35)
    assert data["provenance"]["game_version"] == LOCAL_VERSION
    assert data["provenance"]["certainty"] == "certain"


def test_lookup_all_ranks_text(capsys, make_deps):
    code, out, _ = run(capsys, ["lookup", "spell", "frostbolt", "--limit", "3"], make_deps())
    assert code == 0
    assert "20-22 dégâts" in out and "47-52 dégâts" in out
    assert "--offset 3" in out


def test_usage_error_exit_2(capsys, make_deps):
    assert run(capsys, ["lookup"], make_deps())[0] == 2
    assert run(capsys, ["lookup", "spell", "frostbolt", "--rank", "deux"], make_deps())[0] == 2
    assert run(capsys, ["inconnu"], make_deps())[0] == 2


def test_unknown_spell_exit_4(capsys, make_deps):
    code, _, err = run(capsys, ["lookup", "spell", "frostbollt"], make_deps())
    assert code == 4
    assert "frostbolt" in err
    assert err.rstrip("\n").splitlines()[-1].startswith("Provenance")


def test_unknown_spell_json(capsys, make_deps):
    code, out, _ = run(capsys, ["lookup", "spell", "frostbollt", "--json"], make_deps())
    assert code == 4
    data = json.loads(out)
    assert data["error"]["code"] == "unknown_spell"
    assert "frostbolt" in data["error"]["suggestions"]


def test_integrity_error_exit_3(capsys, make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    code, _, err = run(capsys, ["lookup", "spell", "frostbolt", "--rank", "2"], make_deps(data_dir=data_copy))
    assert code == 3
    assert "manifest --update" in err


def test_status_text(capsys, make_deps):
    code, out, _ = run(capsys, ["status"], make_deps(http=FakeHttp.fixture("builds_fresh.json")))
    assert code == 0
    assert LOCAL_VERSION in out
    assert "fresh" in out
    assert "intégrité ok" in out
    assert "registre 16/97" in out
    assert out.rstrip("\n").splitlines()[-1].startswith("Provenance")


def test_status_json(capsys, make_deps):
    code, out, _ = run(capsys, ["status", "--json"], make_deps(http=FakeHttp.fixture("builds_stale.json")))
    assert code == 0
    data = json.loads(out)
    assert data["local_version"] == LOCAL_VERSION
    assert data["freshness"]["freshness"] == "stale"
    assert data["integrity"]["ok"] is True
    assert data["registry_coverage"] == "16/97"


def test_status_offline_makes_no_call(capsys, make_deps):
    http = FakeHttp.fixture("builds_fresh.json")
    code, out, _ = run(capsys, ["status", "--offline", "--json"], make_deps(http=http))
    assert code == 0
    assert http.calls == []
    assert json.loads(out)["freshness"]["freshness"] == "unknown"


def test_status_reports_integrity_failure(capsys, make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    code, out, _ = run(capsys, ["status", "--json"], make_deps(data_dir=data_copy))
    assert code == 3
    data = json.loads(out)
    assert data["integrity"]["ok"] is False
    assert data["integrity"]["mismatched"] == [f"{LOCAL_VERSION}/spells.json"]


def test_manifest_check(capsys, make_deps, data_copy):
    assert run(capsys, ["manifest", "--check"], make_deps(data_dir=data_copy))[0] == 0
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    code, _, err = run(capsys, ["manifest", "--check"], make_deps(data_dir=data_copy))
    assert code == 3
    assert "spells.json" in err


def test_manifest_update(capsys, make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    code, out, _ = run(capsys, ["manifest", "--update"], make_deps(data_dir=data_copy))
    assert code == 0
    assert "manifest.json" in out
    assert run(capsys, ["manifest", "--check"], make_deps(data_dir=data_copy))[0] == 0


@pytest.mark.parametrize("kind", MANIFEST_CORRUPTIONS)
@pytest.mark.parametrize("argv", [["lookup", "spell", "frostbolt"], ["manifest", "--check"]])
def test_corrupt_manifest_is_integrity_error_without_traceback(capsys, make_deps, data_copy, argv, kind):
    corrupt_manifest(data_copy, kind)
    code, out, err = run(capsys, argv, make_deps(data_dir=data_copy))
    assert code == 3
    assert "(data_integrity)" in err
    assert "Traceback" not in out + err
    assert err.rstrip("\n").splitlines()[-1].startswith("Provenance")


@pytest.mark.parametrize("kind", MANIFEST_CORRUPTIONS)
def test_status_reports_corrupt_manifest(capsys, make_deps, data_copy, kind):
    corrupt_manifest(data_copy, kind)
    code, out, _ = run(capsys, ["status", "--json"], make_deps(data_dir=data_copy))
    assert code == 3
    integrity = json.loads(out)["integrity"]
    assert integrity["ok"] is False
    assert integrity["manifest_found"] is True
    assert integrity["manifest_error"]


def test_status_text_reports_corrupt_manifest(capsys, make_deps, data_copy):
    corrupt_manifest(data_copy)
    code, out, _ = run(capsys, ["status"], make_deps(data_dir=data_copy))
    assert code == 3
    assert "manifeste illisible" in out


def test_manifest_update_repairs_corrupt_manifest(capsys, make_deps, data_copy):
    corrupt_manifest(data_copy)
    assert run(capsys, ["manifest", "--update"], make_deps(data_dir=data_copy))[0] == 0
    assert run(capsys, ["manifest", "--check"], make_deps(data_dir=data_copy))[0] == 0


def fingerprints(data_dir):
    """(empreinte réelle des fichiers sur disque, empreinte annoncée par le manifeste)."""
    real = compute_manifest(data_dir)["versions"][LOCAL_VERSION]["data_sha"]
    declared = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))["versions"][LOCAL_VERSION]
    return real, declared["data_sha"]


@pytest.mark.parametrize(
    "argv", [["lookup", "spell", "frostbolt"], ["manifest", "--check"], ["status"]], ids=["lookup", "check", "status"]
)
def test_tampered_data_provenance_shows_disk_fingerprint(capsys, make_deps, data_copy, argv):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    real, declared = fingerprints(data_copy)
    assert real != declared
    code, out, _ = run(capsys, [*argv, "--json"], make_deps(data_dir=data_copy))
    assert code == 3
    provenance = json.loads(out)["provenance"]
    assert provenance["data_sha"] == real
    assert any(real in a and declared in a for a in provenance["assumptions"])
    code, out, err = run(capsys, argv, make_deps(data_dir=data_copy))
    assert f"données {real}" in (out or err).rstrip("\n").splitlines()[-1]


def test_intact_data_provenance_has_no_fingerprint_gap(capsys, make_deps, data_copy):
    real, declared = fingerprints(data_copy)
    assert real == declared
    code, out, _ = run(capsys, ["status", "--json"], make_deps(data_dir=data_copy))
    assert code == 0
    provenance = json.loads(out)["provenance"]
    assert provenance["data_sha"] == real
    assert not any(real in a for a in provenance["assumptions"])


def test_manifest_requires_a_mode(capsys, make_deps):
    assert run(capsys, ["manifest"], make_deps())[0] == 2
