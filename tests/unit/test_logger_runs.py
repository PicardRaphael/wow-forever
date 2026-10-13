"""DJ1, bloc D : vrai Lua de ForeverLogger 0.6.0 (schéma 4) exécuté sous lupa.lua51 avec le client simulé
`tests/fixtures/bridge/wow_stub.lua` : passages en instance (entrée, sortie, rencontres), butin ramassé avec le PNJ
qui l'a lâché ; lecture des passages et du butin dans les SavedVariables (`forever/pipeline/addon_sv.py`).
Valeurs synthétiques (entrées du client simulé, fixture `tests/fixtures/addon/ForeverLoggerDB_runs.lua`), aucune
règle de jeu."""

import re

import pytest
from conftest import FIXTURES, REPO_ROOT

from forever.pipeline.addon_sv import read_logger_db

lupa = pytest.importorskip("lupa")
from lupa import lua51

ADDON = REPO_ROOT / "addon" / "ForeverLogger"
STUB = FIXTURES / "bridge" / "wow_stub.lua"
GUID = "Player-0000-00000001"
INSTANCE = {"inside": True, "type": "party", "name": "Ragefire Chasm", "id": 389}
OUTSIDE = {"inside": False, "type": "none"}
BOSS_GUID = "Creature-0-4170-389-28-11520-0000ABCDEF"
ITEM_LINK = "|cff1eff00|Hitem:14149::::::::15:::::|h[Subterranean Cape]|h|r"


class Logger:
    def __init__(self, *, failing=()):
        self.lua = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB.read_bytes())
        self.stub = self.lua.globals().Stub
        for name in failing:
            self.stub.failing[name] = True
        self.stub.player.level = 15
        self.lua.execute((ADDON / "ForeverLogger.lua").read_bytes(), "ForeverLogger", self.lua.table())
        self.fire("ADDON_LOADED", "ForeverLogger")
        self.fire("PLAYER_LOGIN")
        self.fire("PLAYER_ENTERING_WORLD")

    def fire(self, event, *args):
        self.stub.Fire(event, *args)

    def place(self, instance, event="PLAYER_ENTERING_WORLD"):
        self.stub.instance = self.lua.table_from(instance)
        self.fire(event)

    def db(self):
        return self.lua.globals().ForeverLoggerDB

    def entries(self, name):
        table = self.db().characters[GUID][name]
        return [table[i] for i in range(1, len(table) + 1)] if table is not None else []

    def errors(self):
        errors = self.db().errors
        return {k: v.count for k, v in errors.items()} if errors is not None else {}


def test_schema_and_version():
    game = Logger()
    assert game.db().schema == 4
    toc = (ADDON / "ForeverLogger.toc").read_text(encoding="utf-8")
    assert re.search(r"^## Version: 0\.6\.0$", toc, re.MULTILINE)


def test_run_entry_and_exit_recorded():
    game = Logger()
    game.stub.group = game.lua.table_from({"size": 5, "raid": False})
    game.place(INSTANCE)
    game.stub.Advance(600)
    game.place(OUTSIDE)
    (run,) = game.entries("runs")
    assert run.instance == "Ragefire Chasm" and run.id == 389 and run.type == "party"
    assert run.level == 15 and run.group == 5 and run.difficulty == 1
    assert run.left - run.entered == 600
    assert game.errors() == {}


def test_zone_change_inside_keeps_one_run():
    game = Logger()
    game.place(INSTANCE)
    game.stub.Advance(60)
    game.place(INSTANCE, "ZONE_CHANGED_NEW_AREA")
    game.stub.Advance(60)
    game.place(INSTANCE, "PLAYER_ENTERING_WORLD")  # rechargement de l'interface dans l'instance
    (run,) = game.entries("runs")
    assert run.left is None


def test_other_instance_closes_the_open_run():
    game = Logger()
    game.place(INSTANCE)
    game.stub.Advance(30)
    game.place({**INSTANCE, "name": "Wailing Caverns", "id": 43})
    first, second = game.entries("runs")
    assert first.left is not None and second.id == 43 and second.left is None


def test_encounter_end_recorded():
    game = Logger()
    game.place(INSTANCE)
    game.stub.Advance(120)
    game.fire("ENCOUNTER_END", 2735, "Bazzalan", 1, 5, 1)
    game.fire("ENCOUNTER_END", 2734, "Jergosh the Invoker", 1, 5, 0)
    (run,) = game.entries("runs")
    first, second = run.encounters[1], run.encounters[2]
    assert (first.id, first.name, first.success) == (2735, "Bazzalan", True)
    assert second.success is False and isinstance(first.time, int | float)


def test_loot_records_source_npc():
    game = Logger()
    game.place(INSTANCE)
    game.stub.loot = game.lua.table_from(
        [
            {"link": ITEM_LINK, "name": "Subterranean Cape", "quantity": 1, "sources": [BOSS_GUID, 1]},
            {"name": "Copper", "quantity": 0},  # monnaie : sans lien d'objet
        ],
        recursive=True,
    )
    game.fire("LOOT_OPENED")
    (loot,) = game.entries("loot")
    assert loot.instance == 389
    item = loot["items"][1]
    assert (item.item, item.quantity, item.npc) == (14149, 1, 11520)
    assert item.source == BOSS_GUID
    assert len(loot["items"]) == 1


def test_api_errors_are_counted():
    """API du butin en panne : butin gardé sans source, aucune erreur remontée ; instance en panne : aucun passage."""
    game = Logger(failing=("GetLootSourceInfo",))
    game.place(INSTANCE)
    game.stub.loot = game.lua.table_from([{"link": ITEM_LINK, "name": "Cape", "quantity": 1}], recursive=True)
    game.fire("LOOT_OPENED")
    (loot,) = game.entries("loot")
    assert loot["items"][1].item == 14149 and loot["items"][1].npc is None
    broken = Logger(failing=("GetInstanceInfo", "IsInInstance"))
    broken.place(INSTANCE)
    assert broken.entries("runs") == []
    assert broken.errors() == {}


def test_no_combat_log_subscription():
    source = (ADDON / "ForeverLogger.lua").read_text(encoding="utf-8")
    assert "COMBAT_LOG_EVENT" not in source


def test_runs_are_read_from_saved_variables():
    db = read_logger_db(FIXTURES / "addon" / "ForeverLoggerDB_runs.lua")
    (character,) = db.characters.values()
    run = character.runs[0]
    assert (run.instance_id, run.name, run.level, run.group_size) == (389, "Ragefire Chasm", 15, 5)
    assert run.seconds == run.left - run.entered
    assert [e.name for e in run.encounters] == ["Oggleflint", "Bazzalan"]
    assert run.encounters[0].success is True
    assert character.runs[1].seconds is None  # passage encore ouvert
    (loot,) = character.loot
    assert loot.instance_id == 389 and loot.items[0]["item"] == 14149 and loot.items[0]["npc"] == 11520
