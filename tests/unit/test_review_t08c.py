"""Relecture de T08c : règles `correctif_serveur` jamais héritées sans correctifs, entrée sans valeur d'une poussée plus
haute, dispositions d'un autre build refusées, veille d'un `DBCache.bin` illisible ou de tables non validées, validation
qui exige une comparaison ou une référence. Fixtures : `tests/fixtures/hotfix/`, `tests/fixtures/dbd/`,
`tests/fixtures/wago/1.60.1.70170/`."""

import json
import shutil
import struct

from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, isolated_deps, read_json

from forever.cli import main
from forever.manifest import write_manifest
from forever.origins import ORIGINS_NAME
from forever.pipeline.dbcache import Entry, Status, effective, known_tables, read_dbcache, table_hash, table_names
from forever.pipeline.dbd import layouts_from_json, validate_layout
from forever.pipeline.decode import decode_version
from forever.pipeline.hotfix_overlay import SERVER_ORIGIN, hotfix_source
from forever.pipeline.install import carry_hotfix_provenance
from forever.watch import watch

HOTFIX = FIXTURES / "hotfix"
DBCACHE = HOTFIX / "DBCache.bin"
LAYOUTS = FIXTURES / "dbd" / "layouts-1.60.1.70170.json"
WAGO = FIXTURES / "wago" / "1.60.1.70170"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")


def source():
    doc = read_json(LAYOUTS)
    return hotfix_source(
        DBCACHE,
        layouts_from_json(doc),
        {"repo": doc["repo"], "commit": doc["commit"], "files": {}},
        read_json(HOTFIX / "hotfixes-70170.json")["entries"],
        LOCAL_VERSION,
        RULES,
        "2026-10-05T10:00:00Z",
    )


def server_rules(path):
    return [r for r in read_json(path / ORIGINS_NAME)["rules"] if r["origin"] == SERVER_ORIGIN]


def test_decode_without_hotfixes_never_inherits_server_rules(data_copy, tmp_path):
    with_fix = decode_version(
        isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=WAGO, out=tmp_path / "avec", hotfixes=source()
    )
    vdir = data_copy / LOCAL_VERSION
    shutil.copyfile(with_fix.root / LOCAL_VERSION / "classes.json", vdir / "classes.json")
    carry_hotfix_provenance(vdir, with_fix.root / LOCAL_VERSION)
    write_manifest(data_copy)
    assert server_rules(vdir)
    without = decode_version(isolated_deps(tmp_path, data_copy), LOCAL_VERSION, csv_dir=WAGO, out=tmp_path / "sans")
    assert server_rules(without.root / LOCAL_VERSION) == []
    assert carry_hotfix_provenance(vdir, without.root / LOCAL_VERSION) is False
    assert server_rules(vdir) == [] and "hotfixes" not in read_json(vdir / "sources.json")


def test_higher_entry_without_value_supersedes_an_older_valid(tmp_path):
    names = table_names(known_tables(RULES))
    th = table_hash("TraitNode")
    old = Entry(70, 5, 1, th, 42, Status.VALID, b"x", 44)
    newer = Entry(70, 6, 2, th, 42, Status.INVALID, b"", 100)
    res = effective([old, newer], names)
    assert ("TraitNode", 42) not in res.applicable
    assert ("TraitNode", 42, 6) in res.invalid


def test_layouts_of_another_build_are_refused(tmp_path, make_deps, capsys):
    doc = read_json(LAYOUTS)
    doc["build"] = "1.60.1.70124"
    other = tmp_path / "layouts.json"
    other.write_text(json.dumps(doc), encoding="utf-8")
    args = ["decode", "--version", LOCAL_VERSION, "--csv-dir", str(WAGO), "--out", str(tmp_path / "c"), "--hotfixes"]
    code = main([*args, "--dbcache", str(DBCACHE), "--dbd-layouts", str(other)], make_deps())
    out, err = capsys.readouterr()
    assert code != 0 and "1.60.1.70124" in out + err


def wow_with(tmp_path, raw):
    root = tmp_path / "wow"
    target = root / "Cache" / "ADB" / "enUS" / "DBCache.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    return root


def test_unreadable_dbcache_is_reported_by_the_watch(tmp_path, make_deps):
    raw = bytearray(DBCACHE.read_bytes())
    struct.pack_into("<I", raw, 4, 10)  # format inconnu
    result = watch(make_deps(wow_dir=wow_with(tmp_path, bytes(raw))))
    event = next(e for e in result["events"] if e["kind"] == "hotfixes_dbcache")
    assert "illisible" in event["detail"] and event["pending"] == 0


def test_unvalidated_tables_are_not_pending_forever(tmp_path, make_deps, data_copy):
    res = effective(read_dbcache(DBCACHE).entries, table_names(known_tables(RULES)))
    path = data_copy / LOCAL_VERSION / "sources.json"
    sources = read_json(path)
    applied = [
        {"table": t, "rec_id": r, "status": "VALID" if e.status == 1 else "DELETE", "push": e.push_id,
         "unique_id": e.unique_id}
        for (t, r), e in res.applicable.items()
        if t != "SpellLevels"
    ]  # fmt: skip
    sources["hotfixes"] = {"applied": applied, "listed": {"unvalidated": {"SpellLevels": "disposition non validée"}}}
    path.write_bytes((json.dumps(sources, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    write_manifest(data_copy)
    result = watch(make_deps(wow_dir=wow_with(tmp_path, DBCACHE.read_bytes()), data_dir=data_copy))
    assert not [e for e in result["events"] if e["kind"] == "hotfixes_dbcache"]


def test_validation_needs_a_comparison_or_a_reference():
    layouts = layouts_from_json(read_json(LAYOUTS))
    cache = read_dbcache(DBCACHE)
    res = effective(cache.entries, table_names(known_tables(RULES)))
    entries = [e for (t, _), e in res.applicable.items() if t == "TraitNodeEntry"]
    check = validate_layout(layouts["TraitNodeEntry"], entries, None, {}, {})
    assert not check.ok and "aucune" in check.reason
