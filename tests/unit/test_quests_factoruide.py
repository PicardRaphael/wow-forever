"""Base de Factoruide en recoupement local (RX1, bloc A, décision 266) : lecture du cache, base absente, quêtes vues
seulement chez Factoruide, écarts, format du cache des quêtes.

Fixtures : `tests/fixtures/factoruide/forever.sql` (schéma réduit, quêtes inventées, base bâtie dans `tmp_path`) et
`tests/fixtures/addons/quests_rx1/` (README). Aucun réseau ; aucune valeur de jeu."""

import json
import sqlite3

import pytest
from conftest import FIXTURES, isolated_deps

from forever.cli import main
from forever.pipeline.factoruide import DB_REL, FACTORUIDE_COMMIT, SEEN_ONLY, diff_factoruide, load_factoruide
from forever.provenance import validate_provenance
from forever.quests import MERGE_FORMAT, STATUSES, build_quests, routable

WOW = FIXTURES / "addons" / "quests_rx1"
SQL = FIXTURES / "factoruide" / "forever.sql"
KNOWN = (990010, 990022)  # dans la fixture de Factoruide et dans nos sources (Completo, livres de Discovery)
UNSEEN = 990070  # `available` chez Factoruide, inconnue de nos sources
REMOVED = 990071  # `removed` chez Factoruide
INCOMPLETE = 990072  # `incomplete` chez Factoruide


def make_db(cache):
    path = cache / DB_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SQL.read_text(encoding="utf-8"))
    con.commit()
    con.close()
    return path


@pytest.fixture
def deps(tmp_path):
    d = isolated_deps(tmp_path)
    make_db(d.cache_dir)
    return d


def test_factoruide_db_read_locally(deps):
    db = load_factoruide(deps.cache_dir)
    assert db.status == "present"
    assert set(db.quests) == {*KNOWN, UNSEEN, REMOVED, INCOMPLETE}
    q = db.quests[UNSEEN]
    assert (q.name, q.level, q.min_level, q.status) == ("Fixture Unseen", 12, 10, "available")
    assert q.sources == ("wowhead", "att")
    assert db.provenance["commit"] == FACTORUIDE_COMMIT
    assert len(db.provenance["sha256"]) == 16
    assert db.provenance["imported_at"] == "2026-10-13 19:36:15"  # import le plus récent de la fixture


def test_factoruide_absent_is_reported(tmp_path):
    db = load_factoruide(tmp_path / "vide")
    assert db.status == "absent" and db.quests == {}
    assert db.notes and "absente" in db.notes[0]
    diff = diff_factoruide({1, 2}, db)
    assert diff["status"] == "absent" and diff["seen_only"] == []


def test_factoruide_unreadable_is_reported(tmp_path):
    path = tmp_path / DB_REL
    path.parent.mkdir(parents=True)
    path.write_bytes(b"pas une base")
    db = load_factoruide(tmp_path)
    assert db.status == "illisible" and db.quests == {}


def test_factoruide_diff_counts(deps):
    db = load_factoruide(deps.cache_dir)
    diff = diff_factoruide({*KNOWN, 1}, db)
    assert diff["status"] == "present"
    assert diff["counts"] == {
        "available": {"both": 2, "factoruide_only": 1},
        "incomplete": {"both": 0, "factoruide_only": 1},
        "removed": {"both": 0, "factoruide_only": 1},
    }
    assert diff["ours_only"] == 1
    assert [q["id"] for q in diff["seen_only"]] == [UNSEEN]
    assert diff["provenance"]["commit"] == FACTORUIDE_COMMIT


def test_seen_only_at_factoruide(deps):
    book = build_quests(deps, wow_dir=WOW)
    q = book.quests[UNSEEN]
    assert q["status"] == SEEN_ONLY and SEEN_ONLY in STATUSES
    assert q["certainty"] == "suppose"
    assert q["sources"] == ["factoruide"]
    assert routable(q) is False
    assert REMOVED not in book.quests and INCOMPLETE not in book.quests  # seules les `available` sont signalées
    for quest_id in KNOWN:
        assert book.quests[quest_id]["status"] != SEEN_ONLY
        assert "factoruide" not in book.quests[quest_id]["sources"]  # recoupement : jamais fusionnée


def test_routable_needs_a_placed_giver(deps):
    book = build_quests(deps, wow_dir=WOW)
    assert routable(book.quests[990010]) is True  # donneur de Completo positionné
    assert routable(book.quests[990060]) is False  # quête faite (QuestieConfig) : aucun donneur


def test_book_without_factoruide_has_no_seen_only(tmp_path):
    book = build_quests(isolated_deps(tmp_path), wow_dir=WOW)
    assert all(q["status"] != SEEN_ONLY for q in book.quests.values())


def test_merge_format_bumped(deps, monkeypatch):
    from forever import quests

    assert MERGE_FORMAT == 3
    first = build_quests(deps, wow_dir=WOW)
    assert not first.from_cache
    assert build_quests(deps, wow_dir=WOW).from_cache
    monkeypatch.setattr(quests, "MERGE_FORMAT", 2)
    assert not build_quests(deps, wow_dir=WOW).from_cache  # autre format : autre empreinte, cache rebâti


def test_factoruide_db_change_rebuilds_cache(deps):
    first = build_quests(deps, wow_dir=WOW)
    con = sqlite3.connect(deps.cache_dir / DB_REL)
    con.execute("INSERT INTO m_quest VALUES (990073, 'Fixture Late', 5, 5, NULL, NULL, 'att', 'available', 1, NULL)")
    con.commit()
    con.close()
    second = build_quests(deps, wow_dir=WOW)
    assert second.fingerprint != first.fingerprint and 990073 in second.quests


def test_cli_quests_diff_factoruide(capsys, tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    make_db(cache)
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(cache))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(WOW))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    assert main(["quests", "diff", "--factoruide", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["factoruide"]["counts"]["available"] == {"both": 2, "factoruide_only": 1}
    assert [q["id"] for q in doc["factoruide"]["seen_only"]] == [UNSEEN]
    assert validate_provenance(doc["provenance"]) == []
    assert main(["quests", "diff", "--factoruide"]) == 0
    text = capsys.readouterr().out
    assert SEEN_ONLY in text and str(UNSEEN) in text
