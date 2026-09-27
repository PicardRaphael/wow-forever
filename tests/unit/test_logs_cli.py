"""Commandes `forever logs scan` et `forever logs measure` : texte et JSON, codes de sortie, provenance, aucun réseau,
`forever/data/` inchangé."""

import hashlib
import json

from conftest import COMBATLOG, LOCAL_VERSION, REAL_LOG, SYNTHETIC_LOGS, FakeHttp

from forever.cli import main


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode() + p.read_bytes())
    return h.hexdigest()


def test_logs_scan(capsys, make_deps, data_copy):
    http = FakeHttp.failing()
    deps = make_deps(http=http, data_dir=data_copy)
    before = tree_sha(data_copy)
    code, out, _ = run(capsys, ["logs", "scan", "--dir", str(COMBATLOG), "--json"], deps)
    payload = json.loads(out)
    assert code == 0
    log, second = payload["logs"]  # T04b : seconde fixture compressée (.txt.gz) listée aussi
    assert log["name"] == REAL_LOG.name and log["lines"] == 194 and log["mine"] == ["Moi-Royaume"]
    assert second["name"] == "WoWCombatLog-092726_150346.anon.txt.gz" and second["lines"] == 3330
    code, out, _ = run(capsys, ["logs", "scan", "--dir", str(COMBATLOG)], deps)
    assert code == 0 and REAL_LOG.name in out and out.rstrip().splitlines()[-1].startswith("Provenance")
    assert http.calls == [] and tree_sha(data_copy) == before


def test_logs_scan_missing_dir(capsys, make_deps, tmp_path):
    code, out, _ = run(capsys, ["logs", "scan", "--dir", str(tmp_path / "absent"), "--json"], make_deps())
    assert code == 4 and json.loads(out)["error"]["code"] == "path_not_found"


def test_logs_measure_json(capsys, make_deps, data_copy):
    http = FakeHttp.failing()
    deps = make_deps(http=http, data_dir=data_copy)
    before = tree_sha(data_copy)
    code, out, _ = run(capsys, ["logs", "measure", str(REAL_LOG), "--json"], deps)
    assert code == 0
    payload = json.loads(out)
    (log,) = payload["logs"]
    assert log["caster"] == {"guid": "Player-0000-00000000", "name": "Moi-Royaume"}
    monsters = {(m["npc_id"], m["level"]): m["max_hp"] for m in log["monsters"]}
    assert monsters == {(3099, 6): 120, (3099, 7): 137, (5951, 1): 8}
    assert log["costs"] == {"837": [50], "145": [65], "1449": [75], "2137": [75]}
    assert [round(x, 3) for x in log["gcd_intervals"]["values"]] == [1.516, 1.503, 1.59]
    assert log["gcd_intervals"]["n"] == 3
    assert log["crits"] == [{"spell_id": 145, "ratio": 1.5}]
    assert log["cast_times"]["837"] == [1.916, 2.074, 1.982]
    prov = payload["provenance"]
    assert prov["game_version"] == LOCAL_VERSION
    assert any("1.60.1" in a and "build" in a for a in prov["assumptions"])
    assert http.calls == [] and tree_sha(data_copy) == before


def test_logs_measure_text(capsys, make_deps):
    code, out, _ = run(capsys, ["logs", "measure", str(COMBATLOG)], make_deps())
    assert code == 0 and "Dire Mottled Boar" in out and out.rstrip().splitlines()[-1].startswith("Provenance")


def test_logs_measure_errors(capsys, make_deps):
    deps = make_deps()
    code, out, _ = run(capsys, ["logs", "measure", str(SYNTHETIC_LOGS / "version21.txt"), "--json"], deps)
    assert code == 3 and json.loads(out)["error"]["code"] == "unsupported_log"
    code, out, _ = run(capsys, ["logs", "measure", str(SYNTHETIC_LOGS / "truncated.txt"), "--json"], deps)
    assert code == 3 and json.loads(out)["error"]["code"] == "data_schema"
    code, out, _ = run(capsys, ["logs", "measure", str(SYNTHETIC_LOGS / "absent.txt"), "--json"], deps)
    assert code == 4 and json.loads(out)["error"]["code"] == "path_not_found"
