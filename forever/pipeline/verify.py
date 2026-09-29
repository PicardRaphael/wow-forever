"""Vérification d'une version de données (dépôt ou candidate), sans chiffre de jeu.

Contrôles : intégrité du manifeste (DataIntegrityError), schéma du moteur (`build_game_data`, et en mode seed quand
les copies figées du seed sont présentes), puis cohérence :
`len(ranks) == max` pour chaque talent, prérequis existant dans le même arbre à un palier inférieur, position
(arbre, palier, colonne) unique, rangs de sort de longueur `len(rank_format)` et de niveau croissant, chaque fichier
décrit dans `sources.json` avec une certitude valide. Les fichiers hérités (`inherited_from`) sont listés."""

from __future__ import annotations

import json
from itertools import pairwise
from typing import Any, TypedDict

from forever.config import Deps
from forever.errors import DataSchemaError
from forever.gamedata import SEED_FILES, build_game_data
from forever.manifest import SOURCES_NAME
from forever.pipeline.sources import CERTAINTIES, inherited_files, load_source, source_provenance
from forever.provenance import Provenance
from forever.store import VersionData, current_identity


class VerifyReport(TypedDict):
    version: str
    source: str
    ok: bool
    errors: list[str]
    warnings: list[str]
    inherited: list[str]
    provenance: Provenance


def _json(v: VersionData, name: str) -> Any:
    return json.loads((v.path / name).read_text(encoding="utf-8"))


def _talent_errors(doc: Any) -> list[str]:
    errors: list[str] = []
    at: dict[tuple[str, int, int], str] = {}
    talents = [t for tree in doc.get("trees", []) for t in tree.get("talents", [])]
    for t in talents:
        key = t.get("key", "?")
        if len(t.get("ranks", [])) != t.get("max"):
            errors.append(f"talents.json : {key} a {len(t.get('ranks', []))} rang(s) pour max {t.get('max')}")
        place = (t.get("tree"), t.get("tier"), t.get("col"))
        if place in at:
            errors.append(f"talents.json : {at[place]} et {key} occupent la même case {place}")
        else:
            at[place] = key
    for t in talents:
        p = t.get("prereq")
        if not p:
            continue
        target = at.get((t.get("tree"), p.get("tier"), p.get("col")))
        if target is None:
            errors.append(f"talents.json : prérequis de {t.get('key')} vers une case vide {p}")
        elif p.get("tier", 0) >= t.get("tier", 0):
            errors.append(f"talents.json : prérequis de {t.get('key')} ({target}) à un palier non inférieur")
    return errors


def _spell_errors(doc: Any) -> list[str]:
    errors: list[str] = []
    width = len(doc.get("rank_format", []))
    for key, spell in doc.get("spells", {}).items():
        ranks = spell.get("ranks", [])
        errors += [
            f"spells.json : {key} rang {i} de {len(r)} valeur(s) pour {width}"
            for i, r in enumerate(ranks, start=1)
            if len(r) != width
        ]
        levels = [r[0] for r in ranks if r]
        if any(b < a for a, b in pairwise(levels)):
            errors.append(f"spells.json : {key} a des rangs de niveau décroissant {levels}")
    return errors


def _sources_errors(v: VersionData) -> list[str]:
    files = v.sources.get("files", {})
    errors = []
    for path in sorted(v.path.iterdir()):
        if not path.is_file() or path.name == SOURCES_NAME:
            continue
        entry = files.get(path.name) if isinstance(files, dict) else None
        if not isinstance(entry, dict):
            errors.append(f"sources.json : {path.name} n'est pas décrit")
        elif entry.get("certainty") not in CERTAINTIES:
            errors.append(f"sources.json : {path.name} a une certitude invalide {entry.get('certainty')!r}")
    return errors


def check_version(v: VersionData) -> tuple[list[str], list[str], list[str]]:
    """(erreurs, avertissements, fichiers hérités) d'une version déjà chargée."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        build_game_data(v)
    except DataSchemaError as exc:
        errors.append(exc.message)
    if all((v.path / name).is_file() for name in SEED_FILES.values()):
        try:
            build_game_data(v, rules="seed")
        except DataSchemaError as exc:
            errors.append(exc.message)
    try:
        errors += _talent_errors(_json(v, "talents.json"))
        errors += _spell_errors(_json(v, "spells.json"))
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        errors.append(f"talents.json ou spells.json illisible ({exc})")
    errors += _sources_errors(v)
    inherited = inherited_files(v)
    if inherited:
        warnings.append(f"{len(inherited)} fichier(s) hérité(s) d'une version antérieure, à revérifier")
    return errors, warnings, inherited


def verify_version(deps: Deps, source: str | None = None) -> VerifyReport:
    """`source` : identifiant de version du dépôt ou chemin d'une candidate (défaut : version locale courante)."""
    ref = source or current_identity(deps.data_dir).game_version
    src, v = load_source(deps, ref)
    errors, warnings, inherited = check_version(v)
    return {
        "version": v.game_version,
        "source": ref,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "inherited": inherited,
        "provenance": source_provenance(deps, src, v),
    }
