"""Ordre des quêtes (T04d, bloc D, préparation de RX1) : prérequis et chaînes respectés, cycle signalé.

Fixture : `tests/fixtures/addons/quests/` (7 exige 783, 15 exige 7 ; chaîne de Completo 783 → 7 → 15)."""

import pytest
from conftest import FIXTURES, isolated_deps

from forever.quests import build_quests, order_quests

WOW = FIXTURES / "addons" / "quests"


@pytest.fixture
def book(tmp_path):
    return build_quests(isolated_deps(tmp_path), wow_dir=WOW)


def test_order_respects_prerequisites_and_chains(book):
    result = order_quests(book, [15, 7, 783])
    assert result.order == [783, 7, 15]
    assert result.cycles == [] and result.missing_prereqs == {}


def test_missing_prerequisite_is_listed(book):
    result = order_quests(book, [15, 7])
    assert result.order == [7, 15]
    assert result.missing_prereqs == {7: [783]}


def test_a_cycle_is_reported(book):
    book.quests[783]["fields"]["prereq_all"] = {"value": [15], "source": "test", "certainty": "suppose"}
    result = order_quests(book, [15, 7, 783])
    assert result.cycles and set(result.cycles[0]) == {783, 7, 15}
    assert set(result.order) | set(result.cycles[0]) == {783, 7, 15}
