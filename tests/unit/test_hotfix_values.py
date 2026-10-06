"""Valeurs corrigées montrées (T08c, bloc D) : `forever diff` compare les valeurs des fichiers des classes et attribue
chaque ligne au correctif qui la porte ; `forever hotfixes --values` montre chaque enregistrement, avant et après ;
l'hypothèse de consultation dit si la valeur du correctif est appliquée.

Fixtures : `tests/fixtures/hotfix/`, `tests/fixtures/dbd/`, `tests/fixtures/wago/1.60.1.70170/`."""

import json
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, WAGO_70124, isolated_deps, read_json, rewind_to

from forever.cli import main
from forever.pipeline.dbd import layouts_from_json
from forever.pipeline.decode import decode_version
from forever.pipeline.hotfix_overlay import hotfix_source
from forever.pipeline.hotfixes import entity_assumptions, parse_hotfix_log, update_journal

HOTFIX = FIXTURES / "hotfix"
DBCACHE = HOTFIX / "DBCache.bin"
LAYOUTS = FIXTURES / "dbd" / "layouts-1.60.1.70170.json"
WAGO = FIXTURES / "wago" / "1.60.1.70170"
FIXTURE_VERSION = "1.60.1.70170"  # build de DBCache.bin, des dispositions et des tables des fixtures (décision 192)
RULES = read_json(DATA_DIR / FIXTURE_VERSION / "decode_rules.json")


@pytest.fixture(scope="module")
def candidates(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("t08c-d")
    doc = read_json(LAYOUTS)
    source = hotfix_source(
        DBCACHE,
        layouts_from_json(doc),
        {"repo": doc["repo"], "commit": doc["commit"], "files": {}},
        read_json(HOTFIX / "hotfixes-70170.json")["entries"],
        FIXTURE_VERSION,
        RULES,
        "2026-10-05T10:00:00Z",
    )
    without = decode_version(isolated_deps(tmp), FIXTURE_VERSION, csv_dir=WAGO, out=tmp / "sans")
    with_fix = decode_version(isolated_deps(tmp), FIXTURE_VERSION, csv_dir=WAGO, out=tmp / "avec", hotfixes=source)
    return without.root, with_fix.root


def diff_json(make_deps, capsys, a, b):
    code = main(["diff", str(a), str(b), "--json"], make_deps())
    out, _ = capsys.readouterr()
    assert code == 0, out
    return json.loads(out)


def test_diff_shows_class_values_with_their_hotfix(candidates, make_deps, capsys):
    data = diff_json(make_deps, capsys, *candidates)
    classes = [c for c in data["changes"] if c["kind"] == "class"]
    moved = next(c for c in classes if c["key"] == "Warrior Fury Flurry" and c["field"] == "col")
    assert (moved["change"], moved["old"], moved["new"]) == ("modified", 3, 2)
    assert moved["hotfix"]["pushes"] == [112347]
    assert moved["hotfix"]["first_logged_at"].startswith("2026-10-02T08:00:23")
    added = next(c for c in classes if c["change"] == "added" and c["key"] == "Warrior Fury Gore Drinker")
    assert added["hotfix"]["pushes"] == [112347]
    removed = next(c for c in classes if c["change"] == "removed" and c["key"] == "Warrior Fury Precision")
    assert removed["hotfix"]["pushes"] == [112347]
    assert data["counts"]["class"] == len(classes)


def test_diff_text_names_the_hotfix(candidates, make_deps, capsys):
    code = main(["diff", str(candidates[0]), str(candidates[1])], make_deps())
    out, _ = capsys.readouterr()
    assert code == 0
    line = next(ln for ln in out.splitlines() if "Warrior Fury Flurry" in ln and "col" in ln)
    assert "correctif 112347" in line and "2026-10-02" in line


def test_diff_without_hotfix_has_no_attribution(candidates, make_deps, capsys):
    data = diff_json(make_deps, capsys, candidates[0], candidates[0])
    assert data["changes"] == []


@pytest.fixture
def data_70170(data_copy):
    """Données ramenées au build des fixtures : `forever hotfixes --values` lit les correctifs de la version
    installée."""
    return rewind_to(data_copy, FIXTURE_VERSION)


def values_json(make_deps, capsys, data):
    deps = make_deps(data_dir=data)
    deps.cache_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HOTFIX / "hotfixes-70170.json", deps.cache_dir / "hotfixes.json")
    args = ["hotfixes", "--values", "--dbcache", str(DBCACHE), "--dbd-layouts", str(LAYOUTS), "--csv-dir", str(WAGO)]
    code = main([*args, "--json"], deps)
    out, _ = capsys.readouterr()
    assert code == 0, out
    return json.loads(out), out


def record(data, table, rec_id):
    return next(r for r in data["values"]["records"] if (r["table"], r["rec_id"]) == (table, rec_id))


def test_values_show_build_and_hotfix_value(make_deps, capsys, data_70170):
    data, out = values_json(make_deps, capsys, data_70170)
    node = record(data, "TraitNode", 105928)
    assert node["status"] == "VALID" and node["push"] == 112347 and node["seen_at"].startswith("2026-10-02")
    assert {"field": "PosX", "build": 6220, "hotfix": 5620} in node["fields"]
    assert any("Flurry" in e for e in node["entities"])
    definition = record(data, "TraitDefinition", 135484)
    assert {"field": "SpellID", "build": 1310236, "hotfix": 1323963} in definition["fields"]
    same = record(data, "TraitDefinitionEffectPoints", 25099)
    assert same["identical"] is True and same["fields"] == []
    assert "TactKey" not in out
    assert data["provenance"]["game_version"] == FIXTURE_VERSION


def test_values_list_what_is_not_applied(make_deps, capsys, data_70170):
    data, _ = values_json(make_deps, capsys, data_70170)
    listed = data["values"]["listed"]
    assert {"table": "SpellPower", "rec_id": 315008, "push": 112347} in listed["invalid"]
    assert listed["dbreply"] == {"Spell": 2}
    assert {"Curve", "TraitNodeGroupXTraitNode"} <= set(listed["not_loaded"])
    deleted = record(data, "TraitNode", 105929)
    assert deleted["status"] == "DELETE" and deleted["fields"] == []


def test_values_text(make_deps, capsys, data_70170):
    deps = make_deps(data_dir=data_70170)
    args = ["hotfixes", "--values", "--dbcache", str(DBCACHE), "--dbd-layouts", str(LAYOUTS), "--csv-dir", str(WAGO)]
    code = main(args, deps)
    out, _ = capsys.readouterr()
    assert code == 0
    assert any("TraitNode 105928" in ln and "PosX 6220 → 5620" in ln for ln in out.splitlines())


# --- Hypothèse de consultation ---------------------------------------------------------------------------------


@pytest.fixture
def journal_cache(tmp_path):
    from datetime import UTC, datetime

    from forever.pipeline.hotfixes import tracked_tables

    cache = tmp_path / "cache"
    lines = parse_hotfix_log((HOTFIX / "Hotfix.log").read_text(encoding="utf-8"), 2026)
    update_journal(cache, lines, tracked_tables(RULES), "1.60.1.70124", datetime(2026, 10, 1, 9, 0, tzinfo=UTC))
    shutil.copytree(WAGO_70124, cache / "wago" / LOCAL_VERSION)
    return cache


def test_assumption_says_not_applied(journal_cache):
    notes = entity_assumptions(journal_cache, LOCAL_VERSION, DATA_DIR / LOCAL_VERSION, "spell", "frostbolt")
    assert notes and all("valeur non appliquée" in n and "forever hotfixes --values" in n for n in notes)
    assert any("2026-09-30" in n for n in notes)


def test_assumption_says_applied_when_the_push_is_installed(journal_cache, tmp_path):
    vdir = tmp_path / "version"
    shutil.copytree(DATA_DIR / LOCAL_VERSION, vdir)
    sources = read_json(vdir / "sources.json")
    sources["revision"] = 4
    sources["hotfixes"] = {"pushes": [900001], "max_push": 900001}
    (vdir / "sources.json").write_bytes(json.dumps(sources, ensure_ascii=False, indent=2).encode("utf-8"))
    notes = entity_assumptions(journal_cache, LOCAL_VERSION, vdir, "spell", "frostbolt")
    assert notes and all("valeur appliquée (révision 4)" in n for n in notes)
