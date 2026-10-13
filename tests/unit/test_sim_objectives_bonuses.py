"""Objectifs de leveling avec bonus d'XP (T04f, bloc C) : XP par heure sans bonus, avec repos, avec le sac de
couchage et avec les bonus actifs ; « quel bonus prendre » rangé par gain, calculé par l'outil.

Fixture : `tests/fixtures/addons/quests/` (quêtes de la Horde) ; données : version du dépôt."""

import json

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, isolated_deps, read_json

from forever.cli import main
from forever.engine.xp import ActiveAura, session_xp, sleeping_bag_state
from forever.gamedata import load_game_data
from forever.sim.objectives import objectives
from forever.xp_bonuses import DEFAULT_SESSION_H

WOW = FIXTURES / "addons" / "quests"
WELL_RESTED = 429959
KEYS = ("xp_h", "xp_h_rested", "xp_h_sleeping_bag", "xp_h_all")


def well_rested():
    doc = read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")
    return next(a for a in doc["auras"] if a["spell_id"] == WELL_RESTED)


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("objectives-bonus"))


@pytest.fixture(scope="module")
def plain(deps):
    return objectives(deps, class_name="hunter", level=15, faction="horde", wow_dir=WOW)


@pytest.fixture(scope="module")
def boosted(deps):
    return objectives(deps, class_name="hunter", level=15, faction="horde", wow_dir=WOW, rested=5000.0, food=True)


def rows(report):
    return [*report["zones"], *(r for d in report["dungeons"] for r in (d["first_pass"], d["repeat"]))]


def test_every_objective_has_the_four_rates(plain):
    assert rows(plain)
    for r in rows(plain):
        assert all(isinstance(r[k], float) for k in KEYS), r["name"]
        assert r["xp_h_sleeping_bag"] >= r["xp_h"] and r["xp_h_all"] >= r["xp_h"]
        assert 0.0 <= r["kill_share"] <= 1.0


def test_sleeping_bag_rate_is_the_session_factor(deps, plain):
    gd = load_game_data(deps)
    assert plain["bonuses"]["hours"] == DEFAULT_SESSION_H
    for r in rows(plain):
        session = session_xp(
            gd,
            base_xp_h=r["xp_h"],
            kill_share=r["kill_share"],
            hours=DEFAULT_SESSION_H,
            state=sleeping_bag_state(gd),
            rested_pool=0.0,
            level=15,
        )
        assert r["xp_h_sleeping_bag"] == pytest.approx(session.xp_h, rel=1e-9)


def test_rested_is_applied_and_no_longer_an_assumption(plain, boosted):
    assert not any("repos non appliqué" in a for a in boosted["provenance"]["assumptions"])
    killing = [r for r in rows(boosted) if r["kills"] > 0]
    assert killing and all(r["xp_h_rested"] > r["xp_h"] for r in killing)
    assert all(r["xp_h_rested"] == r["xp_h"] for r in rows(plain))


def test_active_bonuses_are_listed_with_certainty(boosted):
    active = boosted["bonuses"]["active"]
    assert active and all(b["certainty"] in {"certain", "probable", "suppose"} for b in active)
    assert any(b["access"] == "food" for b in active)


def test_active_aura_from_the_context_counts(deps):
    a = well_rested()
    report = objectives(
        deps,
        class_name="hunter",
        level=15,
        faction="horde",
        wow_dir=WOW,
        auras=(ActiveAura(WELL_RESTED, 2, a["duration_ms"] / 1000 / 2),),
    )
    (active,) = report["bonuses"]["active"]
    assert active["spell_id"] == WELL_RESTED and active["stacks"] == 2
    assert active["remaining_s"] == a["duration_ms"] / 1000 / 2
    assert all(r["xp_h_all"] > r["xp_h"] for r in rows(report) if r["kills"] > 0)


def test_best_bonus_is_ranked_by_gain(plain):
    advice = plain["bonuses"]["advice"]
    gains = [b["xp_h_gain"] for b in advice]
    assert advice and gains == sorted(gains, reverse=True) and all(g > 0 for g in gains)
    assert {b["key"] for b in advice} <= {"sleeping_bag", "food", "tent"}
    assert "sleeping_bag" in {b["key"] for b in advice}
    assert all(b["how"] and b["certainty"] in {"certain", "probable", "suppose"} for b in advice)


def test_legacy_rank_missing_is_reported(plain):
    assert plain["bonuses"]["legacy_rested_rank"] == 0
    assert any("Legacy" in a for a in plain["provenance"]["assumptions"])


def test_cli_options(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(WOW))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    args = ["sim", "objectives", "--level", "15", "--class", "hunter", "--faction", "horde"]
    code = main([*args, "--food", "--sleeping-bag", "--rested", "3000", "--hours", "3", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["bonuses"]["hours"] == 3
    assert {"sleeping_bag", "food"} <= {b["key"] for b in out["bonuses"]["active"]}
    assert main([*args, "--legacy-rested-rank", "2"]) == 0
    text = capsys.readouterr().out
    assert "avec le sac" in text and "bonus" in text.lower()
