"""Veille des notes officielles du forum de Blizzard (T08b, bloc F ; décision 148 : lancement à la main seulement).

Sujets nouveaux ou révisés des catégories suivies, message non officiel ignoré (son sujet n'est pas lu), sujet
« Known Issues » repéré (bugs reconnus, jamais modélisés), entités reconnues par les noms des données et le
dictionnaire de mots-clés ; `robots.txt` relu à chaque passage, arrêt si une adresse suivie est interdite ; une fois
par jour au plus ; corps d'issue déterministe avec marqueur d'état. Réseau simulé ; fixtures synthétiques
(`tests/fixtures/forum/`, voir son README)."""

import json
from datetime import timedelta

import pytest
from conftest import FIXTURES, NOW, FakeHttp

from forever.cli import main
from forever.errors import FetchFailedError, OfflineError
from forever.pipeline.notes import (
    ROBOTS_URL,
    category_url,
    issue_body,
    read_notes,
    state_from_issues,
    topic_url,
)

F = FIXTURES / "forum"


def routes(robots: str = "robots.txt"):
    return {
        ROBOTS_URL: (F / robots).read_bytes(),
        category_url(349): (F / "category_349.json").read_bytes(),
        category_url(347): (F / "category_347.json").read_bytes(),
        topic_url(9001): (F / "topic_9001.json").read_bytes(),
        topic_url(9002): (F / "topic_9002.json").read_bytes(),
    }


def by_id(result):
    return {n["topic_id"]: n for n in result["notes"]}


def test_new_official_topics_are_listed_and_player_topics_ignored(make_deps):
    http = FakeHttp(routes=routes())
    result = read_notes(make_deps(http=http))
    notes = by_id(result)
    assert set(notes) == {9001, 9002}
    assert notes[9001]["change"] == "nouveau" and notes[9001]["version"] == 2
    assert topic_url(9003) not in [c[0] for c in http.calls]
    assert http.calls[0][0] == ROBOTS_URL


def test_revised_topic_is_detected_and_unchanged_one_is_not(make_deps):
    state = {
        "9001": {"updated_at": "2026-10-01T10:30:00.000Z", "version": 2},
        "9002": {"updated_at": "2026-09-20T10:00:00.000Z", "version": 3},
    }
    result = read_notes(make_deps(http=FakeHttp(routes=routes())), state=state)
    notes = by_id(result)
    assert set(notes) == {9002} and notes[9002]["change"] == "révisé"


def test_known_issues_are_flagged_as_acknowledged_bugs(make_deps):
    notes = by_id(read_notes(make_deps(http=FakeHttp(routes=routes()))))
    ki = notes[9002]
    assert ki["known_issues"] is True and ki["items"] == 3
    assert notes[9001]["known_issues"] is False


def test_entities_and_keywords_are_recognised(make_deps):
    notes = by_id(read_notes(make_deps(http=FakeHttp(routes=routes()))))
    names = {e["name"] for e in notes[9001]["entities"]}
    assert "Frostbolt" in names and "Ignite" in names
    registry = {k["registry"] for k in notes[9001]["keywords"]}
    assert {"A18", "I5", "K1"} <= registry
    assert "I6" in {k["registry"] for k in notes[9002]["keywords"]}


def test_disallowed_address_stops_the_reading(make_deps):
    http = FakeHttp(routes=routes("robots_interdit.txt"))
    with pytest.raises(FetchFailedError):
        read_notes(make_deps(http=http))
    assert [c[0] for c in http.calls] == [ROBOTS_URL]


def test_once_a_day_at_most(make_deps):
    http = FakeHttp(routes=routes())
    deps = make_deps(http=http)
    read_notes(deps)
    calls = len(http.calls)
    again = read_notes(make_deps(http=http, now=NOW + timedelta(hours=2), cache_dir=deps.cache_dir))
    assert len(http.calls) == calls and again["skipped"]


def test_offline_makes_no_call(make_deps):
    http = FakeHttp(routes=routes())
    with pytest.raises(OfflineError):
        read_notes(make_deps(http=http, offline=True))
    assert http.calls == []


def test_issue_body_is_deterministic_and_carries_its_state(make_deps):
    note = by_id(read_notes(make_deps(http=FakeHttp(routes=routes()))))[9001]
    body = issue_body(note)
    assert body == issue_body(note)
    assert topic_url(9001).replace(".json", "") in body
    state = state_from_issues([{"number": 1, "body": body}])
    assert state["9001"] == {"updated_at": note["updated_at"], "version": note["version"]}


def test_cli_notes_json(make_deps, capsys, tmp_path):
    issues = tmp_path / "issues.json"
    issues.write_text("[]", encoding="utf-8")
    code = main(["notes", "--json", "--state-from-issues", str(issues)], make_deps(http=FakeHttp(routes=routes())))
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert {n["topic_id"] for n in data["notes"]} == {9001, 9002}
    assert all(n["issue_body"] for n in data["notes"])
    assert data["provenance"]["game_version"]
