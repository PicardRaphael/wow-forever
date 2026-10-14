"""`.toc` et numéro d'interface (LN1, bloc C, décision 271) : ordre de lecture des suffixes (warcraft.wiki.gg,
`TOC_format`), une seule constante des valeurs `## Interface` admises (`forever.toc.INTERFACES`) partagée par le
contrôle de l'addon et les `.toc` générés, ForeverLogger 0.7.0 qui note `GetBuildInfo()` dans ses instantanés, et
`forever doctor` qui compare l'interface vue en jeu aux valeurs admises. `99999` : valeur d'interface fictive."""

import importlib.util
import json

import pytest
from conftest import REPO_ROOT
from test_doctor import World

from forever import toc
from forever.addons import _version
from forever.bridge.install import install_bridge
from forever.bridge.slots import slot_name
from forever.pipeline.addon_sv import read_logger_db


def check_addon_module():
    spec = importlib.util.spec_from_file_location("check_addon_ln1", REPO_ROOT / "scripts" / "check_addon.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def four_tocs(folder):
    folder.mkdir(parents=True)
    for suffix, version in (("", "1"), ("_Mainline", "2"), ("_Camelot", "3"), ("_Forever", "4")):
        (folder / f"Addon{suffix}.toc").write_text(f"## Interface: 16001\n## Version: {version}\n", encoding="utf-8")
    return folder


def test_reading_order_of_the_suffixes(tmp_path):
    folder = four_tocs(tmp_path / "Addon")
    assert [p.name for p in toc.toc_files(folder)] == [
        "Addon_Forever.toc",
        "Addon_Camelot.toc",
        "Addon_Mainline.toc",
        "Addon.toc",
    ]


def test_addon_version_is_read_from_the_first_toc_in_that_order(tmp_path):
    assert _version(four_tocs(tmp_path / "Addon")) == "4"


def test_interface_values_and_line():
    assert toc.interface_values("## Interface: 16001, 99999") == ["16001", "99999"]
    assert toc.interface_line(["16001", "99999"]) == "## Interface: 16001, 99999"
    assert toc.interface_line() == "## Interface: " + ", ".join(toc.INTERFACES)


def test_several_values_are_accepted_only_if_all_are_admitted(tmp_path, monkeypatch):
    folder = tmp_path / "Addon"
    folder.mkdir()
    path = folder / "Addon.toc"
    path.write_text("## Interface: 16001, 99999\n", encoding="utf-8")
    check = check_addon_module()
    errors = check.check_toc(path)
    assert errors and "99999" in errors[0]
    monkeypatch.setattr(toc, "INTERFACES", ("16001", "99999"))
    assert check.check_toc(path) == []


def test_our_tocs_have_no_suffix():
    for addon in ("ForeverLogger", "ForeverBridge"):
        assert [p.name for p in (REPO_ROOT / "addon" / addon).glob("*.toc")] == [f"{addon}.toc"]


def test_generated_tocs_use_the_shared_values(tmp_path, monkeypatch):
    monkeypatch.setattr(toc, "INTERFACES", ("16001", "99999"))
    wow = tmp_path / "wow"
    (wow / "Interface" / "AddOns").mkdir(parents=True)
    install_bridge(wow, slots=8)
    slot = wow / "Interface" / "AddOns" / slot_name(1) / f"{slot_name(1)}.toc"
    assert "## Interface: 16001, 99999" in slot.read_text(encoding="utf-8").splitlines()
    probe = wow / "Interface" / "AddOns" / "ForeverBridge_Probe" / "ForeverBridge_Probe.toc"
    assert "## Interface: 16001, 99999" in probe.read_text(encoding="utf-8").splitlines()


def test_no_other_interface_constant():
    """Une seule source des valeurs admises : plus de constante INTERFACE propre au pont ni au contrôle."""
    for rel in ("forever/bridge/install.py", "scripts/check_addon.py", "forever/bridge/guide_addon.py"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert '"16001"' not in text, rel


# --- ForeverLogger 0.7.0 : interface vue en jeu --------------------------------------------------------------------


def test_logger_snapshot_notes_the_client_build():
    pytest.importorskip("lupa")
    from test_addon_logger_xp import Logger

    logger = Logger()
    snapshot = logger.entries("snapshots")[-1]
    client = snapshot.client
    assert client is not None
    assert client.interface == 16001  # valeur du client simulé (wow_stub.lua)
    assert client.version is not None and client.build is not None


def test_logger_version_is_0_7_0():
    lines = (REPO_ROOT / "addon" / "ForeverLogger" / "ForeverLogger.toc").read_text(encoding="utf-8").splitlines()
    assert "## Version: 0.7.0" in lines


LOGGER_SV = """ForeverLoggerDB = {
\t["schema"] = 4,
\t["characters"] = {
\t\t["Player-0000-00000001"] = {
\t\t\t["name"] = "Moi",
\t\t\t["realm"] = "Royaume",
\t\t\t["snapshots"] = {
\t\t\t\t{
\t\t\t\t\t["reason"] = "connexion",
\t\t\t\t\t["time"] = 1790513400,
\t\t\t\t\t["localtime"] = "09/27/2026 14:50:00",
\t\t\t\t\t["level"] = 14,
\t\t\t\t\t["client"] = {
\t\t\t\t\t\t["version"] = "9.99.9",
\t\t\t\t\t\t["build"] = "99999",
\t\t\t\t\t\t["interface"] = INTERFACE,
\t\t\t\t\t},
\t\t\t\t},
\t\t\t},
\t\t},
\t},
}
"""


def write_logger_sv(world, interface):
    path = world.wow / "WTF" / "Account" / "COMPTE" / "SavedVariables" / "ForeverLogger.lua"
    path.write_text(LOGGER_SV.replace("INTERFACE", str(interface)), encoding="utf-8")
    return path


@pytest.fixture
def world(tmp_path, make_deps):
    return World(tmp_path, make_deps)


def test_the_client_block_is_read_back(world):
    path = write_logger_sv(world, 99999)
    [character] = read_logger_db(path).characters.values()
    assert character.snapshots[-1].client == {"version": "9.99.9", "build": "99999", "interface": 99999}


def test_doctor_flags_an_interface_seen_in_game_that_the_tocs_do_not_admit(world):
    write_logger_sv(world, 99999)
    check = world.checks()["addons.logger"]
    assert check.status == "fail" and "99999" in check.finding
    assert "docs/LANCEMENT.md" in check.fix


def test_doctor_accepts_an_admitted_interface(world):
    write_logger_sv(world, 16001)
    assert world.checks()["addons.logger"].status == "ok"


def test_json_of_the_admitted_values():
    assert json.loads(json.dumps(list(toc.INTERFACES))) == ["16001"]
