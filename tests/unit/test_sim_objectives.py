"""Objectifs de leveling (T04d, bloc F) : zones et donjons (premier passage avec quêtes, passages suivants), XP
par heure, source du temps par monstre, conseil construit sur les chiffres.

Fixture : `tests/fixtures/addons/quests/` (Ragefire Chasm, quêtes de la Horde) ; données : version du dépôt."""

import json
import re

import pytest
from conftest import FIXTURES, isolated_deps

from forever.cli import main
from forever.provenance import validate_provenance
from forever.sim.objectives import objectives

WOW = FIXTURES / "addons" / "quests"
SECONDS_PER_HOUR = 3600  # conversion d'unité


@pytest.fixture(scope="module")
def hunter(tmp_path_factory):
    deps = isolated_deps(tmp_path_factory.mktemp("objectives"))
    return objectives(deps, class_name="hunter", level=15, faction="horde", wow_dir=WOW)


def rfc(report):
    return next(d for d in report["dungeons"] if "Ragefire" in d["name"])


def test_ragefire_chasm_has_a_first_pass_and_repeats(hunter):
    d = rfc(hunter)
    first, repeat = d["first_pass"], d["repeat"]
    assert first["quests"] >= 4 and first["quest_xp"] > 0
    assert first["xp"] > repeat["xp"] > 0
    assert repeat["quests"] == 0 and repeat["quest_xp"] == 0
    assert 5727 in first["missing_prereqs"]  # Hidden Enemies (5728) exige 5727, hors du donjon


@pytest.mark.parametrize("kind", ["first_pass", "repeat"])
def test_xp_per_hour_is_xp_over_time(hunter, kind):
    o = rfc(hunter)[kind]
    assert o["xp_h"] == pytest.approx(o["xp"] / (o["minutes"] / 60), rel=1e-9)
    assert o["minutes"] * 60 == pytest.approx(o["seconds"], rel=1e-9)


def test_hunter_kill_time_is_measured_or_estimated(hunter):
    kt = hunter["kill_time"]
    assert kt["source"] in ("measured", "estimated")
    if kt["source"] == "estimated":
        assert kt["low"] <= kt["seconds"] <= kt["high"] and kt["certainty"] == "suppose"


def test_mage_kill_time_comes_from_the_engine(tmp_path):
    report = objectives(isolated_deps(tmp_path), class_name="mage", level=16, faction="horde", wow_dir=WOW)
    assert report["kill_time"]["source"] == "engine"
    assert report["kill_time"]["seconds"] > 0


def test_advice_repeats_the_numbers_of_the_objective(hunter):
    advice = hunter["advice"]
    best = hunter["best"]
    numbers = {int(n) for n in re.findall(r"\d+", advice.replace(" ", "").replace(" ", ""))}
    assert round(best["xp"]) in numbers or round(best["xp_h"]) in numbers
    if best["kind"] == "dungeon_first":
        assert best["name"] in advice and round(best["minutes"]) in numbers


def test_provenance_and_assumptions(hunter):
    assert validate_provenance(hunter["provenance"]) == []
    assert any("objectives" in a for a in hunter["provenance"]["assumptions"])


def test_cli_sim_objectives(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(WOW))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    code = main(["sim", "objectives", "--level", "15", "--class", "hunter", "--faction", "horde", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and rfc(out)["first_pass"]["xp"] > 0
    assert validate_provenance(out["provenance"]) == []


def test_mcp_sim_leveling_objectives(make_deps):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(make_deps(wow_dir=WOW))) as client:
            return await client.call_tool(
                "forever_sim_leveling",
                {"kind": "objectives", "level": 15, "class_name": "hunter", "faction": "horde"},
            )

    result = asyncio.run(go())
    assert not result.is_error
    data = result.structured_content
    assert rfc(data)["first_pass"]["xp"] > 0 and data["advice"]
