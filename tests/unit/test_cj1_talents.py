"""CJ1, bloc 3 : le bouton Talents donne toujours le plan complet, même avant le premier point de talent. Sous le
premier niveau de talent, le Mage reçoit le build conseillé jusqu'à l'objectif (niveau maximal des données), point par
point dans l'ordre de prise, avec le lien Talents Forever et le code Naowh à importer dans le Training Planner ; les
autres classes, le build populaire le plus proche avec son code Naowh (ordre généré, dit comme tel).

Contexte synthétique ; données de la version du dépôt (premier niveau de talent et niveau maximal lus, jamais écrits)."""

from forever.bridge.context import load_context_data, resolve
from forever.bridge.plans import button_message, button_plan


def _ctx(cls="MAGE", level="1", race="Gnome", faction="Alliance"):
    return {"name": "Bob", "class": cls, "level": level, "race": race, "faction": faction, "zone": "Dun Morogh"}


def test_first_talent_level_is_read_from_the_data(make_deps):
    data = load_context_data(make_deps())
    assert isinstance(data.talent_first_level, int) and 1 < data.talent_first_level < (data.level_cap or 0)


def test_mage_below_the_first_talent_level_gets_the_full_plan(make_deps):
    data = load_context_data(make_deps())
    r = resolve(data, _ctx(level="1"))
    plan = button_plan("talents", r, data.level_cap, first_talent_level=data.talent_first_level)
    call = plan.calls[0]
    assert call.tool == "forever_build" and call.args["level"] == data.level_cap
    read = " ".join(plan.read)
    assert "Naowh" in read and "Talents Forever" in read and "ordre" in read
    assert str(data.talent_first_level) in read or "first" in read or "premier point" in read


def test_mage_with_points_keeps_the_next_point_and_gets_the_naowh_code(make_deps):
    data = load_context_data(make_deps())
    level = data.talent_first_level + 5
    r = resolve(data, _ctx(level=str(level)))
    plan = button_plan("talents", r, data.level_cap, first_talent_level=data.talent_first_level)
    assert plan.calls[0].args["level"] == level + 1
    assert "Naowh" in " ".join(plan.read)


def test_other_class_gets_the_popular_build_with_its_naowh_code(make_deps):
    data = load_context_data(make_deps())
    r = resolve(data, _ctx(cls="WARRIOR", level="1", race="Human"))
    plan = button_plan("talents", r, data.level_cap, first_talent_level=data.talent_first_level)
    assert plan.calls[0].tool == "forever_lookup" and plan.calls[0].args["kind"] == "tf_popular"
    read = " ".join(plan.read)
    assert "Naowh" in read and "généré" in read


def test_bridge_message_uses_the_full_plan(make_deps):
    data = load_context_data(make_deps())
    text, plan = button_message(data, "talents", _ctx(level="1"))
    assert plan is not None and plan.calls[0].args["level"] == data.level_cap
    assert "forever_build" in text
