"""État des données montré dans la fenêtre du jeu (P06a, bloc D) : version, fraîcheur, attentes de `forever update`,
lus par le pont dans son propre processus (jamais par le modèle), sans réseau ; ne lève jamais : le pont publie même
quand les données sont illisibles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.config import Deps

FRESHNESS_FR = {"fresh": "à jour", "stale": "en retard", "silent": "incertaine", "unknown": "inconnue"}
# État de l'addon ForeverBridge installé (sonde en jeu F) : clé `addon` du bloc d'état.
ADDON_LINES = {
    "a_reinstaller": "addon à réinstaller : forever bridge install, jeu fermé",
    "en_attente": "addon mis à jour à la prochaine fermeture du jeu",
    "mis_a_jour": "addon mis à jour par le pont pendant que le jeu était fermé",
}
_LABELS = 3


def status_payload(deps: Deps, *, addon: str | None = None, addon_files: list[str] | None = None) -> dict[str, Any]:
    """Version, fraîcheur et âge, couverture du registre, intégrité, attentes (nombre et trois premiers libellés),
    passage en cours, état de l'addon installé (`addon`, clé de ADDON_LINES, et ses fichiers à remplacer) ; `line` :
    la ligne affichée en tête de la fenêtre."""
    payload: dict[str, Any] = {
        "version": None,
        "freshness": "unknown",
        "age_hours": None,
        "coverage": None,
        "integrity_ok": None,
        "pending": 0,
        "pending_labels": [],
        "running": False,
        "client": None,
        "addon": addon,
        "addon_files": list(addon_files or []),
    }
    try:
        from forever.pipeline.client_builds import read_build_info

        info = read_build_info(deps.wow_dir) if deps.wow_dir else None
        payload["client"] = info.build if info else None
    except Exception:  # noqa: BLE001 : version du client inconnue, rien d'autre ne change
        payload["client"] = None
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


def _newer(client: Any, data: Any) -> bool:
    """Vrai si la version du client est plus récente que celle des données (comparaison par nombres)."""
    try:
        return tuple(int(x) for x in str(client).split(".")) > tuple(int(x) for x in str(data).split("."))
    except ValueError:
        return False


def status_line(payload: Mapping[str, Any]) -> str:
    """« Données <version> · <fraîcheur> · <n> mise(s) à jour à valider sur le PC » ; client plus récent que les
    données : « client <version> : mise à jour en attente » au lieu de la fraîcheur (« à jour » serait trompeur)."""
    if not payload.get("version"):
        return "Données : état illisible (lancer uv run forever status)"
    client = payload.get("client")
    if client and _newer(client, payload["version"]):
        state = f"client {client} : mise à jour en attente"
    else:
        state = FRESHNESS_FR.get(str(payload.get("freshness")), "fraîcheur inconnue")
    parts = [f"Données {payload['version']}", state]
    if payload.get("integrity_ok") is False:
        parts.append("données altérées")
    if payload.get("running"):
        parts.append("mise à jour en cours")
    pending = int(payload.get("pending") or 0)
    if pending:
        plural = "s" if pending > 1 else ""
        parts.append(f"{pending} mise{plural} à jour à valider sur le PC")
    addon = ADDON_LINES.get(str(payload.get("addon")))
    if addon:
        parts.append(addon)
    return " · ".join(parts)
