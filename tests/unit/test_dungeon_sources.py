"""Lecteurs locaux des donjons des addons (DJ1, bloc B) et corrections des lecteurs de quêtes (`read_fdj` : tous les
donjons de ForeverDungeonJournal ; `read_forever_guide` : `DalaranData.lua`).

Fixtures synthétiques `tests/fixtures/addons/dungeons/` (structure des addons du 2026-10-13, valeurs inventées,
README) ; aucun réseau, aucun chiffre de jeu : les valeurs attendues sont celles écrites dans les fixtures."""

import json

import pytest
from conftest import FIXTURES

from forever.addons import DATA_ADDONS
from forever.pipeline.dungeon_sources import (
    dungeon_source_files,
    read_atlasloot,
    read_companion,
    read_fdj_dungeons,
    read_fojji,
    read_guide_dungeons,
    read_naowh_journal,
    read_naowh_runs,
    read_zoneinfo,
)
from forever.pipeline.quest_sources import read_fdj, read_forever_guide

WOW = FIXTURES / "addons" / "dungeons"
ADDONS = WOW / "Interface" / "AddOns"
WTF = WOW / "WTF"
PERCENT = 100.0  # conversion d'unité : les sources écrivent des pourcentages, le dépôt des fractions


@pytest.fixture(scope="module")
def naowh():
    return read_naowh_journal(ADDONS)


def boss(dungeon, name):
    return next(b for b in dungeon["bosses"] if b["name"] == name)


def loot(b, item):
    return next(x for x in b["loot"] if x["item"] == item)


def test_readers_return_none_without_their_addon(tmp_path):
    for reader in (
        read_naowh_journal,
        read_fojji,
        read_fdj_dungeons,
        read_guide_dungeons,
        read_atlasloot,
        read_companion,
        read_zoneinfo,
    ):
        assert reader(tmp_path) is None, reader.__name__
    assert read_naowh_runs(tmp_path) is None


def test_naowh_dungeon_keyed_by_instance(naowh):
    assert naowh.info.version == "1.1.11" and naowh.info.certainty == "suppose"
    rfc = naowh.dungeons["389"]
    assert rfc["name"] == "Ragefire Chasm" and rfc["levels"] == {"min": 13, "max": 18}
    assert rfc["entrance"] == {"map": 1454, "x": 52.0, "y": 49.0}
    assert rfc["quests"] == [5723, 5728]
    assert boss(rfc, "Taragaman the Hungerer")["npc"] == 11520
    assert boss(rfc, "Taragaman the Hungerer")["encounter"] == 2733
    assert all(b["name"] != "Trash" for b in rfc["bosses"])  # monstres ordinaires : pas un boss
    excavation = naowh.dungeons["2998"]
    assert excavation["new"] is True and "closed" not in excavation
    closed = naowh.dungeons["name:Alcaz Prison"]  # sans instance dans la source
    assert closed["closed"] is True and closed["new"] is True


def test_naowh_boss_levels_from_boss_info(naowh):
    assert boss(naowh.dungeons["389"], "Taragaman the Hungerer")["level"] == 16
    assert "level" not in boss(naowh.dungeons["2998"], "Highland Horror")  # niveau négatif : inconnu


def test_naowh_rates_are_percent(naowh):
    taragaman = boss(naowh.dungeons["389"], "Taragaman the Hungerer")
    assert loot(taragaman, 14149)["rate"] == pytest.approx(32 / PERCENT)
    assert loot(taragaman, 14148)["rate"] is None  # 0 : moins de victoires que le seuil de l'addon, inconnu
    assert "classic" not in loot(taragaman, 14149)


def test_naowh_prereqs_and_min_level(naowh):
    assert naowh.prereqs[5728] == [5727]
    assert naowh.prereqs[96500] == [96498, [96499, 96497]]  # sous-liste : l'un des deux suffit
    assert naowh.min_levels == {5723: 9, 96500: 22}


def test_naowh_runs_skip_player_names():
    runs = read_naowh_runs(WTF)
    dump = json.dumps([runs.runs, runs.kills, runs.loot], ensure_ascii=False)
    assert "JoueurSecret" not in dump and "Autre" not in dump
    tracker = next(r for r in runs.runs if r["source"] == "instance_tracker")
    assert (tracker["instance_id"], tracker["seconds"], tracker["level"], tracker["xp"], tracker["deaths"]) == (
        389,
        2400,
        15,
        9000,
        1,
    )
    journal = next(r for r in runs.runs if r["source"] == "journal_run")
    assert journal["instance_id"] == 389 and journal["seconds"] == 2360
    assert runs.kills[2733] == {"took": [95], "n": 1}
    assert runs.loot == [
        {"item": 14149, "dungeon": "RagefireChasm", "boss": "Taragaman the Hungerer", "at": 1791548010}
    ]


def test_fojji_access_keys():
    fojji = read_fojji(ADDONS)
    assert fojji.info.version == "3.3.5"
    excavation = fojji.dungeons["2998"]
    assert excavation["levels"] == {"min": 26, "max": 31}
    assert excavation["access"] == [{"item": 280100, "name": "Dig Permit", "required": True, "quests": [96498]}]
    taragaman = boss(fojji.dungeons["389"], "Taragaman the Hungerer")
    assert taragaman["level"] == 17 and loot(taragaman, 14149)["rate"] == pytest.approx(30.5 / PERCENT)
    assert loot(boss(excavation, "Saltspine"), 280002)["rate"] is None  # odds absents
    assert fojji.prereqs[5728] == [5726, 5727]


def test_fdj_reads_every_dungeon():
    fdj = read_fdj_dungeons(ADDONS)
    names = {d["name"] for d in fdj.dungeons.values()}
    assert names == {"Hall of Thanes", "Ragefire Chasm", "Excavation Site: Wetlands"}  # trois formes d'écriture
    excavation = fdj.dungeons["name:Excavation Site: Wetlands"]
    assert excavation["levels"] == {"min": 26, "max": 33}
    assert boss(excavation, "Relic Guardian")["level"] == 28  # BOSS_LEVELS (texte)
    thanes = fdj.dungeons["name:Hall of Thanes"]
    assert thanes["entrance"] == {"map": 1426, "x": 50.0, "y": 40.0}  # 0-1 converti en %
    assert fdj.prereqs[96395] == [96391, 96392]


def test_fdj_quests_of_every_dungeon():
    quests = read_fdj(ADDONS).quests
    assert {q: quests[q]["dungeon"] for q in (96395, 5723, 96500)} == {
        96395: "Hall of Thanes",
        5723: "Ragefire Chasm",
        96500: "Excavation Site: Wetlands",
    }


def test_guide_reads_dalaran_data():
    quests = read_forever_guide(ADDONS).quests
    assert quests[96986]["dungeon"] == "City of Dalaran" and quests[96986]["level"] == 33
    assert quests[96987]["faction"] == "alliance"
    assert quests[544]["next"] == 96986 and "dungeon" not in quests[544]  # clé des égouts : prérequis hors donjon
    guide = read_guide_dungeons(ADDONS)
    assert guide.dungeons["2959"]["quests"] == [96986, 96987]


def test_guide_dungeons_loot_and_trash():
    guide = read_guide_dungeons(ADDONS)
    rfc = guide.dungeons["389"]
    assert rfc["levels"] == {"min": 13, "max": 18} and rfc["entrance"] == {"map": 1454, "x": 52.6, "y": 49.0}
    assert rfc["quests"] == [5723, 5728] and rfc["trash_npcs"] == 3
    item = loot(boss(rfc, "Taragaman the Hungerer"), 14149)
    assert item["rate"] == pytest.approx(31.0 / PERCENT) and item["classic"] is True
    assert loot(boss(rfc, "Taragaman the Hungerer"), 14148)["rate"] is None
    excavation = guide.dungeons["2998"]
    assert excavation["quests"] == [96500]  # quête sans identifiant (texte) : non rendue
    assert loot(boss(excavation, "Saltspine"), 280002).get("classic") is not True  # objet nouveau : pas Classic


def test_atlasloot_rates_marked_classic():
    atlas = read_atlasloot(ADDONS)
    assert atlas.info.version == "Forever 1.60.1"
    rfc = atlas.dungeons["389"]
    assert rfc["access_level"] == 10 and rfc["levels"] == {"min": 13, "max": 18}  # première valeur de GetForVersion
    taragaman = boss(rfc, "Taragaman the Hungerer")
    assert taragaman["npc"] == 11520 and taragaman["level"] == 16
    assert loot(taragaman, 14149) == {"item": 14149, "rate": pytest.approx(31.5 / PERCENT), "classic": True}
    ruins = atlas.dungeons["name:Ruins of Lordaeron"]
    assert ruins["levels"] == {"min": 13, "max": 18} and loot(boss(ruins, "Witherfang"), 280500)["rate"] is None


def test_alexatlasloot_is_not_read():
    files = dungeon_source_files(ADDONS, WTF)
    assert files and all("AlexAtlasLoot" not in str(p) for p in files)
    assert "AlexAtlasLoot" not in DATA_ADDONS


def test_companion_rates_marked_classic():
    companion = read_companion(ADDONS)
    rfc = companion.dungeons["name:Ragefire Chasm"]
    assert rfc["levels"] == {"min": 13, "max": 18}
    item = loot(boss(rfc, "Taragaman the Hungerer"), 14149)
    assert item["rate"] == pytest.approx(0.3094) and item["classic"] is True
    assert companion.dungeons["name:Excavation Site: Wetlands"]["new"] is True


def test_zoneinfo_levels_by_area():
    zone = read_zoneinfo(ADDONS)
    assert zone.dungeons["area:16732"]["levels"] == {"min": 24, "max": 29}
    assert zone.dungeons["name:The Drowned City"]["levels"] == {"min": 35, "max": 40}


def test_addons_status_lists_dungeon_readers():
    for name in ("AtlasLootClassic", "ForeverDungeonJournal", "NaowhForever", "FojjiCore", "ForeverCompanion"):
        assert "forever/pipeline/dungeon_sources.py" in DATA_ADDONS[name].reader, name
    assert "forever/pipeline/dungeon_sources.py" in DATA_ADDONS["ZoneInfoForever"].reader
    assert any("donjons" in u for u in DATA_ADDONS["NaowhForever"].uses)
