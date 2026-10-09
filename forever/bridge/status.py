"""État des données montré dans la fenêtre du jeu (P06a, bloc D) : version, fraîcheur, attentes de `forever update`,
lus par le pont dans son propre processus (jamais par le modèle), sans réseau ; ne lève jamais : le pont publie même
quand les données sont illisibles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.config import Deps

FRESHNESS_FR = {"fresh": "à jour", "stale": "en retard", "silent": "incertaine", "unknown": "inconnue"}
_LABELS = 3


def status_payload(deps: Deps) -> dict[str, Any]:
    """Version, fraîcheur et âge, couverture du registre, intégrité, attentes (nombre et trois premiers libellés),
    passage en cours ; `line` : la ligne affichée en tête de la fenêtre."""
    payload: dict[str, Any] = {
        "version": None,
        "freshness": "unknown",
        "age_hours": None,
        "coverage": None,
        "integrity_ok": None,
        "pending": 0,
        "pending_labels": [],
        "running": False,
    }
    try:
        from forever.status import status_report

        report = status_report(deps, allow_network=False)
        found = report["integrity"]["manifest_found"]
        payload.update(
            version=report["local_version"] if found else None,  # sans manifeste : aucune donnée installée
            freshness=report["freshness"]["freshness"],
            age_hours=report["freshness"]["age_hours"],
            coverage=report["registry_coverage"],
            integrity_ok=report["integrity"]["ok"],
        )
    except Exception:  # noqa: BLE001 : l'état affiché ne doit jamais arrêter le pont
        payload["version"] = None
    try:
        from forever.update import update_summary

        summary = update_summary(deps.cache_dir, deps.now())
        pending = summary["pending"]
        payload["pending"] = len(pending)
        payload["pending_labels"] = [str(p.get("summary") or p.get("kind") or p.get("id")) for p in pending[:_LABELS]]
        payload["running"] = bool(summary["running"])
    except Exception:  # noqa: BLE001 : attentes inconnues, l'état des données reste affiché
        payload["pending_labels"] = []
    payload["line"] = status_line(payload)
    return payload


def status_line(payload: Mapping[str, Any]) -> str:
    """« Données <version> · <fraîcheur> · <n> attente(s) : forever update status »."""
    if not payload.get("version"):
        return "Données : état illisible (lancer uv run forever status)"
    parts = [f"Données {payload['version']}", FRESHNESS_FR.get(str(payload.get("freshness")), "fraîcheur inconnue")]
    if payload.get("integrity_ok") is False:
        parts.append("données altérées")
    if payload.get("running"):
        parts.append("mise à jour en cours")
    pending = int(payload.get("pending") or 0)
    if pending:
        parts.append(f"{pending} attente{'s' if pending > 1 else ''} : forever update status")
    return " · ".join(parts)
