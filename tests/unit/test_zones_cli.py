"""`forever lookup zones` (T04c, bloc F ; décision 294) : zones et donjons au niveau donné tirés du livre de quêtes
des sources Forever (dossier du client réduit de `tests/fixtures/addons/quests/`), provenance, erreurs."""

import json

from conftest import FIXTURES, FakeHttp

from forever.cli import main
from forever.provenance import validate_provenance

WOW = FIXTURES / "addons" / "quests"


def run_json(capsys, argv, deps):
    code = main([*argv, "--json"], deps)
    return code, json.loads(capsys.readouterr().out)


def test_lookup_zones_level_12(capsys, make_deps):
    http = FakeHttp.failing()
    argv = ["lookup", "zones", "--level", "12", "--faction", "horde", "--wow", str(WOW)]
    code, out = run_json(capsys, argv, make_deps(http=http))
    assert code == 0 and out["zones"][0]["name"] == "Durotar"
    assert validate_provenance(out["provenance"]) == [] and out["provenance"]["certainty"] == "suppose"
    assert any("sources Forever" in a for a in out["provenance"]["assumptions"])
    assert http.calls == []


def test_lookup_zones_text_output(capsys, make_deps):
    code = main(["lookup", "zones", "--level", "12", "--faction", "horde", "--wow", str(WOW)], make_deps())
    text = capsys.readouterr().out
    assert code == 0 and "Durotar" in text and "Ragefire Chasm" in text


def test_lookup_zones_errors(capsys, make_deps):
    for argv in (
        ["lookup", "zones", "--level", "0", "--wow", str(WOW)],
        ["lookup", "zones", "--level", "61", "--wow", str(WOW)],
        ["lookup", "zones", "--wow", str(WOW)],
        ["lookup", "zones", "--level", "12", "--faction", "elfe", "--wow", str(WOW)],
    ):
        code, out = run_json(capsys, argv, make_deps())
        assert code == 2 and out["error"]["code"] in ("invalid_argument", "usage"), argv


def test_lookup_spell_still_needs_a_name(capsys, make_deps):
    code, out = run_json(capsys, ["lookup", "spell"], make_deps())
    assert code == 2 and out["error"]["code"] == "invalid_argument"


def test_without_class_the_answer_says_so(capsys, make_deps):
    code, out = run_json(
        capsys, ["lookup", "zones", "--level", "12", "--faction", "horde", "--wow", str(WOW)], make_deps()
    )
    assert code == 0 and any("classe inconnue" in a for a in out["provenance"]["assumptions"])
