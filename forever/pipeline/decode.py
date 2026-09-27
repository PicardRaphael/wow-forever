"""Décodage des tables du client en données au format du dépôt (`talents.json`, `spells.json`).

Toutes les constantes de lecture (lignes de compétence, géométrie de l'arbre, identifiants d'effet, niveaux
d'évaluation) viennent de `decode_rules.json` ; ce module n'en contient aucune. Le résultat est une version
candidate écrite hors de `forever/data/` : T03 n'installe jamais une version."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.pipeline.tables import Row

RULES_NAME = "decode_rules.json"
DECODED_FILES = ("talents.json", "spells.json")
INHERITED_FILES = (
    "racials.json",
    "leveling.json",
    "mechanics.json",
    "respec.json",
    "overrides.json",
    "meta.json",
    RULES_NAME,
)

Tables = Mapping[str, Sequence[Row]]
"""Table -> lignes typées ; « SpellName » pour la locale par défaut, « frFR/SpellName » pour une autre locale."""


class Candidate(NamedTuple):
    root: Path  # dossier de données : manifest.json + <version>/
    version: str
    talents: int
    spells: int
    spell_ranks: int
    observations: list[str]


def load_rules(data_dir: Path) -> tuple[str, dict[str, Any]]:
    """(version, règles) : `decode_rules.json` de la version locale la plus récente qui en a un."""
    raise NotImplementedError


def load_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    """Tables des règles lues dans `csv_dir/<locale>/<Table>.csv` (DataSchemaError si une colonne manque,
    CsvMissingError si un fichier manque)."""
    raise NotImplementedError


def talent_key(name: str) -> str:
    """Clé d'un talent : nom anglais en camelCase, apostrophes retirées (« Winter's Chill » -> wintersChill)."""
    raise NotImplementedError


def decode_talents(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `talents.json` décodé : arbres, puis talents par palier et colonne."""
    raise NotImplementedError


def decode_spells(
    tables: Tables, rules: Mapping[str, Any], inherited: Mapping[str, Any], version: str
) -> dict[str, Any]:
    """Contenu de `spells.json` : rangs décodés (`rank_format`), noms anglais et français, identifiants des rangs ;
    les autres champs (portée, ralentissement, sorts utilitaires…) sont repris de `inherited`."""
    raise NotImplementedError


def decode_version(
    deps: Deps, version: str, *, csv_dir: Path | None = None, out: Path | None = None, force: bool = False
) -> Candidate:
    """Écrit une version candidate complète dans `out` (défaut : `<cache>/candidates/<version>/`).

    `csv_dir` : dossier des CSV (défaut : cache de `forever fetch`). Règles et fichiers hérités : version locale la
    plus récente. Refuse d'écraser une candidate existante sans `force`. Aucun accès réseau."""
    raise NotImplementedError
