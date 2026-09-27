"""Explication d'une mécanique : entrée du registre, paramètres de la version courante, implémentation, provenance.

La formule du registre est symbolique ; les valeurs affichées viennent des données de la version (`mechanics.json`,
règles de `leveling.json.combat_rules`), avec leur certitude."""

from __future__ import annotations

from typing import Any, TypedDict, cast, get_args

from forever.config import Deps
from forever.errors import DataSchemaError
from forever.freshness import freshness_for_version
from forever.gamedata import COMBAT_RULE_MECHANICS, LEVELING_FILE, MECHANICS_FILE
from forever.provenance import Certainty, Provenance, make_provenance, min_certainty
from forever.registry import ENGINE_DIR, RegistryError, find_entry, implementations, load
from forever.store import VersionData, load_version

ABSENT_NOTE = "mécanique non modélisée dans forever-core : aucun calcul ne s'appuie encore sur elle"
_CERTAINTIES: tuple[str, ...] = get_args(Certainty)


class MechanicParameter(TypedDict):
    key: str
    value: object
    certainty: Certainty
    source: str


class MechanicExplanation(TypedDict):
    id: str
    category: str
    description: str
    forever: str
    status: str
    certainty: Certainty
    formula: str | None
    note: str | None
    parameters: list[MechanicParameter]
    implementations: list[str]
    sources: list[str]
    tests: list[str]
    proofs: list[dict[str, Any]]  # preuves de journal du registre (T04)
    provenance: Provenance


def _certainty(value: object) -> Certainty:
    return cast(Certainty, value) if value in _CERTAINTIES else "suppose"


def _parameters(version: VersionData, mechanic_id: str) -> list[MechanicParameter]:
    """Entrées de `mechanics.json` étiquetées par l'identifiant, puis règles de combat associées."""
    try:
        values = version.read_json(MECHANICS_FILE).get("values")
        rules = version.read_json(LEVELING_FILE).get("combat_rules")
    except (OSError, ValueError, AttributeError) as exc:
        raise DataSchemaError(f"Données de la version {version.game_version} illisibles ({exc}).") from exc
    if not isinstance(values, dict) or not isinstance(rules, dict):
        raise DataSchemaError(f"{MECHANICS_FILE} ou {LEVELING_FILE} : structure inattendue.")
    params: list[MechanicParameter] = [
        {
            "key": key,
            "value": entry.get("value"),
            "certainty": _certainty(entry.get("certainty")),
            "source": str(entry.get("source", "")),
        }
        for key, entry in values.items()
        if isinstance(entry, dict) and entry.get("registry") == mechanic_id
    ]
    files = version.sources.get("files", {})
    meta: Any = files.get(LEVELING_FILE, {}) if isinstance(files, dict) else None
    field_certainty: Any = meta.get("field_certainty", {}) if isinstance(meta, dict) else None
    field_notes: Any = meta.get("field_notes", {}) if isinstance(meta, dict) else None
    if not isinstance(meta, dict) or not isinstance(field_certainty, dict) or not isinstance(field_notes, dict):
        raise DataSchemaError(f"sources.json : bloc « {LEVELING_FILE} » absent ou mal formé.")
    for rule in COMBAT_RULE_MECHANICS.get(mechanic_id, ()):
        name = f"combat_rules.{rule}"
        params.append(
            {
                "key": name,
                "value": rules.get(rule),
                "certainty": _certainty(field_certainty.get(name, meta.get("certainty"))),
                "source": field_notes.get(name, str(meta.get("source", LEVELING_FILE))),
            }
        )
    return params


def explain_mechanic(deps: Deps, mechanic_id: str) -> MechanicExplanation:
    """Explication d'une mécanique du registre ; lève UnknownMechanicError, DataSchemaError ou DataIntegrityError."""
    version = load_version(deps)  # intégrité d'abord, comme les autres consultations
    try:
        mechanics = load(deps.registry_path)
    except RegistryError as exc:
        raise DataSchemaError(
            f"Registre des mécaniques inutilisable ({exc}).", "restaurer docs/MECHANICS_REGISTRY.yaml depuis git"
        ) from exc
    entry = find_entry(mechanics, mechanic_id)
    params = _parameters(version, entry.id)
    certainty = _certainty(entry.certainty)
    fresh = freshness_for_version(deps, version.game_version, allow_network=False)
    notes = [*fresh["assumptions"]]
    if entry.status == "absent":
        notes.append(ABSENT_NOTE)
    provenance = make_provenance(
        deps,
        game_version=version.game_version,
        data_sha=version.data_sha,
        freshness=fresh["freshness"],
        certainty=min_certainty([certainty, *(p["certainty"] for p in params)]),
        assumptions=notes,
    )
    return {
        "id": entry.id,
        "category": entry.category,
        "description": entry.description,
        "forever": entry.forever,
        "status": entry.status,
        "certainty": certainty,
        "formula": entry.formula,
        "note": entry.note,
        "parameters": params,
        "implementations": implementations([ENGINE_DIR], ENGINE_DIR.parent.parent).get(entry.id, []),
        "sources": list(entry.sources),
        "tests": list(entry.tests),
        "proofs": [dict(p) for p in entry.proofs],
        "provenance": provenance,
    }
