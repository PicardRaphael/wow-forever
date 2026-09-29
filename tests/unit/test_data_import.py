"""Les données 1.60.1.70009 sont des copies octet pour octet du seed forever-mage (sauf sources.json et
mechanics.json, rédigés dans forever-core). Depuis la révision 2 (T06b), talents.json et spells.json portent les
valeurs du client ; leurs copies du seed sont `_seed_talents.json` et `_seed_spells.json` (test_seed_data.py)."""

import hashlib

from conftest import DATA_DIR, LOCAL_VERSION, SEED_DATA

SEED_FILES = [
    "_source_gunba_mage_tree.json",
    "leveling.json",
    "meta.json",
    "racials.json",
    "respec.json",
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
        "talents.json",  # T06b : valeurs du client (révision 2), plus des copies du seed
        "spells.json",
        "overrides.json",
        "sources.json",
        "mechanics.json",
        "decode_rules.json",  # T03 : règles de lecture des tables du client
        "confirmed_changes.json",  # T03 : écarts client ↔ référence tranchés
        "monsters.json",  # T04 : PV des monstres (journaux, Questie en regard)
        "spell_scaling.json",  # T04 : points de base des sorts par niveau (decode)
        "_seed_talents.json",  # T06b : copies figées du seed pour le mode seed (décision D2)
        "_seed_spells.json",
        "revisions.json",  # T06b : journal des révisions de la version (forever install)
    }
