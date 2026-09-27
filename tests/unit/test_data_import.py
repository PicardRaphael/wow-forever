"""Les données 1.60.1.70009 sont des copies octet pour octet du seed forever-mage (sauf sources.json et
mechanics.json, rédigés dans forever-core)."""

import hashlib

from conftest import DATA_DIR, LOCAL_VERSION, SEED_DATA

SEED_FILES = [
    "_source_gunba_mage_tree.json",
    "leveling.json",
    "meta.json",
    "racials.json",
    "respec.json",
    "spells.json",
    "talents.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_seed_files_are_byte_identical():
    for name in SEED_FILES:
        assert sha(DATA_DIR / LOCAL_VERSION / name) == sha(SEED_DATA / LOCAL_VERSION / name), name


def test_overrides_copied_into_version_dir():
    assert sha(DATA_DIR / LOCAL_VERSION / "overrides.json") == sha(SEED_DATA / "overrides.json")


def test_version_dir_contains_exactly_expected_files():
    names = {p.name for p in (DATA_DIR / LOCAL_VERSION).iterdir()}
    assert names == set(SEED_FILES) | {
        "overrides.json",
        "sources.json",
        "mechanics.json",
        "decode_rules.json",  # T03 : règles de lecture des tables du client
        "confirmed_changes.json",  # T03 : écarts client ↔ référence tranchés
    }
