"""Bloc 4c (idées du chat du 2026-10-16, points 1 et 3 ; décision 282) : réponse d'équipement lisible et suite
proposée. Le résumé vient d'abord (combien d'objets par quêtes, donjons, marchands, butin aléatoire) ; dans une
tranche, chaque emplacement a son titre, puis l'objet à viser maintenant et les suivants, chacun sur sa ligne ; après
la liste, « Veux-tu la feuille de route pour obtenir ces objets ? » avec un bouton qui la demande (`a=gear_route`).

Valeurs : addons fabriqués (`test_gear_level_reply.wow_dir`, `test_gear_level_range.wow_dir`), contexte synthétique.
Aucun chiffre de jeu ici."""

from test_bridge_choices import setup_bridge
from test_gear_level_range import CONTEXT as PRIEST
from test_gear_level_range import HIGH as RANGE_HIGH
from test_gear_level_range import LOW as RANGE_LOW
from test_gear_level_range import wow_dir as range_wow_dir
from test_gear_level_reply import LEVEL, context, wow_dir

from forever.bridge import gear_level


def test_summary_comes_first(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    text, _ = gear_level.gear_level_reply(deps, context(), LEVEL)
    lines = text.splitlines()
    assert lines[1].startswith("En bref :") and "marchand" in lines[1] and "butin aléatoire" in lines[1]
    assert lines.index(lines[1]) < min(i for i, line in enumerate(lines) if line.startswith("- "))


def test_range_lists_each_item_on_its_own_line(tmp_path, make_deps):
    deps = make_deps(wow_dir=range_wow_dir(tmp_path), offline=True)
    text, _ = gear_level.gear_level_reply(deps, PRIEST, (RANGE_LOW, RANGE_HIGH))
    lines = text.splitlines()
    head = lines.index("- Mains :")
    assert lines[head + 1].strip().startswith(f"· niveaux {RANGE_LOW} à {RANGE_LOW + 1} : ")
    assert "940001" in lines[head + 1] and "940002" in lines[head + 2]


def test_the_next_step_is_offered_with_a_button(tmp_path, make_deps):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    (tmp_path / "bridge").mkdir()
    bridge, _addons, _agent, send, _cards = setup_bridge(tmp_path / "bridge")
    bridge.gearer = lambda ctx, level: gear_level.gear_level_reply(deps, context(), level)
    reply = send(flags={f"a=gear_level:{LEVEL}"}, text="")
    assert "Veux-tu la feuille de route pour obtenir ces objets ?" in reply.text
    buttons = [reply.choices.buttons[i] for i in range(1, len(reply.choices.buttons) + 1)]
    assert [b.action for b in buttons] == [f"gear_route:{LEVEL}"] and buttons[0].label
