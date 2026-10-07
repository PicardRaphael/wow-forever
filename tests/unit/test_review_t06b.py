"""Relecture de T06b : présélection du faisceau à égalité, point de passage partagé, règles du graphique, talents
inconnus du profil, niveau des valeurs dérivées, chemins personnels hors du dépôt, prochain talent non calculé."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import DATA_DIR, PREVIOUS_VERSION, REPO_ROOT, isolated_deps
from test_install import rewind_to_r1

import forever.cli as cli_module
from forever.build import build_report
from forever.cli import main
from forever.engine.talents import tier_points_required
from forever.errors import InvalidArgumentError
from forever.explain import explain_mechanic
from forever.manifest import write_manifest
from forever.optimize.leveling import _opens_tier, _shortlist
from forever.pipeline.install import apply_install, plan_install, render_install_report
from forever.profile import set_character

FROST_21 = {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceShards": 1}


def test_shortlist_keeps_the_modeled_talent_at_equal_score():
    pre = [(10.0, "sansEffet", {}, ()), (10.0, "modele", {}, ()), (12.0, "lent", {}, ())]
    assert [p[1] for p in _shortlist(pre, 1, frozenset({"modele"}))] == ["modele"]
    assert [p[1] for p in _shortlist(pre, 2, frozenset({"modele"}))] == ["modele", "sansEffet"]
    assert [p[1] for p in _shortlist(pre, 1, None)] == ["sansEffet"]  # mode seed : ordre des données


def test_passage_is_not_needed_when_a_modeled_rival_opens_the_same_tier(game_data):
    need = tier_points_required(game_data, 2)
    tier1 = [k for k, t in game_data.talents.items() if t.tree == "Frost" and t.tier == 1]
    tier2 = [k for k, t in game_data.talents.items() if t.tree == "Frost" and t.tier == 2]
    pts, key, rival, target = {tier1[0]: need - 1}, tier1[1], tier1[2], tier2[0]
    modeled = frozenset({target, rival})
    assert _opens_tier(game_data, pts, key, (target,), modeled)
    assert not _opens_tier(game_data, pts, key, (target,), modeled, rivals=(rival,))
    other = next(k for k, t in game_data.talents.items() if t.tree == "Fire" and t.tier == 1)
    assert _opens_tier(game_data, pts, key, (target,), modeled | {other}, rivals=(other,))


def test_chart_passes_rules_to_the_loader(make_deps, tmp_path, monkeypatch):
    seen = []
    real = cli_module.build_game_data

    def spy(version, rules="forever"):
        seen.append(rules)
        return real(version, rules=rules)

    monkeypatch.setattr(cli_module, "build_game_data", spy)
    argv = ["chart", "leveling", "--out", str(tmp_path / "c.png"), "--from", "10", "--to", "11", "--n", "10"]
    assert main([*argv, "--rules", "seed", "--mob-source", "seed", "--spell-level", "rank"], deps=make_deps()) == 0
    assert seen == ["seed"]


def test_profile_rejects_unknown_talents_without_a_level(make_deps, tmp_path):
    deps = replace(make_deps(), profile_path=tmp_path / "p" / "profile.json")
    with pytest.raises(InvalidArgumentError):
        set_character(deps, "Bob", cls="Mage", race="Orc", talents={"fooBar": 9})


@pytest.mark.parametrize("level", [0, 999])
def test_derived_values_refuse_a_level_out_of_bounds(make_deps, level):
    with pytest.raises(InvalidArgumentError):
        explain_mechanic(make_deps(), "B11", level=level)


def test_revision_records_no_personal_path(tmp_path, candidate):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    for d in data.iterdir():  # révision de la version courante : les versions plus récentes sont retirées
        if d.is_dir() and d.name != PREVIOUS_VERSION:
            shutil.rmtree(d)
    rewind_to_r1(data)
    write_manifest(data)
    deps = isolated_deps(tmp_path, data)
    inside = deps.cache_dir / "candidates" / PREVIOUS_VERSION
    shutil.copytree(candidate.root, inside)
    text = render_install_report(plan_install(deps, str(inside)))
    assert f"Candidate : `<cache>/candidates/{PREVIOUS_VERSION}`" in text
    assert str(tmp_path) not in text and tmp_path.as_posix() not in text
    rev = apply_install(deps, str(inside), motif="test", date="2026-09-29")
    assert rev["candidate"]["path"] == f"<cache>/candidates/{PREVIOUS_VERSION}"
    assert rev["command"] == f"forever install <cache>/candidates/{PREVIOUS_VERSION} --yes"


def test_repository_trace_has_no_personal_path():
    home = Path.home()
    for path in (DATA_DIR / PREVIOUS_VERSION / "revisions.json", REPO_ROOT / "docs/research/data-1.60.1.70009-r2.md"):
        text = path.read_text(encoding="utf-8")
        for form in (str(home), home.as_posix(), json.dumps(str(home))[1:-1]):
            assert form not in text, (path.name, form)


@pytest.mark.slow
def test_missing_next_step_is_explained(make_deps):
    over = {**FROST_21, "iceShards": 2}  # légal au niveau 22, pas au niveau 21
    rep = build_report(make_deps(), "leveling", 22, current=over, preset="rapide", sensitivity=False)
    assert rep["next_step"] is None
    assert any("prochain talent" in a for a in rep["assumptions"])


def test_hook_reads_thousands_in_tool_results():
    """Évaluation T06b (build-givre-ou-feu) : un rapport de sous-agent écrit « 11 153 » (espace des milliers) ; le
    contrôle lisait 11 et 153 dans le résultat d'outil, et signalait à tort « 11 153 XP/h » de la réponse."""
    from forever import hooks

    tool = "mcp__plugin_forever_forever__forever_sim_leveling"
    lines = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": tool, "input": {}}]}},
        {
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "| 23 | 11 153 | 10 770 |"}]
            },
        },
    ]
    assert hooks.unsourced_numbers(lines, "Givre : 11 153 XP/h, Feu : 10 770 XP/h.") == []
    assert hooks.unsourced_numbers(lines, "Givre : 12 153 XP/h.") == ["12 153 XP/h"]
