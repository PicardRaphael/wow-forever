"""Règles de l'addon (section « Addon » de CLAUDE.md, docs/ADDON.md), contrôlées statiquement sur les .lua et .toc.

Chaque règle a un cas négatif dans tests/fixtures/addon/bad/ (voir son README.md)."""

import importlib.util

import pytest
from conftest import FIXTURES, REPO_ROOT

spec = importlib.util.spec_from_file_location("check_addon", REPO_ROOT / "scripts" / "check_addon.py")
assert spec and spec.loader
check_addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_addon)

BAD = FIXTURES / "addon" / "bad"
ADDON = REPO_ROOT / "addon" / "ForeverLogger"


def test_forever_logger_respects_every_rule():
    assert check_addon.check_addon(ADDON) == []


def test_forever_bridge_respects_every_rule():
    """P06a, bloc A : l'addon du pont passe les mêmes contrôles statiques (généralisés au bloc E)."""
    assert check_addon.check_addon(REPO_ROOT / "addon" / "ForeverBridge") == []


def test_forever_logger_toc_is_repaired():
    toc = (ADDON / "ForeverLogger.toc").read_text(encoding="utf-8")
    assert "## Interface: 16001" in toc.splitlines()
    assert "## SavedVariables: ForeverLoggerDB" in toc.splitlines()
    assert check_addon.check_toc(ADDON / "ForeverLogger.toc") == []


@pytest.mark.parametrize(
    ("name", "line", "message"),
    [
        ("file_alias.lua", 2, "alias local de ForeverLoggerDB"),
        ("bare_register.lua", 3, "RegisterEvent sans pcall"),
        ("cast_spell.lua", 3, "fonction interdite CastSpellByName"),
        ("create_macro.lua", 3, "fonction interdite CreateMacro"),  # EX1 : macros importées par le joueur seulement
        ("combat_log.lua", 3, "COMBAT_LOG_EVENT_UNFILTERED"),
        ("init_at_file_level.lua", 2, "hors d'une fonction"),
    ],
)
def test_each_lua_fault_names_file_and_line(name, line, message):
    errors = check_addon.check_lua(BAD / name)
    assert any(e.startswith(f"{name}:{line} :") and message in e for e in errors), errors


def test_init_outside_addon_loaded_is_refused():
    errors = check_addon.check_lua(BAD / "init_at_file_level.lua")
    assert any("ADDON_LOADED" in e for e in errors), errors


@pytest.mark.parametrize(
    ("name", "line", "message"),
    [("merged.toc", 4, "lignes fusionnées"), ("wrong_interface.toc", 1, "## Interface: 16001")],
)
def test_each_toc_fault_names_file_and_line(name, line, message):
    errors = check_addon.check_toc(BAD / name)
    assert any(e.startswith(f"{name}:{line} :") and message in e for e in errors), errors


def test_comments_and_strings_do_not_trigger_rules(tmp_path):
    path = tmp_path / "ok.lua"
    path.write_text(
        '-- CastSpellByName est interdit ; frame:RegisterEvent("X") aussi\nlocal s = "UseAction"\n', encoding="utf-8"
    )
    assert check_addon.check_lua(path) == []


def test_forever_logger_records_the_pet_out_of_combat():
    """CH0, bloc F : instantané du familier et du Chasseur hors combat (UNIT_PET, PET_UI_UPDATE, reporté à la sortie
    du combat), relevé de la fenêtre Beast Training (CRAFT_SHOW, CRAFT_UPDATE) ; toujours aucune fonction d'action ni
    aucun abonnement au journal de combat (les règles ci-dessus restent vraies)."""
    text = (ADDON / "ForeverLogger.lua").read_text(encoding="utf-8")
    for event in ("UNIT_PET", "PET_UI_UPDATE", "PLAYER_REGEN_ENABLED", "CRAFT_SHOW", "CRAFT_UPDATE"):
        assert f"function handlers.{event}(" in text, event
    assert "InCombatLockdown" in text and "pet_snapshots" in text and "training" in text
    assert check_addon.check_addon(ADDON) == []
    toc = (ADDON / "ForeverLogger.toc").read_text(encoding="utf-8")
    assert "## Version: 0.7.0" in toc.splitlines()  # T04d : 0.4.0 ; T04f : 0.5.0 ; DJ1 : 0.6.0 ; LN1 : 0.7.0


def test_blizzard_functions_are_hooked_never_replaced():
    """P06b, bloc A : les accroches de Maj+clic passent par hooksecurefunc ; remplacer la fonction est refusé."""
    errors = check_addon.check_lua(BAD / "replace_blizzard.lua")
    assert any(
        e.startswith("replace_blizzard.lua:3 :") and "fonction de Blizzard remplacée (utiliser hooksecurefunc)" in e
        for e in errors
    ), errors
    source = (REPO_ROOT / "addon" / "ForeverBridge" / "ForeverBridge.lua").read_text(encoding="utf-8")
    assert "hooksecurefunc" in source


def test_forever_logger_records_xp_and_quests():
    """T04d, bloc A : 0.4.0 relève l'XP de chaque monstre et de chaque quête rendue ; toujours aucune fonction d'action
    ni aucun abonnement au journal de combat (règles ci-dessus) ; un gestionnaire en erreur est compté, jamais levé."""
    text = (ADDON / "ForeverLogger.lua").read_text(encoding="utf-8")
    for event in (
        "QUEST_ACCEPTED",
        "QUEST_TURNED_IN",
        "PLAYER_XP_UPDATE",
        "UPDATE_EXHAUSTION",
        "PLAYER_UPDATE_RESTING",
    ):
        assert f"function handlers.{event}(" in text, event
    assert "xp_states" in text and "quests" in text and "ForeverLoggerDB.errors" in text
    assert check_addon.check_addon(ADDON) == []
    toc = (ADDON / "ForeverLogger.toc").read_text(encoding="utf-8")
    assert "## Version: 0.7.0" in toc.splitlines()  # T04f : 0.5.0 ; DJ1 : 0.6.0 ; LN1 : 0.7.0
