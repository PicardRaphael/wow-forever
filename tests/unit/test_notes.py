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
    post_page_url,
    read_notes,
    read_post,
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


# --- Lecture ciblée d'un message officiel (`forever notes --post SUJET/N`, demande de l'utilisateur du 2026-10-02) ---


def post_routes(robots: str = "robots.txt"):
    return {ROBOTS_URL: (F / robots).read_bytes(), topic_url(9004): (F / "topic_9004.json").read_bytes()}


def test_targeted_post_is_read_with_its_revision(make_deps):
    http = FakeHttp(routes=post_routes())
    post = read_post(make_deps(http=http), 9004, 3)
    assert post["post_number"] == 3 and post["version"] == 4
    assert post["updated_at"] == "2026-10-01T12:00:00.000Z"
    assert post["url"] == post_page_url(9004, 3)
    assert "Frostbolt change de façon inventée." in post["lines"]
    assert "Paragraphe inventé & final." in post["lines"]
    assert "I5" in {k["registry"] for k in post["keywords"]}
    assert [c[0] for c in http.calls] == [ROBOTS_URL, topic_url(9004)]


def test_targeted_player_post_is_refused(make_deps):
    with pytest.raises(FetchFailedError):
        read_post(make_deps(http=FakeHttp(routes=post_routes())), 9004, 2)


def test_targeted_missing_post_fails(make_deps):
    with pytest.raises(FetchFailedError):
        read_post(make_deps(http=FakeHttp(routes=post_routes())), 9004, 7)


def test_targeted_read_respects_robots_and_offline(make_deps):
    http = FakeHttp(routes={ROBOTS_URL: b"User-agent: *\nDisallow: /en/wow/t/\n"})
    with pytest.raises(FetchFailedError):
        read_post(make_deps(http=http), 9004, 3)
    assert [c[0] for c in http.calls] == [ROBOTS_URL]
    offline = FakeHttp(routes=post_routes())
    with pytest.raises(OfflineError):
        read_post(make_deps(http=offline, offline=True), 9004, 3)
    assert offline.calls == []


def test_targeted_read_leaves_the_watch_state_alone(make_deps):
    deps = make_deps(http=FakeHttp(routes={**routes(), **post_routes()}))
    read_notes(deps)
    state = (deps.cache_dir / "notes" / "state.json").read_bytes()
    read_post(deps, 9004, 3)
    assert (deps.cache_dir / "notes" / "state.json").read_bytes() == state


def test_cli_notes_post_json_carries_the_revision(make_deps, capsys):
    code = main(["notes", "--post", "9004/3", "--json"], make_deps(http=FakeHttp(routes=post_routes())))
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert data["post"]["version"] == 4 and data["post"]["topic_id"] == 9004
    assert any("révision 4" in a for a in data["provenance"]["assumptions"])
