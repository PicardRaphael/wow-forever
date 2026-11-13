"""Relevé complet du familier par ForeverLogger (vrai Lua sous lupa.lua51, client simulé
`tests/fixtures/bridge/wow_stub.lua`) : grimoire du familier (`C_SpellBook`, banque du familier), liste des
familiers du jeu (`C_StableInfo.GetActivePetList`, loyauté et capacités), API du familier absentes ou muettes nommées
(`unavailable`), abonnements refusés par le client gardés (`unknown_events`). Valeurs synthétiques (entrées du
client simulé), aucune règle de jeu."""

import pytest
from test_addon_logger_xp import Logger, to_py

lupa = pytest.importorskip("lupa")

PET = {"name": "FelinInvente", "level": 13}
SPELLS = [
    {"name": "GriffeInventee", "subName": "Rang 2", "spellID": 900001, "iconID": 11},
    {"name": "FeulementInvente", "subName": "", "spellID": 900002, "iconID": 12},
]
STABLE = [
    {
        "name": "FelinInvente",
        "level": 13,
        "familyName": "Félin",
        "creatureID": 900100,
        "petNumber": 77,
        "slotID": 1,
        "loyaltyName": "LoyautéInventée",
        "abilities": [900001, 900002],
    }
]


def hunter_with_pet(**kwargs):
    log = Logger(**kwargs)
    log.unit("pet", **PET)
    return log


def put(log, name, rows):
    log.stub[name] = log.lua.table_from(rows, recursive=True)


def last_pet(log):
    snaps = log.entries("pet_snapshots")
    assert snaps, "aucun instantané du familier"
    return to_py(snaps[-1])


def as_list(table):
    return [table[k] for k in sorted(table)] if isinstance(table, dict) else table


def test_pet_spellbook_is_recorded_with_rank_text_and_spell_id():
    log = hunter_with_pet()
    put(log, "pet_spells", SPELLS)
    log.fire("UNIT_PET", "player")
    spells = as_list(last_pet(log)["spells"])
    assert [s["name"] for s in spells] == ["GriffeInventee", "FeulementInvente"]
    assert spells[0]["sub"] == "Rang 2" and spells[0]["spell_id"] == 900001
    assert log.errors() == {}


def test_active_pet_list_keeps_loyalty_and_abilities():
    log = hunter_with_pet()
    put(log, "stable", STABLE)
    log.fire("UNIT_PET", "player")
    (pet,) = as_list(last_pet(log)["stable"])
    assert pet["loyaltyName"] == "LoyautéInventée" and pet["creatureID"] == 900100
    assert as_list(pet["abilities"]) == [900001, 900002]


def test_missing_and_silent_pet_apis_are_named():
    log = hunter_with_pet()
    g = log.lua.globals()
    g.C_SpellBook = None  # API absente du client
    g.GetPetLoyalty = log.lua.eval("function() return nil end")  # API présente mais muette
    log.fire("UNIT_PET", "player")
    snap = last_pet(log)
    assert snap["unavailable"]["C_SpellBook"] == "absente"
    assert snap["unavailable"]["GetPetLoyalty"] == "vide"
    assert "spells" not in snap and log.errors() == {}


def test_secret_spell_name_leaves_the_field_out():
    log = hunter_with_pet()
    rows = [dict(SPELLS[0])]
    put(log, "pet_spells", rows)
    log.stub.pet_spells[1].name = log.stub.SECRET
    log.fire("UNIT_PET", "player")
    (spell,) = as_list(last_pet(log)["spells"])
    assert "name" not in spell and spell["spell_id"] == 900001


def test_events_refused_by_the_client_are_kept():
    log = Logger(unknown_events=("CRAFT_SHOW",))
    refused = log.db().unknown_events
    assert refused is not None and "CRAFT_SHOW" in list(refused.values())
