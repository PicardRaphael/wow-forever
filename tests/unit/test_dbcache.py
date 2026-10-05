"""Correctifs du serveur lus dans `DBCache.bin` (T08c, bloc A) : format, statuts, familles d'entrées, poussée la plus
haute, hachages inconnus, recoupement avec le journal des correctifs, `forever hotfixes`. Fixture extraite du fichier
de l'utilisateur, sans `TactKey` : `tests/fixtures/hotfix/` (voir son README, dont les comptes sont lus ici)."""

import json
import re
import shutil
import struct

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.cli import main
from forever.errors import DataSchemaError
from forever.pipeline.dbcache import (
    DBCACHE_PATH,
    Entry,
    Status,
    crosscheck,
    effective,
    entry_kind,
    known_tables,
    parse_dbcache,
    read_dbcache,
    summarize_cache,
    table_hash,
    table_names,
)
from forever.pipeline.hotfixes import JOURNAL_NAME, tracked_tables

HOTFIX = FIXTURES / "hotfix"
DBCACHE = HOTFIX / "DBCache.bin"
JOURNAL = HOTFIX / "hotfixes-70170.json"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")


def readme_counts() -> dict:
    text = (HOTFIX / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)\n```", text[text.index("dbcache:début") :], re.DOTALL)
    assert block is not None
    return json.loads(block.group(1))


COUNTS = readme_counts()


@pytest.fixture(scope="module")
def cache():
    return read_dbcache(DBCACHE)


@pytest.fixture(scope="module")
def names():
    return table_names(known_tables(RULES))


@pytest.fixture(scope="module")
def resolved(cache, names):
    return effective(cache.entries, names)


def test_table_hash_is_storm_sstrhash():
    assert table_hash("TraitNode") == 0xE1432D63
    assert table_hash("traitnode") == table_hash("TraitNode")
    assert table_hash("ItemSparse") == 0x919BE54E


def test_known_tables_cover_tracked_and_pet_tables():
    known = known_tables(RULES)
    assert tracked_tables(RULES) <= known
    assert {"CreatureFamily", "ItemPetFood", "TraitNode", "Curve"} <= known
    assert "TactKey" not in known


def test_fixture_header_and_counts(cache):
    assert (cache.format, cache.build) == (COUNTS["format"], COUNTS["build"]) == (9, 70170)
    assert len(cache.entries) == COUNTS["entries"]
    assert (cache.size, cache.sha256) == (COUNTS["size"], COUNTS["sha256"])
    by_status = {s.name: sum(1 for e in cache.entries if e.status == s) for s in Status}
    assert {k: v for k, v in by_status.items() if v} == COUNTS["by_status"]
    assert cache.entries[0].offset == 44


def test_fixture_has_no_tactkey(cache):
    tact = table_hash("TactKey")
    assert all(e.table_hash != tact for e in cache.entries)
    assert b"TactKey" not in DBCACHE.read_bytes()


def test_altered_signature_is_refused():
    raw = bytearray(DBCACHE.read_bytes())
    raw[0] ^= 0xFF
    with pytest.raises(DataSchemaError):
        parse_dbcache(bytes(raw))
    raw = bytearray(DBCACHE.read_bytes())
    second = read_dbcache(DBCACHE).entries[1].offset
    raw[second] ^= 0xFF
    with pytest.raises(DataSchemaError):
        parse_dbcache(bytes(raw))


def test_other_format_is_refused():
    raw = bytearray(DBCACHE.read_bytes())
    struct.pack_into("<I", raw, 4, 8)
    with pytest.raises(DataSchemaError):
        parse_dbcache(bytes(raw))


def test_truncated_file_is_refused(cache):
    raw = DBCACHE.read_bytes()
    last = max(cache.entries, key=lambda e: len(e.data))
    with pytest.raises(DataSchemaError):
        parse_dbcache(raw[: last.offset + 32 + len(last.data) // 2])  # données de l'entrée coupées
    with pytest.raises(DataSchemaError):
        parse_dbcache(raw[: cache.entries[-1].offset + 10])  # en-tête d'entrée coupé
    with pytest.raises(DataSchemaError):
        parse_dbcache(raw[:20])  # en-tête du fichier coupé


def test_statuses_of_known_records(resolved):
    node = resolved.applicable[("TraitNode", 105928)]
    assert (node.status, node.push_id) == (Status.VALID, 112347) and node.data
    gone = resolved.applicable[("TraitNode", 105929)]
    assert (gone.status, gone.data) == (Status.DELETE, b"")
    assert ("SpellPower", 315008, 112347) in resolved.invalid
    assert ("SpellClassOptions", 73078, 112347) in resolved.notpublic
    assert ("SpellPower", 315008) not in resolved.applicable
    assert ("SpellClassOptions", 73078) not in resolved.applicable


def test_dbreply_is_never_applicable(cache, resolved):
    replies = [e for e in cache.entries if e.push_id == -1]
    assert len(replies) == 2 and all(entry_kind(e) == "dbreply" for e in replies)
    assert resolved.dbreply == {"Spell": 2}
    assert ("Spell", 15147) not in resolved.applicable


def test_item_replies_are_counted_apart(cache, resolved):
    items = [e for e in cache.entries if e.push_id >= 0x01000000]
    assert len(items) == COUNTS["pushes"]["16777936"] == 6
    assert all(entry_kind(e) == "item_reply" and e.unique_id == e.push_id for e in items)
    assert resolved.item_reply["Item"] == 1 and resolved.item_reply["ItemSparse"] == 1
    assert ("Item", 720) not in resolved.applicable and ("ItemSparse", 720) not in resolved.applicable


def test_highest_push_wins_whatever_the_file_order(cache, resolved):
    synth = [e for e in cache.entries if e.rec_id == 999901]
    assert [e.push_id for e in synth] == [100002, 100001]  # la plus haute d'abord dans le fichier
    winner = resolved.applicable[("SpellLevels", 999901)]
    assert (winner.push_id, winner.status) == (100002, Status.DELETE)


def test_equal_push_keeps_the_last_entry(names):
    th = table_hash("TraitNode")
    first = Entry(70, 5, 1, th, 42, Status.VALID, b"a", 44)
    last = Entry(70, 5, 2, th, 42, Status.VALID, b"b", 100)
    assert effective([first, last], names).applicable[("TraitNode", 42)].data == b"b"


def test_unknown_hashes_are_listed_not_applied(resolved):
    assert resolved.unknown_hash[table_hash("GlobalStrings")] == 1
    assert resolved.unknown_hash[table_hash("QuestV2CliTask")] == 1
    assert resolved.unknown_hash[table_hash("TraitNodeGroupXTraitNode")] == 46
    assert all(table in known_tables(RULES) for table, _ in resolved.applicable)


def test_tactkey_entries_are_ignored_without_trace(names):
    entry = Entry(70, -1, 0xFFFFFFFF, table_hash("TactKey"), 1, Status.NOTPUBLIC, b"", 44)
    res = effective([entry], {**names, table_hash("TactKey"): "TactKey"})
    assert not res.applicable and not res.notpublic and not res.dbreply and not res.unknown_hash


def test_summary_counts_by_table_and_status(cache, names):
    s = summarize_cache(cache, names)
    assert s["tables"]["TraitNode"] == {"VALID": 14, "DELETE": 3}
    assert s["tables"]["SpellName"] == {"VALID": 20, "DELETE": 1}
    assert s["dbreply"] == {"Spell": 2}
    assert s["max_push"] == 112349
    assert s["build"] == 70170 and s["entries"] == COUNTS["entries"]
    assert f"{table_hash('QuestV2CliTask'):#010x}" in s["unknown_hash"]


def test_crosscheck_matches_the_journal_of_the_same_build(cache, names):
    journal = read_json(JOURNAL)["entries"]
    tracked = tracked_tables(RULES)
    check = crosscheck(cache.entries, names, journal, cache.build, tracked)
    assert check.only_log == [] and check.only_cache == []
    assert check.matched == COUNTS["journal_lines"] == 192
    removed = next(e for e in journal if e["table"] == "TraitNode" and e["rec_id"] == 105928)
    fewer = [e for e in journal if e is not removed]
    check = crosscheck(cache.entries, names, fewer, cache.build, tracked)
    assert [(e["table"], e["rec_id"]) for e in check.only_cache] == [("TraitNode", 105928)]
    other_build = [{**e, "client_build": "1.60.1.70124"} for e in journal]
    check = crosscheck(cache.entries, names, other_build, cache.build, tracked)
    assert check.matched == 0 and len(check.only_cache) == 192


def wow_with_cache(tmp_path):
    root = tmp_path / "wow"
    target = root.joinpath(*(part.format(locale="enUS") for part in DBCACHE_PATH))
    target.parent.mkdir(parents=True)
    shutil.copyfile(DBCACHE, target)
    return root


def test_cli_hotfixes_reads_dbcache(tmp_path, make_deps, capsys):
    deps = make_deps(wow_dir=wow_with_cache(tmp_path))
    deps.cache_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(JOURNAL, deps.cache_dir / JOURNAL_NAME)
    code = main(["hotfixes", "--json"], deps)
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    block = data["dbcache"]
    assert block["build"] == 70170 and block["sha256"] == COUNTS["sha256"]
    assert block["tables"]["TraitNode"] == {"VALID": 14, "DELETE": 3}
    assert block["crosscheck"]["matched"] == 192
    assert block["crosscheck"]["only_log"] == [] and block["crosscheck"]["only_cache"] == []
    assert not any("non lue" in a for a in data["provenance"]["assumptions"])
    assert data["provenance"]["game_version"] == LOCAL_VERSION
    assert "TactKey" not in out


def test_cli_hotfixes_dbcache_option_and_text(tmp_path, make_deps, capsys):
    deps = make_deps()
    code = main(["hotfixes", "--dbcache", str(DBCACHE)], deps)
    out, _ = capsys.readouterr()
    assert code == 0
    assert "DBCache.bin" in out and "70170" in out and "TactKey" not in out


def test_cli_hotfixes_without_dbcache_keeps_the_note(tmp_path, make_deps, capsys):
    deps = make_deps(wow_dir=tmp_path / "vide")
    code = main(["hotfixes", "--json"], deps)
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert data["dbcache"] is None
    assert any("DBCache.bin" in a and "non lu" in a for a in data["provenance"]["assumptions"])
