"""Addons (T08d, bloc D) : Talents Forever et Forever Companion suivis avec leur version de contenu, addons
d'interface notés sans lecture, addons présents non inventoriés signalés, `forever addons inventory` sans valeur.

Addons synthétiques de `tests/fixtures/addons/` (voir son README) ; classes.json : version installée du dépôt."""

import builtins
import io
import json
import shutil
from pathlib import Path

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION

from forever.addons import (
    DATA_ADDONS,
    UI_ADDONS,
    addons_status,
    content_version,
    fingerprint_folder,
    inventory,
    untracked_addons,
)
from forever.cli import main
from forever.pipeline.talents_forever import crosscheck

ADDONS = FIXTURES / "addons"


@pytest.fixture
def addons(tmp_path):
    root = tmp_path / "wow" / "Interface" / "AddOns"
    shutil.copytree(ADDONS, root, ignore=shutil.ignore_patterns("README.md"))
    return root


@pytest.fixture
def deps(addons, make_deps):
    return make_deps(wow_dir=addons.parent.parent)


def by_name(report):
    return {a["name"]: a for a in report["addons"]}


def edit(path, old, new):
    text = path.read_bytes().decode("utf-8")
    assert old in text
    path.write_bytes(text.replace(old, new).encode("utf-8"))


def test_new_addons_are_followed():
    tf = DATA_ADDONS["TalentsForeverBook"]
    assert tf.reader == "forever/pipeline/talents_forever.py" and tf.depends
    assert DATA_ADDONS["ForeverCompanion"].depends == ()
    assert "NaowhForever_*" in DATA_ADDONS["NaowhForever"].folders
    assert {"EllesmereUI*", "Leatrix_Maps", "ForeverMapFix"} <= set(UI_ADDONS)


def test_content_version_is_read_without_running_lua(addons):
    assert content_version("TalentsForeverBook", addons / "TalentsForeverBook") == {
        "build": "1.60.1.79999",
        "generated": "2026-01-01",
        "codeVersion": "9",
    }
    assert content_version("ForeverCompanion", addons / "ForeverCompanion") == {
        "dataVersion": 7,
        "updated": "2026-01-02",
    }
    assert content_version("SomeDataAddon", addons / "SomeDataAddon") is None


def test_changed_content_version_is_reported(deps, addons):
    first = by_name(addons_status(deps, save=True))["ForeverCompanion"]
    assert first["status"] == "nouveau" and first["content_version"]["dataVersion"] == 7
    edit(addons / "ForeverCompanion" / "Data" / "Meta.lua", "dataVersion=7", "dataVersion=8")
    again = by_name(addons_status(deps))["ForeverCompanion"]
    assert again["status"] == "changé"
    assert again["files"]["modified"] == ["ForeverCompanion/Data/Meta.lua"]
    assert again["content_version"]["dataVersion"] == 8
    assert again["previous_content_version"]["dataVersion"] == 7
    assert "proposal" not in again  # aucun agrégat du dépôt n'en dépend : une liste seulement


def test_change_of_an_addon_with_dependents_proposes_a_pending_entry(deps, addons):
    addons_status(deps, save=True)
    edit(addons / "TalentsForeverBook" / "Data.lua", 'generated = "2026-01-01"', 'generated = "2026-01-03"')
    tf = by_name(addons_status(deps))["TalentsForeverBook"]
    assert tf["status"] == "changé"
    assert tf["proposal"]["kind"] == "addon_data"
    assert tf["proposal"]["depends"] == list(DATA_ADDONS["TalentsForeverBook"].depends)
    # relecture : recoupement des arbres avec classes.json installé (comptes seulement)
    assert tf["recheck"]["tf"] == 1 and tf["recheck"]["only_tf"] == 1


def test_untracked_folders_are_classified(addons):
    found = {u["folder"]: u for u in untracked_addons(addons)}
    assert found["EllesmereUI"]["status"] == "interface" and found["EllesmereUI"]["version"] == "9.9.9"
    assert found["EllesmereUI_Extra"]["status"] == "interface"
    assert found["ForeverCompletionist"]["status"] == "pas_un_addon"
    some = found["SomeDataAddon"]
    assert some["status"] == "non_inventorié" and some["action"] == "forever addons inventory SomeDataAddon"
    assert not {"TalentsForeverBook", "ForeverCompanion"} & set(found)


def test_status_lists_untracked_addons(deps):
    report = addons_status(deps)
    assert {u["folder"] for u in report["untracked"]} >= {"EllesmereUI", "SomeDataAddon", "ForeverCompletionist"}


def test_interface_addons_are_never_opened_beyond_their_toc(deps, addons, monkeypatch):
    opened: list[str] = []
    real_open, real_io_open = builtins.open, io.open
    real_read_text, real_read_bytes = Path.read_text, Path.read_bytes

    def note(path):
        opened.append(str(path).replace("\\", "/"))

    def fake_open(file, *a, **k):
        note(file)
        return real_open(file, *a, **k)

    def fake_io_open(file, *a, **k):
        note(file)
        return real_io_open(file, *a, **k)

    def fake_read_text(self, *a, **k):
        note(self)
        return real_read_text(self, *a, **k)

    def fake_read_bytes(self):
        note(self)
        return real_read_bytes(self)

    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(io, "open", fake_io_open)
    monkeypatch.setattr(Path, "read_text", fake_read_text)
    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    addons_status(deps)
    untracked_addons(addons)
    ui = [p for p in opened if "/EllesmereUI" in p]
    assert ui and all(p.endswith(".toc") for p in ui)


def test_inventory_gives_metadata_without_values(addons):
    out = inventory(addons / "SomeDataAddon")
    assert out["toc"]["Title"] == "Some Data Addon" and out["toc"]["Version"] == "2.1"
    assert out["saved_variables"] == ["SomeDataAddonDB"]
    assert out["license"] == {"source": "X-License", "name": "MIT"}
    assert out["files"]["count"] == 1
    assert out["fingerprint"] == fingerprint_folder(addons / "SomeDataAddon")
    [data] = out["files"]["list"]
    assert data["path"] == "Data.lua" and len(data["sha256"]) == 64
    assert data["header"] == ["Generated by fixture-tool 1.0"]
    assert out["globals"] == {"SomeDataAddonData": ["items", "rate"]}
    text = json.dumps(out, ensure_ascii=False)
    assert "Secret Sword" not in text and "4242" not in text


def test_inventory_of_forever_companion(addons):
    out = inventory(addons / "ForeverCompanion")
    assert out["license"] is None
    assert out["toc"]["Interface"] == "16001" and out["toc"]["X-Website"] == "https://example.invalid"
    assert out["files"]["count"] == 2
    assert out["globals"]["ForeverCompanionData.meta"] == ["dataVersion", "updated"]
    assert out["globals"]["ForeverCompanionData.bis"] == ["MAGE"]
    assert "Fixture Hat Of Values" not in json.dumps(out, ensure_ascii=False)


def test_inventory_writes_nothing(addons, tmp_path):
    before = sorted((p.as_posix(), p.stat().st_mtime_ns) for p in tmp_path.rglob("*"))
    inventory(addons / "ForeverCompanion")
    assert sorted((p.as_posix(), p.stat().st_mtime_ns) for p in tmp_path.rglob("*")) == before


def test_cli_inventory_json(deps, addons, capsys):
    assert main(["addons", "inventory", "SomeDataAddon", "--dir", str(addons), "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["toc"]["Title"] == "Some Data Addon"
    assert data["provenance"]["certainty"] == "suppose"


def test_crosscheck_counts_only(addons):
    result = crosscheck(addons / "TalentsForeverBook" / "Data.lua", DATA_DIR / LOCAL_VERSION / "classes.json")
    assert result["head"] == {"build": "1.60.1.79999", "generated": "2026-01-01", "codeVersion": "9"}
    assert result["classes"]["WARRIOR"]["tf"] == 1 and result["classes"]["WARRIOR"]["only_tf"] == 1
    assert "Fixture Talent" not in json.dumps(result, ensure_ascii=False)
