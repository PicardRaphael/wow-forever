"""Explication d'une mécanique (critère 3) : `explain_mechanic`, CLI `forever explain-mechanic`.

Valeurs attendues : docs/MECHANICS_REGISTRY.yaml (A5 : certitude probable) ; forever/data/1.60.1.70009/mechanics.json
(character.crit_base) ; forever/data/1.60.1.70009/sources.json (certitude des règles de combat)."""

import json
import re

import pytest
from conftest import LOCAL_VERSION, tamper

from forever.cli import main
from forever.errors import DataIntegrityError, DataSchemaError, UnknownMechanicError
from forever.explain import explain_mechanic
from forever.provenance import validate_provenance

NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w])")


def test_explain_a5(make_deps):
    e = explain_mechanic(make_deps(), "A5")
    assert e["id"] == "A5"
    assert e["certainty"] == "probable"
    assert e["status"] == "teste"
    assert e["formula"]
    assert [n for n in NUMBER.findall(e["formula"]) if n not in ("0", "1")] == []
    params = {p["key"]: p for p in e["parameters"]}
    assert params["character.crit_base"]["value"] == 0.002
    assert params["character.crit_base"]["certainty"] == "suppose"
    assert "character.int_per_crit" in params
    assert e["sources"]
    assert "forever/engine/crit.py::crit_chance" in e["implementations"]
    assert "forever/engine/character.py::character" in e["implementations"]
    assert e["tests"]
    assert validate_provenance(e["provenance"]) == []
    assert e["provenance"]["certainty"] == "suppose"
    assert e["provenance"]["game_version"] == LOCAL_VERSION


def test_explain_ignores_case(make_deps):
    assert explain_mechanic(make_deps(), "a5")["id"] == "A5"


def test_explain_combat_rule_parameters(make_deps):
    params = {p["key"]: p for p in explain_mechanic(make_deps(), "A3")["parameters"]}
    assert params["combat_rules.spell_miss_by_level_diff"]["certainty"] == "suppose"
    assert params["combat_rules.min_miss"]["value"] == 0.01
    assert explain_mechanic(make_deps(), "A21")["parameters"][0]["key"] == "combat_rules.crit_mult_spell"


def test_explain_unknown(make_deps):
    with pytest.raises(UnknownMechanicError) as exc:
        explain_mechanic(make_deps(), "Z9")
    assert exc.value.code == "unknown_mechanic"
    assert exc.value.exit_code == 4
    assert exc.value.suggestions


def test_explain_absent_mechanic(make_deps):
    e = explain_mechanic(make_deps(), "A1")
    assert e["status"] == "absent"
    assert e["formula"] is None
    assert e["implementations"] == []
    assert any("non modélisée" in a for a in e["provenance"]["assumptions"])


def test_explain_without_registry(make_deps, tmp_path):
    with pytest.raises(DataSchemaError):
        explain_mechanic(make_deps(registry_path=tmp_path / "absent.yaml"), "A5")


def test_explain_tampered_data(make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "mechanics.json")
    with pytest.raises(DataIntegrityError):
        explain_mechanic(make_deps(data_dir=data_copy), "A5")


def test_cli_text(capsys, make_deps):
    code = main(["explain-mechanic", "A5"], make_deps())
    out = capsys.readouterr().out
    assert code == 0
    lines = out.rstrip("\n").splitlines()
    assert lines[0].startswith("A5")
    for fragment in ["Formule", "certitude probable", "Paramètres", "character.crit_base", "Sources", LOCAL_VERSION]:
        assert fragment in out, fragment
    assert lines[-1].startswith("Provenance")


def test_cli_json(capsys, make_deps):
    code = main(["explain-mechanic", "a5", "--json"], make_deps())
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["id"] == "A5"
    assert validate_provenance(data["provenance"]) == []


def test_cli_unknown(capsys, make_deps):
    assert main(["explain-mechanic", "Z9"], make_deps()) == 4
    err = capsys.readouterr().err
    assert "unknown_mechanic" in err and "Suggestions" in err
