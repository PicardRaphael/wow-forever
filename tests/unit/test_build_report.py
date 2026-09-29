"""Rapport de build par contexte (T05, bloc I2 ; décisions 79 à 89) : champs du schéma, raisons, alternative,
stabilité, sensibilité (sept hypothèses), respec, angles morts, hypothèses affichées, certitude, plafond de la bêta,
bonus Legacy « Talented », erreurs d'argument. Préréglage rapide pour tenir le temps des tests."""

import json

import pytest
from conftest import isolated_deps

from forever.build import CONTEXTS, build_report
from forever.engine.blind_spots import select_blind_spots
from forever.engine.talents import check_build, points_available
from forever.engine.variants import ASSUMPTIONS
from forever.errors import InvalidArgumentError
from forever.provenance import min_certainty, validate_provenance
from forever.registry import blind_spot_rules, load

FIELDS = (
    "context",
    "level",
    "race",
    "scenario",
    "talents",
    "talents_by_tree",
    "points",  # T06b : totaux (points par arbre, au total, disponibles, non dépensés)
    "order",
    "choices",
    "metric",
    "reasons",
    "alternative",
    "stability",
    "sensitivity",
    "respec",
    "blind_spots",
    "certainty",
    "certainty_sources",
    "verifiable_in_game",
    "assumptions",
    "provenance",
)


@pytest.fixture(scope="module")
def deps(tmp_path_factory):
    return isolated_deps(tmp_path_factory.mktemp("build"))


@pytest.fixture(scope="module")
def leveling(deps):
    return build_report(deps, "leveling", 14, preset="rapide")


@pytest.fixture(scope="module")
def dungeon(deps):
    return build_report(deps, "dungeon", 25, preset="rapide")


def test_every_field_is_present(leveling, dungeon):
    for rep in (leveling, dungeon):
        assert tuple(rep) == FIELDS
        json.dumps(rep, ensure_ascii=False)  # sérialisable
        validate_provenance(rep["provenance"])
    assert leveling["context"] == "leveling" and leveling["level"] == 14 and leveling["race"] == "Orc"
    assert CONTEXTS == ("leveling", "dungeon", "raid", "pvp-bg", "pvp-world")


def test_talents_are_legal_and_ordered(game_data, leveling):
    assert check_build(game_data, leveling["talents"], 14) == []
    assert sum(leveling["talents"].values()) == points_available(game_data, 14)
    assert [s["level"] for s in leveling["order"]] == list(range(10, 15))
    assert sum(sum(t.values()) for t in leveling["talents_by_tree"].values()) == sum(leveling["talents"].values())


def test_reasons_cover_every_talent(leveling, dungeon):
    for rep in (leveling, dungeon):
        assert [r["talent"] for r in rep["reasons"]] == list(rep["talents"])
        for r in rep["reasons"]:
            assert r["rank"] == rep["talents"][r["talent"]]
            assert "marginal" in r and "moved_to" in r and "confirmed" in r
        confirmed = [r for r in rep["reasons"] if r["confirmed"] is not None]
        assert 0 < len(confirmed) <= 3


def test_alternative_is_a_different_build(leveling, dungeon):
    for rep in (leveling, dungeon):
        alt = rep["alternative"]
        assert alt["talents"] != rep["talents"] and alt["diff"]
        gap = alt["gap"]
        assert gap["low"] <= gap["mean"] <= gap["high"] and isinstance(gap["significant"], bool)
        assert alt["decided_by"] in ("monte_carlo", "analytique")


def test_stability_and_sensitivity(game_data, leveling, dungeon):
    for rep in (leveling, dungeon):
        st = rep["stability"]
        assert len(st["seeds"]) == game_data.build.stability_seeds and isinstance(st["stable"], bool)
        assert set(st["winners"]) <= {"build", "alternative"}
        assert [row["assumption"] for row in rep["sensitivity"]] == list(ASSUMPTIONS)
        for row in rep["sensitivity"]:
            assert row["variant"] != row["value"] and row["source"] and isinstance(row["holds"], bool)


def test_metric_direction(leveling, dungeon):
    assert leveling["metric"]["higher_is_better"] is False and leveling["metric"]["monte_carlo"] > 0
    assert dungeon["metric"]["higher_is_better"] is True and dungeon["metric"]["n"] > 0


def test_assumptions_are_displayed(game_data, leveling, dungeon):
    for rep in (leveling, dungeon):
        text = " ; ".join(rep["assumptions"])
        assert "équipement : fiche de base par niveau" in text
        assert "coefficients de puissance des sorts du client" in text  # damage_assumptions (T04e)
        assert "Talented" in text
    assert "XP" in " ; ".join(leveling["assumptions"])
    assert "scénario provisoire" in " ; ".join(dungeon["assumptions"])
    assert dungeon["scenario"]["provisional"] is True and leveling["scenario"]["provisional"] is False


def test_certainty_is_the_minimum_of_its_sources(leveling, dungeon):
    for rep in (leveling, dungeon):
        assert rep["certainty"] == min_certainty(rep["certainty_sources"].values())
        assert rep["provenance"]["certainty"] == rep["certainty"]
    assert dungeon["certainty_sources"]["scénarios"] == "suppose"


def test_beta_level_cap(game_data, leveling, dungeon):
    cap = game_data.build.beta_level_cap
    assert leveling["verifiable_in_game"] is True  # niveau 14 ≤ plafond
    assert dungeon["verifiable_in_game"] is False  # niveau 25 > plafond
    assert any("non vérifiable en jeu avant la sortie" in a and str(cap) in a for a in dungeon["assumptions"])
    assert not any("non vérifiable" in a for a in leveling["assumptions"])


def test_blind_spots_follow_the_registry(game_data, deps, dungeon):
    rules = blind_spot_rules(load(deps.registry_path))
    expected = select_blind_spots(
        game_data, rules, "dungeon", 25, dungeon["talents"], near=dungeon["alternative"]["talents"]
    )
    assert [b["id"] for b in dungeon["blind_spots"]] == [b.id for b in expected]
    assert dungeon["blind_spots"]  # règles de contexte (Évocation, plafond de cibles, menace, buffs de groupe)
    for b in dungeon["blind_spots"]:
        assert b["effect_pct"] is None or b["effect_pct"] > 0


def test_talented_bonus(game_data, deps):
    rep = build_report(deps, "leveling", 12, preset="rapide", talented_bonus=2, sensitivity=False)
    assert sum(rep["talents"].values()) == points_available(game_data, 12, 2)
    assert check_build(game_data, rep["talents"], 12, 2) == []
    assert any("Talented" in a and "2 point" in a for a in rep["assumptions"])
    assert rep["sensitivity"] == []


def test_respec_advice(deps, leveling, dungeon):
    assert leveling["respec"]["verdict"] is None and leveling["respec"]["cost_gold"] > 0  # pas de --current
    rep = build_report(deps, "leveling", 16, preset="rapide", current={"wandSpecialization": 2}, sensitivity=False)
    assert rep["respec"]["verdict"] in ("réinitialiser", "garder")
    assert rep["respec"]["cost_certainty"] in ("probable", "suppose")
    gap = dungeon["respec"]["gap"]  # contexte : écart avec le build de leveling du niveau, sans conversion en or
    assert dungeon["respec"]["reference"] == "leveling" and "mean" in gap and "significant" in gap


def test_pvp_report(deps):
    rep = build_report(deps, "pvp-bg", 20, preset="rapide", sensitivity=False)
    assert rep["metric"]["monte_carlo"] is None and rep["alternative"]["decided_by"] == "profil"
    assert rep["verifiable_in_game"] is True


def test_report_is_deterministic(deps, leveling):
    assert build_report(deps, "leveling", 14, preset="rapide") == leveling


@pytest.mark.parametrize(
    ("args", "match"),
    [
        (("arena", 20), "Contexte inconnu"),
        (("leveling", 5), "Niveau 5"),
        (("raid", 61), "Niveau 61"),
    ],
)
def test_invalid_arguments(deps, args, match):
    with pytest.raises(InvalidArgumentError, match=match):
        build_report(deps, *args, preset="rapide")


def test_invalid_options(deps):
    with pytest.raises(InvalidArgumentError, match="illégal"):
        build_report(deps, "leveling", 20, current={"iceLance": 1}, preset="rapide")
    with pytest.raises(InvalidArgumentError, match="préréglage"):
        build_report(deps, "leveling", 20, preset="instantané")
    with pytest.raises(InvalidArgumentError, match="Talented"):
        build_report(deps, "leveling", 20, preset="rapide", talented_bonus=-1)
    with pytest.raises(InvalidArgumentError, match="seed"):
        build_report(deps, "raid", 20, preset="rapide", rules="seed")
