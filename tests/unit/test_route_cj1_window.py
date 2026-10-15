"""CJ1, bloc 6a (décision 280) : l'assistant de feuille de route de la fenêtre envoie la même demande que le chat
(`b=route`) avec ses choix en drapeaux : niveaux `lv=<de>-<à>`, donjons `dj=none`, quêtes de classe `cq=no`. Le pont
les passe à forever_route ; un drapeau mal formé est ignoré (réglage par défaut).

Valeurs : contexte et données fabriqués (`make_deps`, fixture du client simulé). Aucun chiffre de jeu ici."""

from forever.bridge.context import load_context_data, resolve
from forever.bridge.plans import button_plan, route_options


def _ctx(**extra):
    base = {"name": "Bob", "realm": "Forever", "class": "MAGE", "level": "1", "race": "Gnome",
            "faction": "Alliance", "zone": "Fixture Vale", "map": "9001", "x": "29.8", "y": "71.2"}  # fmt: skip
    return {**base, **extra}


def test_route_options_read_from_the_flags():
    flags = frozenset({"b=route", "lv=1-5", "dj=none", "cq=no", "n"})
    assert route_options(flags) == {"lv": (1, 5), "dj": "none", "cq": False}
    assert route_options(frozenset({"b=route"})) == {}
    for bad in ("lv=5-3", "lv=x-4", "lv=4", "lv=0-3"):
        assert "lv" not in route_options(frozenset({bad}))
    assert route_options(frozenset({"dj=auto", "cq=yes"})) == {"dj": "auto", "cq": True}


def test_assistant_levels_and_options_reach_forever_route(make_deps):
    data = load_context_data(make_deps())
    plan = button_plan(
        "route", resolve(data, _ctx()), data.level_cap, options={"lv": (1, 3), "dj": "none", "cq": False}
    )
    args = plan.calls[0].args
    assert (args["start_level"], args["end_level"]) == (1, 3)
    assert args["dungeons"] == "none" and args["class_quests"] is False
    assert args["start_map"] == 9001  # départ au niveau actuel : position réelle gardée


def test_route_from_a_later_level_does_not_start_from_the_current_position(make_deps):
    data = load_context_data(make_deps())
    plan = button_plan("route", resolve(data, _ctx()), data.level_cap, options={"lv": (2, 4)})
    args = plan.calls[0].args
    assert (args["start_level"], args["end_level"]) == (2, 4) and "start_map" not in args
    assert "dungeons" not in args and "class_quests" not in args  # défauts de forever_route


def test_without_options_the_route_is_unchanged(make_deps):
    data = load_context_data(make_deps())
    r = resolve(data, _ctx())
    assert button_plan("route", r, data.level_cap, options={}) == button_plan("route", r, data.level_cap)


def test_levels_from_the_assistant_are_not_asked_again(tmp_path):
    from test_bridge_choices import setup_bridge

    _bridge, _addons, _agent, send, _cards = setup_bridge(tmp_path)
    reply = send(flags={"b=route", "lv=1-4"}, text="Prépare ma feuille de route de leveling du niveau 1 au niveau 4.")
    choices = reply.choices
    actions = [choices.buttons[i].action for i in range(1, len(choices.buttons) + 1)]
    assert actions == ["route_deliver"]  # niveaux déjà choisis : seulement « Valider et livrer »
