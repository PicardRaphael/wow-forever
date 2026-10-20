"""Builds de talents vers Naowh Forever (EX1, bloc B) : chaîne `!NFB1!` du module Training (décisions 255 et 267).

Valeurs lues dans les données installées (`classes.json` : identifiant de la classe, `node_id`, arbre, palier, rang
maximal, prérequis) et dans les fixtures de FA1 (`tests/fixtures/talents_forever/mage_builds.json` : points et ordre
figés ; `popular.json` par l'addon synthétique de `tests/talents_forever_data.py`). Bornes du format relevées dans
Naowh Forever 1.1.12 (`NaowhForever_Training/Constants.lua` : 51 entrées, 40 octets de nom). Le contrôle « à chaque
prise » est réécrit ici d'après la règle de Naowh (`CheckBuild`), indépendamment du code testé."""

import asyncio
import json
from collections import Counter

import pytest
from conftest import DATA_DIR, PRE_70450_VERSION
from lua_oracle import lua_unpack, runtime
from mcp import Client
from talents_forever_data import load_fixture, write_addon

from forever.cli import main
from forever.engine.talents import check_order, legal_order
from forever.exports.codec import ExportFormatError, pack
from forever.exports.naowh import BUILD_PREFIX, naowh_build, read_naowh_build
from forever.exports.talents import ORDER_NOTE, naowh_export, naowh_points
from forever.gamedata import build_game_data
from forever.lookup import check_talents
from forever.mcp_server import build_server
from forever.provenance import validate_provenance
from forever.store import load_version
from forever.talents_forever import load_addon, popular_builds


@pytest.fixture
def make_deps(make_deps_at_pre_70450_version):
    """Données de PRE_70450_VERSION : les arbres de l'addon fabriqué sont ceux de layout.json (conftest)."""
    return make_deps_at_pre_70450_version


CLASSES = DATA_DIR / PRE_70450_VERSION / "classes.json"
DOC = json.loads(CLASSES.read_text(encoding="utf-8"))["classes"]
CASES = load_fixture("mage_builds.json")["cases"]
ORDERED = [name for name, case in CASES.items() if case.get("order")]


def nodes(cls: str) -> dict[str, dict]:
    return {t["key"]: t for tree in DOC[cls]["trees"] for t in tree["talents"]}


def dominant_tree(cls: str, talents: dict[str, int]) -> str:
    by_tree = Counter()
    for key, rank in talents.items():
        by_tree[nodes(cls)[key]["tree"]] += rank
    return max(by_tree, key=lambda t: by_tree[t])


def naowh_rule_errors(cls: str, order: list[str], per_tier: int) -> list[str]:
    """Contrôle de Naowh à chaque prise, réécrit d'après sa règle : rang au plus maximal, prérequis requis au
    maximum (ou un des suffisants), 5 × (palier − 1) points déjà pris dans l'arbre (points par palier lus dans
    `mechanics.json`)."""
    known = nodes(cls)
    by_node = {t["node_id"]: t for t in known.values()}
    count: Counter = Counter()
    spent: Counter = Counter()
    errors = []
    for i, key in enumerate(order):
        t = known[key]
        if count[key] + 1 > t["max"]:
            errors.append(f"{i}: rang")
        required = [by_node[p["node_id"]] for p in t["prereqs"] if p["kind"] == "required"]
        sufficient = [by_node[p["node_id"]] for p in t["prereqs"] if p["kind"] == "sufficient"]
        if any(count[p["key"]] < p["max"] for p in required):
            errors.append(f"{i}: prérequis")
        if sufficient and not any(count[p["key"]] >= p["max"] for p in sufficient):
            errors.append(f"{i}: prérequis suffisant")
        if spent[t["tree"]] < per_tier * (t["tier"] - 1):
            errors.append(f"{i}: palier")
        count[key] += 1
        spent[t["tree"]] += 1
    return errors


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


# --- points et va-et-vient ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ORDERED)
def test_points_follow_the_fixture_order(deps, gd, name):
    case = CASES[name]
    known = nodes("Mage")
    out = naowh_export(deps, "Mage", case["level"], case["talents"], case["order"])
    assert out["status"] == "ok" and out["order_source"] == "leveling" and out["order_note"] is None
    expected = [known[k]["node_id"] for k in case["order"]]
    assert list(out["points"]) == expected
    assert len(expected) == sum(case["talents"].values())
    assert naowh_points(gd.classes["Mage"], case["order"]) == tuple(expected)
    build = read_naowh_build(out["code"])
    assert build.class_id == DOC["Mage"]["id"] == out["class_id"]
    assert build.points == tuple(expected)
    assert build.spec == dominant_tree("Mage", case["talents"]) == out["spec"]
    assert build.name == out["name"] and build.name
    assert out["certainty"] == "probable"
    assert validate_provenance(out["provenance"]) == []
    assert out["code"].startswith(BUILD_PREFIX)


def test_code_read_by_the_lua_libraries(deps):
    case = CASES["leveling-20"]
    out = naowh_export(deps, "Mage", case["level"], case["talents"], case["order"])
    table = lua_unpack(runtime(), out["code"][len(BUILD_PREFIX) :].encode())
    assert table == {
        "v": 1,
        "class": DOC["Mage"]["id"],
        "name": out["name"],
        "spec": out["spec"],
        "points": list(out["points"]),
    }


def test_build_without_order_gets_a_generated_legal_order(deps, gd):
    case = CASES["leveling-20"]
    out = naowh_export(deps, "Mage", case["level"], case["talents"])
    assert out["status"] == "ordre_genere" and out["order_source"] == "genere"
    assert out["order_note"] == ORDER_NOTE
    assert Counter(out["order"]) == Counter({k: v for k, v in case["talents"].items() if v})
    assert naowh_rule_errors("Mage", out["order"], gd.constants.talents.points_per_tier) == []
    by_node = {t["node_id"]: k for k, t in nodes("Mage").items()}
    assert [by_node[n] for n in read_naowh_build(out["code"]).points] == out["order"]


# --- ordre légal et contrôle à chaque prise -------------------------------------------------------------------------


def test_legal_order_of_every_popular_build(deps, gd):
    popular = popular_builds(load_addon(deps), deps)
    seen = 0
    for cls, block in popular["classes"].items():
        for entry in block["top"]:
            if entry["legality"] != "légal":
                continue
            talents = {k: v for k, v in entry["talents"].items() if v}
            order = legal_order(gd.classes[cls], gd.constants.talents, talents)
            assert Counter(order) == Counter(talents), (cls, entry["rank"])
            assert naowh_rule_errors(cls, order, gd.constants.talents.points_per_tier) == [], (cls, entry["rank"])
            assert check_order(gd.classes[cls], gd.constants.talents, order) == []
            seen += 1
    assert seen == 45


def test_check_order_refuses_a_tier_before_its_points(deps, gd):
    case = CASES["leveling-20"]
    known = nodes("Mage")
    order = list(case["order"])
    first = next(k for k in order if known[k]["tier"] == 2)
    order.remove(first)
    order.insert(0, first)
    assert naowh_rule_errors("Mage", order, gd.constants.talents.points_per_tier)
    errors = check_order(gd.classes["Mage"], gd.constants.talents, order)
    assert errors and any(known[first]["name"] in e for e in errors)
    out = naowh_export(deps, "Mage", case["level"], case["talents"], order)
    assert out["status"] == "bloque" and out["code"] is None
    assert known[first]["name"] in out["reason"]


def test_check_order_refuses_a_prerequisite_not_at_full_rank(deps, gd):
    popular = popular_builds(load_addon(deps), deps)
    for cls, block in popular["classes"].items():
        known = nodes(cls)
        by_node = {t["node_id"]: t for t in known.values()}
        for entry in block["top"]:
            talents = {k: v for k, v in entry["talents"].items() if v}
            order = legal_order(gd.classes[cls], gd.constants.talents, talents)
            for i, key in enumerate(order):
                req = [by_node[p["node_id"]] for p in known[key]["prereqs"] if p["node_id"] in by_node]
                if len(req) == 1 and req[0]["max"] > 1:
                    last = max(j for j, k in enumerate(order) if k == req[0]["key"])
                    bad = order[:last] + [key] + [k for j, k in enumerate(order[last:], last) if j != i]
                    errors = check_order(gd.classes[cls], gd.constants.talents, bad)
                    assert any(req[0]["name"] in e for e in errors), (cls, key, errors)
                    return
    pytest.fail("aucun talent à prérequis de plusieurs rangs dans les builds populaires")


def test_order_that_does_not_match_the_ranks_is_refused(deps):
    case = CASES["leveling-20"]
    out = naowh_export(deps, "Mage", case["level"], case["talents"], case["order"][:-1])
    assert out["status"] == "bloque" and out["code"] is None and "ordre" in out["reason"]


def test_illegal_build_is_blocked_with_the_talent_named(deps):
    out = naowh_export(deps, "Mage", 20, {"iceLance": 1})
    assert out["status"] == "bloque" and out["code"] is None
    assert nodes("Mage")["iceLance"]["name"] in out["reason"]


def test_unknown_talent_is_blocked(deps):
    out = naowh_export(deps, "Mage", 20, {"pasUnTalent": 1})
    assert out["status"] == "bloque" and "pasUnTalent" in out["reason"]


# --- bornes du format -----------------------------------------------------------------------------------------------


def test_format_bounds_like_naowh():
    with pytest.raises(ExportFormatError):
        naowh_build(8, "Trop", "Frost", [1] * 52)
    with pytest.raises(ExportFormatError):
        naowh_build(8, "Vide", "Frost", [])
    assert len(read_naowh_build(naowh_build(8, "x", "Frost", [1] * 51)).points) == 51
    long_name = read_naowh_build(naowh_build(8, "é" * 30, "Frost", [1])).name
    assert long_name == "é" * 20 and len(long_name.encode()) == 40
    assert read_naowh_build(naowh_build(8, "a|b\nc", "x" * 45, [1])).name == "abc"
    assert read_naowh_build(naowh_build(8, "a", "x" * 45, [1])).spec == "x" * 40


def test_read_refuses_other_versions_and_shapes():
    with pytest.raises(ExportFormatError):
        read_naowh_build(pack(BUILD_PREFIX, {"v": 2, "class": 8, "name": "a", "spec": "b", "points": [1]}))
    with pytest.raises(ExportFormatError):
        read_naowh_build(pack(BUILD_PREFIX, {"v": 1, "class": 8, "name": "a", "spec": "b", "points": []}))
    with pytest.raises(ExportFormatError):
        read_naowh_build(pack(BUILD_PREFIX, {"v": 1, "class": 8, "name": "a", "spec": "b", "points": ["x"]}))
    with pytest.raises(ExportFormatError):
        read_naowh_build(pack("!NFM1!", {"v": 1}))


# --- CLI, MCP, builds populaires et build_check ---------------------------------------------------------------------


def talents_arg(talents: dict[str, int]) -> str:
    return ",".join(f"{k}={v}" for k, v in talents.items())


def test_cli_naowh_build(deps, capsys):
    case = CASES["leveling-20"]
    argv = ["export", "naowh-build", "--class", "Mage", "--level", "20", "--talents", talents_arg(case["talents"])]
    assert main([*argv, "--order", ",".join(case["order"]), "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ok" and data["code"].startswith(BUILD_PREFIX)
    assert validate_provenance(data["provenance"]) == []
    assert main(argv, deps) == 0
    out = capsys.readouterr().out
    assert data["code"] in out and ORDER_NOTE in out
    assert out.rstrip("\n").splitlines()[-1].startswith("Provenance")


def test_cli_naowh_build_from_a_talents_forever_code(deps, capsys):
    case = CASES["leveling-20"]
    assert main(["export", "naowh-build", "--code", case["expected_code"], "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["order_source"] == "code" and data["status"] == "ok"
    known = nodes("Mage")
    assert list(data["points"]) == [known[k]["node_id"] for k in case["order"]]


def test_cli_naowh_build_from_a_popular_build(deps, capsys):
    assert main(["export", "naowh-build", "--class", "Hunter", "--popular", "1", "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ordre_genere" and data["class"] == "Hunter"
    assert read_naowh_build(data["code"]).class_id == DOC["Hunter"]["id"]


def test_cli_illegal_build_is_an_error(deps, capsys):
    argv = ["export", "naowh-build", "--class", "Mage", "--level", "20", "--talents", "iceLance=1", "--json"]
    assert main(argv, deps) == 2
    data = json.loads(capsys.readouterr().out)
    assert nodes("Mage")["iceLance"]["name"] in data["error"]["message"]


def test_cli_read(deps, capsys):
    case = CASES["leveling-20"]
    code = naowh_export(deps, "Mage", case["level"], case["talents"], case["order"])["code"]
    assert main(["export", "read", code, "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "naowh_build" and data["class"] == "Mage"
    assert data["order"] == case["order"]
    assert validate_provenance(data["provenance"]) == []
    assert main(["export", "read", "!NFB1!abc(", "--json"], deps) == 2


def test_popular_builds_carry_the_naowh_code(deps):
    popular = popular_builds(load_addon(deps), deps, "Mage")
    for entry in popular["classes"]["Mage"]["top"]:
        block = entry["naowh"]
        assert block["status"] == "ordre_genere" and block["code"].startswith(BUILD_PREFIX)
        assert len(read_naowh_build(block["code"]).points) == sum(entry["talents"].values())


def test_build_check_carries_the_naowh_code(deps):
    case = CASES["leveling-20"]
    legal = check_talents(deps, "Mage", dict(case["talents"]), case["level"])
    assert legal["naowh"]["code"].startswith(BUILD_PREFIX)
    assert check_talents(deps, "Mage", {"iceLance": 1}, 20)["naowh"] is None


def test_mcp_lookup_export(deps):
    case = CASES["leveling-20"]

    async def go():
        async with Client(build_server(deps)) as client:
            made = await client.call_tool(
                "forever_lookup",
                {
                    "kind": "export",
                    "name": "naowh_build",
                    "class_name": "Mage",
                    "level": 20,
                    "talents": talents_arg(case["talents"]),
                },
            )
            read = await client.call_tool(
                "forever_lookup", {"kind": "export", "name": "read", "text": made.structured_content["code"]}
            )
            return made, read

    made, read = asyncio.run(go())
    assert not made.is_error and made.structured_content["status"] == "ordre_genere"
    assert validate_provenance(made.structured_content["provenance"]) == []
    assert read.structured_content["class"] == "Mage"


@pytest.mark.slow
def test_mcp_build_carries_the_naowh_export(deps):
    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool(
                "forever_build", {"context": "leveling", "level": 20, "preset": "rapide", "sensitivity": False}
            )

    r = asyncio.run(go())
    assert not r.is_error
    data = r.structured_content
    block = data["export"]["naowh"]
    assert block["status"] == "ok" and block["order_source"] == "leveling"
    known = nodes("Mage")
    expected = [known[s["talent"]]["node_id"] for s in data["order"] if s["talent"]]
    assert list(read_naowh_build(block["code"]).points) == expected
