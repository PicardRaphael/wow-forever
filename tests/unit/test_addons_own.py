"""Addons du projet et addons connus (demande de l'utilisateur du 2026-10-10, décision 227) : ForeverLogger,
ForeverBridge, sa réserve d'emplacements, ses sondes et RaphCompletionist ne sont jamais « à inventorier » ; RXPGuides
est connu et exclu ; ForeverCompletionist n'est jamais lu comme un addon, même avec un `.toc` ; AtlasBIStooltips est
suivi (listes BiS de la communauté, lecteur en T10a).

Dossiers synthétiques écrits dans `tmp_path` (aucun contenu d'addon réel)."""

from pathlib import Path

import pytest

from forever.addons import DATA_ADDONS, addons_status, own_addons, untracked_addons
from forever.bridge.install import PROBE2_ADDON, PROBE_ADDON
from forever.bridge.slots import ADDON, slot_name
from forever.cli import main


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


@pytest.fixture
def addons(tmp_path):
    root = tmp_path / "wow" / "Interface" / "AddOns"
    write(root / ADDON / f"{ADDON}.toc", "## Version: 0.1.0\n")
    for i in range(1, 4):
        write(root / slot_name(i) / f"{slot_name(i)}.toc", "## Title: emplacement\n")
    for probe in (PROBE_ADDON, PROBE2_ADDON):
        write(root / probe / f"{probe}.toc", "## Title: sonde\n")
    write(root / "ForeverLogger" / "ForeverLogger.toc", "## Version: 0.3.0\n")
    write(root / "ForeverLogger" / "ForeverLogger.lua", "-- addon\n")
    write(root / "RaphCompletionist" / "RaphCompletionist.toc", "## Version: 0.2.1\n")
    write(root / "RXPGuides" / "RXPGuides.toc", "## Version: v4.11.15\n")
    write(root / "ForeverCompletionist" / "LOCAL_INVENTORY.md", "projet\n")
    write(root / "ForeverCompletionist" / "Stray.toc", "## Title: copie de travail\n")  # même avec un .toc
    write(root / "AtlasBIStooltips" / "AtlasBIStooltips.toc", "## Version: 1.0.1\n## Dependencies: AtlasLootClassic\n")
    write(root / "AtlasBIStooltips" / "ClassDataBase" / "Main.lua", "-- base\n")
    write(root / "SomeDataAddon" / "SomeDataAddon.toc", "## Version: 1\n")
    return root


@pytest.fixture
def deps(addons, make_deps):
    return make_deps(wow_dir=addons.parent.parent)


def test_own_addons_are_never_to_inventory(addons):
    found = {u["folder"]: u for u in untracked_addons(addons)}
    own = {ADDON, slot_name(1), slot_name(2), slot_name(3), PROBE_ADDON, PROBE2_ADDON, "RaphCompletionist"}
    assert not own & set(found)
    assert "ForeverLogger" not in found
    assert [u["folder"] for u in found.values() if u["status"] == "non_inventorié"] == ["SomeDataAddon"]


def test_own_addons_are_grouped_with_their_slots_and_probes(addons):
    groups = {g["folder"]: g for g in own_addons(addons)}
    assert set(groups) == {ADDON, "ForeverLogger", "RaphCompletionist"}
    bridge = groups[ADDON]
    assert bridge["version"] == "0.1.0" and bridge["slots"] == 3 and bridge["probes"] == 2
    assert groups["ForeverLogger"]["version"] == "0.3.0"
    assert "P06b" in groups["RaphCompletionist"]["note"]


def test_forever_logger_is_no_longer_a_data_addon():
    assert "ForeverLogger" not in DATA_ADDONS


def test_rxpguides_is_known_and_excluded(addons):
    rxp = next(u for u in untracked_addons(addons) if u["folder"] == "RXPGuides")
    assert rxp["status"] == "exclu" and "action" not in rxp
    assert "payant" in rxp["note"]


def test_forever_completionist_is_never_read_as_an_addon(addons):
    entry = next(u for u in untracked_addons(addons) if u["folder"] == "ForeverCompletionist")
    assert entry["status"] == "pas_un_addon" and entry["version"] is None
    assert "projet" in entry["note"]


def test_atlas_bis_tooltips_is_followed_for_t10a(deps):
    spec = DATA_ADDONS["AtlasBIStooltips"]
    assert spec.folders == ("AtlasBIStooltips",) and "T10a" in spec.reader
    report = addons_status(deps)
    atlas = next(a for a in report["addons"] if a["name"] == "AtlasBIStooltips")
    assert atlas["status"] == "nouveau" and atlas["version"] == "1.0.1"
    assert "AtlasBIStooltips" not in {u["folder"] for u in report["untracked"]}


def test_status_counts_only_unknown_addons(deps, capsys):
    report = addons_status(deps)
    assert {g["folder"] for g in report["own"]} == {ADDON, "ForeverLogger", "RaphCompletionist"}
    assert main(["addons", "status"], deps) == 0
    out = capsys.readouterr().out
    assert "ForeverBridge_S001" not in out and "non inventorié" in out
    assert "Addons du projet (ignorés)" in out and "3 emplacement(s)" in out
    assert "RXPGuides" in out and "exclu" in out


def test_update_step_counts_only_unknown_addons(deps):
    from forever.update import UpdateOptions, run_update

    report = run_update(deps, UpdateOptions(dry_run=True, only=frozenset({"addons"})), replay=lambda *a: {})
    step = next(s for s in report["steps"] if s["name"] == "addons")
    assert [u["folder"] for u in step["data"]["untracked"]] == ["SomeDataAddon"]
    assert "1 à inventorier" in step["detail"]
