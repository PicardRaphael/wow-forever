"""Bloc provenance, présent dans chaque résultat d'outil (CLI et MCP)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal, TypedDict, get_args

from forever.config import Deps
from forever.errors import ErrorInfo, ForeverError
from forever.freshness import Freshness, freshness_for_version
from forever.registry import coverage
from forever.store import current_identity
from forever.timefmt import format_utc

Certainty = Literal["certain", "probable", "suppose"]

LEGACY_CERTAINTY: dict[str, Certainty] = {"FC": "certain", "FS": "probable", "PC": "suppose", "EST": "suppose"}

PROVENANCE_KEYS = (
    "game_version",
    "data_sha",
    "generated_at",
    "freshness",
    "certainty",
    "assumptions",
    "registry_coverage",
)

_CERTAINTY_ORDER: tuple[Certainty, ...] = ("suppose", "probable", "certain")
_PATTERNS = {
    "game_version": re.compile(r"^\d+\.\d+\.\d+\.\d+$"),
    "data_sha": re.compile(r"^[0-9a-f]{12}$"),
    "generated_at": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"),
    "registry_coverage": re.compile(r"^\d+/\d+$"),
}
_ENUMS: dict[str, tuple[str, ...]] = {"freshness": get_args(Freshness), "certainty": get_args(Certainty)}


class Provenance(TypedDict):
    game_version: str
    data_sha: str
    generated_at: str
    freshness: Freshness
    certainty: Certainty
    assumptions: list[str]
    registry_coverage: str


class ErrorPayload(TypedDict):
    error: ErrorInfo
    provenance: Provenance


def make_provenance(
    deps: Deps,
    *,
    game_version: str,
    data_sha: str,
    freshness: Freshness,
    certainty: Certainty,
    assumptions: Iterable[str],
) -> Provenance:
    notes = list(assumptions)
    if not deps.registry_path.is_file():
        notes.append(f"registre introuvable ({deps.registry_path.name}) : couverture inconnue")
    return {
        "game_version": game_version,
        "data_sha": data_sha,
        "generated_at": format_utc(deps.now()),
        "freshness": freshness,
        "certainty": certainty,
        "assumptions": notes,
        "registry_coverage": coverage(deps.registry_path),
    }


def validate_provenance(obj: object) -> list[str]:
    """Liste des écarts au schéma (vide si le bloc est valide)."""
    if not isinstance(obj, dict):
        return ["la provenance doit être un objet"]
    errors = [f"clé manquante : {k}" for k in PROVENANCE_KEYS if k not in obj]
    errors += [f"clé inattendue : {k}" for k in obj if k not in PROVENANCE_KEYS]
    for key, pattern in _PATTERNS.items():
        value = obj.get(key)
        if key in obj and not (isinstance(value, str) and pattern.match(value)):
            errors.append(f"{key} invalide : {value!r}")
    for key, allowed in _ENUMS.items():
        if key in obj and obj[key] not in allowed:
            errors.append(f"{key} invalide : {obj[key]!r} (attendu : {', '.join(allowed)})")
    if "assumptions" in obj:
        value = obj["assumptions"]
        if not (isinstance(value, list) and all(isinstance(a, str) for a in value)):
            errors.append("assumptions doit être une liste de chaînes")
    return errors


def format_provenance_line(p: Provenance) -> str:
    notes = " ; ".join(p["assumptions"]) if p["assumptions"] else "aucune"
    return (
        f"Provenance · version {p['game_version']} · données {p['data_sha']} · générée {p['generated_at']}"
        f" · fraîcheur {p['freshness']} · certitude {p['certainty']} · registre {p['registry_coverage']}"
        f" · hypothèses : {notes}"
    )


def min_certainty(values: Iterable[Certainty]) -> Certainty:
    return min(values, key=_CERTAINTY_ORDER.index, default="certain")


def local_provenance(deps: Deps, *, certainty: Certainty = "certain", assumptions: Iterable[str] = ()) -> Provenance:
    """Provenance des données présentes sur disque, sans contrôle d'intégrité ni réseau (fraîcheur du cache)."""
    game_version, sha = current_identity(deps.data_dir)
    fresh = freshness_for_version(deps, game_version, allow_network=False)
    return make_provenance(
        deps,
        game_version=game_version,
        data_sha=sha,
        freshness=fresh["freshness"],
        certainty=certainty,
        assumptions=[*fresh["assumptions"], *assumptions],
    )


def error_payload(deps: Deps, err: ForeverError) -> ErrorPayload:
    """Erreur + provenance calculée sans contrôle d'intégrité ni réseau."""
    return {"error": err.to_info(), "provenance": local_provenance(deps)}
