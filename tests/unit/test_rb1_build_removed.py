"""RB1 (décision 299) : retrait de la recherche de build du Mage. Le build du Mage vient, comme pour les huit autres
classes, des builds populaires de Talents Forever vérifiés sur les données du client ; le moteur gelé du Mage reste
pour le temps par monstre et l'XP par heure.

Valeurs : addon Talents Forever synthétique (`talents_forever_data`) sur les données de PRE_70450_VERSION ; talents
attendus tirés des builds populaires lus par le code (`popular_builds`, `closest_popular`, `legal_order`), jamais
écrits ici. Aucun chiffre de jeu ici."""

import asyncio
import importlib.util
from pathlib import Path

import pytest
from conftest import DATA_DIR, PRE_70450_VERSION
from mcp import Client
from talents_forever_data import write_addon
from test_bridge_bench import bench, context  # noqa: F401  (fixture importée)
from test_gear_level_reply import wow_dir

from forever.bridge.buttons import BUTTONS, button_payload, visible_buttons
from forever.bridge.context import resolve
from forever.bridge.plans import button_plan
from forever.gamedata import build_game_data
from forever.store import load_version

ROOT = Path(__file__).resolve().parents[2]
CLASSES = DATA_DIR / PRE_70450_VERSION / "classes.json"
HIGH = 20

REMOVED_MODULES = (
    "forever.build",
    "forever.replay",
    "forever.optimize.leveling",
    "forever.optimize.endgame",
    "forever.optimize.respec",
    "forever.optimize.decide",
    "forever.engine.respec",
    "forever.sim.community",
)


# --- Code retiré --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", REMOVED_MODULES)
def test_build_search_modules_are_gone(name):
    assert importlib.util.find_spec(name) is None


def test_scripts_of_the_build_search_are_gone():
    for name in ("replay_builds.py", "build_community_fixture.py"):
        assert not (ROOT / "scripts" / name).exists(), name


def test_cli_has_no_build_command():
    import argparse

    from forever.cli import build_parser

    parser = build_parser()
    (sub,) = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    assert "build" not in sub.choices


def test_mcp_has_no_build_tool(make_deps):
    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(make_deps())) as client:
            return await client.list_tools()

    names = {t.name for t in asyncio.run(go()).tools}
    assert "forever_build" not in names and "forever_lookup" in names


def test_bridge_and_plugin_no_longer_name_the_build_tool():
    from forever.bridge.agent import ALLOWED_TOOLS

    assert not any(t.endswith("forever_build") for t in ALLOWED_TOOLS)
    runner = (ROOT / "plugin" / "agents" / "forever-sim-runner.md").read_text(encoding="utf-8")
    assert "forever_build" not in runner


def test_talents_forever_no_longer_exports_a_computed_build():
    import forever.talents_forever as tf

    assert not hasattr(tf, "attach_export") and not hasattr(tf, "BuildWithExport")


def test_gamedata_has_no_ablation():
    from forever import gamedata

    assert not hasattr(gamedata, "ABLATABLE") and not hasattr(gamedata, "ablated")


# --- Veille -------------------------------------------------------------------------------------------------------


def test_no_mage_build_engine():
    from forever.engine_inputs import ENGINES

    assert "mage_build" not in ENGINES
    assert {"mage_leveling", "pvp_dr"} <= set(ENGINES)


def test_select_tests_has_no_mage_build_engine():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import select_tests
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    assert "mage_build" not in select_tests.ENGINE_MODULES
    assert all("forever.optimize" not in p for mods in select_tests.ENGINE_MODULES.values() for p in mods)


def test_update_has_no_production_replay():
    from forever import update

    assert not hasattr(update, "_ProductionReplay") and not hasattr(update, "_default_replay")


def test_measure_summary_has_no_builds():
    from forever.update import measure_summary

    out = measure_summary({"added": [], "changed": [], "removed": [], "excluded": []}, {"5": {"before": 1, "after": 2}})
    assert "builds" not in out["measures"]
    assert "builds" not in out["measures"]["sentence"]


def test_card_has_no_builds_line():
    from forever.bridge.cards import _measure_lines

    summary = {"measures": {"npcs": {}, "hp_by_level": {}, "builds": {"replayed": True, "changed": []}}}
    assert not any(line.startswith("Builds") for line in _measure_lines(summary))


# --- Boutons du pont : le Mage suit le chemin des autres classes ---------------------------------------------------


def test_talents_button_asks_the_same_question_to_every_class():
    talents = next(b for b in BUTTONS if b.key == "talents")
    assert talents.question_for("MAGE") == talents.question_for("PALADIN")
    assert talents.notice_for("MAGE") == talents.notice_for("PALADIN")
    assert "T05" not in talents.requires
    entry = next(e for e in button_payload(visible_buttons()) if e["key"] == "talents")
    assert "questions" not in entry


def test_talents_button_of_the_mage_reads_the_closest_popular_build(bench):  # noqa: F811
    _, data = bench
    r = resolve(data, context("mage19"))
    plan = button_plan("talents", r, data.level_cap, first_talent_level=data.talent_first_level)
    assert [(c.tool, c.args.get("kind")) for c in plan.calls] == [
        ("forever_lookup", "tf_popular"),
        ("forever_lookup", "build_check"),
        ("forever_lookup", "class_guide"),
    ]
    assert plan.calls[0].args["name"] == "Mage" and plan.calls[0].args["current"]
    assert plan.link == "closest"


def test_talents_button_of_a_new_mage_reads_the_most_played_build(bench):  # noqa: F811
    _, data = bench
    ctx = {**context("mage19"), "level": "1"}
    ctx.pop("talents", None)
    r = resolve(data, ctx)
    plan = button_plan("talents", r, data.level_cap, first_talent_level=data.talent_first_level)
    assert [(c.tool, c.args.get("kind")) for c in plan.calls] == [
        ("forever_lookup", "tf_popular"),
        ("forever_lookup", "class_guide"),
    ]
    assert "current" not in plan.calls[0].args


def test_leveling_button_of_the_mage_reads_the_popular_build(bench):  # noqa: F811
    _, data = bench
    plan = button_plan("leveling", resolve(data, context("mage19")), data.level_cap)
    assert [(c.tool, c.args.get("kind")) for c in plan.calls] == [
        ("forever_lookup", "zones"),
        ("forever_lookup", "tf_popular"),
        ("forever_sim_leveling", "objectives"),
    ]
    assert all(c.tool != "forever_build" for c in plan.calls)


# --- Équipement du Mage sous le 60 : talents connectés, sinon build populaire -------------------------------------


@pytest.fixture
def popular_wow(tmp_path):
    root = wow_dir(tmp_path)
    write_addon(root, CLASSES)
    return root


def leveling(deps, level, **kwargs):
    from forever.gear import gear_report

    return gear_report(deps, "leveling", class_name="Mage", race="Gnome", faction="alliance", level=level, **kwargs)


def expected_prefix(deps, talents, level):
    """Points du build populaire `talents` pris au niveau `level` dans son ordre légal généré."""
    from forever.engine.talents import legal_order, points_available

    gd = build_game_data(load_version(deps))
    order = legal_order(gd.classes["Mage"], gd.constants.talents, talents)
    out: dict[str, int] = {}
    for key in order[: points_available(gd, level)]:
        out[key] = out.get(key, 0) + 1
    return out


def test_gear_without_talents_uses_the_most_played_popular_build(popular_wow, make_deps_at_pre_70450_version):
    from forever.talents_forever import load_addon, popular_builds

    deps = make_deps_at_pre_70450_version(wow_dir=popular_wow, offline=True)
    first = popular_builds(load_addon(deps), deps, "Mage")["classes"]["Mage"]["top"][0]
    doc = leveling(deps, HIGH)
    used = doc["talents_used"][str(HIGH)]
    assert used["source"] == "populaire"
    assert used["talents"] == expected_prefix(deps, first["talents"], HIGH)
    assert any("build populaire" in note for note in doc["weights_notes"])
    assert not any("build calculé" in note for note in doc["weights_notes"])
    assert any("build populaire" in a for a in doc["provenance"]["assumptions"])


def test_gear_uses_the_popular_build_closest_to_my_talents(popular_wow, make_deps_at_pre_70450_version):
    from forever.talents_forever import closest_popular, load_addon, popular_builds

    deps = make_deps_at_pre_70450_version(wow_dir=popular_wow, offline=True)
    addon = load_addon(deps)
    popular = popular_builds(addon, deps, "Mage")
    top = popular["classes"]["Mage"]["top"]
    other = next(b for b in top if b["tree_index"] != top[0]["tree_index"])  # autre spécialisation que le n° 1
    mine = dict(sorted(other["talents"].items())[:1])
    mine = {k: 1 for k in mine}
    closest = closest_popular(addon, popular, "Mage", mine)
    assert closest is not None and closest["rank"] != top[0]["rank"]
    wanted = next(b for b in top if b["rank"] == closest["rank"])
    doc = leveling(deps, HIGH, talents=mine, talents_level=HIGH - 5)
    used = doc["talents_used"][str(HIGH)]
    assert used["source"] == "populaire"
    assert used["talents"] == expected_prefix(deps, wanted["talents"], HIGH)


def test_gear_at_my_level_keeps_my_talents(popular_wow, make_deps_at_pre_70450_version):
    deps = make_deps_at_pre_70450_version(wow_dir=popular_wow, offline=True)
    mine = dict(list(leveling(deps, HIGH)["talents_used"][str(HIGH)]["talents"].items())[:1])
    doc = leveling(deps, HIGH, talents=mine, talents_level=HIGH)
    assert doc["talents_used"][str(HIGH)] == {"source": "actuels", "talents": mine}


def test_gear_without_talents_forever_says_so(tmp_path, make_deps_at_pre_70450_version):
    deps = make_deps_at_pre_70450_version(wow_dir=wow_dir(tmp_path), offline=True)
    doc = leveling(deps, HIGH)
    assert doc["talents_used"][str(HIGH)]["source"] == "aucun"
    assert any("Talents Forever" in note for note in doc["weights_notes"])


# --- Registre -----------------------------------------------------------------------------------------------------


def test_registry_marks_the_talent_optimizer_absent():
    from forever.registry import load

    entries = {m.id: m for m in load(ROOT / "docs" / "MECHANICS_REGISTRY.yaml")}
    assert entries["I5"].status == "absent"
    assert not any("optimize" in t or "respec" in t or "next_step" in t for t in entries["I5"].tests)
