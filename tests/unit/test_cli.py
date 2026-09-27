"""CLI : rendu texte français, --json, codes de sortie (0 succès, 2 usage, 3 intégrité, 4 introuvable)."""

import json

from conftest import LOCAL_VERSION, FakeHttp, tamper

from forever.cli import main


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


def test_manifest_requires_a_mode(capsys, make_deps):
    assert run(capsys, ["manifest"], make_deps())[0] == 2
