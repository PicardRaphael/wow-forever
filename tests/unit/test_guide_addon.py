"""Repli de livraison jeu fermé (RX1, bloc D) : dossier `Interface/AddOns/ForeverRoute/` écrit par
`forever/bridge/guide_addon.py` et `forever route deliver <id> --addon`. Le `Guide.lua` écrit est exécuté sous
lupa.lua51 avec un faux `RXPGuides`. Tout s'écrit dans `tmp_path`."""

import json
from datetime import UTC, datetime

import pytest
from conftest import DATA_DIR, FIXTURES, REGISTRY_PATH, FakeHttp, read_json

from forever.bridge.guide_addon import ADDON_NAME, bracket_level, bridge_interface, guide_lua, write_guide_addon
from forever.cli import main
from forever.config import Deps
from forever.errors import InvalidArgumentError

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
PLAN = read_json(FIXTURES / "rxp" / "plan.json")
TOC = "## Interface: 99999\n## Title: ForeverBridge\n"  # valeur de fixture : recopiée telle quelle, jamais devinée


def _addons(tmp_path):
    addons = tmp_path / "wow" / "Interface" / "AddOns"
    (addons / "ForeverBridge").mkdir(parents=True)
    (addons / "ForeverBridge" / "ForeverBridge.toc").write_text(TOC, encoding="utf-8")
    return addons


def test_interface_read_from_the_bridge_toc(tmp_path):
    addons = _addons(tmp_path)
    assert bridge_interface(addons) == "99999"
    (addons / "ForeverBridge" / "ForeverBridge.toc").unlink()
    with pytest.raises(InvalidArgumentError):
        bridge_interface(addons)


def test_guide_addon_written_only_when_game_closed(tmp_path):
    addons = _addons(tmp_path)
    backups = tmp_path / "backups"
    with pytest.raises(InvalidArgumentError):
        write_guide_addon(addons, "step\n", game_running=lambda: True, backup_dir=backups, now=NOW)
    assert not (addons / ADDON_NAME).exists()
    folder = write_guide_addon(addons, "#name A\nstep\n", game_running=lambda: False, backup_dir=backups, now=NOW)
    assert folder == addons / ADDON_NAME
    assert sorted(p.name for p in folder.iterdir()) == ["ForeverRoute.toc", "Guide.lua"]
    toc = (folder / "ForeverRoute.toc").read_text(encoding="utf-8").splitlines()
    assert "## Interface: 99999" in toc and "## Dependencies: RXPGuides" in toc and "Guide.lua" in toc
    (folder / "stale.txt").write_text("ancien", encoding="utf-8")
    write_guide_addon(addons, "#name B\nstep\n", game_running=lambda: False, backup_dir=backups, now=NOW)
    assert not (folder / "stale.txt").exists()  # réécrit en entier
    saved = list(backups.iterdir())
    assert len(saved) == 1 and (saved[0] / "stale.txt").is_file()  # ancien dossier sauvegardé hors des addons
    others = sorted(p.name for p in addons.iterdir())
    assert others == ["ForeverBridge", ADDON_NAME]  # aucun autre chemin


def test_guide_addon_bracket_level():
    text = "a ]] b ]=] c"
    level = bracket_level(text)
    assert level == 2
    assert "]" + "=" * level + "]" not in text
    lua = guide_lua(text)
    assert f"[{'=' * level}[" in lua and lua.count("RegisterGuide") == 1


def test_guide_lua_registers_the_exact_text():
    lupa = pytest.importorskip("lupa")
    lua = lupa.lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute("got = {}\nRXPGuides = { RegisterGuide = function(text) got[#got + 1] = text end }")
    text = "#forever\n#name X ]] y\nstep\n    .accept 1 >>Accept X\n"
    lua.execute(guide_lua(text))
    got = lua.globals().got
    assert len(got) == 1 and got[1] == text
    lua2 = lupa.lua51.LuaRuntime(unpack_returned_tuples=True)
    lua2.execute(guide_lua(text))  # RestedXP absent : aucune erreur


def test_route_deliver_addon_cli(tmp_path, capsys):
    addons = _addons(tmp_path)
    cache = tmp_path / "cache"
    (cache / "routes").mkdir(parents=True)
    (cache / "routes" / f"{PLAN['id']}.json").write_text(json.dumps({**PLAN, "provenance": {}}), encoding="utf-8")

    def deps(running):
        return Deps(
            data_dir=DATA_DIR,
            registry_path=REGISTRY_PATH,
            cache_dir=cache,
            http_get=FakeHttp.failing(),
            now=lambda: NOW,
            offline=True,
            wow_dir=addons.parent.parent,
            game_running=lambda: running,
        )

    assert main(["route", "deliver", PLAN["id"], "--addon", "--json"], deps=deps(True)) != 0
    assert not (addons / ADDON_NAME).exists()
    capsys.readouterr()
    assert main(["route", "deliver", PLAN["id"], "--addon", "--json"], deps=deps(False)) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["folder"].endswith(ADDON_NAME) and (addons / ADDON_NAME / "Guide.lua").is_file()
    assert "provenance" in doc
