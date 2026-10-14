"""Bonne installation partout (LN1, bloc B, décision 271) : quand la bêta et la version finale cohabitent, la
veille, l'archivage, la mise à jour, `forever builds`, le décodage, la surveillance du pont et les addons lisent
l'installation choisie ; aucune archive, aucune mesure ni aucune version d'un produit n'est attribuée à l'autre.

Deux installations de fixture dans `tmp_path` : la bêta (`wow_classic_beta`, 1.60.1.70374) et une version finale
**fictive** (`wow_fictif_finale`, 9.99.9.99999) adoptée."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import FIXTURES, LOCAL_VERSION, PRODUCT, REPO_ROOT, FakeHttp
from test_installs import BETA_V, FINAL, FINAL_V, NOW, make_root

from forever.archive import archive_client_files, archive_dir, archived_dbcache
from forever.bridge import autostart
from forever.bridge.journal import Journal
from forever.cli import main
from forever.config import default_deps
from forever.installs import discover
from forever.pipeline.client_builds import (
    ClientBuild,
    accept_earlier,
    adopt_product,
    final_client,
    load_builds,
    record_build,
    split_by_version,
    version_at,
    version_prefix,
)

DBCACHE = FIXTURES / "hotfix" / "DBCache.bin"
WAGO_70009 = FIXTURES / "wago" / "1.60.1.70009"


def two_installs(base: Path, *, final_version: str = FINAL_V) -> Path:
    return make_root(
        base,
        [(PRODUCT, BETA_V), (FINAL, final_version)],
        {"_classic_beta_": (PRODUCT, "WowB.exe"), "_fictif_": (FINAL, "WowF.exe")},
    )


def adopt(cache: Path, root: Path) -> None:
    adopt_product(cache, next(i for i in discover([root]) if i.product == FINAL), NOW)


def with_dbcache(folder: Path) -> Path:
    live = folder / "Cache" / "ADB" / "enUS" / "DBCache.bin"
    live.parent.mkdir(parents=True)
    shutil.copyfile(DBCACHE, live)
    return folder


# --- Choix de production ---------------------------------------------------------------------------------------------


def test_default_deps_read_the_adopted_final(tmp_path):
    root = two_installs(tmp_path)
    cache = tmp_path / "cache"
    adopt(cache, root)
    environ = {"FOREVER_WOW_ROOTS": str(root), "FOREVER_CACHE_DIR": str(cache), "FOREVER_WOW_NO_DRIVES": "1"}
    assert default_deps(environ).wow_dir == root / "_fictif_"


def test_default_deps_read_the_beta_while_nothing_is_adopted(tmp_path):
    root = two_installs(tmp_path)
    environ = {"FOREVER_WOW_ROOTS": str(root), "FOREVER_CACHE_DIR": str(tmp_path / "c"), "FOREVER_WOW_NO_DRIVES": "1"}
    assert default_deps(environ).wow_dir == root / "_classic_beta_"


def test_install_addon_targets_the_chosen_installation(tmp_path, monkeypatch, capsys):
    root = two_installs(tmp_path)
    cache = tmp_path / "cache"
    adopt(cache, root)
    (root / "_fictif_" / "Interface" / "AddOns").mkdir(parents=True)
    monkeypatch.setenv("FOREVER_WOW_ROOTS", str(root))
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(cache))
    monkeypatch.delenv("FOREVER_WOW_DIR", raising=False)
    monkeypatch.delenv("FOREVER_WOW_FORCE", raising=False)
    spec = importlib.util.spec_from_file_location("install_addon_ln1", REPO_ROOT / "scripts" / "install_addon.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--dry-run"]) == 0
    assert str(root / "_fictif_" / "Interface" / "AddOns" / "ForeverLogger") in capsys.readouterr().out


# --- Journal des versions par produit --------------------------------------------------------------------------------


T1 = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
T2 = datetime(2026, 11, 4, 8, 0, tzinfo=UTC)
T3 = datetime(2026, 11, 5, 20, 0, tzinfo=UTC)
BUILDS = [ClientBuild(BETA_V, T1, PRODUCT), ClientBuild(FINAL_V, T2, FINAL)]


def test_version_at_by_product():
    assert version_at(BUILDS, T3, product=PRODUCT) == BETA_V
    assert version_at(BUILDS, T3, product=FINAL) == FINAL_V
    assert version_at(BUILDS, T3) == FINAL_V  # sans produit : comme avant LN1


def test_the_same_build_of_two_products_is_recorded_twice(tmp_path):
    record_build(tmp_path, ClientBuild(BETA_V, T1, PRODUCT))
    record_build(tmp_path, ClientBuild(BETA_V, T2, FINAL))
    assert [(b.build, b.product) for b in load_builds(tmp_path)] == [(BETA_V, PRODUCT), (BETA_V, FINAL)]


def test_a_beta_log_is_never_measured_in_the_final_data():
    keep, held, unknown = split_by_version(
        [("WoWCombatLog-a.txt", T3)], BUILDS, FINAL_V, product=PRODUCT, data_product=FINAL
    )
    assert keep == [] and unknown == []
    assert [(h.name, h.client_version) for h in held] == [("WoWCombatLog-a.txt", BETA_V)]
    assert PRODUCT in held[0].reason and FINAL in held[0].reason
    accepted, still = accept_earlier(held, BETA_V, "PNJ inchangés depuis la bêta", FINAL_V)
    assert [a.name for a in accepted] == ["WoWCombatLog-a.txt"] and still == []


def test_a_final_log_is_never_measured_in_the_beta_data():
    _, held, _ = split_by_version([("WoWCombatLog-b.txt", T3)], BUILDS, BETA_V, product=FINAL, data_product=PRODUCT)
    assert [h.client_version for h in held] == [FINAL_V]


def test_a_log_of_the_data_product_is_kept():
    keep, held, _ = split_by_version([("WoWCombatLog-c.txt", T3)], BUILDS, FINAL_V, product=FINAL, data_product=FINAL)
    assert keep == ["WoWCombatLog-c.txt"] and held == []


# --- Archives par produit --------------------------------------------------------------------------------------------


def test_archive_dir_by_product(tmp_path):
    assert archive_dir(tmp_path, PRODUCT, "70170") == tmp_path / "dbcache" / "70170"
    assert archive_dir(tmp_path, None, "70170") == tmp_path / "dbcache" / "70170"
    assert archive_dir(tmp_path, FINAL, "70170") == tmp_path / "dbcache" / FINAL / "70170"


def test_same_build_in_both_installations_gives_two_archives(tmp_path, make_deps):
    root = two_installs(tmp_path)
    beta, final = with_dbcache(root / "_classic_beta_"), with_dbcache(root / "_fictif_")
    deps = make_deps(wow_dir=beta)
    adopt(deps.cache_dir, root)
    archive_client_files(deps)
    assert not (deps.cache_dir / "dbcache" / FINAL).exists()  # rien de la bêta chez la finale
    archive_client_files(make_deps(wow_dir=final))
    legacy = deps.cache_dir / "dbcache" / "70170"
    by_product = deps.cache_dir / "dbcache" / FINAL / "70170"
    assert archived_dbcache(deps.cache_dir, "70170") == legacy / "DBCache.bin"
    assert archived_dbcache(deps.cache_dir, "70170", product=FINAL) == by_product / "DBCache.bin"
    legacy_copies = json.loads((legacy / "index.json").read_text(encoding="utf-8"))["copies"]
    final_copies = json.loads((by_product / "index.json").read_text(encoding="utf-8"))["copies"]
    assert [c["kind"] for c in legacy_copies] == ["dbcache"] and [c["kind"] for c in final_copies] == ["dbcache"]


# --- Produit demandé à wago.tools, produit de la candidate ------------------------------------------------------------


def test_version_prefix():
    assert version_prefix(BETA_V) == "1.60."
    assert version_prefix(FINAL_V) == "9.99."


def test_final_client_only_for_an_adopted_product(tmp_path):
    root = two_installs(tmp_path)
    cache = tmp_path / "cache"
    assert final_client(cache, root / "_fictif_") is None
    adopt(cache, root)
    found = final_client(cache, root / "_fictif_")
    assert found is not None and (found.build, found.product) == (FINAL_V, FINAL)
    assert final_client(cache, root / "_classic_beta_") is None


def published():
    doc = {
        PRODUCT: [{"version": BETA_V, "created_at": "2026-10-13 08:00:00"}],
        FINAL: [{"version": FINAL_V, "created_at": "2026-11-04 08:00:00"}],
    }
    return FakeHttp(body=json.dumps(doc).encode())


def test_builds_asks_wago_for_the_adopted_final(tmp_path, make_deps, capsys):
    root = two_installs(tmp_path)
    deps = make_deps(wow_dir=root / "_fictif_", http=published())
    adopt(deps.cache_dir, root)
    assert main(["builds", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr().out)
    assert (payload["product"], payload["prefix"], payload["latest"]) == (FINAL, "9.99.", FINAL_V)


def test_builds_asks_wago_for_the_data_product_without_adoption(tmp_path, make_deps, capsys):
    root = two_installs(tmp_path)
    deps = make_deps(wow_dir=root / "_fictif_", http=published())
    assert main(["builds", "--json"], deps) == 0
    assert json.loads(capsys.readouterr().out)["product"] == PRODUCT


def test_a_candidate_decoded_from_the_final_carries_its_product(tmp_path, make_deps, capsys):
    root = two_installs(tmp_path, final_version=LOCAL_VERSION)
    deps = make_deps(wow_dir=root / "_fictif_")
    adopt(deps.cache_dir, root)
    code = main(["decode", "--version", LOCAL_VERSION, "--csv-dir", str(WAGO_70009), "--json"], deps)
    assert code == 0, capsys.readouterr()
    candidate = deps.cache_dir / "candidates" / LOCAL_VERSION / LOCAL_VERSION
    sources = json.loads((candidate / "sources.json").read_text(encoding="utf-8"))
    assert (sources["product"], sources["version_prefix"]) == (FINAL, "1.60.")


# --- Surveillance du pont --------------------------------------------------------------------------------------------


def test_task_without_forced_folder(tmp_path):
    args = autostart.task_arguments(None, tmp_path / "cache")
    assert "--wow-dir" not in args and "--cache-dir" in args


def test_bridge_launched_without_folder_chooses_itself(tmp_path, monkeypatch):
    from forever import spawn

    calls = []
    monkeypatch.setattr(spawn, "spawn_detached", lambda args, log, env=None: calls.append(args))
    monkeypatch.setattr(spawn, "current_interpreter", lambda: ("REAL", {}))
    monkeypatch.setattr(spawn, "probe_environment", lambda exe, env, **kw: None)
    autostart.launch_bridge(None, tmp_path / "cache", datetime(2026, 11, 4, 9, 0, tzinfo=UTC))
    assert calls[0] == ["REAL", "-u", "-m", "forever", "bridge", "run"]


def hold_lock(cache, pid):
    from forever.bridge import loop

    path = loop.lock_path(cache)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": pid, "started_at": "2026-11-04T08:00:00Z"}), encoding="utf-8")


def journal_events(cache):
    out = []
    for path in sorted((cache / "bridge" / "journal").glob("*.jsonl")):
        out += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return out


def test_supervisor_moves_the_bridge_to_the_new_choice_once_the_game_is_closed(tmp_path):
    chosen = {"dir": tmp_path / "A"}
    game = {"on": True}
    stop_file = tmp_path / "bridge" / "stop"
    seen: dict[int, bool] = {}
    clock = {"t": 0.0}
    launches = []

    def sleep(seconds):
        clock["t"] += seconds
        n = len(seen) + 1
        seen[n] = stop_file.exists()
        if n == 1:
            hold_lock(tmp_path, 4242)  # le pont lancé a pris le verrou
        if n == 3:
            chosen["dir"] = tmp_path / "B"  # version finale adoptée
        if n == 6:
            game["on"] = False
        if n == 9:
            hold_lock(tmp_path, 5555)  # le pont a obéi au fichier d'arrêt
        if n == 10:
            hold_lock(tmp_path, 4242)  # pont relancé
        if n == 11:
            autostart.request_stop(tmp_path)

    journal = Journal(tmp_path / "bridge" / "journal", lambda: datetime(2026, 11, 4, 9, 0, tzinfo=UTC))
    autostart.supervise(
        tmp_path,
        lambda: launches.append(clock["t"]),
        journal=journal,
        clock=lambda: clock["t"],
        sleep=sleep,
        alive=lambda pid: pid in (4242, 999),
        pid=999,
        resolve=lambda: chosen["dir"],
        game_running=lambda old, new: game["on"],
    )
    assert not any(seen[n] for n in range(1, 7))  # jeu ouvert : rien avant sa fermeture
    assert seen[8]
    changed = [e for e in journal_events(tmp_path) if e["event"] == "autostart_wow_changed"]
    assert len(changed) == 1
    assert (changed[0]["old"], changed[0]["new"]) == (str(tmp_path / "A"), str(tmp_path / "B"))
    assert len(launches) == 2 and launches[1] > launches[0]


def test_a_forced_task_never_follows_the_choice(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(autostart, "supervise", lambda cache, launch, **kw: calls.update(kw) or 0)
    assert autostart.main(["--wow-dir", str(tmp_path / "wow"), "--cache-dir", str(tmp_path / "cache")]) == 0
    assert calls["resolve"] is None
    assert autostart.main(["--cache-dir", str(tmp_path / "cache")]) == 0
    assert callable(calls["resolve"])


def test_the_supervisor_resolution_needs_only_the_standard_library(tmp_path):
    root = two_installs(tmp_path)
    env = {**os.environ, "FOREVER_WOW_ROOTS": str(root), "FOREVER_WOW_NO_DRIVES": "1"}
    code = f"from forever.bridge import autostart; print(autostart.resolve_wow_dir(__import__('pathlib').Path(r'{tmp_path / 'cache'}')))"
    done = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str(root / "_classic_beta_")


# --- Script d'installation -------------------------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell de Windows")
def test_install_plugin_print_shows_the_choice_and_changes_nothing(tmp_path):
    import winreg

    def user_value():
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            try:
                return winreg.QueryValueEx(key, "FOREVER_WOW_DIR")[0]
            except FileNotFoundError:
                return None

    root = two_installs(tmp_path)
    before = user_value()
    env = {**os.environ, "FOREVER_WOW_ROOTS": str(root), "FOREVER_CACHE_DIR": str(tmp_path / "cache")}
    env["FOREVER_WOW_NO_DRIVES"] = "1"
    script = REPO_ROOT / "scripts" / "install_plugin.ps1"
    done = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Print"],
        env=env,
        capture_output=True,
        timeout=180,
        check=False,
    )
    out = done.stdout.decode("utf-8", errors="replace")
    assert done.returncode == 0, out + done.stderr.decode("utf-8", errors="replace")
    assert str(root / "_classic_beta_") in out
    assert "bêta : aucune version finale adoptée" in out
    assert user_value() == before
