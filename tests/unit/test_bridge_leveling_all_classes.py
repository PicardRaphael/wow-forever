"""Bouton Leveling pour toutes les classes (T04d, bloc F, décisions 242 et 243) : le plan appelle
`forever_sim_leveling(kind="objectives")` pour le Chasseur comme pour le Mage, et ne dit plus que l'XP par heure
n'est pas calculée. Contextes : ceux du banc de P06b (`tests/fixtures/bridge/`)."""

from test_hunter_p06b import context, hunter_bench  # noqa: F401 (fixture du banc réel)

from forever.bridge.context import resolve
from forever.bridge.plans import button_plan


def objectives_call(plan):
    return next(c for c in plan.calls if c.tool == "forever_sim_leveling" and c.args.get("kind") == "objectives")


def text(plan):
    return " ".join(plan.read)


def test_hunter_leveling_calls_objectives(hunter_bench):  # noqa: F811
    _, data = hunter_bench
    r = resolve(data, context("chasseur15"))
    plan = button_plan("leveling", r, data.level_cap)
    call = objectives_call(plan)
    assert call.args["level"] == r.level and call.args["class_name"] == r.class_name
    assert "XP par heure pas encore calculée" not in text(plan)
    assert "objectives" in text(plan) or "objectifs" in text(plan)


def test_mage_leveling_calls_objectives(hunter_bench):  # noqa: F811
    _, data = hunter_bench
    r = resolve(data, context("mage19"))
    plan = button_plan("leveling", r, data.level_cap)
    call = objectives_call(plan)
    assert call.args["class_name"] == r.class_name
    assert "XP par heure pas encore calculée" not in text(plan)
