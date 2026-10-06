"""Veille locale `forever watch` (T08b, bloc G) : build du client, addons, correctifs du serveur, journaux de combat et
sauvegardes nouveaux ; chacun détecté et assorti d'une action proposée (commande exacte, réseau ou non), rien lancé.
Un second passage sans changement ne rend rien ; la ligne de démarrage de session tient sur une ligne et ne lève
jamais. Dossier du client construit dans le test (fichiers factices) ; Hotfix.log : `tests/fixtures/hotfix/`."""

import json
import shutil

import pytest
from conftest import FIXTURES, FakeHttp

from forever.cli import main
from forever.pipeline import hotfixes
from forever.watch import watch, watch_line

HEADER = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"


def build_info(root, version):
    (root.parent / ".build.info").write_text(f"{HEADER}\nus|1|{version}|wow_classic_beta\n", encoding="utf-8")


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "World of Warcraft" / "_classic_beta_"
    (root / "Logs").mkdir(parents=True)
    build_info(root, "1.60.1.70124")
    shutil.copyfile(FIXTURES / "hotfix" / "Hotfix.log", root / "Logs" / "Hotfix.log")
    addon = root / "Interface" / "AddOns" / "AtlasLootClassic"
    addon.mkdir(parents=True)
    (addon / "AtlasLootClassic.toc").write_text("## Version: Forever 1.60.1\n", encoding="utf-8")
    (addon / "data.lua").write_text("local a = 1\n", encoding="utf-8")
    (root / "WTF" / "Account" / "COMPTE" / "SavedVariables").mkdir(parents=True)
    return root


def kinds(result):
    return {e["kind"] for e in result["events"]}


def test_second_pass_without_change_is_empty(wow, make_deps):
    http = FakeHttp.failing()
    deps = make_deps(wow_dir=wow, http=http)
    first = watch(deps)
    assert first["events"]
    assert watch(deps)["events"] == []
    assert http.calls == []


def test_each_change_is_detected_with_a_proposed_action(wow, make_deps):
    http = FakeHttp.failing()
    deps = make_deps(wow_dir=wow, http=http)
    watch(deps)
    build_info(wow, "1.60.1.70200")
    (wow / "Interface" / "AddOns" / "AtlasLootClassic" / "data.lua").write_text("local a = 22\n", encoding="utf-8")
    with (wow / "Logs" / "Hotfix.log").open("a", encoding="utf-8") as f:
        f.write("10/1 09:00:00.000  \t112300 Table SpellMisc RecID 314147 VALIDATION_RESULT_VALID\n")
    (wow / "Logs" / "WoWCombatLog-100126_090000.txt").write_text("journal\n", encoding="utf-8")
    (wow / "WTF" / "Account" / "COMPTE" / "SavedVariables" / "ForeverLogger.lua").write_text(
        "x = 1\n", encoding="utf-8"
    )
    result = watch(deps)
    assert kinds(result) == {"client_build", "addons", "hotfixes", "combat_logs", "saved_variables"}
    for event in result["events"]:
        assert event["actions"], event
        assert all({"command", "network"} <= set(a) for a in event["actions"])
    build = next(e for e in result["events"] if e["kind"] == "client_build")
    commands = [a["command"] for a in build["actions"]]
    assert any(c.startswith("forever notes") for c in commands)  # D1 : proposé, jamais lancé
    assert all(a["network"] for a in build["actions"] if a["command"].startswith(("forever notes", "forever fetch")))
    logs = next(e for e in result["events"] if e["kind"] == "combat_logs")
    assert not logs["actions"][0]["network"]
    assert http.calls == []


def test_unchanged_hotfix_log_is_not_read_again(wow, make_deps, monkeypatch):
    deps = make_deps(wow_dir=wow)
    watch(deps)
    calls = []
    real = hotfixes.parse_hotfix_log
    monkeypatch.setattr(hotfixes, "parse_hotfix_log", lambda *a, **k: calls.append(1) or real(*a, **k))
    watch(deps)
    assert calls == []


def test_report_is_written_to_the_cache(wow, make_deps):
    deps = make_deps(wow_dir=wow)
    watch(deps, report=True)
    assert json.loads((deps.cache_dir / "watch" / "report.json").read_text(encoding="utf-8"))["events"]


def test_session_line_is_one_line_and_never_raises(wow, make_deps, tmp_path):
    deps = make_deps(wow_dir=wow)
    watch(deps)
    assert watch_line(deps) is None
    build_info(wow, "1.60.1.70200")
    line = watch_line(deps)
    assert line and "\n" not in line and "forever watch" in line
    assert watch_line(make_deps(wow_dir=tmp_path / "absent")) is None
    assert watch_line(make_deps(wow_dir=None)) is None


def test_cli_watch_json(wow, make_deps, capsys):
    assert main(["watch", "--json"], make_deps(wow_dir=wow)) == 0
    data = json.loads(capsys.readouterr()[0])
    assert data["events"] and data["provenance"]["game_version"]


# --- T08c, bloc E : correctifs du serveur de DBCache.bin non appliqués -----------------------------------------

DBCACHE = FIXTURES / "hotfix" / "DBCache.bin"


def with_dbcache(wow, raw=None):
    target = wow / "Cache" / "ADB" / "enUS" / "DBCache.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw if raw is not None else DBCACHE.read_bytes())
    return target


FIXTURE_VERSION = "1.60.1.70170"  # build du DBCache.bin de la fixture (décision 192)


def expected_pending():
    from conftest import DATA_DIR, read_json

    from forever.pipeline.dbcache import effective, known_tables, read_dbcache, table_names
    from forever.pipeline.tables import TABLES

    rules = read_json(DATA_DIR / FIXTURE_VERSION / "decode_rules.json")
    res = effective(read_dbcache(DBCACHE).entries, table_names(known_tables(rules)))
    return res, [k for k in res.applicable if k[0] in TABLES]


def dbcache_event(result):
    return next((e for e in result["events"] if e["kind"] == "hotfixes_dbcache"), None)


def without_hotfixes(data_copy):
    """Copie des données dont la révision installée n'a appliqué aucun correctif (indépendante de la révision du
    dépôt : la révision 4 de 1.60.1.70170 en porte, T08c), ramenée au build de la fixture."""
    from conftest import read_json, rewind_to

    from forever.manifest import write_manifest

    rewind_to(data_copy, FIXTURE_VERSION)
    path = data_copy / FIXTURE_VERSION / "sources.json"
    sources = read_json(path)
    sources.pop("hotfixes", None)
    path.write_bytes((json.dumps(sources, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    write_manifest(data_copy)
    return data_copy, sources.get("revision")


def test_pending_server_hotfixes_are_reported(wow, make_deps, data_copy):
    with_dbcache(wow)
    data, revision = without_hotfixes(data_copy)
    http = FakeHttp.failing()
    deps = make_deps(wow_dir=wow, http=http, data_dir=data)
    event = dbcache_event(watch(deps))
    _, pending = expected_pending()
    assert event is not None and event["pending"] == len(pending) > 0
    assert "non appliqué" in event["detail"] and f"révision {revision}" in event["detail"]
    commands = [a["command"] for a in event["actions"]]
    assert "forever hotfixes --values" in commands
    assert any(c.startswith("forever decode --version 1.60.1.70170 --hotfixes") for c in commands)
    assert any(c.startswith("forever install") for c in commands)
    assert not any(a["network"] for a in event["actions"])
    assert http.calls == []


def test_unchanged_dbcache_is_not_analysed_again(wow, make_deps, monkeypatch):
    from forever.pipeline import dbcache

    with_dbcache(wow)
    deps = make_deps(wow_dir=wow)
    watch(deps)

    def refuse(*_a, **_k):
        raise AssertionError("DBCache.bin relu sans changement")

    monkeypatch.setattr(dbcache, "read_dbcache", refuse)
    assert dbcache_event(watch(deps)) is None


def test_installed_hotfixes_leave_nothing_pending(wow, make_deps, data_copy):
    from conftest import read_json, rewind_to

    from forever.manifest import write_manifest

    res, _ = expected_pending()
    rewind_to(data_copy, FIXTURE_VERSION)
    path = data_copy / FIXTURE_VERSION / "sources.json"
    sources = read_json(path)
    sources["hotfixes"] = {
        "pushes": sorted({e.push_id for e in res.applicable.values()}),
        "applied": [
            {"table": t, "rec_id": r, "status": "VALID" if e.status == 1 else "DELETE", "push": e.push_id,
             "unique_id": e.unique_id}
            for (t, r), e in res.applicable.items()
        ],
    }  # fmt: skip
    path.write_bytes((json.dumps(sources, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    write_manifest(data_copy)
    with_dbcache(wow)
    deps = make_deps(wow_dir=wow, data_dir=data_copy)
    assert dbcache_event(watch(deps)) is None
    line = watch_line(deps)
    assert line is None or "correctif" not in line


def test_dbcache_of_another_build_is_not_applicable(wow, make_deps):
    import struct

    raw = bytearray(DBCACHE.read_bytes())
    struct.pack_into("<I", raw, 8, 70205)
    with_dbcache(wow, bytes(raw))
    event = dbcache_event(watch(make_deps(wow_dir=wow)))
    assert event is not None and "non applicables" in event["detail"] and "70205" in event["detail"]
    assert event["pending"] == 0


def test_session_line_counts_pending_hotfixes(wow, make_deps, data_copy):
    with_dbcache(wow)
    data, _ = without_hotfixes(data_copy)
    deps = make_deps(wow_dir=wow, data_dir=data)
    watch(deps)
    watch(deps)  # second passage : plus d'événement, le compte reste dans l'état
    line = watch_line(deps)
    _, pending = expected_pending()
    assert line and "\n" not in line and f"{len(pending)} correctif(s) du serveur non appliqué(s)" in line
