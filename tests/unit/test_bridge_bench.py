"""Banc d'essai des boutons de ForeverBridge (retours de la sonde en jeu F du 2026-10-09) : sur les contextes réels
relevés en jeu (`tests/fixtures/bridge/contexts/`, conversations « jeu » de la sonde : Mage Orc 19 avec Improved
Frostbolt 5/5 et Elemental Precision 5/5, cibles Chaman de niveau 21), chaque bouton reçoit du pont un appel d'outil
fixé (`forever/bridge/plans.py`), exécuté ici par le serveur MCP sans modèle : talents reconnus, prochain point
calculé depuis le build actuel au niveau suivant, lien Talents Forever valide du chemin du joueur, égalité signalée,
fiche PvP complète. Aucun contexte de Chasseur n'a été relevé : le bouton Familiers n'est vérifié que sur la
construction de son appel. Les valeurs calculées (talent choisi) ne sont jamais écrites ici : seules la structure et
la cohérence entre blocs le sont."""

import asyncio
import json
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION
from forever.bridge.plans import button_plan, plan_text, prepare_record
from mcp import Client
from talents_forever_data import write_addon

from forever.bridge.buttons import BUTTONS, visible_buttons
from forever.bridge.context import load_context_data, resolve
from forever.bridge.prompt import message_text
from forever.bridge.record import Record
from forever.mcp_server import build_server
from forever.talents_forever import decode_code, load_addon

CONTEXTS = FIXTURES / "bridge" / "contexts"
QUESTIE = FIXTURES / "questie" / "11.38.0"


def context(name: str) -> dict[str, str]:
    text = (CONTEXTS / f"{name}.txt").read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


@pytest.fixture(scope="module")
def bench(tmp_path_factory):
    """Deps d'un poste de joueur simulé : addon Talents Forever (fixture) et Questie (fixture) dans le dossier du
    client, cache isolé ; données du dépôt."""
    from conftest import NOW, REGISTRY_PATH, FakeHttp

    from forever.config import Deps

    root = tmp_path_factory.mktemp("banc")
    wow = root / "wow"
    write_addon(wow, DATA_DIR / LOCAL_VERSION / "classes.json")
    shutil.copytree(QUESTIE, wow / "Interface" / "AddOns" / "Questie")
    deps = Deps(
        data_dir=DATA_DIR,
        registry_path=REGISTRY_PATH,
        cache_dir=root / "cache",
        http_get=FakeHttp.failing(),
        now=lambda: NOW,
        wow_dir=wow,
        profile_path=root / "profil" / "profile.json",
    )
    return deps, load_context_data(deps)


def run_calls(deps, plan) -> list[dict]:
    async def go():
        async with Client(build_server(deps)) as client:
            out = []
            for call in plan.calls:
                result = await client.call_tool(call.tool, call.args)
                out.append(json.loads(result.content[0].text))
            return out

    return asyncio.run(go())


@pytest.fixture(scope="module")
def talents_run(bench):
    deps, data = bench
    resolved = resolve(data, context("mage19"))
    plan = button_plan("talents", resolved, data.level_cap)
    return plan, run_calls(deps, plan)


# --- Contexte réel ------------------------------------------------------------------------------------------------


def test_real_contexts_are_fully_recognized(bench):
    _, data = bench
    for name in ("mage19", "mage19_cible_chaman21_tauren", "mage19_cible_chaman21_skyborne"):
        r = resolve(data, context(name))
        assert r.defects == [], name
        assert (r.class_token, r.class_name, r.level, r.race, r.faction) == ("MAGE", "Mage", 19, "Orc", "horde")
        assert r.current == {"elementalPrecision": 5, "improvedFrostbolt": 5}
    tauren = resolve(data, context("mage19_cible_chaman21_tauren"))
    assert (tauren.target_class, tauren.target_level, tauren.target_races) == ("Shaman", 21, ("Tauren",))
    # le client envoie le nom de fichier de la race (UnitRace) : « Skyborne » couvre deux races de nos données
    sky = resolve(data, context("mage19_cible_chaman21_skyborne"))
    assert sky.target_races == ("High Order Skyborne", "Windshaper Skyborne")


# --- Bouton Talents (Mage) ----------------------------------------------------------------------------------------


def test_talents_plan_asks_the_next_level_from_the_current_build(talents_run, bench):
    _, data = bench
    plan, _ = talents_run
    assert data.level_cap is not None and data.level_cap > 20
    ((call,),) = (plan.calls,)
    assert call.tool == "forever_build"
    assert call.args == {
        "context": "leveling",
        "level": 20,
        "race": "Orc",
        "current": {"elementalPrecision": 5, "improvedFrostbolt": 5},
        "sensitivity": False,
    }
    assert plan.link == "projected"


def test_talents_result_gives_the_next_point_from_the_projected_path(talents_run):
    _, (report,) = talents_run
    projected = report["respec"]["projected"]
    assert (projected["from_level"], projected["to_level"]) == (19, 20)
    (step,) = projected["steps"]
    assert step["level"] == 20
    nxt = report["next_step"]
    assert nxt is not None and nxt["level"] == 20
    assert step["talent"] in {c["talent"] for c in nxt["candidates"]}
    expected = {"elementalPrecision": 5, "improvedFrostbolt": 5}
    expected[step["talent"]] = expected.get(step["talent"], 0) + 1
    assert projected["talents"] == expected


def test_talents_result_flags_the_tie(talents_run):
    _, (report,) = talents_run
    nxt = report["next_step"]
    if nxt["decided_by"] in ("non_departage", "modelise"):
        assert nxt["runner_up"] and nxt["gap"]["significant"] is False


def test_talents_link_is_the_valid_link_of_the_players_path(talents_run, bench):
    deps, _ = bench
    _, (report,) = talents_run
    export = report["respec"]["projected"]["export"]
    assert export["status"] == "ok" and export["link"].startswith("https://talentsforever.com/")
    decoded = decode_code(load_addon(deps), deps, export["link"])
    assert decoded["talents"] == report["respec"]["projected"]["talents"]
    assert decoded["legal"] is True


def test_talents_guide_reads_the_projected_step_and_the_tie(talents_run):
    plan, _ = talents_run
    text = plan_text(plan)
    for words in ('"level": 20', "respec.projected.steps", "next_step.decided_by", "runner_up", "complément"):
        assert words in text, words


def test_message_of_the_talents_button_carries_the_plan(bench):
    _, data = bench
    record = Record(
        "6ac884ce31ab", 9, frozenset({"b=talents", "n"}), context("mage19"), "Quel est mon prochain talent ?"
    )
    prepared = prepare_record(data, record)
    assert prepared.defects == [] and prepared.link == "projected"
    text = message_text(record, talents=prepared.notes, guide=prepared.guide)
    assert "elementalPrecision:5 (Elemental Precision 5/5)" in text
    assert '"level": 20' in text and "non reconnu" not in text
    assert text.rstrip().endswith("Quel est mon prochain talent ?")


def test_talents_plan_at_the_level_cap_asks_the_same_level(bench):
    _, data = bench
    ctx = {**context("mage19"), "level": str(data.level_cap)}
    plan = button_plan("talents", resolve(data, ctx), data.level_cap)
    assert plan.calls[0].args["level"] == data.level_cap


# --- Bouton Leveling (Mage) ---------------------------------------------------------------------------------------


def test_leveling_plan_zones_and_next_point(bench):
    deps, data = bench
    plan = button_plan("leveling", resolve(data, context("mage19")), data.level_cap)
    assert [c.tool for c in plan.calls] == ["forever_lookup", "forever_build"]
    assert plan.calls[0].args == {"kind": "zones", "level": 19, "faction": "horde", "limit": 5}
    assert plan.calls[1].args["level"] == 20
    zones = run_calls(deps, type(plan)(plan.button, plan.calls[:1], plan.read, plan.link))[0]
    assert "error" not in zones and zones["provenance"]["game_version"]


# --- Bouton PvP ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["mage19_cible_chaman21_tauren", "mage19_cible_chaman21_skyborne"])
def test_pvp_sheet_of_the_target_is_complete(bench, name):
    deps, data = bench
    plan = button_plan("pvp", resolve(data, context(name)), data.level_cap)
    ((call,),) = (plan.calls,)
    assert call.args == {
        "kind": "pvp",
        "name": "Mage",
        "level": 19,
        "race": "Orc",
        "talents": "elementalPrecision=5,improvedFrostbolt=5",
        "opponent": "Shaman",
        "opponent_level": 21,
    }
    (sheet,) = run_calls(deps, plan)
    assert "error" not in sheet
    for key in ("mine", "opponent", "threats", "answers", "their_answers", "windows", "missing", "limits"):
        assert key in sheet, key
    assert sheet["opponent"] == {"class": "Shaman", "level": 21}
    assert sheet["mine"]["talents_known"] is True


def test_pvp_needs_a_player_target(bench):
    _, data = bench
    assert button_plan("pvp", resolve(data, context("mage19")), data.level_cap) is None


# --- Bouton Familiers (Chasseur) ----------------------------------------------------------------------------------


def test_pets_plan_uses_the_zone_and_the_level(bench):
    """Aucun contexte de Chasseur relevé : contexte construit (classe changée), appel seulement."""
    _, data = bench
    ctx = {**context("mage19"), "class": "HUNTER", "talents": ""}
    plan = button_plan("pets", resolve(data, ctx), data.level_cap)
    assert [(c.tool, c.args) for c in plan.calls] == [
        ("forever_lookup", {"kind": "pets", "zone": "The Barrens", "level": 19})
    ]


# --- Tous les boutons ---------------------------------------------------------------------------------------------


def test_every_visible_button_has_a_plan_for_the_classes_it_serves(bench):
    _, data = bench
    hunter = {**context("mage19_cible_chaman21_tauren"), "class": "HUNTER", "talents": ""}
    for button in visible_buttons():
        for ctx in (context("mage19_cible_chaman21_tauren"), hunter):
            token = ctx["class"]
            if button.classes is not None and token not in button.classes:
                continue
            plan = button_plan(button.key, resolve(data, ctx), data.level_cap)
            assert plan is not None and plan.calls, (button.key, token)
    assert {b.key for b in visible_buttons()} <= {b.key for b in BUTTONS}
