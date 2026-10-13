"""Bonus d'XP par type de créature (T04f, suite de l'audit du registre) : une aura `creature_type_kill_xp_pct`
accessible ne s'applique qu'aux monstres du type lu dans sa valeur diverse ; une aura sans source joueur, jamais.
Valeurs lues dans `xp_bonuses.json` ; identifiants de sorts du client."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.xp import ActiveAura, XpBonusState, mob_kill_xp, xp_multiplier


def creature_auras():
    doc = read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")
    return [a for a in doc["auras"] if any(e["key"] == "creature_type_kill_xp_pct" for e in a["effects"])]


def effect(aura):
    return next(e for e in aura["effects"] if e["key"] == "creature_type_kill_xp_pct")


def test_accessible_aura_applies_to_its_creature_type_only(game_data):
    aura = next(a for a in creature_auras() if a["access"] != "none")
    e = effect(aura)
    state = XpBonusState(auras=(ActiveAura(aura["spell_id"]),))
    factor, terms = xp_multiplier(game_data, state, source="kill", creature_type=e["misc_value"])
    assert factor == pytest.approx(1 + e["base_points"] / 100, rel=1e-12) and terms
    assert xp_multiplier(game_data, state, source="kill", creature_type=e["misc_value"] + 1)[0] == 1.0
    assert xp_multiplier(game_data, state, source="kill")[0] == 1.0  # type inconnu : non appliqué
    assert xp_multiplier(game_data, state, source="quest", creature_type=e["misc_value"])[0] == 1.0
    plain = mob_kill_xp(game_data, 20, 20).xp
    boosted = mob_kill_xp(game_data, 20, 20, bonuses=state, creature_type=e["misc_value"]).xp
    assert boosted == pytest.approx(plain * factor, rel=1e-12)


def test_aura_without_player_source_never_applies(game_data):
    for aura in (a for a in creature_auras() if a["access"] == "none"):
        state = XpBonusState(auras=(ActiveAura(aura["spell_id"]),))
        assert xp_multiplier(game_data, state, source="kill", creature_type=effect(aura)["misc_value"])[0] == 1.0
