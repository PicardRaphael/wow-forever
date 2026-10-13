"""Cache de la liste fusionnée des quêtes (T04d, bloc D) : relu sans changement, rebâti quand une source change,
toujours hors du dépôt. Fixture : copie de `tests/fixtures/addons/quests/` dans `tmp_path`."""

import shutil

from conftest import DATA_DIR, FIXTURES, isolated_deps

from forever.quests import CACHE_DIR, build_quests

WOW = FIXTURES / "addons" / "quests"
GUIDE = "Interface/AddOns/ForeverGuide/DungeonData.lua"


def test_second_build_reads_the_cache_and_a_changed_addon_rebuilds(tmp_path):
    wow = tmp_path / "wow"
    shutil.copytree(WOW, wow)
    deps = isolated_deps(tmp_path)
    first = build_quests(deps, wow_dir=wow)
    assert not first.from_cache
    cached = list((deps.cache_dir / CACHE_DIR).glob("*.json"))
    assert len(cached) == 1 and cached[0].stem == first.fingerprint
    second = build_quests(deps, wow_dir=wow)
    assert second.from_cache and second.fingerprint == first.fingerprint
    assert second.quests.keys() == first.quests.keys()
    path = wow / GUIDE
    path.write_bytes(path.read_bytes().replace(b"lv=16,rl=9", b"lv=17,rl=9", 1))
    third = build_quests(deps, wow_dir=wow)
    assert not third.from_cache and third.fingerprint != first.fingerprint
    assert build_quests(deps, wow_dir=wow, rebuild=True).from_cache is False


def test_the_cache_lives_under_the_cache_dir_only(tmp_path):
    deps = isolated_deps(tmp_path)
    build_quests(deps, wow_dir=WOW)
    assert (deps.cache_dir / CACHE_DIR).is_dir()
    assert not (DATA_DIR / CACHE_DIR).exists() and not (WOW / CACHE_DIR).exists()


def test_no_addon_gives_an_empty_book_with_a_note(tmp_path):
    empty = tmp_path / "wow"
    (empty / "Interface" / "AddOns").mkdir(parents=True)
    book = build_quests(isolated_deps(tmp_path), wow_dir=empty)
    assert all(s["source"] == "client" for s in book.sources)
    assert any("Questie" in n for n in book.notes)
