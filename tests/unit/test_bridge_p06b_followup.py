"""Suites de la mesure de P06b (demandes de l'utilisateur du 2026-10-10, décision 237) : conversations du pont lancées
sans les hooks du plugin (BR8 : démarrage et contrôle de fin ; mesure : médiane 8,37 s avec, 6,02 s sans, trois
conversations de chaque) ; session gardée ouverte par défaut (variante C) ; critère « chiffre hors des résultats
d'outil » qui accepte un chiffre déjà donné par un outil dans un tour précédent de la même conversation ; consigne du
bouton PvP resserrée sous 600 caractères."""

import json

from forever.bridge.agent import addons_argv, claude_argv, parse_stream
from forever.bridge.speed import quality_failures

NO_HOOKS = json.dumps({"disableAllHooks": True})


def test_bridge_conversations_start_without_plugin_hooks(tmp_path):
    argv = claude_argv(claude="claude", plugin_dir=tmp_path, mcp_config=tmp_path / "m.json", system_prompt="s")
    assert argv[argv.index("--settings") + 1] == NO_HOOKS
    assert "--plugin-dir" in argv  # les skills du plugin restent chargés
    addons = addons_argv(claude="claude", folder=tmp_path, mcp_config=tmp_path / "m.json", system_prompt="s")
    assert addons[addons.index("--settings") + 1] == NO_HOOKS


def test_persistent_session_is_the_default(make_deps):
    from forever.bridge.config import load_config

    config = load_config(make_deps().cache_dir)
    assert config["persistent"] == "on" and config["thinking"] == "on"


def turn(text, tool_result=None):
    events = []
    if tool_result is not None:
        events += [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1",
                                                           "name": "mcp__forever__forever_build", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                      "content": json.dumps(tool_result)}]}},
        ]  # fmt: skip
    events.append({"type": "result", "result": text, "session_id": "s"})
    return parse_stream(json.dumps(e) for e in events)


def test_a_number_given_by_a_tool_in_an_earlier_turn_is_sourced():
    first = turn("Build calculé.", {"seconds_per_kill": 38.21, "provenance": {"certainty": "probable"}})
    second = turn("Il mesure 38,21 s par monstre.")
    assert "chiffre hors des résultats d'outil" in quality_failures(second, None, None)
    assert "chiffre hors des résultats d'outil" not in quality_failures(second, None, None, earlier=first.events)
    third = turn("Il mesure 41,5 s par monstre.")
    assert "chiffre hors des résultats d'outil" in quality_failures(third, None, None, earlier=first.events)


def test_pvp_guide_asks_a_short_answer(make_deps):
    from conftest import FIXTURES

    from forever.bridge.context import load_context_data, resolve
    from forever.bridge.plans import button_plan

    data = load_context_data(make_deps())
    text = (FIXTURES / "bridge" / "contexts" / "mage19_cible_chaman21_tauren.txt").read_text(encoding="utf-8")
    ctx = dict(line.split("=", 1) for line in text.split("\n") if "=" in line)
    plan = button_plan("pvp", resolve(data, ctx), data.level_cap)
    guide = " ".join(plan.read)
    # décision 281 (bloc 6b) : « Comment jouer contre lui » puis le détail, la limite passe de 600 à 1200 caractères
    assert "1200 caractères au plus" in guide
    for key in ("threats", "answers", "their_answers", "windows", "missing"):
        assert f"`{key}`" in guide
