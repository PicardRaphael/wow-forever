"""Armure portée selon le niveau (T04c, bloc B ; registre B7, I6).

Valeurs des fixtures wago 1.60.1.70009 (`SpellLevels.BaseLevel`, `SpellEffect`) : Frost Armor 168 / 7300 / 7301
apprise aux niveaux 1 / 10 / 20 (aura 22 armure 30 / 110 / 200), Ice Armor 7302 / 7320 / 10219 / 10220 aux niveaux
30 / 40 / 50 / 60, Mage Armor 6117 / 22782 / 22783 aux niveaux 34 / 46 / 58 (aura 134 à 50 : part de la régénération
gardée en incantation, en % ; aura 22 sur toute la magie, pas d'armure) ; Frost et Ice Armor déclenchent un ralenti
sur un coup reçu (aura 42)."""

import pytest
from conftest import LOCAL_VERSION

from forever.engine.armor import worn_armor
from forever.pipeline.decode import decode_scaling

LEARNED = {"frost_armor": [1, 10, 20], "ice_armor": [30, 40, 50, 60], "mage_armor": [34, 46, 58]}
SPELL_IDS = {
    "frost_armor": [168, 7300, 7301],
    "ice_armor": [7302, 7320, 10219, 10220],
    "mage_armor": [6117, 22782, 22783],
}


def test_armor_ranks_are_decoded_from_the_client(client_tables, decode_rules):
    utility = decode_scaling(client_tables, decode_rules, LOCAL_VERSION)["utility"]
    assert set(utility) == set(LEARNED)
    for kind, levels in LEARNED.items():
        assert [r["learned_level"] for r in utility[kind]] == levels, kind
        assert [r["spell_id"] for r in utility[kind]] == SPELL_IDS[kind], kind
        assert [r["rank"] for r in utility[kind]] == list(range(1, len(levels) + 1)), kind
    assert [r["effects"]["armor"] for r in utility["frost_armor"]] == [30, 110, 200]
    assert [r["effects"]["regen_while_casting_pct"] for r in utility["mage_armor"]] == [50, 50, 50]
    assert all("armor" not in r["effects"] for r in utility["mage_armor"])  # résistance à la magie seulement
    assert all("chill_on_hit_spell" in r["effects"] for r in utility["frost_armor"] + utility["ice_armor"])
    assert all("chill_on_hit_spell" not in r["effects"] for r in utility["mage_armor"])


def test_installed_data_carries_the_client_armors(game_data):
    for kind, levels in LEARNED.items():
        assert [r.learned_level for r in game_data.armors[kind]] == levels, kind
    assert game_data.armors["mage_armor"][0].effects["regen_while_casting_pct"] == 50


@pytest.mark.parametrize(
    ("level", "kind", "rank"),
    [
        (1, "frost_armor", 1),
        (20, "frost_armor", 3),
        (30, "ice_armor", 1),
        (33, "ice_armor", 1),
        (34, "mage_armor", 1),
        (40, "mage_armor", 1),
        (58, "mage_armor", 3),
    ],
)
def test_auto_armor_follows_the_learned_levels(game_data, level, kind, rank):
    worn = worn_armor(game_data, level)
    assert (worn.kind, worn.rank) == (kind, rank)


def test_worn_armor_effects(game_data):
    frost = worn_armor(game_data, 20)
    assert frost.slows_attackers and frost.regen_while_casting == 0.0 and frost.learned_level == 20
    mage = worn_armor(game_data, 34)
    assert not mage.slows_attackers and mage.regen_while_casting == 0.5 and mage.learned_level == 34
    assert "client" in mage.source


def test_forced_armor(game_data):
    assert worn_armor(game_data, 40, "frost")[:2] == ("ice_armor", 2)
    assert worn_armor(game_data, 12, "frost")[:2] == ("frost_armor", 2)
    assert worn_armor(game_data, 40, "mage")[:2] == ("mage_armor", 1)


def test_mage_armor_below_its_learned_level_is_refused(game_data):
    with pytest.raises(ValueError, match="Mage Armor.*34"):
        worn_armor(game_data, 30, "mage")


def test_unknown_armor_choice_is_refused(game_data):
    with pytest.raises(ValueError, match="armor"):
        worn_armor(game_data, 30, "molten")
