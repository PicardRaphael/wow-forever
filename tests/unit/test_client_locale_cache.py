"""Caches du client rangés par langue (`Cache/ADB/<langue>/DBCache.bin`, `Cache/WDB/<langue>/questcache.wdb`) :
trouvés quelle que soit la langue du client (enUS, frFR…), et textes d'un cache d'une autre langue que l'anglais
jamais écrits dans les tables anglaises (demande de l'utilisateur du 2026-10-31 : client frFR sur le portable, peut-être
enUS ensuite).

Dossier du client construit dans `tmp_path` ; `DBCache.bin` (build 70170) : `tests/fixtures/hotfix/`. Aucun réseau."""

import json
import os
import shutil

from conftest import FIXTURES, FakeHttp
from test_bridge_loop import NOW, Clock
from test_hotfix_overlay import RULES, WAGO, by_id, source

from forever.archive import archive_client_files, archived_dbcache, archived_locale
from forever.bridge.journal import Journal
from forever.bridge.updater import CHECK_S, SETTLE_S, UpdateOnClose
from forever.pipeline.client_files import locale_of, locate, text_locale
from forever.pipeline.dbcache import DBCACHE_PATH, locate_dbcache
from forever.pipeline.decode import load_tables
from forever.pipeline.hotfix_overlay import apply_hotfixes
from forever.pipeline.questcache import locate_questcache

HOTFIX = FIXTURES / "hotfix"
DBCACHE = HOTFIX / "DBCache.bin"
HEADER = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"


def put(wow, locale, name="DBCache.bin", folder=("Cache", "ADB"), data=b"x", mtime=None):
    path = wow.joinpath(*folder, locale, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def config(wow, locale):
    path = wow / "WTF" / "Config.wtf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'SET portal "EU"\nSET textLocale "{locale}"\nSET audioLocale "{locale}"\n', encoding="utf-8")


# --- Emplacement --------------------------------------------------------------------------------------------------


def test_a_single_cache_is_found_whatever_its_language(tmp_path):
    path = put(tmp_path, "frFR")
    assert locate_dbcache(tmp_path) == (path, "frFR")


def test_the_language_of_config_wtf_wins_over_a_more_recent_cache(tmp_path):
    english = put(tmp_path, "enUS", mtime=1_000)
    put(tmp_path, "frFR", mtime=2_000)
    config(tmp_path, "enUS")
    assert text_locale(tmp_path) == "enUS"
    assert locate_dbcache(tmp_path) == (english, "enUS")


def test_without_config_wtf_the_most_recent_cache_wins(tmp_path):
    put(tmp_path, "enUS", mtime=1_000)
    french = put(tmp_path, "frFR", mtime=2_000)
    assert locate_dbcache(tmp_path) == (french, "frFR")


def test_a_config_language_without_its_cache_falls_back_on_the_caches_present(tmp_path):
    french = put(tmp_path, "frFR")
    config(tmp_path, "deDE")
    assert locate_dbcache(tmp_path) == (french, "frFR")


def test_no_cache_gives_none(tmp_path):
    assert locate_dbcache(tmp_path) is None
    assert locate_dbcache(None) is None
    (tmp_path / "Cache" / "ADB" / "Temp").mkdir(parents=True)  # dossier qui n'est pas une langue : ignoré
    put(tmp_path, "Temp")
    assert locate(tmp_path, DBCACHE_PATH) is None


def test_the_quest_cache_follows_the_same_rule(tmp_path):
    path = put(tmp_path, "frFR", name="questcache.wdb", folder=("Cache", "WDB"))
    assert locate_questcache(tmp_path) == (path, "frFR")


def test_the_language_of_a_given_path_comes_from_its_folder(tmp_path):
    assert locale_of(tmp_path / "Cache" / "ADB" / "frFR" / "DBCache.bin") == "frFR"
    assert locale_of(tmp_path / "ailleurs" / "DBCache.bin") == "enUS"


# --- Archivage ----------------------------------------------------------------------------------------------------


def french_client(tmp_path):
    wow = tmp_path / "World of Warcraft" / "_classic_beta_"
    (wow / "Logs").mkdir(parents=True)
    (wow.parent / ".build.info").write_text(f"{HEADER}\neu|1|1.60.1.70170|wow_classic_beta\n", encoding="utf-8")
    shutil.copyfile(DBCACHE, put(wow, "frFR"))
    return wow


def test_a_french_client_is_archived_with_its_language(tmp_path, make_deps):
    deps = make_deps(wow_dir=french_client(tmp_path), http=FakeHttp.failing())
    result = archive_client_files(deps)
    assert result.errors == []
    copy = archived_dbcache(deps.cache_dir, "70170")
    assert copy is not None and copy.read_bytes() == DBCACHE.read_bytes()
    index = json.loads((copy.parent / "index.json").read_text(encoding="utf-8"))
    assert [c["locale"] for c in index["copies"] if c["kind"] == "dbcache"] == ["frFR"]
    assert archived_locale(copy) == "frFR"


def test_an_archived_copy_without_language_is_english(tmp_path):
    folder = tmp_path / "dbcache" / "70170"
    folder.mkdir(parents=True)
    shutil.copyfile(DBCACHE, folder / "DBCache.bin")
    (folder / "index.json").write_text(
        json.dumps({"schema_version": 1, "copies": [{"kind": "dbcache", "file": "DBCache.bin"}]}), encoding="utf-8"
    )
    assert archived_locale(folder / "DBCache.bin") == "enUS"
    assert archived_locale(tmp_path / "absent" / "DBCache.bin") == "enUS"


# --- Textes d'un cache d'une autre langue -------------------------------------------------------------------------


def test_a_french_cache_keeps_the_english_texts_and_applies_the_numbers():
    tables = load_tables(WAGO, RULES)
    english = by_id(tables["Spell"])[1680]["Description_lang"]
    ov = apply_hotfixes(tables, source()._replace(locale="frFR"), WAGO)
    assert by_id(ov.tables["Spell"])[1680]["Description_lang"] == english  # texte d'avant gardé
    assert by_id(ov.tables["TraitNode"])[105928]["PosX"] == 5620  # chiffres corrigés appliqués
    kept = ov.listed["foreign_strings"]
    assert kept["locale"] == "frFR"
    assert {"table": "Spell", "rec_id": 1680} in kept["kept"]
    assert {"table": "Spell", "rec_id": 1323963} in kept["added"]  # ligne nouvelle : texte du cache, signalé


def test_an_english_cache_applies_its_texts():
    ov = apply_hotfixes(load_tables(WAGO, RULES), source(), WAGO)
    assert "both melee weapons" in by_id(ov.tables["Spell"])[1680]["Description_lang"]
    assert ov.listed["foreign_strings"] == {"locale": "enUS", "kept": [], "added": []}


# --- Pont ---------------------------------------------------------------------------------------------------------


def test_the_bridge_follows_the_cache_of_the_current_language(tmp_path):
    clock = Clock()
    launched = []
    trigger = UpdateOnClose(
        game_running=lambda: True,
        dbcache=lambda: (locate_dbcache(tmp_path) or (None, None))[0],
        journal=Journal(tmp_path / "journal", lambda: NOW),
        clock=clock,
        launch=lambda: launched.append(1) or True,
    )
    trigger.tick()  # premier relevé : aucun cache encore (jeu jamais lancé)
    put(tmp_path, "frFR", data=b"premiere session")
    end = clock.t + CHECK_S + SETTLE_S + 2 * CHECK_S
    while clock.t < end:
        clock.t += 1.0
        trigger.tick()
    assert launched == [1]
