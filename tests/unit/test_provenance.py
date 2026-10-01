"""Bloc provenance : schéma, couverture du registre, certitudes, rendu texte."""

import re

from conftest import FIXTURES, LOCAL_VERSION, REGISTRY_PATH

from forever.provenance import (
    LEGACY_CERTAINTY,
    PROVENANCE_KEYS,
    format_provenance_line,
    make_provenance,
    min_certainty,
    validate_provenance,
)
from forever.registry import coverage

VALID = {
    "game_version": LOCAL_VERSION,
    "data_sha": "3f9a1c2b7d4e",
    "data_revision": 1,
    "generated_at": "2026-09-27T10:00:00Z",
    "freshness": "fresh",
    "certainty": "certain",
    "assumptions": [],
    "registry_coverage": "16/97",
}


def test_valid_block():
    assert validate_provenance(VALID) == []


def test_missing_key():
    bad = {k: v for k, v in VALID.items() if k != "freshness"}
    assert validate_provenance(bad)


def test_extra_key():
    assert validate_provenance({**VALID, "extra": 1})


def test_bad_certainty():
    assert validate_provenance({**VALID, "certainty": "sure"})


def test_short_data_sha():
    assert validate_provenance({**VALID, "data_sha": "3f9a1c2b7d4"})


def test_other_invalid_values():
    assert validate_provenance({**VALID, "freshness": "old"})
    assert validate_provenance({**VALID, "game_version": "1.60.1"})
    assert validate_provenance({**VALID, "generated_at": "2026-09-27 10:00:00"})
    assert validate_provenance({**VALID, "assumptions": [1]})
    assert validate_provenance({**VALID, "registry_coverage": "16 sur 97"})
    assert validate_provenance({**VALID, "data_revision": 0})
    assert validate_provenance({**VALID, "data_revision": "2"})
    assert validate_provenance({**VALID, "data_revision": True})
    assert validate_provenance("pas un objet")


def test_registry_coverage_small():
    assert coverage(FIXTURES / "registry_small.yaml") == "1/3"


def test_registry_coverage_repository():
    assert re.fullmatch(r"\d+/\d+", coverage(REGISTRY_PATH))


def test_registry_coverage_missing(tmp_path):
    assert coverage(tmp_path / "absent.yaml") == "0/0"


def test_legacy_certainty_mapping():
    assert LEGACY_CERTAINTY == {"FC": "certain", "FS": "probable", "PC": "suppose", "EST": "suppose"}


def test_min_certainty():
    assert min_certainty(["certain", "probable"]) == "probable"
    assert min_certainty(["certain", "suppose", "probable"]) == "suppose"
    assert min_certainty(["certain"]) == "certain"
    assert min_certainty([]) == "certain"


def test_text_line_has_all_seven_fields():
    line = format_provenance_line(VALID)
    assert line.startswith("Provenance")
    for label in [
        f"version {VALID['game_version']} r{VALID['data_revision']}",
        "données 3f9a1c2b7d4e",
        "générée 2026-09-27T10:00:00Z",
        "fraîcheur fresh",
        "certitude certain",
        "registre 16/97",
        "hypothèses : aucune",
    ]:
        assert label in line
    assert "\n" not in line


def test_text_line_lists_assumptions():
    line = format_provenance_line({**VALID, "assumptions": ["première", "seconde"]})
    assert "hypothèses : première ; seconde" in line


def test_make_provenance(make_deps):
    p = make_provenance(
        make_deps(),
        game_version=LOCAL_VERSION,
        data_sha="3f9a1c2b7d4e",
        freshness="fresh",
        certainty="probable",
        assumptions=["a"],
    )
    assert validate_provenance(p) == []
    assert tuple(p) == PROVENANCE_KEYS
    assert p["generated_at"] == "2026-09-27T12:00:00Z"
    assert p["registry_coverage"] == coverage(REGISTRY_PATH)
    assert p["assumptions"] == ["a"]
    # Révision de la version installée, lue dans sources.json (via le manifeste) : 3 depuis PV1 (relecture).
    assert p["data_revision"] == 4  # T08b : révision 4 (ratios du personnage)


def test_make_provenance_without_registry(make_deps, tmp_path):
    p = make_provenance(
        make_deps(registry_path=tmp_path / "absent.yaml"),
        game_version=LOCAL_VERSION,
        data_sha="3f9a1c2b7d4e",
        freshness="unknown",
        certainty="certain",
        assumptions=[],
    )
    assert p["registry_coverage"] == "0/0"
    assert any("registre introuvable" in a for a in p["assumptions"])
