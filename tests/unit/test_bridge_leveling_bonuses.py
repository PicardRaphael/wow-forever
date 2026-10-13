"""Bouton Leveling avec les bonus d'XP (T04f, bloc E) : la consigne transmet l'état du jeu (repos, auras d'XP, sac
porté ou non) aux objectifs ; la réponse de l'outil cite les bonus actifs et leur temps restant, le meilleur bonus à
prendre, et pour un personnage sans sac au niveau de la chaîne « prends le sac de couchage : la chaîne commence ici »
avec l'étape suivante. Fixtures : quêtes `tests/fixtures/addons/quests/`, chaîne `tests/fixtures/addons/xp_bonuses/`."""

import asyncio

from conftest import FIXTURES
from mcp import Client

from forever.bridge.context import load_context_data
from forever.bridge.plans import button_message
from forever.mcp_server import build_server
from forever.sim.objectives import objectives

QUESTS = FIXTURES / "addons" / "quests"
CHAIN = FIXTURES / "addons" / "xp_bonuses"
WELL_RESTED, BAG = 429959, 211527

HUNTER = {"class": "HUNTER", "level": "15", "faction": "Horde", "race": "Orc", "resting": "0"}


def objectives_call(make_deps, context):
    _, plan = button_message(load_context_data(make_deps()), "leveling", context)
    return next(c for c in plan.calls if c.tool == "forever_sim_leveling")


def test_the_plan_passes_the_game_state(make_deps):
    context = {**HUNTER, "rested": "1200", "xp_auras": f"{WELL_RESTED}:2:3000", "xp_items": f"{BAG}:1"}
    call = objectives_call(make_deps, context)
    assert call.args["rested"] == 1200.0
    assert call.args["auras"] == f"{WELL_RESTED}:2:3000"
    assert call.args["has_sleeping_bag"] is True
    _message, plan = button_message(load_context_data(make_deps()), "leveling", context)
    read = " ".join(plan.read)
    assert "bonus_advice" in read and "bonuses.active" in read and "sleeping_bag_chain" in read


def test_without_the_xp_keys_nothing_is_guessed(make_deps):
    call = objectives_call(make_deps, HUNTER)
    assert "auras" not in call.args and "has_sleeping_bag" not in call.args and "rested" not in call.args


def test_active_bonus_and_remaining_time_are_returned(make_deps):
    call = objectives_call(make_deps, {**HUNTER, "xp_auras": f"{WELL_RESTED}:2:3000", "xp_items": f"{BAG}:1"})

    async def go():
        async with Client(build_server(make_deps(wow_dir=QUESTS))) as client:
            return await client.call_tool("forever_sim_leveling", call.args)

    r = asyncio.run(go())
    assert not r.is_error, r.structured_content
    active = r.structured_content["bonuses"]["active"]
    assert [(b["spell_id"], b["stacks"], b["remaining_s"]) for b in active] == [(WELL_RESTED, 2, 3000.0)]
    assert r.structured_content["sleeping_bag_chain"] is None  # sac porté : pas de chaîne
    assert r.structured_content["bonus_advice"]


def test_hunter_without_the_bag_is_sent_to_the_chain(make_deps):
    report = objectives(
        make_deps(wow_dir=QUESTS),
        class_name="hunter",
        level=15,
        faction="horde",
        wow_dir=QUESTS,
        has_sleeping_bag=False,
        chain_dir=CHAIN / "Interface" / "AddOns",
    )
    chain = report["sleeping_bag_chain"]
    assert chain["sentence"].startswith("prends le sac de couchage : la chaîne commence ici")
    assert "The Barrens" in chain["sentence"] and chain["next_step"]["zone"] == "The Barrens"
    assert chain["steps"] and chain["discrepancies"]
