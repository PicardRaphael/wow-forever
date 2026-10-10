"""Calendrier des relevés de la réserve (P06b, bloc A, décision 235) : attente après la réponse prête et relevés
consommés, sur les neuf durées réelles du journal du pont (`tests/fixtures/bridge/reply_seconds.json`) ; le
calendrier de l'addon est celui de `polls.PROPOSED`."""

import json

import pytest
from conftest import FIXTURES

from forever.bridge.polls import CURRENT, PROPOSED, poll_wait, polls_used

SECONDS = json.loads((FIXTURES / "bridge" / "reply_seconds.json").read_text(encoding="utf-8"))["seconds"]


def test_schedules():
    assert CURRENT[:8] == (3, 7, 11, 15, 19, 23, 27, 30) and CURRENT[-1] == 190
    assert PROPOSED[:4] == (2, 4, 8, 12) and 60 in PROPOSED and 64 not in PROPOSED and PROPOSED[-1] == 190
    assert list(PROPOSED) == sorted(PROPOSED)


def test_wait_after_a_reply():
    assert poll_wait(CURRENT, 31.0) == 9.0
    assert poll_wait(PROPOSED, 31.0) == 1.0
    assert poll_wait(PROPOSED, 2.0) == 0.0
    with pytest.raises(ValueError):
        poll_wait(PROPOSED, 191.0)


def test_polls_used():
    assert polls_used(PROPOSED, 1.0) == 1
    assert polls_used(PROPOSED, 9.5) == 4
    assert polls_used(CURRENT, 9.5) == 3


def test_real_durations():
    assert len(SECONDS) == 9
    mean = lambda values: sum(values) / len(values)
    assert mean([poll_wait(CURRENT, s) for s in SECONDS]) == pytest.approx(2.58, abs=0.01)
    assert mean([poll_wait(PROPOSED, s) for s in SECONDS]) == pytest.approx(1.36, abs=0.01)
    assert mean([polls_used(CURRENT, s) for s in SECONDS]) == pytest.approx(5.67, abs=0.01)
    assert mean([polls_used(PROPOSED, s) for s in SECONDS]) == pytest.approx(6.22, abs=0.01)
    assert max(poll_wait(PROPOSED, s) for s in SECONDS) == pytest.approx(2.5)


def test_the_addon_uses_the_proposed_schedule():
    pytest.importorskip("lupa")
    from test_bridge_addon_lua import Game

    game = Game()
    schedule = game.lua.globals().ForeverBridge.SCHEDULE
    assert [schedule[i] for i in range(1, len(schedule) + 1)] == list(PROPOSED)
