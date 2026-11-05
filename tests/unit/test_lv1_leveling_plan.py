"""Plan de talents de leveling niveau par niveau (LV1, décision 303) : build visé lu dans Talents Forever (le plus joué
de la spécialisation, légal sur le client), ordre lu dans Polestar (`Polestar/Talents/Builds.lua`) tant qu'il colle,
points générés légaux sinon (marqués), talents absents du client et nœuds réaffectés dits, tranches de niveaux, code
Naowh `!NFB1!` dans cet ordre, resets jamais inventés.

Addons synthétiques écrits dans `tmp_path` (`tests/talents_forever_data.py`, `tests/polestar_talents_data.py`) ;
aucun accès au dossier réel du jeu."""

import asyncio
import json

import pytest
from conftest import DATA_DIR, PRE_70450_VERSION
from forever.leveling_plan import leveling_plan
from forever.polestar_talents import read_polestar_talents
from mcp import Client
from polestar_talents_data import TOC_VERSION, WRITTEN_ON, write_polestar
from talents_forever_data import write_addon

from forever.cli import main
from forever.engine.talents import legal_order
from forever.errors import InvalidArgumentError
from forever.gamedata import build_game_data
from forever.mcp_server import build_server
from forever.store import load_version
from forever.talents_forever import load_addon, popular_builds

CLASSES = DATA_DIR / PRE_70450_VERSION / "classes.json"


@pytest.fixture
def make_deps(make_deps_at_pre_70450_version):
    return make_deps_at_pre_70450_version


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    write_addon(root, CLASSES)
    return root


@pytest.fixture
def deps(wow, make_deps):
    return make_deps(wow_dir=wow)


@pytest.fixture
def gd(deps):
    return build_game_data(load_version(deps))


@pytest.fixture
def target(deps):
    """Build populaire n° 1 du Mage (le plus joué de sa spécialisation) : talents et arbre."""
    addon = load_addon(deps)
    assert addon is not None
    top = popular_builds(addon, deps, "Mage")["classes"]["Mage"]["top"][0]
    assert top["legality"] == "légal"
    return top


@pytest.fixture
def order(gd, target):
    return legal_order(gd.classes["Mage"], gd.constants.talents, target["talents"])


def _write(wow, order, **kw):
    picks = kw.pop("picks", list(order))
    notes = kw.pop("notes", {})
    write_polestar(wow, CLASSES, "Mage", [{"key": "main", "split": "x", "picks": picks, "notes": notes}], **kw)


def _spec(plan):
    assert len(plan["specs"]) == 1
    return plan["specs"][0]


def test_reads_the_polestar_builds(wow, order):
    _write(wow, order, notes={10: "Note de fixture."})
    read = read_polestar_talents(wow / "Interface" / "AddOns" / "Polestar")
    mage = read["classes"]["Mage"]
    assert read["version"] == TOC_VERSION and read["written_on"] == WRITTEN_ON
    build = mage["builds"][0]
    assert build["key"] == "main" and len(build["picks"]) == len(order)
    assert build["notes"] == {10: "Note de fixture."}
    first = build["picks"][0]
    assert mage["nodes"][first[0]]["name"]


def test_plan_follows_polestar_when_it_matches_the_target(deps, gd, wow, order, target):
    _write(wow, order, notes={gd.constants.talents.first_level: "Premier point."})
    spec = _spec(leveling_plan(deps, "Mage"))
    steps = spec["steps"]
    assert [s["key"] for s in steps] == order
    assert all(s["source"] == "polestar" for s in steps)
    assert steps[0]["level"] == gd.constants.talents.first_level
    assert [s["level"] for s in steps] == list(range(steps[0]["level"], steps[0]["level"] + len(steps)))
    assert steps[0]["note"] == "Premier point."
    assert spec["target"]["source"] == "talents_forever" and spec["target"]["link"] == target["link"]
    assert spec["polestar"]["issues"] == []
    naowh = spec["naowh"]
    assert naowh["status"] == "ok" and naowh["order_source"] == "leveling" and naowh["code"].startswith("!NFB1!")


def test_absent_talent_is_dropped_said_and_replaced_by_a_marked_generated_point(deps, wow, order):
    picks = list(order)
    picks[5] = ("nœud", 999001)
    _write(wow, order, picks=picks, extra_nodes={999001: "Removed Talent"})
    spec = _spec(leveling_plan(deps, "Mage"))
    issues = spec["polestar"]["issues"]
    assert [i["name"] for i in issues] == ["Removed Talent"] and "absent du client" in issues[0]["reason"]
    assert len(spec["steps"]) == len(order)
    assert sum(1 for s in spec["steps"] if s["source"] == "genere") == 1
    assert sorted(s["key"] for s in spec["steps"]) == sorted(order)
    assert spec["naowh"]["status"] == "ok"


def test_reassigned_node_is_said_and_the_pick_is_read_by_its_name(deps, gd, wow, order):
    talents = {t["key"]: t for tree in gd.classes["Mage"].trees for t in tree["talents"]}
    node = int(talents[order[0]]["node_id"])
    other = next(t for t in talents.values() if t["key"] not in order)
    _write(wow, order, renamed_nodes={node: other["name"]}, picks=list(order))
    spec = _spec(leveling_plan(deps, "Mage"))
    reassigned = [i for i in spec["polestar"]["issues"] if "réaffecté" in i["reason"]]
    assert reassigned and reassigned[0]["name"] == other["name"]


def test_tranches_cover_every_level_once(deps, wow, order):
    _write(wow, order)
    spec = _spec(leveling_plan(deps, "Mage"))
    tranches = spec["tranches"]
    levels = [lvl for t in tranches for lvl in range(t["from"], t["to"] + 1)]
    assert levels == [s["level"] for s in spec["steps"]]
    assert all(t["ranks"][0] <= t["ranks"][1] for t in tranches)


def test_next_point_at_the_player_level(deps, gd, wow, order):
    _write(wow, order)
    first = gd.constants.talents.first_level
    spec = _spec(leveling_plan(deps, "Mage", level=first + 2))
    assert spec["next"]["level"] == first + 3 and spec["next"]["key"] == order[3]


def test_resets_are_never_invented(deps, wow, order):
    _write(wow, order)
    plan = leveling_plan(deps, "Mage")
    resets = _spec(plan)["resets"]
    assert resets["planned"] == [] and "aucune source" in resets["note"]
    assert plan["certainty"] == "suppose"


def test_provenance_names_both_addons_and_the_written_version(deps, wow, order):
    _write(wow, order)
    notes = " ".join(leveling_plan(deps, "Mage")["provenance"]["assumptions"])
    assert TOC_VERSION in notes and WRITTEN_ON in notes and "Talents Forever" in notes


def test_without_polestar_a_french_error(deps):
    with pytest.raises(InvalidArgumentError, match="Polestar"):
        leveling_plan(deps, "Mage")


def test_cli_plan(deps, wow, order, capsys):
    _write(wow, order)
    assert main(["talents", "plan", "--class", "Mage", "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "leveling_plan"
    assert main(["talents", "plan", "--class", "Mage"], deps) == 0
    out = capsys.readouterr().out
    assert "niveaux" in out and "!NFB1!" in out and "suppose" in out


def test_mcp_lookup_leveling_plan(deps, wow, order):
    _write(wow, order)

    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_lookup", {"kind": "leveling_plan", "name": "Mage"})

    r = asyncio.run(go())
    assert not r.is_error
    assert r.structured_content["kind"] == "leveling_plan"
