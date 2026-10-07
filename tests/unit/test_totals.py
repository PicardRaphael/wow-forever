"""Totaux dans les sorties des outils (T06b, bloc C, décision D4) : tout total que le modèle devait calculer est
rendu par l'outil, calculé dans `forever/engine/`.

Valeurs attendues : points disponibles = niveau − 9 (`talents.first_level` de mechanics.json, `points_available`) ;
Arcane Blast (talent `arcaneBlast`, talents.json) : coût 15 % du mana de base (`mana_pct_base`), + 175 % par cumul,
4 cumuls, + 10 % de dégâts des autres sorts par cumul ; Winter's Chill : `crit.winters_chill_per_stack` (0,02) ×
cumuls, cumuls maximum = 2e variable du rang ; Hot Streak : 25 % d'incantation de Pyroblast par cumul, 3 cumuls."""

import pytest
from conftest import isolated_deps

from forever.build import build_report
from forever.cli import render_build
from forever.engine.character import character
from forever.engine.crit import winters_chill_crit
from forever.engine.derived import stack_tables
from forever.engine.mana import arcane_blast_cost
from forever.engine.talents import build_points, points_available
from forever.explain import explain_mechanic
from forever.leveling import simulate_leveling
from forever.lookup import lookup_talent

# Lent : la fixture `reports` calcule trois builds complets, dont le raid au niveau 60 (107 s mesurées le 2026-10-07).
pytestmark = pytest.mark.slow

AB_COST_PCT = [15.0, 41.25, 67.5, 93.75, 120.0]
AB_DAMAGE_PCT = [0.0, 10.0, 20.0, 30.0, 40.0]
HS_CAST_PCT = [0.0, 25.0, 50.0, 75.0]


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("totals"))


@pytest.fixture(scope="module")
def reports(deps):
    return {
        (ctx, lv): build_report(deps, ctx, lv, preset="rapide", sensitivity=False)
        for ctx, lv in (("leveling", 20), ("pvp-bg", 40), ("raid", 60))
    }


def table(tables, talent, effect, rank=1):
    return next(t for t in tables if t["talent"] == talent and t["effect"] == effect and t["rank"] == rank)


def test_build_points_engine(game_data):
    p = build_points(game_data, {"improvedFrostbolt": 5, "elementalPrecision": 2}, 20)
    assert p == {"by_tree": {"Arcane": 0, "Fire": 0, "Frost": 7}, "total": 7, "available": 11, "unspent": 4}
    assert build_points(game_data, {}, 20, talented_bonus=2)["available"] == points_available(game_data, 20, 2) == 13


@pytest.mark.parametrize(("context", "level", "total"), [("leveling", 20, 11), ("pvp-bg", 40, 31), ("raid", 60, 51)])
def test_build_report_gives_points(game_data, reports, context, level, total):
    rep = reports[(context, level)]
    p = rep["points"]
    assert p["total"] == total == p["available"] == points_available(game_data, level)
    assert p["unspent"] == 0
    assert sum(p["by_tree"].values()) == p["total"]
    assert p["by_tree"] == {tree: sum(t.values()) for tree, t in rep["talents_by_tree"].items()}
    alt = rep["alternative"]
    assert alt["points"]["total"] == sum(alt["talents"].values())
    assert sum(alt["points"]["by_tree"].values()) == alt["points"]["total"]


def test_order_accumulates_points(reports):
    rep = reports[("leveling", 20)]
    totals = [s["points_total"] for s in rep["order"]]
    assert totals == list(range(1, len(totals) + 1))
    assert totals[-1] == rep["points"]["total"]
    assert all(sum(s["points_by_tree"].values()) == s["points_total"] for s in rep["order"])
    assert rep["order"][-1]["points_by_tree"] == rep["points"]["by_tree"]


def test_gap_advantage_is_never_negative(reports):
    for rep in reports.values():
        gap = rep["alternative"]["gap"]
        assert gap["advantage"] >= 0
        assert gap["advantage"] == pytest.approx(abs(gap["mean"]), rel=1e-12)


def test_alternative_is_measured_like_the_build(reports):
    for (context, _), rep in reports.items():
        alt, metric = rep["alternative"], rep["metric"]
        if context.startswith("pvp"):
            assert alt["monte_carlo"] is None and alt["n"] == 0
            continue
        assert alt["n"] == metric["n"] > 0
        assert alt["monte_carlo"] is not None and alt["sd"] >= 0 and alt["se"] >= 0


def test_text_output_gives_the_total(reports):
    rep = reports[("leveling", 20)]
    assert "Talents : 11 point(s) sur 11" in "\n".join(render_build(rep))


def test_arcane_blast_cost_by_stack(game_data):
    tables = stack_tables(game_data, "arcaneBlast")
    cost = table(tables, "arcaneBlast", "arcane_blast_cost")
    assert [r["stacks"] for r in cost["rows"]] == [0, 1, 2, 3, 4]
    assert [r["value"] for r in cost["rows"]] == pytest.approx(AB_COST_PCT, rel=1e-12)
    assert cost["max_stacks"] == 4 and cost["at_max"] == pytest.approx(120.0, rel=1e-12)
    rank = game_data.spells["arcane_blast"].ranks[0]
    ch = character(game_data, 40)
    at40 = table(stack_tables(game_data, "arcaneBlast", level=40), "arcaneBlast", "arcane_blast_cost")
    for row in at40["rows"]:
        expected = arcane_blast_cost(game_data, rank, {"arcaneBlast": 1}, ch, row["stacks"])
        assert row["mana"] == pytest.approx(expected, rel=1e-12)
    damage = table(tables, "arcaneBlast", "other_spells_damage")
    assert [r["value"] for r in damage["rows"]] == pytest.approx(AB_DAMAGE_PCT, rel=1e-12)


def test_winters_chill_crit_by_stack_and_rank(game_data):
    assert winters_chill_crit(game_data, 5) == pytest.approx(0.10, rel=1e-12)
    tables = stack_tables(game_data, "wintersChill")
    assert [t["rank"] for t in tables] == [1, 2, 3, 4, 5]
    for t in tables:
        assert t["max_stacks"] == t["rank"]
        assert t["at_max"] == pytest.approx(0.02 * t["rank"], rel=1e-12)
    assert table(tables, "wintersChill", "crit", 5)["at_max"] == pytest.approx(0.10, rel=1e-12)


def test_hot_streak_by_stack(game_data):
    t = table(stack_tables(game_data, "hotStreak"), "hotStreak", "pyroblast_cast_reduction")
    assert [r["value"] for r in t["rows"]] == pytest.approx(HS_CAST_PCT, rel=1e-12)
    assert stack_tables(game_data, "improvedFrostbolt") == []


def test_explain_mechanic_gives_derived_values(deps):
    b11 = explain_mechanic(deps, "B11", level=40)
    cost = table(b11["derived"], "arcaneBlast", "arcane_blast_cost")
    assert [r["value"] for r in cost["rows"]] == pytest.approx(AB_COST_PCT, rel=1e-12)
    assert all(r["mana"] is not None for r in cost["rows"])
    assert all(
        r["mana"] is None
        for r in table(explain_mechanic(deps, "B11")["derived"], "arcaneBlast", "arcane_blast_cost")["rows"]
    )
    b15 = {(t["talent"], t["effect"]) for t in explain_mechanic(deps, "B15")["derived"]}
    assert {("arcaneBlast", "other_spells_damage"), ("hotStreak", "pyroblast_cast_reduction")} <= b15
    d4 = explain_mechanic(deps, "D4")["derived"]
    assert table(d4, "wintersChill", "crit", 5)["at_max"] == pytest.approx(0.10, rel=1e-12)
    assert explain_mechanic(deps, "A3")["derived"] == []


@pytest.mark.parametrize(
    ("name", "mechanic"), [("Arcane Blast", "B11"), ("Winter's Chill", "D4"), ("Hot Streak", "B15")]
)
def test_explain_by_alias(deps, name, mechanic):
    assert explain_mechanic(deps, name)["id"] == mechanic


def test_lookup_talent_gives_derived_values(deps):
    wc = lookup_talent(deps, "Winter's Chill")
    assert [t["rank"] for t in wc["derived"]] == [1, 2, 3, 4, 5]
    assert lookup_talent(deps, "Winter's Chill", rank=5)["derived"][0]["at_max"] == pytest.approx(0.10, rel=1e-12)
    ab = lookup_talent(deps, "Arcane Blast")
    assert {t["effect"] for t in ab["derived"]} == {"arcane_blast_cost", "other_spells_damage"}
    assert lookup_talent(deps, "Improved Frostbolt")["derived"] == []


def test_sim_leveling_gives_monte_carlo_stats(deps, game_data):
    rep = simulate_leveling(deps, 20, talents={"improvedFrostbolt": 5}, n=40)
    s = rep["monte_carlo_stats"]
    assert s["n"] == 40
    assert s["low"] <= s["mean"] <= s["high"]
    assert s["mean"] == pytest.approx(rep["monte_carlo"]["total"], rel=1e-9)
    assert s["confidence"] == game_data.build.confidence
    assert s["sd"] > 0 and s["se"] == pytest.approx(s["sd"] / 40**0.5, rel=1e-12)
