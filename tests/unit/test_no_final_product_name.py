"""Garde (LN1, décision 271) : le produit de la version finale n'est jamais deviné ni écrit. Aucun nom de produit
Forever autre que celui de `sources.json` (la bêta) dans `forever/`, `scripts/`, `addon/`, `plugin/` et `tests/`
(hors ce fichier) : la version finale est **adoptée** sur le poste (`forever wow adopt`), jamais écrite dans le code.
Les produits non bêta du code sont la liste d'exclusion publique (`forever.installs.NOT_FOREVER_PRODUCTS`)."""

import re

from conftest import REPO_ROOT

from forever.installs import NOT_FOREVER_PRODUCTS

ZONES = ("forever", "scripts", "addon", "plugin", "tests")
SUFFIXES = {".py", ".lua", ".toc", ".md", ".json", ".yaml", ".yml", ".ps1", ".txt", ".toml"}
# Codes produits supposés de la version finale (stress test « wowf » compris ; un code produit est en minuscules :
# l'exécutable fictif « WowF.exe » des fixtures n'en est pas un) et dossier deviné « _forever_ ».
FORBIDDEN = re.compile(r"\bwowf\b|wow_classic_forever|\bwow_forever\b|(?<![\w])_(?i:forever)_(?![\w])")


def scanned():
    for zone in ZONES:
        for path in (REPO_ROOT / zone).rglob("*"):
            if "__pycache__" in path.parts or "results" in path.parts or not path.is_file():
                continue
            if path.suffix in SUFFIXES and path.name != "test_no_final_product_name.py":
                yield path


def test_no_guessed_product_of_the_final_version():
    hits = []
    for path in scanned():
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits += [f"{path.relative_to(REPO_ROOT)}: {m.group(0)}" for m in FORBIDDEN.finditer(text)]
    assert hits == []


def test_the_pattern_catches_the_guesses():
    for guess in ("wowf", "wow_classic_forever", "wow_forever", r"World of Warcraft\_forever_\WowF.exe"):
        assert FORBIDDEN.search(guess), guess
    for fine in ("forever_status", "mcp__plugin_forever_forever__forever_build", "wow_classic_beta", "WowF.exe"):
        assert not FORBIDDEN.search(fine), fine


def test_the_exclusion_list_holds_no_forever_product():
    assert not [p for p in NOT_FOREVER_PRODUCTS if FORBIDDEN.search(p) or "forever" in p]
