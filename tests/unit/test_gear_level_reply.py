"""Essai CJ-6 du 2026-10-15, réponse des boutons de l'écran Équipement (bloc 4c) :

1. chaque objet est un lien d'objet du jeu (balise `[[item:<id>:<qualité>|<nom>]]`, rendue en lien par l'addon) et la
   réponse remet les liens à copier : [Naowh : BiS] avec la liste du niveau choisi (« Forever · <personnage> · niveau
   N »), [Naowh : poids] et [Forever Companion : échelle] (Mage) ;
2. emplacements en français ;
3. butin aléatoire présenté comme tel (« butin aléatoire des monstres de niveau a à b, n'importe où »), sans zone, après
   les objets qu'on peut viser exprès ;
4. Mage seulement : reclassement par nos poids ; quand notre premier choix diffère de celui de GearQuest, la réponse
   montre les deux et dit pourquoi ; les autres classes gardent l'ordre de GearQuest.

Valeurs : addons fabriqués dans `tmp_path` (structures de GearQuest Forever et de Forever Guide), contexte synthétique ;
poids du Mage calculés par le moteur sur les données du dépôt. Aucun chiffre de jeu ici."""

import pytest

from forever.bridge.gear_level import gear_level_reply, gear_route_reply
from forever.exports.naowh import read_naowh_bis as decode_nbis

LEVEL = 10
# objet : (emplacement GearQuest, rang, qualité, faits, statistiques de Forever Guide)
ITEMS = {
    930001: ("Back", 1, 2, 'reqLevel=8,sourceType="world_drop",instructions="World drop around level 8-12."', "int=1"),
    930002: (
        "Feet",
        1,
        2,
        'reqLevel=8,sourceType="vendor",instructions="Bought from Fixture Vendor.",zone="Fixture Horde Town"',
        "int=1",
    ),
    930003: ("Hands", 1, 2, 'reqLevel=8,sourceType="vendor",instructions="Bought from Fixture Vendor."', "int=1"),
    930004: (
        "Hands",
        2,
        3,
        'reqLevel=9,sourceType="vendor",instructions="Bought from Fixture Vendor."',
        "int=10,sp=10",
    ),
}
FR = {"Back": "Dos", "Feet": "Pieds", "Hands": "Mains"}
GUIDE_SLOTS = {"Back": 16, "Feet": 8, "Hands": 10}  # type d'emplacement de Forever Guide (INVTYPE)


def wow_dir(tmp_path, token="MAGE"):
    addons = tmp_path / "wow" / "Interface" / "AddOns"
    folder = addons / f"GearQuestForever_{token}"
    folder.mkdir(parents=True)
    cls = token.lower()
    facts = "\n".join(f'    [{i}]={{name="Fixture {i}",quality={q},{f}}},' for i, (_, _, q, f, _) in ITEMS.items())
    picks = "\n".join(
        f'    {{{i},"{slot}",{LEVEL - 2},{LEVEL + 2},{rank},"frost","Alliance",1.0}},'
        for i, (slot, rank, _, _, _) in ITEMS.items()
    )
    (folder / f"Data.{token.capitalize()}.generated.lua").write_text(
        f"local GQ = GearQuest\nGQ.Data.{cls}ItemFacts = {{\n{facts}\n}}\nGQ.Data.{cls}Picks = {{\n{picks}\n}}\n",
        encoding="utf-8",
    )
    guide = addons / "ForeverGuide"
    guide.mkdir()
    rows = "\n".join(f"{i} {GUIDE_SLOTS[s]} 1 {LEVEL} {q} 0 0 {st}" for i, (s, _, q, _, st) in ITEMS.items())
    (guide / "GearData.lua").write_text(f"local _, ns = ...\nns.GEAR_DATA = [[\n{rows}\n]]\n", encoding="utf-8")
    return tmp_path / "wow"


def context(cls="MAGE"):
    return {"name": "Go", "class": cls, "race": "Gnome", "faction": "Alliance", "level": "1"}


@pytest.fixture
def mage(tmp_path, make_deps):
    return make_deps(wow_dir=wow_dir(tmp_path), offline=True)


def test_items_are_game_links_and_the_reply_gives_links_to_copy(mage):
    text, links = gear_level_reply(mage, context(), LEVEL)
    for item, (_, _, quality, _, _) in ITEMS.items():
        if item != 930003:  # écarté par nos poids au profit de 930004 (voir plus bas)
            assert f"[[item:{item}:{quality}|Fixture {item}]]" in text
    kinds = {link["kind"]: link for link in links}
    assert {"naowh_bis", "naowh_weights", "companion_scale"} <= set(kinds)
    bis = decode_nbis(kinds["naowh_bis"]["text"])
    assert bis.name == f"Forever · Go · niveau {LEVEL}" and 930004 in bis.slots.values()


def test_slot_names_are_french(mage):
    text, _ = gear_level_reply(mage, context(), LEVEL)
    for english, french in FR.items():
        assert f"- {french} :" in text and f"- {english} :" not in text


def test_random_drops_are_said_as_such_and_come_last(mage):
    text, _ = gear_level_reply(mage, context(), LEVEL)
    lines = [line for line in text.splitlines() if line.startswith("- ")]
    drop = next(i for i, line in enumerate(lines) if "930001" in line)
    assert "butin aléatoire des monstres de niveau 8 à 12, n'importe où" in lines[drop]
    assert drop == len(lines) - 1  # après les objets qu'on peut viser exprès
    route, _ = gear_route_reply(mage, context(), LEVEL)
    assert route.index("930001") > route.index("930002") and "n'importe où" in route


def test_mage_reranking_shows_both_choices_and_why(mage):
    text, _ = gear_level_reply(mage, context(), LEVEL)
    hands = next(line for line in text.splitlines() if line.startswith("- Mains :"))
    assert "930004" in hands.split("GearQuest")[0]  # notre premier choix d'abord
    assert "GearQuest proposait" in hands and "930003" in hands and "poids du Mage" in hands


def test_other_classes_keep_the_gearquest_order(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path, token="PRIEST"), offline=True)
    text, links = gear_level_reply(deps, context("PRIEST"), LEVEL)
    hands = next(line for line in text.splitlines() if line.startswith("- Mains :"))
    assert "930003" in hands and "930004" not in hands and "GearQuest proposait" not in hands
    assert "naowh_weights" not in {link["kind"] for link in links}  # poids calculés pour le Mage seulement
