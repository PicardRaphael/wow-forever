"""Familier actuel relu hors ligne dans ForeverLogger : grimoire, liste des familiers du jeu (loyauté, capacités),
API absentes ou muettes, abonnements refusés ; `forever pets measure` donne le dernier relevé de chaque Chasseur.

Fixture synthétique `tests/fixtures/addon/ForeverLoggerDB_pet_spells.lua` (noms et identifiants inventés)."""

from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.pets import measure_pets
from forever.pipeline.addon_sv import read_logger_db

SV = FIXTURES / "addon" / "ForeverLoggerDB_pet_spells.lua"


def test_spells_stable_and_unavailable_are_read():
    db = read_logger_db(SV)
    (c,) = db.characters.values()
    last = c.pet_snapshots[-1]
    assert [s["name"] for s in last.spells] == ["GriffeInventee", "FeulementInvente"]
    assert last.spells[0] == {"name": "GriffeInventee", "sub": "Rang 2", "spell_id": 900001}
    assert last.stable[0]["loyaltyName"] == "LoyautéInventée" and last.stable[0]["abilities"] == [900001, 900002]
    assert last.unavailable == {"GetPetTrainingPoints": "absente", "GetPetLoyalty": "vide"}
    assert c.pet_snapshots[0].spells == [] and c.pet_snapshots[0].unavailable == {}
    assert db.unknown_events == ["CRAFT_SHOW"]


def test_older_files_have_empty_new_fields():
    db = read_logger_db(FIXTURES / "addon" / "ForeverLoggerDB_pets.lua")
    (c,) = db.characters.values()
    assert all(s.spells == [] and s.stable == [] for s in c.pet_snapshots)
    assert db.unknown_events == []


def test_measure_gives_the_latest_pet_of_each_hunter():
    pets = read_json(DATA_DIR / LOCAL_VERSION / "pets.json")
    rules = read_json(DATA_DIR / LOCAL_VERSION / "pet_rules.json")
    report = measure_pets(pets, rules, read_logger_db(SV))
    (cur,) = report["current"]
    assert cur["character"] == "ChasseurInvente" and cur["pet"]["level"] == 13
    assert [s["name"] for s in cur["spells"]] == ["GriffeInventee", "FeulementInvente"]
    assert cur["stable"][0]["loyaltyName"] == "LoyautéInventée"
    assert cur["unavailable"] == {"GetPetTrainingPoints": "absente", "GetPetLoyalty": "vide"}
    assert report["unknown_events"] == ["CRAFT_SHOW"]
