"""Règles du système de familiers absentes du client (CH0, bloc C) : `pet_rules.json` de la version installée.

Chaque règle porte un texte en français, sa source, sa date, sa certitude et l'identifiant d'une entrée du registre ;
un relevé de joueurs reste au plus `suppose` (décision 127) ; le gain des points d'entraînement est inconnu (`null`)."""

import re

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, REGISTRY_PATH, read_json

from forever.origins import check_version
from forever.pipeline.decode import INHERITED_FILES
from forever.registry import find_entry, load

V = DATA_DIR / LOCAL_VERSION
RANK = {"suppose": 0, "probable": 1, "certain": 2}
MAX_BY_ORIGIN = {"addon": "suppose", "manuel": "suppose", "client": "certain"}
INTERFACE = (
    "tame.level_margin",
    "learning.method",
    "training.rank_level_applies_to",
    "training.points_gain",
    "loyalty.limits_training",
    "inheritance.health_per_stamina",
    "inheritance.armor_pct",
    "inheritance.attack_power_pct",
    "inheritance.crit",
    "attack_speed.base_s",
    "focus.regen_per_s",
    "happiness.decay",
)


@pytest.fixture(scope="module")
def doc():
    return read_json(V / "pet_rules.json")


def test_every_interface_rule_is_present(doc):
    assert set(INTERFACE) <= set(doc["rules"])


def test_each_rule_has_text_source_date_certainty_and_registry(doc):
    mechanics = load(REGISTRY_PATH)
    for key, rule in doc["rules"].items():
        assert rule["text"] and rule["source"], key
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", rule["date"]), key
        assert rule["certainty"] in RANK, key
        assert find_entry(mechanics, rule["registry"]).category == "familiers", key
        assert "value" in rule and "unit" in rule, key


def test_certainty_never_above_its_origin(doc):
    for key, rule in doc["rules"].items():
        assert rule["origin"] in MAX_BY_ORIGIN, key
        assert RANK[rule["certainty"]] <= RANK[MAX_BY_ORIGIN[rule["origin"]]], key


def test_training_points_gain_is_unknown(doc):
    rule = doc["rules"]["training.points_gain"]
    assert rule["value"] is None and rule["certainty"] == "suppose"
    assert find_entry(load(REGISTRY_PATH), rule["registry"]).status == "absent"


def test_tame_margin_stays_suppose_after_reading_the_client(doc):
    rule = doc["rules"]["tame.level_margin"]
    assert rule["certainty"] == "suppose" and rule["origin"] == "addon"
    assert "SpellTargetRestrictions" in rule["note"]


def test_reported_bugs_are_player_reports_never_modelled(doc):
    assert doc["reported_bugs"]
    for bug in doc["reported_bugs"]:
        assert bug["text"] and bug["source"] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", bug["date"])
        assert bug["certainty"] == "suppose" and bug["acknowledged_by_blizzard"] is False


def test_pet_rules_is_inherited_described_and_covered_by_origins():
    assert "pet_rules.json" in INHERITED_FILES
    files = read_json(V / "sources.json")["files"]
    assert files["pet_rules.json"]["certainty"] == "suppose"
    assert files["pets.json"]["certainty"] == "certain"
    report = check_version(DATA_DIR, LOCAL_VERSION)
    assert report.ok, [f"{i.file} {i.path} {i.kind}" for i in report.issues[:10]]
    rules = read_json(V / "origins.json")["rules"]
    assert any(r["file"] == "pets.json" and r["origin"] == "client" for r in rules)
    assert any(r["file"] == "pet_rules.json" and r["origin"] == "addon" for r in rules)
