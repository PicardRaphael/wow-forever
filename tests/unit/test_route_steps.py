"""Étapes de route pour RX1 (T04f, bloc E) : une étape par point de la chaîne du sac, avec carte et position ; rappels
des bonus d'XP sur une séance (sac reposé à chaque recharge de l'objet, nourriture nutritive, tente). Recharge lue
dans les données (`xp_bonuses.json`)."""

import math

from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.engine.xp import XpBonusState
from forever.route import KINDS, bonus_reminders, sleeping_bag_steps
from forever.xp_bonuses import sleeping_bag_chain

WOW = FIXTURES / "addons" / "xp_bonuses"


def test_one_route_step_per_chain_point(make_deps):
    chain = sleeping_bag_chain(make_deps(wow_dir=WOW), faction="horde", addons_dir=WOW / "Interface" / "AddOns")
    steps = sleeping_bag_steps(chain)
    assert steps == list(chain.steps) and len(steps) == 7
    assert all(s.kind in KINDS and s.map and s.x is not None and s.y is not None for s in steps)
    assert steps[-1].item_id == chain.item


def test_bag_reminder_every_cooldown(game_data):
    bag = read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")["sleeping_bag"]
    cooldown = bag["item_cooldown_ms"] / 1000
    hours = 3
    reminders = bonus_reminders(game_data, XpBonusState(), hours=hours, level=15)
    bag_steps = [r for r in reminders if r.kind == "use_item" and r.item_id == bag["item"]]
    assert len(bag_steps) == math.ceil(hours * 3600 / cooldown)
    assert [r.at_s for r in bag_steps] == [i * cooldown for i in range(len(bag_steps))]
    notes = [r for r in reminders if r.kind == "note"]
    assert notes and all(r.source and r.certainty in {"certain", "probable", "suppose"} for r in reminders)


def test_food_reminder_only_without_food(game_data):
    with_food = bonus_reminders(game_data, XpBonusState(food=True), hours=1, level=15)
    without = bonus_reminders(game_data, XpBonusState(), hours=1, level=15)
    assert len([r for r in without if "nourriture" in r.text]) == 1
    assert not [r for r in with_food if "nourriture" in r.text]
