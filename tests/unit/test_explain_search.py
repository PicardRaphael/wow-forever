"""Recherche d'une mécanique par mot (T06) : `forever_explain_mechanic` accepte un identifiant (« A18 ») ou des mots
de la description du registre (« Ignite »), sans quoi une question « comment marche Ignite ? » n'aurait pas d'outil.

Entrées attendues : docs/MECHANICS_REGISTRY.yaml (A18 « Ignite : cumul, rafraîchissement », B12 « Clearcasting »,
B7 « Régénération de mana en combat… »)."""

import asyncio

import pytest
from mcp import Client

from forever.errors import UnknownMechanicError
from forever.explain import explain_mechanic
from forever.mcp_server import build_server

pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])


@pytest.mark.parametrize(("query", "expected"), [("Ignite", "A18"), ("clearcasting", "B12"), ("a18", "A18")])
def test_single_match_is_explained(make_deps, query, expected):
    assert explain_mechanic(make_deps(), query)["id"] == expected


def test_accents_and_case_are_ignored(make_deps):
    assert explain_mechanic(make_deps(), "regeneration de mana en combat")["id"] == "B7"


def test_several_matches_list_ids_and_descriptions(make_deps):
    with pytest.raises(UnknownMechanicError) as exc:
        explain_mechanic(make_deps(), "talents")
    s = exc.value.suggestions
    assert 2 <= len(s) <= 10
    assert all(" : " in x for x in s)
    assert any(x.startswith("G3 : ") for x in s)


def test_no_match_keeps_the_unknown_error(make_deps):
    with pytest.raises(UnknownMechanicError):
        explain_mechanic(make_deps(), "motquinexistepas")


def test_mcp_accepts_words(make_deps):
    async def go():
        async with Client(build_server(make_deps())) as client:
            return await client.call_tool("forever_explain_mechanic", {"mechanic_id": "Ignite"})

    r = asyncio.run(go())
    assert not r.is_error
    assert r.structured_content["id"] == "A18"
