"""CJ1, bloc 4b (décision 277, point 6, registre I16) : route d'équipement. Pour chaque objet de la liste BiS, son
origine (boss d'un donjon avec son taux, quête qui le donne, sinon ce que dit Naowh : métier, réputation, marchand) ;
les donjons sont regroupés (plusieurs objets d'un même donjon cumulés) avec le nombre de passages attendu (espérance)
et le nombre pour neuf chances sur dix ; les quêtes sont regroupées par zone.

Valeurs : taux et objets fabriqués ici. Aucun chiffre de jeu ici."""

import math

from forever.engine.loot import expected_runs, runs_for_chance
from forever.gear_route import item_sources, plan_gear_route


def test_expected_runs_single_item():
    assert expected_runs([0.5]) == 2.0
    assert runs_for_chance([0.5], 0.9) == 4  # 1 - 0,5^4 ≥ 0,9


def test_expected_runs_of_several_items_of_one_dungeon():
    assert math.isclose(expected_runs([0.5, 0.5]), 2 + 2 - 1 / 0.75)  # inclusion-exclusion
    assert runs_for_chance([0.5, 0.5], 0.9) == 5  # (1 - 0,5^5)² ≥ 0,9


def test_impossible_drop_has_no_finite_runs():
    assert expected_runs([0.0]) == math.inf and runs_for_chance([0.0], 0.9) is None


def test_item_sources_dungeon_then_quest_then_naowh():
    def where(item):
        return [{"dungeon": "D1", "dungeon_name": "Fixture Depths", "boss": "Boss", "rate": 0.2, "source": "naowh",
                 "certainty": "suppose"}] if item == 1 else []  # fmt: skip

    def quests(item):
        return [42] if item == 2 else []

    naowh = {3: "Tailoring · Crafted"}
    assert item_sources(1, where, quests, naowh)[0]["kind"] == "donjon"
    assert item_sources(2, where, quests, naowh) == [{"kind": "quête", "quest": 42}]
    assert item_sources(3, where, quests, naowh) == [{"kind": "autre", "text": "Tailoring · Crafted"}]
    assert item_sources(4, where, quests, naowh) == [{"kind": "inconnue"}]


def test_plan_groups_dungeons_and_quests():
    items = [
        {"slot": 1, "item": 1, "sources": [{"kind": "donjon", "dungeon": "D1", "dungeon_name": "A", "rate": 0.5}]},
        {"slot": 2, "item": 2, "sources": [{"kind": "donjon", "dungeon": "D1", "dungeon_name": "A", "rate": 0.5}]},
        {"slot": 3, "item": 3, "sources": [{"kind": "donjon", "dungeon": "D2", "dungeon_name": "B", "rate": 0.1}]},
        {"slot": 5, "item": 4, "sources": [{"kind": "quête", "quest": 42, "zone": "Vale"}]},
        {"slot": 6, "item": 5, "sources": [{"kind": "autre", "text": "Tailoring · Crafted"}]},
    ]
    plan = plan_gear_route(items, chance=0.9)
    first, second = plan["dungeons"]
    assert first["dungeon"] == "D1" and first["items"] == [1, 2]  # deux objets : passé en premier
    assert math.isclose(first["expected_runs"], expected_runs([0.5, 0.5]))
    assert first["runs_for_chance"] == runs_for_chance([0.5, 0.5], 0.9)
    assert second["dungeon"] == "D2" and second["runs_for_chance"] == runs_for_chance([0.1], 0.9)
    assert plan["quests"] == [{"zone": "Vale", "quests": [42], "items": [4]}]
    assert plan["others"] == [{"item": 5, "text": "Tailoring · Crafted"}]
