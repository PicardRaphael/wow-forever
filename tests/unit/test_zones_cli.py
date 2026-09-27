"""`forever lookup zones` (T04c, bloc F) : zones et donjons au niveau donné, provenance, erreurs ; fixture Questie
11.38.0 (voir test_questie_zones.py)."""

import json

from conftest import FIXTURES, FakeHttp

from forever.cli import main
from forever.provenance import validate_provenance

QUESTIE = FIXTURES / "questie" / "11.38.0"


def run_json(capsys, argv, deps):
    code = main([*argv, "--json"], deps)
    return code, json.loads(capsys.readouterr().out)


def test_lookup_zones_level_12(capsys, make_deps):
    http = FakeHttp.failing()
    argv = ["lookup", "zones", "--level", "12", "--faction", "horde", "--questie", str(QUESTIE)]
    code, out = run_json(capsys, argv, make_deps(http=http))
    assert code == 0 and out["zones"][0]["name"] == "The Barrens"
    assert validate_provenance(out["provenance"]) == [] and out["provenance"]["certainty"] == "suppose"
    assert any("Questie" in a for a in out["provenance"]["assumptions"])
    assert http.calls == []


def test_lookup_zones_text_output(capsys, make_deps):
    code = main(["lookup", "zones", "--level", "12", "--questie", str(QUESTIE)], make_deps())
    text = capsys.readouterr().out
    assert code == 0 and "The Barrens" in text and "Wailing Caverns" in text


def test_lookup_zones_errors(capsys, make_deps, tmp_path):
    for argv in (
        ["lookup", "zones", "--level", "0", "--questie", str(QUESTIE)],
        ["lookup", "zones", "--level", "61", "--questie", str(QUESTIE)],
        ["lookup", "zones", "--questie", str(QUESTIE)],
        ["lookup", "zones", "--level", "12", "--questie", str(tmp_path / "absent")],
    ):
        code, out = run_json(capsys, argv, make_deps())
        assert code == 2 and out["error"]["code"] == "invalid_argument", argv


def test_lookup_spell_still_needs_a_name(capsys, make_deps):
    code, out = run_json(capsys, ["lookup", "spell"], make_deps())
    assert code == 2 and out["error"]["code"] == "invalid_argument"
