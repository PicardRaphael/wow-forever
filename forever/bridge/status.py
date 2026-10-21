"""État des données montré dans la fenêtre du jeu (P06a, bloc D) : version, fraîcheur, attentes de `forever update`,
lus par le pont dans son propre processus (jamais par le modèle), sans réseau ; ne lève jamais : le pont publie même
quand les données sont illisibles.

Décision 240 : avancement d'une mise à jour en mots de joueur (étape, heure de début en secondes depuis l'époque,
phrase de fin), compteurs « à valider » et « en attente » comptés par carte (une carte par branche ou par cause), et
ligne coupée en `line_head` et `line_tail` pour que l'addon y place lui-même l'avancement et les compteurs des cartes
qu'il montre (les cartes masquées n'y comptent pas)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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

# Étape d'une mise à jour en mots de joueur : mots-clés de la dernière ligne du journal du passage d'abord (activité
# réelle), puis nom de l'étape.
_DETAIL_STAGES = (
    ("fusion", "installation des données"),
    ("ci attendue", "attente de la validation sur GitHub"),
    ("attente de la ci", "attente de la validation sur GitHub"),
    ("commit et poussée", "envoi sur GitHub"),
    ("uv sync", "préparation de la vérification"),
    ("synchronisation de l'environnement", "préparation de la vérification"),
    ("verify", "vérification des données"),
    ("rejeu", "recalcul des builds"),
    ("copie de", "préparation des données"),
)
_STEP_STAGES = {
    "verrou": "préparation",
    "archivage": "préparation",
    "clone": "préparation",
    "jeu": "recherche d'une nouvelle version du jeu",
    "nouvelle_version": "téléchargement de la nouvelle version",
    "correctifs": "lecture des correctifs du serveur",
    "journaux": "mesures de tes combats",
    "addons": "lecture des addons",
    "guides": "mise à jour des guides de Polestar",
    "simulateurs": "mise à jour de wowsims/forever",
    "fin": "finalisation",
}
DEFAULT_STAGE = "travail en cours"
OUTCOME_ERROR = "en erreur, voir À valider"
OUTCOME_WAITING = "une validation t'attend dans À valider"
OUTCOME_WRITTEN = "données installées"
OUTCOME_NOTHING = "rien de nouveau"


def update_stage(step: Any, detail: Any = None) -> str:
    """Étape d'une mise à jour en mots simples (« vérification des données », « attente de la validation sur
    GitHub »…), d'après la dernière ligne du journal du passage puis le nom de l'étape."""
    low = str(detail or "").lower()
    for key, stage in _DETAIL_STAGES:
        if key in low:
            return stage
    return _STEP_STAGES.get(str(step), DEFAULT_STAGE)


def _seconds(start: Any, end: Any) -> int | None:
    from forever.timefmt import parse_utc

    try:
        return max(0, int((parse_utc(str(end)) - parse_utc(str(start))).total_seconds()))
    except (TypeError, ValueError):
        return None


def duration_text(seconds: int | None) -> str:
    """« 45 s » sous une minute, sinon « 4 min » (minutes entières, arrondies)."""
    if seconds is None:
        return ""
    if seconds < 60:
        return f"{seconds} s"
    return f"{round(seconds / 60)} min"


def pass_outcome(last: Mapping[str, Any], pending: Sequence[Mapping[str, Any]] = ()) -> str:
    """Phrase de fin d'un passage : « Mise à jour terminée en 4 min : rien de nouveau », « … : données installées »,
    « … : en erreur, voir À valider » ou « … : une validation t'attend dans À valider »."""
    steps = [s for s in last.get("steps") or [] if isinstance(s, Mapping)]
    verdicts = [v for v in last.get("verdicts") or [] if isinstance(v, Mapping)]
    if last.get("written"):
        outcome = OUTCOME_WRITTEN
    elif (
        any(s.get("status") in ("erreur", "arrêt") for s in steps)
        or any(v.get("action") == "bloqué" for v in verdicts)
        or any(p.get("kind") == "pass_error" for p in pending)
    ):
        outcome = OUTCOME_ERROR
    elif any(v.get("action") == "attente" for v in verdicts):
        outcome = OUTCOME_WAITING
    else:
        outcome = OUTCOME_NOTHING
    took = duration_text(_seconds(last.get("started_at"), last.get("finished_at")))
    return f"Mise à jour terminée en {took} : {outcome}" if took else f"Mise à jour terminée : {outcome}"


def _epoch(stamp: Any) -> int | None:
    from forever.timefmt import parse_utc

    try:
        return int(parse_utc(str(stamp)).timestamp()) if stamp else None
    except ValueError:
        return None


def status_payload(deps: Deps, *, addon: str | None = None, addon_files: list[str] | None = None) -> dict[str, Any]:
    """Version, fraîcheur et âge, couverture du registre, intégrité, attentes (nombre et trois premiers libellés ;
    P06b : `approvable`, cartes que Valider et Refuser traitent, et `waiting`, les autres cartes des attentes
    ouvertes), passage en cours et dernier passage (`update` : étape en mots simples, début, phrase de fin), état de
    l'addon installé (`addon`, clé de ADDON_LINES, et ses fichiers à remplacer) ; `line` : la ligne affichée en tête
    de la fenêtre, `line_head` et `line_tail` : la même sans l'avancement ni les compteurs (placés par l'addon)."""
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
        from forever.bridge.cards import update_cards
        from forever.update import list_pending, update_summary

        summary = update_summary(deps.cache_dir, deps.now())
        pending = summary["pending"]
        cards = update_cards(list_pending(deps.cache_dir))
        payload["pending"] = len(pending)
        payload["pending_labels"] = [str(p.get("summary") or p.get("kind") or p.get("id")) for p in pending[:_LABELS]]
        payload["approvable"] = sum(1 for c in cards if c.get("count") == "approvable")
        payload["waiting"] = len(cards) - payload["approvable"]
        payload["running"] = bool(summary["running"])
        payload["pass_error"] = any(p.get("kind") == "pass_error" for p in pending)
        last = summary.get("last")
        payload["update"] = {
            "running": bool(summary["running"]),
            "step": summary.get("running_step"),
            "activity": summary.get("running_activity"),
            "minutes": summary.get("running_minutes"),
            "detail": summary.get("running_detail"),
            "stage": update_stage(summary.get("running_step"), summary.get("running_detail"))
            if summary["running"]
            else None,
            "started": _epoch(summary.get("running_started_at")) if summary["running"] else None,
            "last": None
            if not last or not last.get("finished_at")
            else {
                "finished_at": last.get("finished_at"),
                "written": len(last.get("written") or []),
                "approvable": payload["approvable"],
                "text": pass_outcome(last, pending),
            },
        }
    except Exception:  # noqa: BLE001 : attentes inconnues, l'état des données reste affiché
        payload["pending_labels"] = []
    payload["line"] = status_line(payload)
    payload["line_head"], payload["line_tail"] = line_parts(payload)
    return payload


def _newer(client: Any, data: Any) -> bool:
    """Vrai si la version du client est plus récente que celle des données (comparaison par nombres)."""
    try:
        return tuple(int(x) for x in str(client).split(".")) > tuple(int(x) for x in str(data).split("."))
    except ValueError:
        return False


def line_parts(payload: Mapping[str, Any]) -> tuple[str, str]:
    """(tête, fin) de la ligne d'état sans l'avancement ni les compteurs : « Données <version> · client <version> ·
    <fraîcheur> » (et l'erreur du dernier passage), puis l'état de l'addon installé."""
    if not payload.get("version"):
        return "Données : état illisible (lancer uv run forever status)", ""
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
    if payload.get("pass_error"):
        parts.append("dernière mise à jour en erreur (voir À valider)")
    return " · ".join(parts), ADDON_LINES.get(str(payload.get("addon")), "")


def status_line(payload: Mapping[str, Any]) -> str:
    """« Données <version> · client <version> · <fraîcheur> · <n> à valider · <m> en attente » (P06b, décision 235) :
    client toujours affiché quand il est connu ; plus récent que les données : « client <version> : mise à jour en
    attente » au lieu de la fraîcheur (« à jour » serait trompeur) ; « à valider » ne compte que les cartes
    approuvables (Valider, Refuser), « en attente » les autres ; mise à jour en cours : son étape en mots simples."""
    head, tail = line_parts(payload)
    if not payload.get("version"):
        return head
    parts = [head]
    if payload.get("running"):
        update = payload.get("update") or {}
        stage = update.get("stage") or update_stage(update.get("step"), update.get("detail") or update.get("activity"))
        minutes = update.get("minutes")
        inside = stage + (f", {minutes} min" if minutes is not None else "")
        parts.append(f"mise à jour en cours ({inside})")
    approvable = int(payload.get("approvable") or 0)
    waiting = int(payload.get("waiting") or 0)
    if approvable:
        parts.append(f"{approvable} à valider")
    if waiting:
        parts.append(f"{waiting} en attente")
    if tail:
        parts.append(tail)
    return " · ".join(parts)
