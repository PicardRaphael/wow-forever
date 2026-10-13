"""Quêtes nouvellement vues par le client dans `forever update` (T04d, bloc B) : une quête du cache archivé absente
de `quest_rewards.json` installé donne une révision, jamais une écriture silencieuse.

Cache : `tests/fixtures/client/questcache_sample.wdb` (build 70338). Aucun réseau."""

import json
import shutil

from conftest import FIXTURES, LOCAL_VERSION

from forever.archive import ARCHIVE_DIR, QUESTCACHE
from forever.update import seen_quest_gap

SAMPLE = FIXTURES / "client" / "questcache_sample.wdb"
BUILD = LOCAL_VERSION.rsplit(".", 1)[-1]


def archive_sample(cache_dir):
    folder = cache_dir / ARCHIVE_DIR / "70338"
    folder.mkdir(parents=True)
    shutil.copyfile(SAMPLE, folder / QUESTCACHE)


def test_no_archive_means_no_gap(tmp_path, data_copy):
    assert seen_quest_gap(tmp_path / "cache", data_copy, LOCAL_VERSION) == []


def test_installed_quests_cover_the_archive(tmp_path, data_copy):
    archive_sample(tmp_path / "cache")
    assert BUILD == "70338"
    assert seen_quest_gap(tmp_path / "cache", data_copy, LOCAL_VERSION) == []


def test_a_quest_missing_from_the_installed_file_is_a_gap(tmp_path, data_copy):
    archive_sample(tmp_path / "cache")
    path = data_copy / LOCAL_VERSION / "quest_rewards.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["seen_quests"]["479"]
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    assert seen_quest_gap(tmp_path / "cache", data_copy, LOCAL_VERSION) == [479]
