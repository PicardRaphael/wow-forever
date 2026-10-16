"""Fin du bloc 4c (décision 282) :

- origine détaillée : une quête dit son donneur, sa zone, sa position et les quêtes à faire d'abord ; un butin de
  donjon dit le donjon, le boss et le taux ;
- autre source quand GearQuest n'a rien d'obtenable pour un emplacement : butin d'un donjon ouvert à ce niveau, d'un
  type d'objet que GearQuest donne à ma classe pour cet emplacement (tissu pour le Mage), niveau requis au plus N,
  classé par nos poids (Mage), dit « autre source ».

Valeurs : addon GearQuest et Forever Guide fabriqués dans `tmp_path`, quêtes, donjons et poids fabriqués ici. Aucun
chiffre de jeu ici."""

from forever.gear import Access, DungeonDrop, leveling_gear

LEVEL = 10
QUEST = {
    "id": 970100, "level": LEVEL, "min_level": LEVEL - 2, "faction": "both",
    "giver": {"name": "Fixture Giver", "zone": "Fixture Vale", "x": 41.5, "y": 63.0}, "after": ["Fixture First Step"],
}  # fmt: skip
DROPS = [
    # (objet, donjon, boss, taux, niveau d'ouverture du donjon)
    DungeonDrop(970201, "Fixture Depths", "Fixture Boss", 0.2, LEVEL - 2),
    DungeonDrop(970202, "Fixture Depths", "Fixture Boss", 0.3, LEVEL - 2),
    DungeonDrop(970203, "Fixture Spire", "Fixture Late Boss", 0.4, LEVEL + 10),  # donjon pas encore ouvert
    DungeonDrop(970204, "Fixture Depths", "Fixture Boss", 0.5, LEVEL - 2),  # autre type d'armure
]


def addons(tmp_path):
    root = tmp_path / "AddOns"
    gq = root / "GearQuestForever_MAGE"
    gq.mkdir(parents=True)
    (gq / "Data.Mage.generated.lua").write_text(
        "local GQ = GearQuest\nGQ.Data.mageItemFacts = {\n"
        '    [970001]={name="Quest Gloves",quality=2,reqLevel=9,sourceType="quest_reward",questName="Fixture Errand"},\n'
        '    [970002]={name="Boss Boots",quality=3,reqLevel=9,sourceType="boss_drop",instructions="Drops from Fixture Boss."},\n'
        '    [970003]={name="Cloth Hood",quality=2,reqLevel=30,sourceType="vendor",instructions="Bought."},\n'
        "}\nGQ.Data.magePicks = {\n"
        f'    {{970001,"Hands",{LEVEL},{LEVEL},1,"frost","Alliance",1.0}},\n'
        f'    {{970002,"Feet",{LEVEL},{LEVEL},1,"frost","Alliance",1.0}},\n'
        f'    {{970003,"Head",{LEVEL},{LEVEL},1,"frost","Alliance",1.0}},\n'
        "}\n",
        encoding="utf-8",
    )
    guide = root / "ForeverGuide"
    guide.mkdir()
    rows = [
        "970003 1 1 30 2 0 0 int=9",  # tête, tissu (type que GearQuest donne au Mage pour la tête)
        f"970201 1 1 {LEVEL - 1} 2 0 0 int=2",  # tête, tissu, donjon ouvert
        f"970202 1 1 {LEVEL} 3 0 0 int=5",  # tête, tissu, meilleur score
        f"970203 1 1 {LEVEL} 4 0 0 int=20",  # tête, tissu, donjon pas encore ouvert
        f"970204 1 4 {LEVEL} 4 0 0 int=30",  # tête, plaques : pas un type du Mage
    ]
    (guide / "GearData.lua").write_text("local _, ns = ...\nns.GEAR_DATA = [[\n" + "\n".join(rows) + "\n]]\n", "utf-8")
    return root


def access():
    return Access(
        quests=lambda name: [QUEST] if name == "Fixture Errand" else [],
        dungeon_level=lambda item: LEVEL - 2 if item == 970002 else None,
        red_min_diff=5,
        dungeon_drops=lambda item: (
            [d for d in DROPS if d.item == item]
            or ([DungeonDrop(970002, "Fixture Depths", "Fixture Boss", 0.25, LEVEL - 2)] if item == 970002 else [])
        ),
        all_dungeon_drops=lambda: DROPS,
    )


def picks(tmp_path, weights=None):
    out = leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, access=access(), weights=weights)
    return {p["slot"]: p for p in out}


def test_quest_pick_says_giver_position_and_quests_first(tmp_path):
    hands = picks(tmp_path)["Hands"]
    assert hands["quest_detail"] == {
        "id": 970100, "giver": "Fixture Giver", "zone": "Fixture Vale", "x": 41.5, "y": 63.0,
        "after": ["Fixture First Step"],
    }  # fmt: skip


def test_dungeon_pick_says_dungeon_boss_and_rate(tmp_path):
    feet = picks(tmp_path)["Feet"]
    assert feet["dungeon_detail"] == {"dungeon": "Fixture Depths", "boss": "Fixture Boss", "rate": 0.25}


def test_empty_slot_gets_another_source(tmp_path):
    head = picks(tmp_path, weights={"int": 1.0})["Head"]  # GearQuest : objet de niveau requis 30, écarté
    assert head["item"] == 970202 and head["other_source"]  # meilleur score parmi le tissu des donjons ouverts
    assert head["dungeon_detail"] == {"dungeon": "Fixture Depths", "boss": "Fixture Boss", "rate": 0.3}
    assert head["required_level"] == LEVEL
