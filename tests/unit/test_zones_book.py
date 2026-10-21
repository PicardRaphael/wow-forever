"""Zones et donjons du niveau tirés du livre de quêtes fusionné des sources Forever (décision 294, plan des simulateurs
§6) : plus la base Classic Era de Questie. Une quête que seule une source Classic connaît (statut « absente des sources
Forever », ou source `questie` seule) n'est jamais comptée ; camp, classe et niveau requis filtrent ; les zones sont
nommées par leur carte (noms de Completo) et classées par quêtes utiles (vertes, jaunes, orange) ; les quêtes de
donjon vont au donjon.

Livre fabriqué ici (structure de `forever.quests`) ; quêtes, cartes et niveaux inventés."""

from forever.quests import QuestBook, zones_from_book

MAGE, WARRIOR = 1 << 7, 1 << 0  # masques de classe (identifiants de ChrClasses du client : Mage 8, Guerrier 1)


def quest(qid, level, *, map_id=None, sources=("completo",), status="nouvelle", faction="both", classes=None,
          dungeon=None, min_level=None):  # fmt: skip
    fields = {"level": level, "min_level": min_level if min_level is not None else level - 2, "faction": faction}
    if map_id is not None:
        fields["map"] = map_id
    if classes is not None:
        fields["classes"] = classes
    if dungeon is not None:
        fields["dungeon"] = dungeon
    return {
        "id": qid, "name": f"Quête {qid}", "status": status, "certainty": "suppose", "sources": list(sources),
        "fields": {k: {"value": v, "source": sources[0], "certainty": "suppose"} for k, v in fields.items()},
        "changed_fields": [], "discrepancies": {},
    }  # fmt: skip


def book(*quests):
    return QuestBook({q["id"]: q for q in quests}, [], "x", False, [], {9001: "Zone Une", 9002: "Zone Deux"})


def test_only_forever_sources_count(game_data):
    b = book(
        quest(1, 12, map_id=9001),
        quest(2, 12, map_id=9001, sources=("questie",), status="absente des sources Forever"),
        quest(3, 12, map_id=9002, sources=("questie",)),
        quest(4, 13, map_id=9002, sources=("questie", "naowh_dj")),
    )
    out = zones_from_book(b, game_data, 12, faction="alliance", player_class="mage")
    by_name = {z["name"]: z for z in out["zones"]}
    assert by_name["Zone Une"]["quests"] == [1] and by_name["Zone Deux"]["quests"] == [4]
    assert any("sources Forever" in n for n in out["notes"]) and "Classic Era" not in out["source"]


def test_faction_class_and_level_filter(game_data):
    b = book(
        quest(1, 12, map_id=9001, faction="horde"),
        quest(2, 12, map_id=9001, classes=WARRIOR),
        quest(3, 12, map_id=9001, classes=MAGE),
        quest(4, 30, map_id=9001, min_level=28),
    )
    out = zones_from_book(b, game_data, 12, faction="alliance", player_class="mage")
    assert out["zones"][0]["quests"] == [3]


def test_dungeon_quests_go_to_the_dungeon_and_zones_are_ranked(game_data):
    b = book(
        quest(1, 12, map_id=9001),
        quest(2, 12, map_id=9002),
        quest(3, 13, map_id=9002),
        quest(4, 14, dungeon="Fixture Depths"),
    )
    out = zones_from_book(b, game_data, 12, faction="alliance", player_class="mage")
    assert [z["name"] for z in out["zones"]] == ["Zone Deux", "Zone Une"]
    assert out["dungeons"][0]["name"] == "Fixture Depths" and out["dungeons"][0]["kind"] == "dungeon"


def test_unknown_class_is_said_and_class_quests_are_left_out(game_data):
    """Classe inconnue : la réponse le dit, ne suppose aucune classe (plus le Mage par défaut) et laisse de côté les
    quêtes de classe."""
    b = book(quest(1, 12, map_id=9001), quest(2, 12, map_id=9001, classes=MAGE))
    out = zones_from_book(b, game_data, 12, faction="alliance", player_class=None)
    assert out["zones"][0]["quests"] == [1]
    assert any("classe inconnue" in n for n in out["notes"]) and not any("classe mage" in n for n in out["notes"])
