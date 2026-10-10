"""Classement des addons inventoriés le 2026-10-10 (décision 228, `tasks/inventaire-addons.md`) : sources de données
possibles suivies, addons d'interface seule, addons connus et exclus ; ZoneInfoForever suivi à la place de
ZoneLevelForever (renommé par son auteur). Plus aucun de ces dossiers n'est « à inventorier ».

Dossiers synthétiques écrits dans `tmp_path` (aucun contenu d'addon réel)."""

from pathlib import Path

import pytest

from forever.addons import DATA_ADDONS, addons_status, untracked_addons

DATA = {
    "FojjiCore": ("FojjiCore", "FojjiCore_BiS", "FojjiCore_DungeonJournal", "FojjiCore_SpellRanks"),
    "ShortestPathForever": ("ShortestPathForever",),
    "SkillUpForever": ("SkillUpForever",),
    "ZoneInfoForever": ("ZoneInfoForever",),
}
UI = (
    "AppelSwingsForever",
    "BetterForeverChat",
    "DeleteCheapestItem",
    "ExtendedVendorForever",
    "FojjiCore_RaidTools",
    "FontMagic",
    "ForeverMove",
    "Simulationcraft",
)
EXCLUDED = {"Tamed": "Classic", "AlexAtlasLoot": "licence"}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


@pytest.fixture
def addons(tmp_path):
    root = tmp_path / "wow" / "Interface" / "AddOns"
    folders = [f for group in DATA.values() for f in group] + list(UI) + list(EXCLUDED) + ["UnknownAddon"]
    for name in folders:
        write(root / name / f"{name}.toc", "## Version: 1.0\n")
        write(root / name / "Data.lua", "-- données\n")
    return root


@pytest.fixture
def deps(addons, make_deps):
    return make_deps(wow_dir=addons.parent.parent)


def test_data_addons_are_followed(deps):
    report = addons_status(deps)
    names = {a["name"]: a for a in report["addons"]}
    for name in DATA:
        assert name in DATA_ADDONS, name
        assert names[name]["status"] == "nouveau", name
    assert "suppose" in DATA_ADDONS["FojjiCore"].reader and "FojjiCore_*" in DATA_ADDONS["FojjiCore"].folders
    untracked = {u["folder"] for u in report["untracked"]}
    assert not untracked & {f for group in DATA.values() for f in group}


def test_zone_info_replaces_zone_level(deps):
    """ZoneInfoForever (« Formerly Zone Level ») est suivi ; l'ancien dossier n'est plus attendu."""
    assert "ZoneLevelForever" not in DATA_ADDONS
    assert DATA_ADDONS["ZoneInfoForever"].folders == ("ZoneInfoForever",)
    report = addons_status(deps)
    assert not any(a["name"] == "ZoneLevelForever" for a in report["addons"])


def test_interface_only_addons(addons):
    status = {u["folder"]: u for u in untracked_addons(addons)}
    for name in UI:
        if name.startswith("FojjiCore"):  # module de la suite FojjiCore, suivie avec elle
            assert name not in status
            continue
        assert status[name]["status"] == "interface", name
        assert "action" not in status[name]


def test_known_and_excluded_addons(addons):
    status = {u["folder"]: u for u in untracked_addons(addons)}
    for name, reason in EXCLUDED.items():
        assert status[name]["status"] == "exclu", name
        assert reason in status[name]["note"], name


def test_only_the_unknown_addon_is_left_to_inventory(addons):
    left = [u["folder"] for u in untracked_addons(addons) if u["status"] == "non_inventorié"]
    assert left == ["UnknownAddon"]
