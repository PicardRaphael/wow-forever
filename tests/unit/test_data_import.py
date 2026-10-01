"""Les fichiers non décodés de la version installée viennent du seed forever-mage (sauf sources.json et
mechanics.json, rédigés dans forever-core). Depuis la révision 2 (T06b), talents.json et spells.json portent les
valeurs du client ; leurs copies du seed sont `_seed_talents.json` et `_seed_spells.json` (test_seed_data.py).

Depuis T08a, la version installée (1.60.1.70124) hérite ces fichiers de 1.60.1.70009 : `forever decode` y ajoute
`inherited_from` et les réécrit. Ils ne sont donc plus identiques octet pour octet au seed ; leur **contenu** l'est,
cette marque d'origine mise à part."""

import hashlib
import json

from conftest import DATA_DIR, LOCAL_VERSION, PREVIOUS_VERSION, SEED_DATA, SEED_VERSION

SEED_FILES = [
    "_source_gunba_mage_tree.json",
    "leveling.json",
    "meta.json",
    "racials.json",
    "respec.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content(path):
    """Contenu du fichier, sa marque d'origine mise à part (`inherited_from`, écrite par forever decode)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    # T08b : meta.json porte aussi game_state, fait d'installation (D2)
    return {k: v for k, v in doc.items() if k not in ("inherited_from", "game_state")} if isinstance(doc, dict) else doc


def test_seed_files_are_byte_identical_in_the_version_they_came_from():
    for name in SEED_FILES:
        assert sha(DATA_DIR / PREVIOUS_VERSION / name) == sha(SEED_DATA / SEED_VERSION / name), name


# PV1, D5 : racials.json retiré de la version installée (raciaux décodés dans races.json), copie figée gardée.
INSTALLED_NAME = {"racials.json": "_seed_racials.json"}


def test_seed_files_are_inherited_unchanged_by_the_installed_version():
    for name in SEED_FILES:
        local = INSTALLED_NAME.get(name, name)
        assert content(DATA_DIR / LOCAL_VERSION / local) == content(SEED_DATA / SEED_VERSION / name), name


def test_overrides_copied_into_version_dir():
    assert sha(DATA_DIR / PREVIOUS_VERSION / "overrides.json") == sha(SEED_DATA / "overrides.json")
    assert content(DATA_DIR / LOCAL_VERSION / "overrides.json") == content(SEED_DATA / "overrides.json")


def test_version_dir_contains_exactly_expected_files():
    names = {p.name for p in (DATA_DIR / LOCAL_VERSION).iterdir()}
    assert names == {INSTALLED_NAME.get(n, n) for n in SEED_FILES} | {
        "classes.json",  # PV1 : savoir des 9 classes décodé du client (révision 2)
        "races.json",  # PV1 : races et raciaux décodés du client (décision 106)
        "pvp_items.json",  # PV1 : bijoux PvP décodés du client
        "pvp_rules.json",  # PV1 : règles du serveur des rendements décroissants (suppose, sources citées)
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
        "origins.json",  # T08b, bloc H : origine déclarée de chaque valeur
        "character_scaling.json",  # T08b, révision 4 : ratios du personnage décodés du client
    }
