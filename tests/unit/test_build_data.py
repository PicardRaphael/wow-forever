"""Données des builds de T05 (bloc A2) : recharges des talents actifs lues dans le client, barème et valeur de la
respec, paramètres de méthode de la décision et plafond de niveau de la bêta.

Recharges : tests/fixtures/wago/1.60.1.70009/enUS/SpellCooldowns.csv (max de RecoveryTime et CategoryRecoveryTime,
DifficultyID 0) : Arcane Power 12042 (ligne 53936, RecoveryTime 180000), Presence of Mind 12043 (54721, catégorie
180000), Combustion 11129 (54531, catégorie 180000), Cold Snap 12472 (54611, 600000), Ice Block 11958 (54107,
catégorie 300000), Ice Barrier 11426 (54485, catégorie 30000), Blast Wave 11113 (54339, catégorie 45000).
Barème de respec : forever/data/1.60.1.70009/respec.json ; or par heure : seed/forever-mage/scripts/respec.py
(`GOLD_PER_HOUR`, trajet 6 min) ; plafond de la bêta : docs/research/community-builds-mage.md (niveau 20)."""

import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.errors import DataSchemaError
from forever.gamedata import load_game_data
from forever.manifest import write_manifest
from forever.pipeline.decode import decode_scaling

TALENT_COOLDOWNS = {
    "arcanePower": {"spell_id": 12042, "cooldown_ms": 180000},
    "presenceOfMind": {"spell_id": 12043, "cooldown_ms": 180000},
    "combustion": {"spell_id": 11129, "cooldown_ms": 180000},
    "coldSnap": {"spell_id": 12472, "cooldown_ms": 600000},
    "iceBlock": {"spell_id": 11958, "cooldown_ms": 300000},
    "iceBarrier": {"spell_id": 11426, "cooldown_ms": 30000},
    "blastWave": {"spell_id": 11113, "cooldown_ms": 45000},
}


def edit_json(data_dir, name, change):
    path = data_dir / LOCAL_VERSION / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    write_manifest(data_dir)  # modification voulue : seule la forme est en cause


def test_talent_cooldowns_decoded_from_client(client_tables, decode_rules):
    doc = decode_scaling(client_tables, decode_rules, LOCAL_VERSION)
    assert doc["talent_cooldowns"] == TALENT_COOLDOWNS


def test_talent_cooldowns_installed(game_data):
    assert read_json(DATA_DIR / LOCAL_VERSION / "spell_scaling.json")["talent_cooldowns"] == TALENT_COOLDOWNS
    assert dict(game_data.talent_cooldowns_s) == {k: v["cooldown_ms"] / 1000 for k, v in TALENT_COOLDOWNS.items()}


def test_talent_cooldowns_keys_are_talents(game_data):
    assert set(game_data.talent_cooldowns_s) <= set(game_data.talents)


def test_spell_scaling_without_talent_cooldowns_is_refused(make_deps, data_copy):
    edit_json(data_copy, "spell_scaling.json", lambda doc: doc.pop("talent_cooldowns"))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert "talent_cooldowns" in exc.value.message


def test_respec_schedule_loaded(game_data):
    r = game_data.respec
    assert r.schedule_gold == (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50)
    assert r.beta_observed_resets == 2
    assert dict(r.gold_per_hour) == {10: 1.0, 20: 4.0, 30: 9.0, 40: 16.0, 50: 25.0, 60: 40.0}
    assert r.trip_minutes == 6.0


def test_respec_without_schedule_is_refused(make_deps, data_copy):
    edit_json(data_copy, "respec.json", lambda doc: doc.pop("classic_schedule_gold"))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert "classic_schedule_gold" in exc.value.message


def test_build_method_loaded(game_data):
    b = game_data.build
    assert b.beta_level_cap == 20
    assert b.confidence == 0.95
    assert b.stability_seeds == 5


def test_build_keys_carry_certainty_and_source():
    values = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
    expected = {
        "build.beta_level_cap": "probable",
        "build.confidence": "certain",
        "build.stability_seeds": "certain",
        "respec.gold_per_hour": "suppose",
        "respec.trip_minutes": "suppose",
        "respec.beta_observed_resets": "probable",
    }
    for key, certainty in expected.items():
        assert values[key]["certainty"] == certainty, key
        assert values[key]["source"], key
        assert values[key]["registry"] == "I5", key


def test_missing_build_key_is_schema_error(make_deps, data_copy):
    edit_json(data_copy, "mechanics.json", lambda doc: doc["values"].pop("build.beta_level_cap"))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert "build.beta_level_cap" in exc.value.message
