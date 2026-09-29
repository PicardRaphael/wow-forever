"""Consultation des talents (T06, décision D8) : `lookup_talent`, `forever lookup talent`, `forever_lookup(kind="talent")`.

Valeurs attendues : forever/data/1.60.1.70009/talents.json (Improved Frostbolt : arbre Frost, palier 1, 5 rangs,
rang 3 = 0.3 ; Hot Streak : palier 4, prérequis Pyroblast ; Pyroblast : 95 à 125, 44 sur 12 s, certitude FC-70009) et
mechanics.json (talents.points_per_tier = 5)."""

import asyncio
import json

import pytest
from conftest import LOCAL_VERSION, FakeHttp
from mcp import Client

from forever.cli import main
from forever.errors import UnknownRankError, UnknownTalentError
from forever.lookup import lookup_talent
from forever.mcp_server import build_server
from forever.provenance import validate_provenance


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


@pytest.mark.parametrize(
    "name", ["improvedFrostbolt", "Improved Frostbolt", "improved-frostbolt", "IMPROVED_FROSTBOLT"]
)
def test_key_and_english_name_find_the_same_talent(make_deps, name):
    r = lookup_talent(make_deps(), name)
    assert r["kind"] == "talent"
    assert r["id"] == "improvedFrostbolt"
    assert r["name"] == "Improved Frostbolt"
    assert r["tree"] == "Frost"
    assert r["tier"] == 1
    assert r["max_rank"] == 5
    assert [x["rank"] for x in r["ranks"]] == [1, 2, 3, 4, 5]
    assert r["required_tree_points"] == 0
    assert r["prereq"] is None


def test_rank_gives_the_value_and_the_description_of_that_rank(make_deps):
    r = lookup_talent(make_deps(), "Improved Frostbolt", rank=3)
    assert r["ranks"] == [
        {
            "rank": 3,
            "values": [0.3],
            "description": "Reduces the casting time of your Frostbolt spell by 0.3 sec.",
        }
    ]
    assert r["description_template"] == "Reduces the casting time of your Frostbolt spell by {0} sec."


def test_tier_prerequisite_and_tree_points(make_deps):
    r = lookup_talent(make_deps(), "hotStreak")
    assert r["tier"] == 4
    assert r["required_tree_points"] == 15  # 5 points par palier précédent (mechanics.json, G3)
    assert r["prereq"] == {"id": "pyroblast", "name": "Pyroblast", "max_rank": 1}


def test_talent_that_teaches_a_spell(make_deps):
    r = lookup_talent(make_deps(), "Pyroblast", rank=1)
    assert r["spell"] == "pyroblast"
    assert r["ranks"][0]["description"] == (
        "Hurls an immense fiery boulder that causes 95 to 125 Fire damage and an additional 44 Fire damage over 12 sec."
    )
    assert lookup_talent(make_deps(), "Improved Frostbolt")["spell"] is None


def test_unknown_name_suggests_close_talents(make_deps):
    with pytest.raises(UnknownTalentError) as exc:
        lookup_talent(make_deps(), "Improved Frostblot")
    assert exc.value.code == "unknown_talent"
    assert "Improved Frostbolt" in exc.value.suggestions


@pytest.mark.parametrize("rank", [0, 6])
def test_rank_out_of_bounds(make_deps, rank):
    with pytest.raises(UnknownRankError):
        lookup_talent(make_deps(), "Improved Frostbolt", rank=rank)


def test_provenance_and_certainty_by_source_build(make_deps):
    # T06b, révision 2 : les 54 talents sont lus dans le client 1.60.1.70009 (FC-69893 auparavant pour 49).
    old = lookup_talent(make_deps(http=FakeHttp.failing()), "Improved Frostbolt")
    assert validate_provenance(old["provenance"]) == []
    assert old["provenance"]["game_version"] == LOCAL_VERSION
    assert old["source"] == "FC-70009"
    assert old["provenance"]["certainty"] == "certain"
    assert not any("69893" in a for a in old["provenance"]["assumptions"])
    new = lookup_talent(make_deps(), "Pyroblast")
    assert new["source"] == "FC-70009"
    assert new["provenance"]["certainty"] == "certain"


def test_cli_text(capsys, make_deps):
    code, out, _ = run(capsys, ["lookup", "talent", "Improved Frostbolt", "--rank", "3"], make_deps())
    assert code == 0
    assert "Improved Frostbolt" in out and "Frost" in out
    assert "3/5" in out
    assert "Reduces the casting time of your Frostbolt spell by 0.3 sec." in out
    assert LOCAL_VERSION in out


def test_cli_unknown_talent_exit_code(capsys, make_deps):
    code, out, _ = run(capsys, ["lookup", "talent", "Improved Frostblot", "--json"], make_deps())
    assert code != 0
    err = json.loads(out)["error"]
    assert err["code"] == "unknown_talent" and "Improved Frostbolt" in err["suggestions"]


def test_mcp_returns_the_cli_json(capsys, make_deps):
    deps = make_deps()
    code, out, _ = run(capsys, ["lookup", "talent", "Improved Frostbolt", "--rank", "3", "--json"], deps)
    assert code == 0

    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_lookup", {"kind": "talent", "name": "Improved Frostbolt", "rank": 3})

    r = asyncio.run(go())
    assert not r.is_error
    assert r.structured_content == json.loads(out)


def test_unsupported_kind_lists_talent(capsys, make_deps):
    code, out, _ = run(capsys, ["lookup", "item", "x", "--json"], make_deps())
    assert code != 0
    err = json.loads(out)["error"]
    assert err["code"] == "unsupported_kind"
    assert "talent" in err["suggestions"]
