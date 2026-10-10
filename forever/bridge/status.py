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
    """Version, fraîcheur et âge, couverture du registre, intégrité, attentes (nombre et trois premiers libellés ;
    P06b : `approvable`, attentes que Valider et Refuser traitent, et `waiting`, les autres attentes ouvertes),
    passage en cours et dernier passage (`update`), état de l'addon installé (`addon`, clé de ADDON_LINES, et ses
    fichiers à remplacer) ; `line` : la ligne affichée en tête de la fenêtre."""
    payload: dict[str, Any] = {
        "version": None,
        "freshness": "unknown",
        "age_hours": None,
        "coverage": None,
        "integrity_ok": None,
        "pending": 0,
        "pending_labels": [],
        "approvable": 0,
        "waiting": 0,
        "running": False,
        "update": {"running": False, "step": None, "last": None},
        "pass_error": False,
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
        from forever.bridge.actions import approvable
        from forever.update import update_summary

        summary = update_summary(deps.cache_dir, deps.now())
        pending = summary["pending"]
        payload["pending"] = len(pending)
        payload["pending_labels"] = [str(p.get("summary") or p.get("kind") or p.get("id")) for p in pending[:_LABELS]]
        payload["approvable"] = sum(1 for p in pending if approvable(p))
        payload["waiting"] = len(pending) - payload["approvable"]
        payload["running"] = bool(summary["running"])
        payload["pass_error"] = any(p.get("kind") == "pass_error" for p in pending)
        last = summary.get("last")
        payload["update"] = {
            "running": bool(summary["running"]),
            "step": summary.get("running_step"),
            "activity": summary.get("running_activity"),
            "minutes": summary.get("running_minutes"),
            "detail": summary.get("running_detail"),
            "last": None
            if not last or not last.get("finished_at")
            else {
                "finished_at": last.get("finished_at"),
                "written": len(last.get("written") or []),
                "approvable": payload["approvable"],
            },
        }
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
    """« Données <version> · client <version> · <fraîcheur> · <n> à valider · <m> en attente » (P06b, décision 235) :
    client toujours affiché quand il est connu ; plus récent que les données : « client <version> : mise à jour en
    attente » au lieu de la fraîcheur (« à jour » serait trompeur) ; « à valider » ne compte que les attentes
    approuvables (Valider, Refuser), « en attente » les autres attentes ouvertes."""
    if not payload.get("version"):
        return "Données : état illisible (lancer uv run forever status)"
    client = payload.get("client")
    parts = [f"Données {payload['version']}"]
    if client and _newer(client, payload["version"]):
        parts.append(f"client {client} : mise à jour en attente")
    else:
        if client:
            parts.append(f"client {client}")
        parts.append(FRESHNESS_FR.get(str(payload.get("freshness")), "fraîcheur inconnue"))
    if payload.get("integrity_ok") is False:
        parts.append("données altérées")
    if payload.get("running"):
        update = payload.get("update") or {}
        step, activity, minutes = update.get("step"), update.get("activity"), update.get("minutes")
        inside = str(step) if step else ""
        if activity:
            inside += f" : {activity}" if inside else str(activity)
        if minutes is not None:
            inside += f", {minutes} min"
        parts.append(f"mise à jour en cours ({inside})" if inside else "mise à jour en cours")
    if payload.get("pass_error"):
        parts.append("dernier passage en erreur (voir À valider)")
    approvable = int(payload.get("approvable") or 0)
    waiting = int(payload.get("waiting") or 0)
    if approvable:
        parts.append(f"{approvable} à valider")
    if waiting:
        parts.append(f"{waiting} en attente")
    addon = ADDON_LINES.get(str(payload.get("addon")))
    if addon:
        parts.append(addon)
    return " · ".join(parts)
