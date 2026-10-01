"""Ablation des valeurs du client au rejeu des builds (T08b, bloc I) : `--ratios seed:<nom>[,<nom>]` remet une valeur
lue dans le client à son estimation (mode forever), une seule à la fois ou une combinaison, sans toucher aux données ;
un nom inconnu est refusé. Fichier décodé tiré des fixtures, installé dans une copie des données."""

import importlib.util
import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, REPO_ROOT, WAGO_70124, read_json

from forever.engine import character, int_per_crit
from forever.errors import InvalidArgumentError
from forever.gamedata import ABLATABLE, ablated, build_game_data
from forever.manifest import write_manifest
from forever.pipeline.character_scaling import (
    CHARACTER_FILE,
    decode_character_scaling,
    load_character_tables,
    load_gametables,
)
from forever.store import load_version

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")


def replay_module():
    spec = importlib.util.spec_from_file_location("replay_builds", REPO_ROOT / "scripts" / "replay_builds.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def deps(data_copy, make_deps):
    tables = load_character_tables(WAGO_70124, RULES)
    doc = decode_character_scaling(tables, RULES, load_gametables(WAGO_70124 / "gametables", RULES), LOCAL_VERSION)
    (data_copy / LOCAL_VERSION / CHARACTER_FILE).write_bytes(json.dumps(doc).encode("utf-8"))
    write_manifest(data_copy)
    return make_deps(data_dir=data_copy)


def test_ablatable_names():
    assert {"int_per_crit", "base_mana", "xp_to_next", "armor_constant", "utility"} <= set(ABLATABLE)


def test_one_value_is_put_back_to_its_estimate(deps, seed_game_data):
    full = build_game_data(load_version(deps))
    with ablated({"base_mana"}):
        gd = build_game_data(load_version(deps))
    level = 10
    assert character(gd, level).base_mana == character(seed_game_data, level).base_mana
    assert character(full, level).base_mana != character(seed_game_data, level).base_mana
    assert int_per_crit(gd, level) == int_per_crit(full, level)  # les autres valeurs restent celles du client
    after = build_game_data(load_version(deps))
    assert character(after, level).base_mana == character(full, level).base_mana  # rien ne reste ablaté


def test_unknown_name_is_refused():
    with pytest.raises(InvalidArgumentError), ablated({"inconnu"}):
        pass


def test_replay_option_parses_names():
    replay = replay_module()
    assert replay.parse_ratios("seed:base_mana,int_per_crit") == {"base_mana", "int_per_crit"}
    with pytest.raises(InvalidArgumentError):
        replay.parse_ratios("seed:inconnu")
    with pytest.raises(InvalidArgumentError):
        replay.parse_ratios("client:base_mana")
