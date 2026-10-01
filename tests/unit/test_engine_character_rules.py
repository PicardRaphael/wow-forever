"""Ratios du personnage selon le mode (T08b, bloc A) : en mode forever, lus dans `character_scaling.json` quand la
version le porte ; en mode seed, estimations de `mechanics.json` (fm.py) inchangées ; sans le fichier, le mode forever
garde les estimations et le dit.

Le fichier décodé vient des fixtures (`tests/fixtures/wago/1.60.1.70124/`), installé dans une copie des données."""

import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, read_json

from forever.cli import main
from forever.engine import character, int_per_crit
from forever.engine.monsters import armor_reduction
from forever.gamedata import build_game_data
from forever.leveling import ratio_assumption
from forever.manifest import write_manifest
from forever.pipeline.character_scaling import (
    CHARACTER_FILE,
    decode_character_scaling,
    load_character_tables,
    load_gametables,
)
from forever.store import load_version

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
PERCENT = 100.0  # conversion d'unité : critique par point d'Intelligence (fraction) -> Intelligence pour 1 %
LEVELS = (1, 10, 25, 60)


@pytest.fixture(scope="module")
def decoded():
    tables = load_character_tables(WAGO_70124, RULES)
    return decode_character_scaling(tables, RULES, load_gametables(WAGO_70124 / "gametables", RULES), LOCAL_VERSION)


@pytest.fixture
def with_file(data_copy, decoded, make_deps):
    path = data_copy / LOCAL_VERSION / CHARACTER_FILE
    path.write_bytes((json.dumps(decoded, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(data_copy)
    return make_deps(data_dir=data_copy)


def test_forever_mode_reads_decoded_ratios(with_file, decoded):
    gd = build_game_data(load_version(with_file))
    mage = decoded["classes"]["Mage"]
    assert gd.character_ratios == "client"
    for level in LEVELS:
        assert character(gd, level).base_mana == mage["base_mana"][level - 1]
        assert int_per_crit(gd, level) == pytest.approx(1 / (PERCENT * mage["spell_crit_per_intellect"][level - 1]))
    assert gd.xp_to_next == tuple(decoded["xp_to_next"])
    for level in LEVELS:
        armor = 500.0  # armure arbitraire du test : seule la constante du niveau varie
        expected = armor / (armor + decoded["armor_constant"][level - 1])
        assert armor_reduction(gd, armor, level) == pytest.approx(expected)


def test_seed_mode_keeps_estimates(with_file, seed_game_data):
    gd = build_game_data(load_version(with_file), rules="seed")
    assert gd.character_ratios == "estimations"
    for level in LEVELS:
        assert character(gd, level) == character(seed_game_data, level)
        assert int_per_crit(gd, level) == int_per_crit(seed_game_data, level)
        assert armor_reduction(gd, 500.0, level) == armor_reduction(seed_game_data, 500.0, level)
    assert gd.xp_to_next == seed_game_data.xp_to_next


def test_forever_mode_without_file_keeps_estimates(game_data, seed_game_data):
    assert not (DATA_DIR / LOCAL_VERSION / CHARACTER_FILE).exists() or game_data.character_ratios == "client"
    if game_data.character_ratios == "estimations":
        for level in LEVELS:
            assert character(game_data, level).base_mana == character(seed_game_data, level).base_mana
            assert int_per_crit(game_data, level) == int_per_crit(seed_game_data, level)


def test_ratio_assumption_names_the_source(with_file, seed_game_data):
    gd = build_game_data(load_version(with_file))
    assert CHARACTER_FILE in ratio_assumption(gd) and "client" in ratio_assumption(gd)
    assert "estim" in ratio_assumption(seed_game_data)


def test_sim_leveling_shows_ratio_assumption(capsys, with_file):
    code = main(["sim", "leveling", "--level", "12", "--n", "4", "--json"], with_file)
    out, _ = capsys.readouterr()
    assert code == 0
    gd = build_game_data(load_version(with_file))
    assert ratio_assumption(gd) in json.loads(out)["provenance"]["assumptions"]
