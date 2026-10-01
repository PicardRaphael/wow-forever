"""Correctifs du serveur listés depuis `Logs/Hotfix.log` (T08b, bloc E) : tables suivies seulement, `VALID` et
`DELETE` (`INVALID` compté à part), journal en ajout seul dans le cache, « depuis l'installation », entités touchées
reliées par les CSV, hypothèse ajoutée à `forever lookup`. Fixture : `tests/fixtures/hotfix/` (voir son README)."""

import json
import os
import shutil
from datetime import UTC, datetime

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, WAGO_70124, read_json

from forever.cli import main
from forever.pipeline.fetch import wago_dir
from forever.pipeline.hotfixes import (
    JOURNAL_NAME,
    load_journal,
    parse_hotfix_log,
    summarize,
    touched_entities,
    tracked_tables,
    update_journal,
)

LOG = FIXTURES / "hotfix" / "Hotfix.log"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
YEAR = 2026  # année du fichier de fixture (le journal n'a pas d'année)
SEEN = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def lines():
    return parse_hotfix_log(LOG.read_text(encoding="utf-8"), YEAR)


def test_parse_keeps_table_lines_only(lines):
    assert {ln.result for ln in lines} == {"VALID", "INVALID", "DELETE", "NOTPUBLIC"}
    first = next(ln for ln in lines if ln.table == "Curve")
    assert (first.push, first.rec_id, first.at) == ("112238", 124805, "2026-10-01T07:44:04.990")
    assert all(ln.table != "TactKey" or ln.push == "DBReply" for ln in lines)


def test_tracked_tables_come_from_decode_rules():
    tracked = tracked_tables(RULES)
    assert {"CurvePoint", "SpellMisc", "SpellName", "ItemSparse", "Item", "Curve"} <= tracked
    assert "Light" not in tracked and "TransmogHoliday" not in tracked


def test_journal_is_append_only(tmp_path, lines):
    tracked = tracked_tables(RULES)
    new = update_journal(tmp_path, lines, tracked, "1.60.1.70124", SEEN)
    assert new and all(e["table"] in tracked for e in new)
    assert {e["result"] for e in new} == {"VALID", "INVALID", "DELETE"}
    path = tmp_path / JOURNAL_NAME
    before = path.read_bytes()
    assert update_journal(tmp_path, lines, tracked, "1.60.1.70124", SEEN) == []
    assert path.read_bytes() == before
    assert all(e["client_build"] == "1.60.1.70124" for e in load_journal(tmp_path))


def test_summary_counts_and_ranges(tmp_path, lines):
    update_journal(tmp_path, lines, tracked_tables(RULES), "1.60.1.70124", SEEN)
    s = summarize(load_journal(tmp_path))
    assert s["tables"]["Curve"]["valid"] == 2 and s["tables"]["Curve"]["ranges"] == [[124805, 124806]]
    assert s["tables"]["ItemSparse"]["delete"] == 1
    assert s["invalid"] == {"ItemSparse": 1}
    assert "Light" not in s["tables"]


def test_since_install_uses_the_revision_date(tmp_path, lines):
    update_journal(tmp_path, lines, tracked_tables(RULES), "1.60.1.70124", SEEN)
    s = summarize(load_journal(tmp_path), since="2026-10-01")
    assert "Item" not in s["tables"]  # ligne du 30/9
    assert s["tables"]["Curve"]["valid"] == 2


def test_touched_entities_are_linked_by_csv(tmp_path, lines):
    update_journal(tmp_path, lines, tracked_tables(RULES), "1.60.1.70124", SEEN)
    found = touched_entities(load_journal(tmp_path), WAGO_70124 / "enUS", DATA_DIR / LOCAL_VERSION)
    keys = {(e["kind"], e["key"]) for e in found}
    assert ("talent", "wintersChill") in keys
    assert ("spell", "frostbolt") in keys
    assert ("item", "4381") in keys
    assert all(e["date"] for e in found)


def wow_dir(tmp_path):
    root = tmp_path / "wow"
    (root / "Logs").mkdir(parents=True)
    shutil.copyfile(LOG, root / "Logs" / "Hotfix.log")
    stamp = datetime(YEAR, 10, 1, 8, 0, tzinfo=UTC).timestamp()
    os.utime(root / "Logs" / "Hotfix.log", (stamp, stamp))
    return root


def test_cli_hotfixes_json(tmp_path, make_deps, capsys):
    deps = make_deps(wow_dir=wow_dir(tmp_path))
    code = main(["hotfixes", "--json"], deps)
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert data["summary"]["tables"]["Curve"]["valid"] == 2
    assert data["provenance"]["game_version"] == LOCAL_VERSION
    assert (deps.cache_dir / JOURNAL_NAME).is_file()


def test_lookup_names_the_server_fix(tmp_path, make_deps, capsys):
    deps = make_deps(wow_dir=wow_dir(tmp_path))
    shutil.copytree(WAGO_70124, wago_dir(deps.cache_dir, LOCAL_VERSION))
    main(["hotfixes", "--json"], deps)
    capsys.readouterr()
    code = main(["lookup", "spell", "frostbolt", "--json"], deps)
    out, _ = capsys.readouterr()
    assert code == 0
    notes = json.loads(out)["provenance"]["assumptions"]
    assert any("corrigé par le serveur le 2026-09-30" in n for n in notes)
