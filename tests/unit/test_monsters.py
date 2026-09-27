"""Table des monstres : PV mesurés dans les journaux (`certain`), Questie en regard (`suppose`), agrégat par niveau
sur les PNJ normaux ; écarts journal ↔ Questie et conflits listés, jamais moyennés."""

from conftest import FIXTURES, LOCAL_VERSION, REAL_LOG, SYNTHETIC_LOGS

from forever.pipeline.combatlog import read_log
from forever.pipeline.measure import monster_hp
from forever.pipeline.monsters import build_monsters
from forever.pipeline.questie import read_questie

QUESTIE = FIXTURES / "questie" / "11.38.0"


def observations(path=REAL_LOG):
    _, events = read_log(path)
    return monster_hp(list(events), log=path.name)


def obs(npc_id, level, max_hp, name="PNJ"):
    return {"npc_id": npc_id, "name": name, "level": level, "max_hp": max_hp, "guids": 1, "ui_map_id": 1411, "log": "x"}


def test_measured_npcs_are_certain_and_match_questie():
    found, conflicts = observations()
    table = build_monsters(found, read_questie(QUESTIE), LOCAL_VERSION, conflicts=conflicts, logs=[REAL_LOG.name])
    boar = table["npcs"]["3099"]
    assert boar["name"] == "Dire Mottled Boar" and boar["rank"] == 0 and boar["zone_id"] == 14
    six, seven = boar["levels"]["6"], boar["levels"]["7"]
    assert (six["max_hp"], six["certainty"], six["questie_hp"]) == (120, "certain", 120)
    assert REAL_LOG.name in six["source"]
    assert (seven["max_hp"], seven["certainty"], seven["questie_hp"]) == (137, "certain", 137)
    hare = table["npcs"]["5951"]["levels"]["1"]
    assert (hare["max_hp"], hare["certainty"], hare["questie_hp"]) == (8, "certain", 8)
    assert "3111" not in table["npcs"]  # dans Questie mais jamais observé : pas de copie de la base
    assert table["questie_gaps"] == [] and table["conflicts"] == []
    assert table["questie_version"] == "11.38.0" and table["game_version"] == LOCAL_VERSION
    level6 = table["hp_by_level"]["6"]
    assert (level6["value"], level6["certainty"], level6["n_npcs"]) == (120, "probable", 1)  # un seul PNJ observé


def test_questie_only_levels_stay_suppose_and_skip_elites():
    table = build_monsters([obs(5951, 1, 8, "Hare")], read_questie(QUESTIE), LOCAL_VERSION)
    level6 = table["hp_by_level"]["6"]
    assert (level6["value"], level6["certainty"], level6["n_npcs"]) == (120, "suppose", 2)  # 3099 et 3111
    assert "communautaire" in level6["source"]
    assert "5" not in table["hp_by_level"]  # 5945 élite (rang 1) écarté
    assert table["hp_by_level"]["1"]["certainty"] == "probable"  # un seul PNJ observé


def test_gap_between_log_and_questie_is_listed():
    table = build_monsters([obs(3099, 6, 125)], read_questie(QUESTIE), LOCAL_VERSION)
    assert table["npcs"]["3099"]["levels"]["6"]["max_hp"] == 125
    assert table["questie_gaps"] == [{"npc_id": 3099, "level": 6, "measured": 125, "questie": 120}]


def test_conflicting_logs_are_listed_not_averaged():
    table = build_monsters([obs(3099, 6, 120), obs(3099, 6, 125)], None, LOCAL_VERSION)
    assert "3099" not in table["npcs"] or "6" not in table["npcs"]["3099"]["levels"]
    assert table["conflicts"] == [{"npc_id": 3099, "level": 6, "values": [120, 125], "log": "x"}]


def test_without_questie():
    found, _ = observations()
    table = build_monsters(found, None, LOCAL_VERSION)
    assert table["npcs"]["3099"]["levels"]["6"]["questie_hp"] is None and table["npcs"]["3099"]["rank"] is None
    assert table["questie_version"] is None
    assert table["hp_by_level"]["7"]["value"] == 137


def test_summoned_creatures_are_not_monsters():
    found, conflicts = observations(SYNTHETIC_LOGS / "summoned.txt")
    assert found == [] and conflicts == []


def test_installed_table_is_read_by_game_data(game_data):
    monsters = game_data.monsters
    assert (
        monsters.hp_by_level[11].value == 239 and monsters.hp_by_level[11].certainty == "certain"
    )  # 7 PNJ concordants
    assert monsters.hp_by_level[25].certainty == "probable"  # un seul PNJ nommé
    assert monsters.npcs[3099][7].value == 137 and monsters.npcs[3099][7].certainty == "certain"
