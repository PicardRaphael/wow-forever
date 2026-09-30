"""Légalité des builds des 9 classes (PV1, bloc E ; registre G3) : savoir décodé du client (`classes.json`), règles
des paliers et des points dans `mechanics.json` (`talents.first_level`, `talents.points_per_tier`).

Talents lus dans les données (clés, paliers, prérequis), jamais écrits comme valeurs de jeu dans le test ; build
d'exemple du Chasseur : `tests/fixtures/community/hunter_example_build.json` (build d'exemple, pas un relevé)."""

import copy
import json
import shutil

import pytest
from conftest import FIXTURES, read_json

from forever.cli import main
from forever.engine.talents import check_build, check_class_build, points_available
from forever.gamedata import build_game_data
from forever.lookup import check_talents, lookup_class_talent
from forever.profile import read_profile
from forever.profile_import import apply_import, plan_import
from forever.store import load_version

EXAMPLE = read_json(FIXTURES / "community" / "hunter_example_build.json")


@pytest.fixture(scope="module")
def gd(tmp_path_factory):
    from conftest import isolated_deps

    return build_game_data(load_version(isolated_deps(tmp_path_factory.mktemp("gd"))))


def talents(gd, cls):
    return {t["key"]: t for tree in gd.classes[cls].trees for t in tree["talents"]}


def with_prereq(gd, cls):
    """Premier talent de la classe avec un prérequis unique, et ce prérequis."""
    by_node = {t["node_id"]: t for t in talents(gd, cls).values()}
    for t in talents(gd, cls).values():
        if len(t["prereqs"]) == 1 and t["tier"]:
            return t, by_node[t["prereqs"][0]["node_id"]]
    raise AssertionError("aucun talent à prérequis")


def filler(gd, cls, tree, below_tier, exclude):
    """Points au maximum dans les talents de l'arbre sous le palier donné (sauf `exclude`), assez pour l'ouvrir."""
    need = gd.constants.talents.points_per_tier * (below_tier - 1)
    pts, spent = {}, 0
    for t in talents(gd, cls).values():
        if spent >= need:
            break
        if t["tree"] == tree and t["tier"] and t["tier"] < below_tier and t["key"] not in exclude and not t["prereqs"]:
            pts[t["key"]] = t["max"]
            spent += t["max"]
    assert spent >= need
    return pts


def test_rejects_tier_overflow_other_class(gd):
    high = next(t for t in talents(gd, "Rogue").values() if t["tier"] and t["tier"] >= 3 and not t["prereqs"])
    errors = check_class_build(gd.classes["Rogue"], gd.constants.talents, {high["key"]: 1}, 60)
    assert any("palier" in e for e in errors)


def test_rejects_missing_prerequisite(gd):
    t, prereq = with_prereq(gd, "Rogue")
    pts = filler(gd, "Rogue", t["tree"], t["tier"], {prereq["key"]})
    pts[t["key"]] = 1
    errors = check_class_build(gd.classes["Rogue"], gd.constants.talents, pts, 60)
    assert any("exige" in e and prereq["name"] in e for e in errors)
    pts[prereq["key"]] = prereq["max"]
    assert not [e for e in check_class_build(gd.classes["Rogue"], gd.constants.talents, pts, 60) if "exige" in e]


def test_rejects_more_points_than_the_level_allows(gd):
    level = gd.constants.talents.first_level
    tier_one = [t for t in talents(gd, "Hunter").values() if t["tier"] == 1]
    pts = {t["key"]: t["max"] for t in tier_one}
    assert sum(pts.values()) > points_available(gd, level)  # prémisse
    errors = check_class_build(gd.classes["Hunter"], gd.constants.talents, pts, level)
    assert any("disponibles" in e for e in errors)


def test_accepts_a_legal_community_build(gd):
    knowledge = gd.classes[EXAMPLE["class"]]
    assert check_class_build(knowledge, gd.constants.talents, EXAMPLE["talents"], EXAMPLE["level"]) == []


def test_mage_check_is_unchanged(gd):
    builds = [b["points"] for b in read_json(FIXTURES / "community" / "mage_builds.json")["references"]]
    builds += [{"iceLance": 1}, {"improvedFrostbolt": 6}, {"frostbite": 3}]
    for pts in builds:
        for level in (12, 40, 60):
            assert check_class_build(gd.classes["Mage"], gd.constants.talents, pts, level) == check_build(
                gd, pts, level
            )


def test_unresolved_tier_uses_community_tier_else_is_undecidable(gd):
    warlock = gd.classes["Warlock"]
    placed = [t for t in talents(gd, "Warlock").values() if t["tier"] is None]
    assert placed and all(t.get("tier_community") for t in placed)  # prémisse : paliers communautaires
    t = placed[0]
    pts = (
        filler(gd, "Warlock", t["tree"], t["tier_community"]["tier"], {t["key"]})
        if t["tier_community"]["tier"] > 1
        else {}
    )
    pts[t["key"]] = 1
    assert not [e for e in check_class_build(warlock, gd.constants.talents, pts, 60) if "non décidable" in e]
    blind = copy.deepcopy(warlock.trees)
    for tree in blind:
        for x in tree["talents"]:
            x.pop("tier_community", None)
    from dataclasses import replace

    errors = check_class_build(replace(warlock, trees=blind), gd.constants.talents, pts, 60)
    assert any("non décidable" in e and t["name"] in e for e in errors)


def test_lookup_talent_of_another_class(make_deps):
    t = talents(build_game_data(load_version(make_deps())), "Hunter")["intimidation"]
    out = lookup_class_talent(make_deps(), "Chasseur", t["name"])
    assert (out["class"], out["id"], out["tree"], out["tier"], out["max_rank"]) == (
        "Hunter",
        "intimidation",
        t["tree"],
        t["tier"],
        t["max"],
    )
    assert out["description_template"] == t["desc"] and len(out["prereqs"]) == len(t["prereqs"])
    assert out["provenance"]["certainty"] in ("certain", "probable")


def test_build_check_kind(make_deps):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    deps = make_deps()
    arguments = {
        "kind": "build_check",
        "name": EXAMPLE["class"],
        "level": EXAMPLE["level"],
        "talents": ",".join(f"{k}={v}" for k, v in EXAMPLE["talents"].items()),
    }

    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_lookup", arguments)

    r = asyncio.run(go())
    assert not r.is_error
    out = r.structured_content
    assert out["legal"] is True and out["errors"] == []
    assert {t["key"] for t in out["talents"]} == set(EXAMPLE["talents"])
    assert all(t["description_template"] for t in out["talents"])
    direct = check_talents(deps, "Chasseur", EXAMPLE["talents"], EXAMPLE["level"])
    assert direct["points"]["spent"] == sum(EXAMPLE["talents"].values())


def test_talents_check_cli(make_deps, capsys):
    argv = ["talents", "check", "--class", "Chasseur", "--level", str(EXAMPLE["level"])]
    argv += [f"{k}={v}" for k, v in EXAMPLE["talents"].items()]
    capsys.readouterr()
    assert main([*argv, "--json"], make_deps()) == 0
    assert json.loads(capsys.readouterr().out)["legal"] is True
    assert (
        main(["talents", "check", "--class", "Chasseur", "--level", "10", "intimidation=1", "--json"], make_deps()) == 0
    )
    assert json.loads(capsys.readouterr().out)["legal"] is False


def test_profile_import_validates_hunter_talents(make_deps, tmp_path):
    sv = tmp_path / "SavedVariables"
    sv.mkdir()
    shutil.copy(FIXTURES / "addon" / "ForeverLoggerDB.lua", sv / "ForeverLogger.lua")
    deps = make_deps()
    apply_import(deps, plan_import(deps, sv_dir=sv, logs_dir=None))
    hunter = read_profile(deps, "Traqueur")["character"]
    known = talents(build_game_data(load_version(deps)), "Hunter")
    by_node = {str(t["node_id"]): key for key, t in known.items()}
    assert hunter["talents"] == {by_node[n]: r for n, r in hunter["talent_nodes"].items()}
    assert hunter["validated"] is True
