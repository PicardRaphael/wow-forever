"""Comparaison avec une route de Factoruide (RX1, bloc G, question RTE1) : lecture d'un `.fgguide` (fixture
fabriquée `tests/fixtures/route/fixture.fgguide`, structure seulement), arrêts rejoués par notre simulation, arrêts
impossibles sautés et dits, maître de classe placé, commande `forever route compare`."""

import json

import pytest
from conftest import FIXTURES
from test_engine_route import CAP, make_world, start_state
from test_route_training import _world

from forever.cli import main
from forever.compare import read_fgguide, replay_guide
from forever.errors import InvalidArgumentError
from forever.provenance import validate_provenance

GUIDE = FIXTURES / "route" / "fixture.fgguide"
WOW = FIXTURES / "addons" / "dungeons"


def test_read_fgguide():
    g = read_fgguide(GUIDE)
    assert (g.class_name, g.faction, g.from_level, g.to_level) == ("hunter", "horde", 10, 18)
    assert g.total_time == 5400.0
    assert g.stops == [("accept", 5723), ("objective", 5723), ("turnin", 5723), ("accept", 999999), ("turnin", 999999)]


def test_read_fgguide_rejects_other_files(tmp_path):
    other = tmp_path / "x.fgguide"
    other.write_text(json.dumps({"format": "autre", "outcome": {}}), encoding="utf-8")
    with pytest.raises(InvalidArgumentError):
        read_fgguide(other)
    other.write_text("pas du JSON", encoding="utf-8")
    with pytest.raises(InvalidArgumentError):
        read_fgguide(other)


def test_replay_skips_what_our_rules_refuse(game_data):
    world, _ = make_world(game_data)
    steps = [("accept", 101), ("objective", 101), ("turnin", 101), ("accept", 999), ("accept", 103), ("objective", 107)]
    replay = replay_guide(game_data, world, steps, start_state(), end_level=3, cap=CAP)
    assert [(s.kind, s.ref) for s in replay.stops] == [("accept", 101), ("objective", 101), ("turnin", 101)]
    assert [(s["quest"], s["kind"]) for s in replay.skipped] == [(999, "accept"), (103, "accept"), (107, "objective")]
    assert all(s["reason"] for s in replay.skipped)
    assert replay.result.feasible and replay.result.reached


def test_replay_places_training(game_data):
    world, _ = _world(game_data, dungeons=[])
    steps = [(k, q) for q in (101, 102, 105, 110) for k in ("accept", "objective", "turnin")]
    replay = replay_guide(game_data, world, steps, start_state(), end_level=5, cap=CAP)
    assert replay.result.feasible and not any("manqué" in w for w in replay.result.warnings)
    assert any(s.kind == "train" for s in replay.stops)


def test_route_compare_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(WOW))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    assert main(["route", "compare", str(GUIDE), "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert validate_provenance(doc["provenance"]) == []
    assert doc["request"] == {"class": "hunter", "faction": "horde", "from": 10, "to": 18}
    assert doc["theirs"]["factoruide_hours"] == pytest.approx(1.5)
    assert {s["quest"] for s in doc["theirs"]["skipped"]} >= {999999}
    for side in ("ours", "theirs"):
        assert {"hours", "xp_h", "quests"} <= set(doc[side])
    assert set(doc) >= {"common", "only_ours", "only_theirs"}
    assert main(["route", "compare", str(GUIDE)]) == 0
    assert "Factoruide" in capsys.readouterr().out
