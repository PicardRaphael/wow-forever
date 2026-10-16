"""Essai CJ-6 du 2026-10-15, suite, défaut 1 : « mon équipement au niveau 10 » proposait des objets bien au-dessus
(récompense d'une quête rouge, objets de niveau 25 à 30, objets de métier). Pour un niveau N, un objet n'est proposé
que s'il est obtenable à ce niveau :

- niveau requis au plus N (affiché pour chaque objet) ;
- récompense de quête : quête du camp (ou des deux camps) qu'on peut prendre au niveau N et qui n'est pas rouge
  (seuil `leveling.quest_band.red_min_diff`, même règle que les routes, registre I7) ;
- butin d'un monstre : plage de niveaux du butin commençant au plus à N ; butin de donjon : donjon ouvert au niveau N ;
- objet de métier : seulement si le personnage a ce métier ;
- source inconnue ou sans niveau connu : mis à part, avec sa raison, jamais proposé.

Valeurs : addon GearQuest fabriqué dans `tmp_path` (structure de GearQuest Forever), quêtes et donjons fabriqués ici ;
écart de la quête rouge passé en paramètre (la vraie valeur vit dans `mechanics.json`). Aucun chiffre de jeu ici."""

from forever.gear import Access, leveling_gear

RED = 5  # écart fabriqué pour le test (la valeur du jeu est lue dans les données)
LEVEL = 10

ITEMS = {
    # objet : (emplacement, rang, faits de GearQuest)
    910001: ("Hands", 1, 'reqLevel=10,sourceType="quest_reward",questName="Fixture Far Hope"'),  # quête rouge
    910002: ("Hands", 2, 'reqLevel=8,sourceType="quest_reward",questName="Fixture Near Errand"'),  # gardé
    910003: ("Back", 1, 'reqLevel=11,sourceType="world_drop",instructions="World drop around level 11-16."'),
    910004: ("Back", 2, 'reqLevel=9,sourceType="world_drop",instructions="World drop around level 8-12."'),  # gardé
    910005: ("Legs", 1, 'reqLevel=9,sourceType="profession",profession="Tailoring"'),  # métier absent
    910006: ("Legs", 2, 'reqLevel=27,sourceType="quest_reward",questName="Fixture Near Errand"'),  # niveau requis
    910007: ("Legs", 3, 'reqLevel=7,sourceType="boss_drop",instructions="Drops from Fixture Boss."'),  # donjon ouvert
    910008: ("Head", 1, 'reqLevel=1,sourceType="unsourced",instructions="Source not listed yet."'),  # mis à part
    910009: ("Head", 2, 'reqLevel=10,sourceType="quest_reward",questName="Fixture Horde Call"'),  # autre camp
    910010: ("Wrist", 1, 'reqLevel=9,sourceType="boss_drop",instructions="Drops from Fixture Late Boss."'),
}
QUESTS = {
    "Fixture Far Hope": [{"level": LEVEL + RED + 3, "min_level": LEVEL, "faction": "alliance"}],
    "Fixture Near Errand": [{"level": LEVEL + 1, "min_level": LEVEL - 4, "faction": "both"}],
    "Fixture Horde Call": [{"level": LEVEL, "min_level": LEVEL - 2, "faction": "horde"}],
}
DUNGEON_MIN = {910007: LEVEL - 2, 910010: LEVEL + 8}


def addons(tmp_path):
    folder = tmp_path / "AddOns" / "GearQuestForever_MAGE"
    folder.mkdir(parents=True)
    facts = "\n".join(f'    [{i}]={{name="Fixture {i}",quality=2,{f}}},' for i, (_, _, f) in ITEMS.items())
    picks = "\n".join(
        f'    {{{i},"{slot}",{LEVEL - 2},{LEVEL + 2},{rank},"frost","Alliance",1.0}},'
        for i, (slot, rank, _) in ITEMS.items()
    )
    text = f"local GQ = GearQuest\nGQ.Data.mageItemFacts = {{\n{facts}\n}}\nGQ.Data.magePicks = {{\n{picks}\n}}\n"
    (folder / "Data.Mage.generated.lua").write_text(text, encoding="utf-8")
    return tmp_path / "AddOns"


def access(professions=()):
    return Access(
        quests=lambda name: QUESTS.get(name, []),
        dungeon_level=lambda item: DUNGEON_MIN.get(item),
        red_min_diff=RED,
        professions=frozenset(professions),
    )


def test_gnome_mage_at_level_ten_gets_nothing_above_ten(tmp_path):
    out = leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, faction="alliance", access=access())
    picks = {p["slot"]: p for p in out}
    assert all(p["required_level"] is not None and p["required_level"] <= LEVEL for p in out)
    assert picks["Hands"]["item"] == 910002  # la récompense de la quête rouge est écartée
    assert picks["Back"]["item"] == 910004  # butin à partir du niveau 11 écarté
    assert picks["Legs"]["item"] == 910007  # métier absent, niveau requis trop haut : butin du donjon ouvert
    assert "Head" not in picks and "Wrist" not in picks
    aside = {a["item"]: a for a in out.set_aside}
    assert set(aside) == {910008} and "source" in aside[910008]["reason"]
    reasons = {e["item"]: e["reason"] for e in out.excluded}
    assert "rouge" in reasons[910001] and "Tailoring" in reasons[910005] and "27" in reasons[910006]
    assert "camp" in reasons[910009] and "donjon" in reasons[910010]


def test_profession_items_only_with_the_profession(tmp_path):
    out = leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, faction="alliance", access=access({"tailoring"}))
    assert {p["slot"]: p["item"] for p in out}["Legs"] == 910005


def test_quest_of_another_race_is_never_offered(tmp_path):
    # « Exploring the Alliance » (Skyborne seulement) proposée à un Gnome le 2026-10-16 : la race de la quête compte
    gnome_only = Access(
        quests=lambda name: (
            [{**QUESTS[name][0], "races": "autre race"}] if name == "Fixture Near Errand" else QUESTS.get(name, [])
        ),
        dungeon_level=lambda item: DUNGEON_MIN.get(item),
        red_min_diff=RED,
        race_ok=lambda races: races != "autre race",
    )
    out = leveling_gear(addons(tmp_path), "MAGE", level=LEVEL, faction="alliance", access=gnome_only)
    assert 910002 not in {p["item"] for p in out}
    assert "autre race" in {e["item"]: e["reason"] for e in out.excluded}[910002]
