"""Commandes `forever questie info` et `forever monsters build` : sorties, codes, provenance, aucun réseau,
`forever/data/` inchangé."""

import hashlib
import json

from conftest import COMBATLOG, FIXTURES, FakeHttp, read_json

from forever.cli import main

QUESTIE = FIXTURES / "questie" / "11.38.0"


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


def test_questie_info(capsys, make_deps):
    http = FakeHttp.failing()
    code, out, _ = run(capsys, ["questie", "info", "--dir", str(QUESTIE), "--json"], make_deps(http=http))
    payload = json.loads(out)
    assert code == 0 and payload["version"] == "11.38.0" and payload["npc_count"] == 5
    assert payload["provenance"]["certainty"] == "suppose"
    code, out, _ = run(capsys, ["questie", "info", "--dir", str(QUESTIE)], make_deps(http=http))
    assert code == 0 and "11.38.0" in out and "communautaire" in out
    assert http.calls == []


def test_questie_info_missing(capsys, make_deps, tmp_path):
    code, out, _ = run(capsys, ["questie", "info", "--dir", str(tmp_path / "Questie"), "--json"], make_deps())
    assert code == 4 and json.loads(out)["error"]["code"] == "path_not_found"


def test_monsters_build(capsys, make_deps, data_copy, tmp_path):
    http = FakeHttp.failing()
    deps = make_deps(http=http, data_dir=data_copy)
    before = tree_sha(data_copy)
    argv = ["monsters", "build", "--logs", str(COMBATLOG), "--questie", str(QUESTIE), "--out", str(tmp_path / "m")]
    code, out, _ = run(capsys, [*argv, "--json"], deps)
    payload = json.loads(out)
    assert code == 0 and payload["npcs"] == 2
    table = read_json(tmp_path / "m" / "monsters.json")
    assert table["npcs"]["3099"]["levels"]["6"]["certainty"] == "certain"
    assert table["npcs"]["3099"]["levels"]["7"]["max_hp"] == table["npcs"]["3099"]["levels"]["7"]["questie_hp"]
    assert table["npcs"]["5951"]["levels"]["1"]["max_hp"] == 8
    code, out, _ = run(capsys, [*argv, "--json"], deps)
    assert code == 2 and json.loads(out)["error"]["code"] == "candidate_exists"
    code, out, _ = run(capsys, [*argv, "--force"], deps)
    assert code == 0 and out.rstrip().splitlines()[-1].startswith("Provenance")
    assert http.calls == [] and tree_sha(data_copy) == before


def test_monsters_build_never_writes_into_data(capsys, make_deps, data_copy):
    deps = make_deps(data_dir=data_copy)
    argv = ["monsters", "build", "--logs", str(COMBATLOG), "--out", str(data_copy / "x"), "--json"]
    code, out, _ = run(capsys, argv, deps)
    assert code == 2 and json.loads(out)["error"]["code"] == "invalid_argument"
