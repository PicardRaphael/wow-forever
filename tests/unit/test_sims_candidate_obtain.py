"""Réserve de candidats (SIM2 bloc 10) : un objet sans niveau requis dans la base des simulateurs (récompense de quête
du niveau 60, bijou de donjon…) n'est plus pris dans toutes les tranches. Cas réel du 2026-11-16 : Royal Seal of
Eldre'Thalas proposé au niveau 15. Sa source dans la base de wowsims est jugée par la règle « obtenable au niveau »
des choix de GearQuest (registre I21) : quête du camp prise à ce niveau et pas rouge, donjon ouvert, marchand ;
source sans niveau connu : écarté sous le niveau 60. Un objet choisi par GearQuest au niveau reste pris.
Base, quêtes et donjons fabriqués : aucune valeur de jeu."""

from forever.gear import Access
from forever.sims.brackets import candidate_pool, obtain_check

QUESTS = {
    "Quête basse": [{"level": 14, "min_level": 10, "faction": "both"}],
    "Quête haute": [{"level": 60, "min_level": 58, "faction": "both"}],
}
DUNGEONS = {910: 15, 911: 50}
ACCESS = Access(quests=lambda name: QUESTS.get(name, []), dungeon_level=DUNGEONS.get, red_min_diff=5)

DB = {
    900: {"type": 12, "sources": [{"quest": {"id": 1, "name": "Quête haute"}}]},  # bijou de quête du 60
    901: {"type": 12, "sources": [{"quest": {"id": 2, "name": "Quête basse"}}]},
    902: {"type": 2, "sources": [{"soldBy": {"npcId": 3}}]},  # marchand
    903: {"type": 11},  # aucune source
    910: {"type": 4, "sources": [{"drop": {"zoneId": 1}}]},  # donjon ouvert au 15
    911: {"type": 4, "sources": [{"drop": {"zoneId": 2}}]},  # donjon ouvert au 50
    912: {"type": 1, "reqLvl": 12, "sources": [{"quest": {"id": 1, "name": "Quête haute"}}]},  # niveau requis connu
    913: {"type": 5, "sources": [{"quest": {"id": 1, "name": "Quête haute"}}]},  # choisi par GearQuest
}


def check(level):
    return lambda item, row: obtain_check(row, item, level, "alliance", ACCESS)


def test_items_without_required_level_are_judged_by_their_source():
    sources = [("GearQuest", [913]), ("Naowh", [900, 901, 902, 903, 910, 911, 912])]
    pool, skipped = candidate_pool(DB, sources, level=15, class_id=3, obtain=check(15))
    assert {c["item"] for c in pool} == {901, 902, 910, 912, 913}
    reasons = {s["item"]: s["reason"] for s in skipped}
    assert set(reasons) == {900, 903, 911}
    assert "Quête haute" in reasons[900] and "50" in reasons[911] and "inconnu" in reasons[903]


def test_level_60_takes_every_source():
    pool, skipped = candidate_pool(DB, [("Naowh", [900, 903, 911])], level=60, class_id=3, obtain=check(60))
    assert {c["item"] for c in pool} == {900, 903, 911} and skipped == []


def test_without_a_check_the_old_rule_holds():
    pool, _ = candidate_pool(DB, [("Naowh", [900])], level=15, class_id=3)
    assert [c["item"] for c in pool] == [900]
