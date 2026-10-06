"""Archivage des fichiers du client par build (T08d, bloc A, décision 182).

Dossier du client construit dans `tmp_path` ; `DBCache.bin` (build 70170) et `Hotfix.log` : `tests/fixtures/hotfix/`
(comptes lus dans son README). Aucun réseau ; rien n'est écrit hors du cache."""

import hashlib
import json
import os
import re
import shutil
from datetime import UTC, datetime

import pytest
from conftest import FIXTURES, FakeHttp

from forever.archive import (
    FAILURE_ALERT,
    archive_client_files,
    archive_line,
    archived_dbcache,
)
from forever.cli import main
from forever.pipeline.client_builds import ClientBuild, load_builds, record_build
from forever.pipeline.dbcache import entry_kind, parse_dbcache

HOTFIX = FIXTURES / "hotfix"
DBCACHE = HOTFIX / "DBCache.bin"
LOG = HOTFIX / "Hotfix.log"
HEADER = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"
# dates des fichiers posées par le test : journal du 01/10, client mis à jour le 02/10 (après la session du journal)
LOG_MTIME = datetime(2026, 10, 1, 12, 0, tzinfo=UTC).timestamp()
BUILD_INFO_MTIME = datetime(2026, 10, 2, 5, 46, 38, tzinfo=UTC).timestamp()


def readme_counts() -> dict:
    text = (HOTFIX / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)\n```", text[text.index("dbcache:début") :], re.DOTALL)
    assert block is not None
    return json.loads(block.group(1))


COUNTS = readme_counts()


def set_build_info(root, version):
    path = root.parent / ".build.info"
    path.write_text(f"{HEADER}\nus|1|{version}|wow_classic_beta\n", encoding="utf-8")
    os.utime(path, (BUILD_INFO_MTIME, BUILD_INFO_MTIME))


def live_dbcache(root):
    return root / "Cache" / "ADB" / "enUS" / "DBCache.bin"


def live_log(root):
    return root / "Logs" / "Hotfix.log"


def write_log(root, data: bytes, mtime: float = LOG_MTIME):
    path = live_log(root)
    path.write_bytes(data)
    os.utime(path, (mtime, mtime))


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "World of Warcraft" / "_classic_beta_"
    (root / "Logs").mkdir(parents=True)
    live_dbcache(root).parent.mkdir(parents=True)
    set_build_info(root, "1.60.1.70170")
    shutil.copyfile(DBCACHE, live_dbcache(root))
    write_log(root, LOG.read_bytes())
    return root


@pytest.fixture
def deps(wow, make_deps):
    return make_deps(wow_dir=wow, http=FakeHttp.failing())


def build_dir(deps, build="70170"):
    return deps.cache_dir / "dbcache" / build


def index(deps, build="70170"):
    return json.loads((build_dir(deps, build) / "index.json").read_text(encoding="utf-8"))


def copies_of(deps, kind, build="70170"):
    return [c for c in index(deps, build)["copies"] if c["kind"] == kind]


def tree_digest(root):
    out = {}
    for p in sorted(root.parent.rglob("*")):
        if p.is_file():
            out[p.relative_to(root.parent).as_posix()] = (
                hashlib.sha256(p.read_bytes()).hexdigest(),
                p.stat().st_mtime_ns,
            )
    return out


def counting_reader():
    calls = []

    def read(path):
        calls.append(path.name)
        return path.read_bytes()

    return read, calls


def max_push(raw: bytes) -> int:
    return max(e.push_id for e in parse_dbcache(raw).entries if entry_kind(e) == "push")


def test_first_pass_archives_dbcache_by_header_build(deps):
    result = archive_client_files(deps)
    assert result.errors == []
    copy = build_dir(deps) / "DBCache.bin"
    assert copy.read_bytes() == DBCACHE.read_bytes()
    made = [c for c in result.copies if c.kind == "dbcache"]
    assert len(made) == 1 and made[0].new is True and made[0].build == "70170"
    assert made[0].sha256 == COUNTS["sha256"] and made[0].size == COUNTS["size"]
    [entry] = copies_of(deps, "dbcache")
    assert entry["sha256"] == COUNTS["sha256"]
    assert entry["size"] == COUNTS["size"]
    assert entry["entries"] == COUNTS["entries"]
    assert entry["max_push"] == max_push(DBCACHE.read_bytes())
    assert entry["file"] == "DBCache.bin"
    assert archived_dbcache(deps.cache_dir, "70170") == copy
    assert archived_dbcache(deps.cache_dir, "70235") is None


def test_first_pass_archives_hotfix_log_with_build_info_fallback(deps):
    result = archive_client_files(deps)
    logs = sorted(build_dir(deps).glob("Hotfix-*.log"))
    assert len(logs) == 1
    assert logs[0].read_bytes() == LOG.read_bytes()
    [entry] = copies_of(deps, "hotfix_log")
    assert entry["file"] == logs[0].name
    assert entry["sha256"] == hashlib.sha256(LOG.read_bytes()).hexdigest()
    # la session du journal (30/09) précède le seul build relevé (02/10) : build de .build.info au moment de la copie
    assert entry["build_source"] == ".build.info"
    assert [c.new for c in result.copies if c.kind == "hotfix_log"] == [True]


def test_hotfix_log_build_comes_from_the_client_journal(deps):
    record_build(
        deps.cache_dir,
        ClientBuild("1.60.1.70124", datetime(2026, 9, 29, tzinfo=UTC), "wow_classic_beta", "test"),
    )
    archive_client_files(deps)
    assert list(build_dir(deps, "70124").glob("Hotfix-*.log"))
    assert not list(build_dir(deps, "70170").glob("Hotfix-*.log"))
    [entry] = copies_of(deps, "hotfix_log", "70124")
    assert entry["build_source"] == "client_builds.json"


def test_second_pass_without_change_reads_nothing(deps):
    archive_client_files(deps)
    read, calls = counting_reader()
    result = archive_client_files(deps, read_bytes=read)
    assert calls == []
    assert result.copies == [] and result.errors == []


def test_same_content_touched_is_not_copied_again(deps, wow):
    archive_client_files(deps)
    later = BUILD_INFO_MTIME + 3600
    os.utime(live_dbcache(wow), (later, later))
    os.utime(live_log(wow), (later, later))
    result = archive_client_files(deps)
    assert result.copies and all(c.new is False for c in result.copies)
    assert len(copies_of(deps, "dbcache")) == 1
    assert len(list(build_dir(deps).glob("Hotfix-*.log"))) == 1


def test_same_build_with_other_bytes_keeps_the_old_copy(deps, wow):
    archive_client_files(deps)
    raw = DBCACHE.read_bytes()
    last = parse_dbcache(raw).entries[-1]
    shorter = raw[: last.offset]  # une entrée retirée : fichier toujours lisible
    live_dbcache(wow).write_bytes(shorter)
    result = archive_client_files(deps)
    assert [c.new for c in result.copies if c.kind == "dbcache"] == [True]
    old_sha = hashlib.sha256(raw).hexdigest()
    assert (build_dir(deps) / "DBCache.bin").read_bytes() == shorter
    assert (build_dir(deps) / f"DBCache-{old_sha[:12]}.bin").read_bytes() == raw
    entries = copies_of(deps, "dbcache")
    assert len(entries) == 2
    assert {e["file"] for e in entries} == {"DBCache.bin", f"DBCache-{old_sha[:12]}.bin"}
    assert archived_dbcache(deps.cache_dir, "70170") == build_dir(deps) / "DBCache.bin"


def test_existing_copy_without_index_is_kept(deps, wow):
    # copie faite à la main (décision 176) avant l'archivage : aucun index
    legacy = build_dir(deps) / "DBCache.bin"
    legacy.parent.mkdir(parents=True)
    raw = DBCACHE.read_bytes()
    legacy.write_bytes(raw)
    shorter = raw[: parse_dbcache(raw).entries[-1].offset]
    live_dbcache(wow).write_bytes(shorter)
    archive_client_files(deps)
    old_sha = hashlib.sha256(raw).hexdigest()
    assert (build_dir(deps) / f"DBCache-{old_sha[:12]}.bin").read_bytes() == raw
    assert (build_dir(deps) / "DBCache.bin").read_bytes() == shorter
    assert len(copies_of(deps, "dbcache")) == 2


def test_truncated_dbcache_is_not_archived_and_is_retried(deps, wow):
    raw = DBCACHE.read_bytes()
    live_dbcache(wow).write_bytes(raw[:-10])
    result = archive_client_files(deps)
    assert any("DBCache.bin" in e for e in result.errors)
    assert not (build_dir(deps) / "DBCache.bin").exists()
    # même fichier tronqué, inchangé : relu au passage suivant (jamais marqué lu)
    read, calls = counting_reader()
    archive_client_files(deps, read_bytes=read)
    assert "DBCache.bin" in calls
    live_dbcache(wow).write_bytes(raw)
    result = archive_client_files(deps)
    assert result.errors == []
    assert (build_dir(deps) / "DBCache.bin").read_bytes() == raw


def test_startup_line_only_after_repeated_failures(deps, wow):
    live_dbcache(wow).write_bytes(DBCACHE.read_bytes()[:-10])
    for _ in range(FAILURE_ALERT - 1):
        archive_client_files(deps)
        assert archive_line(deps.cache_dir) is None
    archive_client_files(deps)
    line = archive_line(deps.cache_dir)
    assert line is not None and "DBCache.bin" in line and "\n" not in line
    live_dbcache(wow).write_bytes(DBCACHE.read_bytes())
    archive_client_files(deps)
    assert archive_line(deps.cache_dir) is None


def test_growing_hotfix_log_keeps_one_copy_per_session(deps, wow):
    archive_client_files(deps)
    base = LOG.read_bytes()
    grown = base + b"10/1 15:00:00.000  \t900002 Table SpellMisc RecID 314147 VALIDATION_RESULT_VALID\n"
    write_log(wow, grown, LOG_MTIME + 60)
    archive_client_files(deps)
    logs = sorted(build_dir(deps).glob("Hotfix-*.log"))
    assert len(logs) == 1 and logs[0].read_bytes() == grown
    [entry] = copies_of(deps, "hotfix_log")
    assert entry["sha256"] == hashlib.sha256(grown).hexdigest() and entry["size"] == len(grown)
    # nouveau démarrage du client : journal réécrit, début différent
    rewritten = b"10/1 18:00:00.000  \t900003 Table SpellMisc RecID 314147 VALIDATION_RESULT_VALID\n"
    write_log(wow, rewritten, LOG_MTIME + 120)
    archive_client_files(deps)
    logs = sorted(build_dir(deps).glob("Hotfix-*.log"))
    assert len(logs) == 2
    assert {p.read_bytes() for p in logs} == {grown, rewritten}
    # le même contenu recopié ne change rien
    write_log(wow, rewritten, LOG_MTIME + 180)
    result = archive_client_files(deps)
    assert [c.new for c in result.copies if c.kind == "hotfix_log"] == [False]
    assert len(list(build_dir(deps).glob("Hotfix-*.log"))) == 2


def test_client_build_is_recorded_even_without_combat_log(deps, wow):
    set_build_info(wow, "1.60.1.79999")
    result = archive_client_files(deps)
    assert result.client_build == "1.60.1.79999"
    assert "1.60.1.79999" in [b.build for b in load_builds(deps.cache_dir)]
    # DBCache.bin rangé par le build de son en-tête, pas par celui du client
    assert (build_dir(deps, "70170") / "DBCache.bin").is_file()


def test_client_folder_is_never_written(deps, wow):
    before = tree_digest(wow)
    archive_client_files(deps)
    live_dbcache(wow).write_bytes(DBCACHE.read_bytes()[:-10])
    after_change = tree_digest(wow)
    archive_client_files(deps)
    assert tree_digest(wow) == after_change
    assert set(before) == set(after_change)


def test_never_raises_without_client(make_deps, tmp_path):
    deps = make_deps(wow_dir=None)
    assert archive_client_files(deps) == ([], [], None)
    deps = make_deps(wow_dir=tmp_path / "absent")
    result = archive_client_files(deps)
    assert result.copies == []


def test_watch_shows_new_copies(deps, capsys):
    from forever.watch import watch

    result = watch(deps)
    archived = result["archived"]
    assert any(a["kind"] == "dbcache" and a["build"] == "70170" and a["new"] for a in archived)
    # second passage : rien de nouveau, aucune ligne
    assert watch(deps)["archived"] == []


def test_cli_watch_text_names_the_new_copy(deps, capsys):
    assert main(["watch"], deps) == 0
    assert "archivé : DBCache.bin 70170 (nouvelle copie)" in capsys.readouterr().out
