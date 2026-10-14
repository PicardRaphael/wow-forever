"""CJ1, bloc 1d (décisions 277 et 279, registre I18, I19) : le guide de la base adaptée garde les étapes d'origine du
parcours gratuit (vols, pierre de foyer, trajets, filtres et conditions de RestedXP compris), l'étape entière étant
l'unité d'adaptation : une étape dont toutes les quêtes sont déjà faites par le personnage est retirée, nos ajouts
(quêtes de classe, donjons avec leurs quêtes) sont insérés après l'étape qui les précède dans la route ; aucun en-tête
du parcours (`#name`, `#next`, `#defaultfor`) n'est repris.

Valeurs : monde fabriqué (`tests/fixtures/route/route.json`), guides fabriqués (`tests/fixtures/rxp_guides`)."""

from dataclasses import replace

from conftest import FIXTURES
from test_engine_route import CAP, make_world, start_state

from forever.compare import adapted_route
from forever.rxp import encode_guide
from forever.rxp_guides import guide_chain, read_rxp_guides, who_for

GUIDES = FIXTURES / "rxp_guides"
END = 5
CLASS_QUEST = 106  # rendue quête de classe ici ; absente du parcours fabriqué


def _adapted(game_data, **kw):
    world, _ = make_world(game_data)
    world = replace(world, quests={**world.quests, CLASS_QUEST: replace(world.quests[CLASS_QUEST], class_quest=True)})
    who = who_for("Mage", "Orc", "Horde")
    chain = guide_chain(read_rxp_guides(GUIDES), who)
    return adapted_route(game_data, world, chain.guides, who, start_state(), end_level=END, cap=CAP, **kw)


def test_parser_keeps_the_lines_of_each_step():
    library = read_rxp_guides(GUIDES)
    vale = next(g for g in library.guides if g.name == "1-3 Fixture Vale")
    assert vale.steps[0].raw[0] == "step"
    assert any(".goto Fixture Vale,40,41" in line for line in vale.steps[0].raw)
    assert any(".accept 101" in line for line in vale.steps[0].raw)


def test_adapted_guide_keeps_original_steps_and_inserts_our_additions(game_data):
    adapted = _adapted(game_data)
    text = "\n".join(adapted.lines)
    assert ".goto Fixture Vale,40,41" in text  # étape d'origine gardée telle quelle
    assert f".turnin {CLASS_QUEST}" in text  # quête de classe ajoutée
    assert "#name" not in text and "#next" not in text and "#defaultfor" not in text
    assert text.index(".accept 101") < text.index(f".accept {CLASS_QUEST}")  # ajout après les étapes qui le précèdent


def test_steps_of_quests_already_done_are_removed(game_data):
    adapted = _adapted(game_data, done=frozenset({101}))
    text = "\n".join(adapted.lines)
    assert ".turnin 101" not in text  # étape « .complete 101,2 / .turnin 101 » retirée
    assert ".accept 102" in text  # étape mixte gardée (RestedXP saute lui-même la quête faite)


def test_encoded_guide_uses_the_adapted_body_and_the_attribution(game_data):
    adapted = _adapted(game_data)
    plan = {
        "id": "x",
        "class": "mage",
        "faction": "horde",
        "levels": {"from": 1, "to": END},
        "stops": [{"kind": "grind", "ref": "farm", "name": None, "map": None, "x": None, "y": None}],
        "basis": {
            "kind": "parcours adapté",
            "attribution": "Adapté de RestedXP Guides, licence CC BY-NC-SA 4.0",
            "body": adapted.lines,
            "adapted_stops": 1,
        },
    }
    text = encode_guide(plan, name="Forever · Bob · 1-5", group="Forever Routes")
    assert "CC BY-NC-SA 4.0" in text and ".goto Fixture Vale,40,41" in text
    assert ">>Kill mobs of your level" not in text  # l'arrêt compté dans le corps n'est pas réécrit après lui
