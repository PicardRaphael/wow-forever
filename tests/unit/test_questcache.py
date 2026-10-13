"""Cache des quêtes du client (`questcache.wdb`, T04d, bloc B) : lecture locale et archivage par build.

Valeurs attendues : `tests/fixtures/client/questcache_sample.wdb` (extrait du cache de 1.60.1.70338 par
`scripts/extract_quest_fixtures.py questcache`, voir son README) et la fixture de Questie
(`tests/fixtures/questie/11.38.0`, quêtes de Durotar et des Tarides). Aucun réseau."""

import json
import shutil

import pytest
from conftest import FIXTURES, FakeHttp

from forever.archive import archive_client_files, archived_questcache
from forever.errors import DataSchemaError
from forever.pipeline.questcache import parse_questcache, questcache_path, read_questcache
from forever.pipeline.questie import read_questie

SAMPLE = FIXTURES / "client" / "questcache_sample.wdb"
QUESTIE = FIXTURES / "questie" / "11.38.0"


@pytest.fixture(scope="module")
def cache():
    return read_questcache(SAMPLE)


def test_header_and_record_count(cache):
    # README de la fixture : build 70338, locale enUS, 12 enregistrements
    assert (cache.build, cache.locale, len(cache.records)) == (70338, "enUS", 12)


def test_quest_479_fields(cache):
    # relevé à la main le 2026-10-13 (plan T04d, « Client : questcache.wdb »)
    q = cache.records[479]
    assert (q.level, q.min_level, q.sort_id, q.next_quest) == (16, 10, 130, 480)
    assert (q.xp_difficulty, q.xp_multiplier, q.money) == (5, 1.0, 800)


def test_dungeon_quest_multiplier_is_read_as_a_float(cache):
    # 5725 The Power to Destroy... (Ragefire Chasm) : multiplicateur relevé par Forever (I9), lu à 6 décimales
    assert cache.records[5725].xp_multiplier == pytest.approx(2.025, abs=1e-9)
    assert cache.records[5725].xp_multiplier == round(cache.records[5725].xp_multiplier, 6)


def test_fields_agree_with_questie_for_classic_quests(cache):
    quests = read_questie(QUESTIE).quests()
    common = [q for q in cache.records if q in quests]
    assert len(common) >= 5
    for quest_id in common:
        record, questie = cache.records[quest_id], quests[quest_id]
        assert (record.level, record.min_level, record.sort_id) == (
            questie.quest_level,
            questie.required_level,
            questie.zone_or_sort,
        ), quest_id


def test_forever_quests_are_read(cache):
    assert {97249, 96638} <= set(cache.records)
    assert all(cache.records[q].level > 0 for q in (97249, 96638))


def test_bad_signature_is_a_schema_error():
    raw = bytearray(SAMPLE.read_bytes())
    raw[:4] = b"XXXX"
    with pytest.raises(DataSchemaError):
        parse_questcache(bytes(raw))


def test_truncated_file_is_a_schema_error():
    raw = SAMPLE.read_bytes()
    with pytest.raises(DataSchemaError):
        parse_questcache(raw[: len(raw) // 2])


def test_record_id_must_match_its_entry():
    raw = bytearray(SAMPLE.read_bytes())
    raw[24 + 8 : 24 + 12] = (1).to_bytes(4, "little")  # premier champ du premier enregistrement
    with pytest.raises(DataSchemaError):
        parse_questcache(bytes(raw))


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "World of Warcraft" / "_classic_beta_"
    live = questcache_path(root)
    live.parent.mkdir(parents=True)
    shutil.copyfile(SAMPLE, live)
    return root


def test_questcache_is_archived_by_build(wow, make_deps):
    deps = make_deps(wow_dir=wow, http=FakeHttp.failing())
    result = archive_client_files(deps)
    assert not result.errors
    archived = archived_questcache(deps.cache_dir, "70338")
    assert archived is not None and archived.read_bytes() == SAMPLE.read_bytes()
    index = json.loads((deps.cache_dir / "dbcache" / "70338" / "index.json").read_text(encoding="utf-8"))
    entry = next(c for c in index["copies"] if c["kind"] == "questcache")
    assert entry["records"] == 12
    # second passage sans changement : aucune nouvelle copie
    again = archive_client_files(deps)
    assert not [c for c in again.copies if c.kind == "questcache" and c.new]


def test_unreadable_questcache_is_not_archived(wow, make_deps):
    live = questcache_path(wow)
    live.write_bytes(SAMPLE.read_bytes()[:100])
    deps = make_deps(wow_dir=wow, http=FakeHttp.failing())
    result = archive_client_files(deps)
    assert any("questcache" in e for e in result.errors)
    assert archived_questcache(deps.cache_dir, "70338") is None
