"""Quêtes nouvellement vues par le client dans `forever update` (T04d, bloc B) : une quête du cache archivé absente
de `quest_rewards.json` installé donne une révision, jamais une écriture silencieuse.

Cache : `tests/fixtures/client/questcache_sample.wdb`, archivé sous le build de la version installée ; le
`quest_rewards.json` de la copie des données est réécrit depuis ce cache (indépendant des quêtes vues installées).
Aucun réseau."""

import json
import shutil

import pytest
from conftest import FIXTURES, LOCAL_VERSION

from forever.archive import ARCHIVE_DIR, QUESTCACHE
from forever.pipeline.quest_rewards import QUEST_FILE, decode_quest_rewards
from forever.pipeline.questcache import read_questcache
from forever.update import seen_quest_gap

SAMPLE = FIXTURES / "client" / "questcache_sample.wdb"
BUILD = LOCAL_VERSION.rsplit(".", 1)[-1]


def archive_sample(cache_dir):
    folder = cache_dir / ARCHIVE_DIR / BUILD
    folder.mkdir(parents=True)
    shutil.copyfile(SAMPLE, folder / QUESTCACHE)


@pytest.fixture
def data(data_copy):
    path = data_copy / LOCAL_VERSION / QUEST_FILE
    rules = json.loads((data_copy / LOCAL_VERSION / "decode_rules.json").read_text(encoding="utf-8"))
    doc = decode_quest_rewards({"QuestXP": []}, rules, LOCAL_VERSION, cache=read_questcache(SAMPLE))
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return data_copy


def test_no_archive_means_no_gap(tmp_path, data):
    assert seen_quest_gap(tmp_path / "cache", data, LOCAL_VERSION) == []


def test_installed_quests_cover_the_archive(tmp_path, data):
    archive_sample(tmp_path / "cache")
    assert seen_quest_gap(tmp_path / "cache", data, LOCAL_VERSION) == []


def test_a_quest_missing_from_the_installed_file_is_a_gap(tmp_path, data):
    archive_sample(tmp_path / "cache")
    path = data / LOCAL_VERSION / QUEST_FILE
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["seen_quests"]["479"]
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    assert seen_quest_gap(tmp_path / "cache", data, LOCAL_VERSION) == [479]
