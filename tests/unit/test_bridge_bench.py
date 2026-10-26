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
from conftest import DATA_DIR, FIXTURES, PRE_70450_VERSION
from mcp import Client
from talents_forever_data import write_addon

from forever.bridge.buttons import BUTTONS, visible_buttons
from forever.bridge.context import load_context_data, resolve
from forever.bridge.plans import button_plan
from forever.mcp_server import build_server

CONTEXTS = FIXTURES / "bridge" / "contexts"
QUESTIE = FIXTURES / "questie" / "11.38.0"


def context(name: str) -> dict[str, str]:
    text = (CONTEXTS / f"{name}.txt").read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


@pytest.fixture(scope="module")
def bench(tmp_path_factory, data_at_pre_70450_version):
    """Deps d'un poste de joueur simulé : addon Talents Forever (fixture) et Questie (fixture) dans le dossier du
    client, cache isolé ; données du dépôt."""
    from conftest import NOW, REGISTRY_PATH, FakeHttp

    from forever.config import Deps

    root = tmp_path_factory.mktemp("banc")
    wow = root / "wow"
    write_addon(wow, DATA_DIR / PRE_70450_VERSION / "classes.json")
    shutil.copytree(QUESTIE, wow / "Interface" / "AddOns" / "Questie")
    deps = Deps(
        data_dir=data_at_pre_70450_version,
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


# --- Bouton Leveling (Mage) ---------------------------------------------------------------------------------------


def test_leveling_plan_zones_and_popular_build(bench):
    deps, data = bench
    plan = button_plan("leveling", resolve(data, context("mage19")), data.level_cap)
    assert [c.tool for c in plan.calls] == ["forever_lookup", "forever_lookup", "forever_sim_leveling"]
    assert plan.calls[0].args == {
        "kind": "zones",
        "level": 19,
        "faction": "horde",
        "limit": 5,
        "class_name": "Mage",
    }  # classe du personnage connecté
    assert plan.calls[1].args["kind"] == "tf_popular"  # RB1 : build populaire, comme les autres classes
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
        if button.action:  # bouton d'action (Mettre à jour, P06b) : traité par le pont, sans conversation
            continue
        for ctx in (context("mage19_cible_chaman21_tauren"), hunter):
            token = ctx["class"]
            if button.classes is not None and token not in button.classes:
                continue
            plan = button_plan(button.key, resolve(data, ctx), data.level_cap)
            assert plan is not None and plan.calls, (button.key, token)
    assert {b.key for b in visible_buttons()} <= {b.key for b in BUTTONS}
