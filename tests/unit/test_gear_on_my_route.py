"""Bloc 4c (idées du chat du 2026-10-16, point 2 ; décision 282) : objets pris d'abord sur ma route de leveling.
Zones de ma route : celles du parcours gratuit de RestedXP de ma race et de ma classe à ces niveaux ; un objet de
ces zones passe devant un objet d'ailleurs ; un objet d'une zone de départ d'une autre race (Zephras Isle pour un
Gnome) n'est jamais proposé, sauf s'il est sur ma route ; un objet hors de ma route, faute de mieux, porte « détour ».
Butin aléatoire (« n'importe où ») et marchand de ma route : non concernés par le détour.

Valeurs : addon GearQuest fabriqué dans `tmp_path`, zones et quêtes fabriquées. Aucun chiffre de jeu ici."""

from forever.gear import Access, leveling_gear

LEVEL = 10
ITEMS = {
    # objet : (emplacement, rang GearQuest, zone, quête)
    960001: ("Hands", 1, "Fixture Far Isle", "Fixture Far Errand"),  # zone de départ d'une autre race
    960002: ("Hands", 2, "Fixture Hills", "Fixture Hills Errand"),  # hors de ma route
    960003: ("Hands", 3, "Fixture Vale", "Fixture Vale Errand"),  # sur ma route
    960004: ("Feet", 1, "Fixture Far Isle", "Fixture Far Errand"),  # seule offre : zone de départ d'une autre race
    960005: ("Feet", 2, "Fixture Hills", "Fixture Hills Errand"),  # faute de mieux : détour
}
QUEST = {"level": LEVEL, "min_level": LEVEL - 2, "faction": "both"}


def addons(tmp_path):
    folder = tmp_path / "AddOns" / "GearQuestForever_MAGE"
    folder.mkdir(parents=True)
    facts = "\n".join(
        f'    [{i}]={{name="Fixture {i}",quality=2,reqLevel={LEVEL},sourceType="quest_reward",questName="{q}",zone="{z}"}},'
        for i, (_, _, z, q) in ITEMS.items()
    )
    picks = "\n".join(
        f'    {{{i},"{slot}",{LEVEL},{LEVEL},{rank},"frost","Alliance",1.0}},'
        for i, (slot, rank, _, _) in ITEMS.items()
    )
    (folder / "Data.Mage.generated.lua").write_text(
        f"local GQ = GearQuest\nGQ.Data.mageItemFacts = {{\n{facts}\n}}\nGQ.Data.magePicks = {{\n{picks}\n}}\n",
        encoding="utf-8",
    )
    return tmp_path / "AddOns"


def access(route=frozenset({"Fixture Vale"}), starts=frozenset({"Fixture Far Isle"})):
    return Access(
        quests=lambda name: [QUEST],
        dungeon_level=lambda item: None,
        red_min_diff=5,
        route_zones=route,
        other_start_zones=starts,
    )


def test_items_on_my_route_come_first(tmp_path):
    picks = {p["slot"]: p for p in leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, access=access())}
    assert picks["Hands"]["item"] == 960003 and not picks["Hands"].get("detour")


def test_other_race_start_zone_is_never_proposed_and_detour_is_said(tmp_path):
    out = leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, access=access())
    picks = {p["slot"]: p for p in out}
    assert picks["Feet"]["item"] == 960005 and picks["Feet"]["detour"] == "Fixture Hills"
    reasons = {e["item"]: e["reason"] for e in out.excluded}
    assert "zone de départ d'une autre race" in reasons[960004]


def test_a_start_zone_on_my_route_is_kept(tmp_path):
    route = frozenset({"Fixture Vale", "Fixture Far Isle"})
    picks = {p["slot"]: p for p in leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, access=access(route=route))}
    assert picks["Feet"]["item"] == 960004 and not picks["Feet"].get("detour")


def test_without_route_knowledge_gearquest_order_stays(tmp_path):
    no_route = access(route=None, starts=frozenset())
    picks = {p["slot"]: p for p in leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, access=no_route)}
    assert picks["Hands"]["item"] == 960001 and not picks["Hands"].get("detour")
