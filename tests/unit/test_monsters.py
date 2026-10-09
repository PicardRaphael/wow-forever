"""Table des monstres : PV mesurés dans les journaux (`certain`), Questie en regard (`suppose`), agrégat par niveau
sur les PNJ normaux ; écarts journal ↔ Questie et conflits listés, jamais moyennés."""

from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, REAL_LOG, SYNTHETIC_LOGS, read_json

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


def test_player_controlled_creatures_are_not_monsters():
    """Décision 204 : toute invocation de joueur est écartée d'office, même sans propriétaire dans le bloc avancé
    (drapeaux du journal : gardien, familier ou contrôle par un joueur) ; une créature contrôlée par le serveur reste
    un monstre, même nommée « Summoned »."""
    found, conflicts = observations(SYNTHETIC_LOGS / "player_controlled.txt")
    assert conflicts == []
    assert [(o["npc_id"], o["name"]) for o in found] == [(5676, "Summoned Voidwalker")]


def test_installed_table_is_read_by_game_data(game_data):
    """Les données typées reprennent `monsters.json` installé, niveau par niveau et PNJ par PNJ (décision 215 : aucune
    valeur ni certitude de la version installée écrite en dur ; une mesure ne touche plus ce test)."""
    table = read_json(DATA_DIR / LOCAL_VERSION / "monsters.json")
    monsters = game_data.monsters
    for level, row in table["hp_by_level"].items():
        got = monsters.hp_by_level[int(level)]
        assert (got.value, got.certainty) == (row["value"], row["certainty"]), level
    for npc_id, entry in table["npcs"].items():
        for level, row in entry["levels"].items():
            got = monsters.npcs[int(npc_id)][int(level)]
            assert (got.value, got.certainty) == (row["max_hp"], row["certainty"]), (npc_id, level)


# --- Courbe des PV : seuls les PNJ combattus par le joueur et non amis (décision 222, 2026-10-09) -------------------
# Journal synthétique : un PNJ hostile et un neutre combattus par le joueur, un hostile seulement vu (combattu par un
# autre joueur), un garde ami vu à côté des combats (comme Dun Morogh Mountaineer, niveau 30), un PNJ ami combattu.


def test_observations_carry_the_fight_and_the_reaction():
    found, _ = observations(SYNTHETIC_LOGS / "reactions.txt")
    seen = {o["npc_id"]: (o["fought"], o["reaction"]) for o in found}
    assert seen == {
        1001: (True, "hostile"),
        1002: (True, "neutre"),
        1003: (False, "hostile"),
        1004: (False, "amie"),
        1005: (True, "amie"),
    }


def test_only_fought_non_friendly_npcs_enter_the_curve():
    found, conflicts = observations(SYNTHETIC_LOGS / "reactions.txt")
    table = build_monsters(found, None, LOCAL_VERSION, conflicts=conflicts)
    assert set(table["npcs"]) == {"1001", "1002", "1003", "1004", "1005"}  # tous mesurés un par un
    reasons = {e["npc_id"]: e["reason"] for e in table["curve_excluded"]}
    assert set(reasons) == {1003, 1004, 1005}
    assert "ami" in reasons[1004] and "ami" in reasons[1005]
    assert "jamais combattu" in reasons[1003]
    assert all("décision 222" in r for r in reasons.values())
    assert set(table["hp_by_level"]) == {"8", "9"}  # niveaux de 1001 et 1002 seulement


def test_an_observation_without_the_fight_flag_stays_in_the_curve():
    """Mesure reportée d'un journal disparu (sans les indicateurs) : la règle ne s'applique pas, rien n'est deviné."""
    table = build_monsters([obs(3099, 6, 120)], None, LOCAL_VERSION)
    assert table["curve_excluded"] == [] and table["hp_by_level"]["6"]["value"] == 120


def test_an_npc_fought_in_a_vanished_log_is_not_excluded_for_being_only_seen_later():
    """Relevé du 2026-10-09 (Sunscale Lashtail, Savannah Huntress) : combattus dans des journaux disparus (mesure
    reportée, sans indicateur), seulement vus dans les nouveaux : rien ne prouve qu'ils n'ont jamais été combattus."""
    seen_only = {**obs(3254, 14, 345, "Sunscale Lashtail"), "fought": False, "reaction": "hostile"}
    carried = {**obs(3254, 13, 307, "Sunscale Lashtail")}
    table = build_monsters([seen_only, carried], None, LOCAL_VERSION)
    assert table["curve_excluded"] == []
    friendly = {**obs(13076, 30, 2484, "Dun Morogh Mountaineer"), "fought": False, "reaction": "amie"}
    table = build_monsters([friendly, obs(13076, 29, 2400)], None, LOCAL_VERSION)
    assert [e["npc_id"] for e in table["curve_excluded"]] == [13076]  # ami : écarté d'office, même mêlé à un report


def test_an_npc_measured_before_in_a_vanished_log_keeps_an_unknown_fight():
    """Greater Plainstrider (2026-10-09) : mesuré jadis dans un journal disparu, remesuré au même niveau en n'étant que
    vu : l'observation reportée est remplacée, mais « jamais combattu » reste non établi (`unknown_fight`)."""
    seen_only = {**obs(3244, 13, 307, "Greater Plainstrider"), "fought": False, "reaction": "hostile"}
    assert [e["npc_id"] for e in build_monsters([seen_only], None, LOCAL_VERSION)["curve_excluded"]] == [3244]
    table = build_monsters([seen_only], None, LOCAL_VERSION, unknown_fight={3244})
    assert table["curve_excluded"] == [] and table["hp_by_level"]["13"]["value"] == 307
