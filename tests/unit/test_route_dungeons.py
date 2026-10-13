"""Préparation de RX1 (DJ1, bloc G) : étapes de route d'un donjon (prérequis à faire d'abord, quêtes à prendre avec
le donneur et sa position, entrée, rendus) et niveau de placement de chaque donjon ouvert.

Fixtures : `tests/fixtures/addons/dungeons/` (addons synthétiques) ; données : version du dépôt. Aucun chiffre de
jeu ici : positions et identifiants viennent des fixtures."""

import pytest
from conftest import FIXTURES, isolated_deps

from forever.dungeons import build_dungeons
from forever.quests import build_quests
from forever.route import RouteStep, dungeon_placements, dungeon_steps

WOW = FIXTURES / "addons" / "dungeons"


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("route_dj1"))


@pytest.fixture(scope="module")
def books(deps):
    return build_dungeons(deps, wow_dir=WOW), build_quests(deps, wow_dir=WOW)


def test_steps_start_with_prerequisites(books):
    book, quests = books
    steps = dungeon_steps(book, "389", faction="horde", level=15, quests=quests)
    assert all(isinstance(s, RouteStep) for s in steps)
    accepted = [s.quest_id for s in steps if s.kind == "accept"]
    assert accepted[:2] == book.dungeons["389"]["first_steps"]  # prérequis d'abord, dans l'ordre
    kinds = [s.kind for s in steps]
    assert kinds.index("goto") > max(i for i, s in enumerate(steps) if s.kind == "accept")  # quêtes prises avant
    assert kinds[-1] == "turnin"


def test_steps_have_giver_positions(books):
    book, quests = books
    steps = dungeon_steps(book, "389", faction="horde", level=15, quests=quests)
    accept = next(s for s in steps if s.kind == "accept" and s.quest_id == 5723)
    assert (accept.map, accept.x, accept.y) == (1454, 40.0, 50.0)  # donneur de la fixture de Naowh Forever
    goto = next(s for s in steps if s.kind == "goto")
    assert (goto.map, goto.x, goto.y) == (1454, 52.0, 49.0)  # entrée retenue (Naowh Forever)


def test_steps_respect_the_faction(books):
    book, quests = books
    steps = dungeon_steps(book, "389", faction="alliance", level=15, quests=quests)
    assert not any(s.kind == "accept" and s.quest_id == 5723 for s in steps)  # quête de la Horde


def test_placements_cover_each_open_dungeon(deps):
    placements = dungeon_placements(deps, class_name="hunter", faction="horde", wow_dir=WOW)
    book = build_dungeons(deps, wow_dir=WOW)
    expected = {
        k
        for k, d in book.dungeons.items()
        if not d["closed"]
        and d["fields"].get("levels")
        and (d["fields"].get("faction") or {}).get("value") in (None, "horde")
    }
    assert {p["id"] for p in placements} == expected
    assert "Alcaz Prison" not in {p["name"] for p in placements}  # fermé
    rfc = next(p for p in placements if p["id"] == "389")
    assert rfc["placement"] is not None and rfc["steps"] and rfc["xp"] > 0 and rfc["minutes"] > 0
    rng = book.dungeons["389"]["fields"]["levels"]["value"]
    assert rng["min"] <= rfc["placement"]["level"] <= rng["max"]
