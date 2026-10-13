"""Cartes « À valider » publiées par le pont (P06b, décision 235) : `{id, kind, title, lines, buttons}`, rendues par
l'addon dans le panneau « À valider (n) ». Un bouton porte `action` (envoyée en `a=<action>` après un second clic de
confirmation), `explain` (question fixe passée par la file) ou `hide` (« Masquer », traité par l'addon seul).

Bloc A : carte de test de `forever bridge selftest --card`, écrite dans `<cache>/bridge/cards/selftest.json` (le pont
en marche réécrit les emplacements à chaque publication : il relit ce fichier lui-même), retirée après une action ou
au bout de `SELFTEST_TTL_S` secondes. Bloc B : cartes des attentes de `forever update`.

Décision 240 : une seule carte par branche ou par cause, textes en mots de joueur (le détail technique va dans
`detail`, transmis par « Expliquer »), empreinte `stamp` et bouton « Masquer » sur chaque carte publiée."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

SELFTEST_PREFIX = "selftest-"
SELFTEST_TTL_S = 900
_SELFTEST_FILE = "selftest.json"


def card_dir(cache_dir: Path) -> Path:
    return cache_dir / "bridge" / "cards"


def selftest_card(stamp: str) -> dict[str, Any]:
    """Carte de test : Valider et Refuser (second clic de confirmation), aucune commande derrière."""
    card_id = SELFTEST_PREFIX + stamp
    return {
        "id": card_id,
        "kind": "update",
        "title": "Carte de test du pont",
        "lines": [
            "Valider ou Refuser, puis Confirmer : le pont note l'action dans son journal sans rien lancer.",
            "Créée par forever bridge selftest --card.",
        ],
        "buttons": [
            {"key": "approve", "label": "Valider", "action": f"approve:{card_id}", "confirm": True},
            {"key": "reject", "label": "Refuser", "action": f"reject:{card_id}", "confirm": True},
        ],
    }


def write_selftest_card(cache_dir: Path, *, stamp: str, now: float) -> dict[str, Any]:
    """Écrit la carte de test (atomiquement) ; rend la carte."""
    card = selftest_card(stamp)
    path = card_dir(cache_dir) / _SELFTEST_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(json.dumps({"created": now, "card": card}, ensure_ascii=False, indent=1).encode("utf-8"))
    os.replace(tmp, path)
    return card


def read_selftest_cards(cache_dir: Path, *, now: float) -> list[dict[str, Any]]:
    """Carte de test en cours ([] si absente, illisible ou périmée)."""
    try:
        doc = json.loads((card_dir(cache_dir) / _SELFTEST_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    card = doc.get("card") if isinstance(doc, dict) else None
    created = doc.get("created") if isinstance(doc, dict) else None
    if not isinstance(card, dict) or not isinstance(created, int | float) or now - created > SELFTEST_TTL_S:
        return []
    if not str(card.get("id", "")).startswith(SELFTEST_PREFIX):
        return []
    return [card]


def clear_selftest_card(cache_dir: Path) -> None:
    (card_dir(cache_dir) / _SELFTEST_FILE).unlink(missing_ok=True)


class CardSource:
    """Cartes que le pont publie (bloc A : la carte de test) ; `done` retire la carte après une action."""

    def __init__(self, cache_dir: Path, now: Callable[[], float] | None = None, profile: Any = None) -> None:
        self.cache_dir = cache_dir
        self.now = now or time.time
        self.profile = profile  # profile_gap.ProfileWatch : propositions de mise à jour du profil (bloc C)

    def current(self) -> list[dict[str, Any]]:
        """Carte de test, puis cartes des attentes ouvertes de `forever update` ; chacune porte son empreinte et le
        bouton « Masquer » (décision 240)."""
        from forever.update import list_pending

        cards = read_selftest_cards(self.cache_dir, now=self.now()) + update_cards(list_pending(self.cache_dir))
        if self.profile is not None:
            cards += self.profile.cards()
        return [published(card) for card in cards]

    def done(self, card_id: str) -> None:
        if card_id.startswith(SELFTEST_PREFIX):
            clear_selftest_card(self.cache_dir)


NAMES_PER_LINE = 10  # PNJ nommés par ligne d'une carte (au-delà : « … et N autre(s) »)
# Textes des cartes en mots de joueur (décision 240) : ni commande, ni branche, ni CI ; le détail technique de
# l'attente va dans `detail`, que « Expliquer » transmet avec la carte.
TITLES = {
    "install_version": "Nouvelle version des données {version}",
    "install_revision": "Mise à jour des données {version}",
    "measures": "Mesures de tes combats ({version})",
    "network": "En attente du réseau ({version})",
    "hotfixes_unread": "Correctifs du serveur à lire ({version})",
    "addon_data": "Données d'addon : {addon}",
    "network_dbd": "Fichiers du jeu à télécharger ({version})",
    "column_names": "Changement de format des données du jeu ({version})",
    "pass_error": "La dernière mise à jour s'est arrêtée",
}
DEFAULT_TITLE = "Mise à jour en attente ({version})"
SELF_CLEARING = {
    "network": "En attente du réseau : la mise à jour reprendra seule.",
}
PC_FIX = "Une mise à jour attend une correction sur ton PC : ouvre une session Claude"
PC_LOOK = "À regarder sur ton PC : ouvre une session Claude"
WRITE_KINDS = ("install_version", "install_revision", "measures")
BLOCKED_WHY = {
    "ci": "La validation sur GitHub a échoué : rien n'a été installé.",
    "verify": "La vérification des données sur ton PC a échoué : rien n'a été installé.",
    "uv_sync": "La préparation de la vérification sur ton PC a échoué : rien n'a été installé.",
    "gh": "GitHub CLI n'est pas installé sur ton PC : rien n'a été installé.",
}
BLOCKED_DEFAULT = "La mise à jour s'est arrêtée en route : rien n'a été installé."
SESSION_WHY = {
    "column_names": "Le jeu a changé le format de certaines données : une correction est nécessaire.",
    "addon_data": "Les données de cet addon ont changé : elles sont à relire.",
    "network_dbd": "Des fichiers de description du jeu manquent pour lire cette version.",
}
APPROVED_LINE = "Validée : sera installée à la prochaine mise à jour."
UNDECIDED_LINE = "Une mise à jour des données attend ta décision."
OPEN = ("en_attente", "approuvée")
HIDE_BUTTON = {"key": "hide", "label": "Masquer", "hide": True}


def _names(items: list[str]) -> str:
    shown = ", ".join(items[:NAMES_PER_LINE])
    more = len(items) - NAMES_PER_LINE
    return shown + (f" ; … et {more} autre(s)" if more > 0 else "")


def _measure_lines(summary: Any) -> list[str]:
    doc = summary.get("measures") if isinstance(summary, dict) else None
    if not isinstance(doc, dict):
        return []
    npcs = doc.get("npcs") or {}
    lines = []
    for key, label in (("added", "PNJ ajoutés"), ("changed", "PNJ changés"), ("removed", "PNJ retirés")):
        names = [str(n.get("name")) for n in npcs.get(key) or [] if isinstance(n, dict)]
        if names:
            lines.append(f"{label} : {_names(names)}")
    fresh = [str(n.get("name")) for n in npcs.get("excluded") or [] if isinstance(n, dict) and n.get("new")]
    if fresh:
        lines.append(f"PNJ nouvellement écartés : {_names(fresh)}")
    levels = doc.get("hp_by_level") or {}
    if levels:
        shown = [
            f"niv. {lv} : {v.get('before')} → {v.get('after')}" if isinstance(v, dict) else f"niv. {lv} : {v}"
            for lv, v in sorted(levels.items(), key=lambda kv: int(kv[0]))
        ]
        lines.append(f"PV par niveau : {_names(shown)}")
    builds = doc.get("builds") or {}
    if builds.get("replayed"):
        changed = [f"{c.get('engine')} {c.get('case')}" for c in builds.get("changed") or [] if isinstance(c, dict)]
        lines.append(f"Builds changés après rejeu : {', '.join(changed)}" if changed else "Builds : aucun changement")
    elif builds:
        lines.append("Builds : pas encore recalculés")
    return lines


def _day(stamp: Any) -> str:
    """« 2026-10-11T05:07:29Z » → « 11/10/2026 » (texte rendu tel quel s'il n'a pas cette forme)."""
    text = str(stamp)
    year, month, day = text[:4], text[5:7], text[8:10]
    if len(text) >= 10 and (year + month + day).isdigit():
        return f"{day}/{month}/{year}"
    return text


def _addon_lines(entry: dict[str, Any]) -> list[str]:
    """Carte « Données d'addon » (décision 244) : ce qui a changé dans l'addon, les données du dépôt qui en dépendent
    et pourquoi une session est nécessaire."""
    addon, version, before = entry.get("addon"), entry.get("version"), entry.get("previous_version")
    if entry.get("first"):
        lines = [f"Aucun relevé précédent de {addon} sur ce PC (version {version}) : relecture complète."]
    elif before and before != version:
        lines = [f"{addon} : {before} → {version}."]
    else:
        lines = [f"{addon} {version} : même version, contenu changé."]
    raw = entry.get("files")
    files: dict[str, Any] = raw if isinstance(raw, dict) else {}
    parts = [
        f"{len(files.get(key) or [])} {label}"
        for key, label in (("added", "ajouté(s)"), ("modified", "modifié(s)"), ("removed", "retiré(s)"))
        if files.get(key)
    ]
    if parts:
        lines.append(f"Fichiers : {parts[0].replace(' ', ' fichier(s) ', 1)}{''.join(', ' + x for x in parts[1:])}.")
    uses = [str(u) for u in entry.get("uses") or []]
    if uses:
        lines.append(f"Nos données qui en dépendent : {', '.join(uses)}.")
    lines.append("Une session est nécessaire : relire l'addon et comparer avec nos données avant de les mettre à jour.")
    lines.append(PC_LOOK)
    return lines


def card_lines(entry: dict[str, Any]) -> list[str]:
    """Lignes d'une carte, rédigées par le pont depuis les champs de l'attente, en mots de joueur."""
    from forever.update import summary_text

    kind = entry.get("kind")
    if kind in SELF_CLEARING:
        return [SELF_CLEARING[str(kind)]]
    if kind == "hotfixes_unread":
        return [f"Correctifs du serveur à lire jusqu'au {_day(entry.get('until'))}."]
    if kind == "pass_error":
        return [PC_FIX]
    if entry.get("action") == "bloqué" and kind in WRITE_KINDS:
        return [BLOCKED_WHY.get(str(entry.get("blocked_by")), BLOCKED_DEFAULT), PC_FIX]
    if kind == "addon_data":
        return _addon_lines(entry)
    if kind in SESSION_WHY:
        return [SESSION_WHY[str(kind)], PC_LOOK]
    if entry.get("action") == "bloqué":
        return [BLOCKED_DEFAULT, PC_FIX]
    lines: list[str] = []
    if kind in ("install_version", "install_revision"):
        lines.append(f"version {entry.get('version')}, révision {entry.get('revision')}")
        text = summary_text(entry.get("summary"))
        lines += [part for part in text.split(" ; ") if part] if text else []
    elif kind == "measures":
        lines += _measure_lines(entry.get("summary"))
    return lines or [UNDECIDED_LINE]


def card_title(entry: dict[str, Any]) -> str:
    title = TITLES.get(str(entry.get("kind")), DEFAULT_TITLE)
    return title.format(version=entry.get("version"), addon=entry.get("addon"))


def _detail(entry: dict[str, Any]) -> str:
    """Détail technique de l'attente (raisons, commandes), transmis par « Expliquer », jamais affiché."""
    parts = [str(r) for r in entry.get("reasons") or []] + [str(c) for c in entry.get("commands") or []]
    return " ; ".join(parts)


def _group(entry: dict[str, Any]) -> tuple[Any, ...] | None:
    """Clé des attentes montrées par une seule carte (décision 240) : écritures bloquées de la même branche
    `data/<version>-r<N>`, ou attentes non approuvables de même nature, même version et même première raison ;
    None : carte à part (une attente approuvable garde toujours sa propre décision)."""
    from forever.bridge.actions import approvable

    if approvable(entry):
        return None
    if entry.get("action") == "bloqué" and entry.get("kind") in WRITE_KINDS:
        return ("branche", entry.get("version"), entry.get("revision"))
    reasons = entry.get("reasons") or []
    return ("cause", entry.get("kind"), entry.get("version"), str(reasons[0]) if reasons else None)


def _merged(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Une attente par groupe, à la place de la première du groupe : la plus récente (`created_at`)."""
    latest: dict[tuple[Any, ...], dict[str, Any]] = {}
    for entry in entries:
        key = _group(entry)
        if key is None:
            continue
        if key not in latest or str(entry.get("created_at") or "") >= str(latest[key].get("created_at") or ""):
            latest[key] = entry
    shown: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for entry in entries:
        key = _group(entry)
        if key is None:
            shown.append(entry)
        elif key not in seen:
            seen.add(key)
            shown.append(latest[key])
    return shown


def update_cards(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cartes des attentes ouvertes (`en_attente`, `approuvée`), dans l'ordre reçu, une seule par branche ou par
    cause ; `count` : « approvable » (Valider, Refuser) ou « waiting », compté par l'addon dans la ligne d'état."""
    from forever.bridge.actions import approvable

    cards = []
    for entry in _merged([e for e in entries if e.get("state") in OPEN]):
        card_id = str(entry.get("id"))
        lines = card_lines(entry)
        if entry.get("state") == "approuvée":
            lines.append(APPROVED_LINE)
        buttons: list[dict[str, Any]] = []
        if approvable(entry):
            buttons += [
                {"key": "approve", "label": "Valider", "action": f"approve:{card_id}", "confirm": True},
                {"key": "reject", "label": "Refuser", "action": f"reject:{card_id}", "confirm": True},
            ]
        buttons.append({"key": "explain", "label": "Expliquer", "explain": True})
        cards.append(
            {
                "id": card_id,
                "kind": "update",
                "title": card_title(entry),
                "lines": lines,
                "detail": _detail(entry),
                "count": "approvable" if approvable(entry) else "waiting",
                "buttons": buttons,
            }
        )
    return cards


def card_stamp(card: dict[str, Any]) -> str:
    """Empreinte d'une carte (identifiant, titre, lignes, détail, boutons) : une carte masquée revient quand elle
    change."""
    body = {k: card.get(k) for k in ("id", "title", "lines", "detail", "buttons")}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def published(card: dict[str, Any]) -> dict[str, Any]:
    """Carte telle que le pont la publie : empreinte et bouton « Masquer » (le masquage est gardé par l'addon)."""
    buttons = [b for b in card.get("buttons") or [] if not (isinstance(b, dict) and b.get("key") == "hide")]
    stamp = card_stamp({**card, "buttons": buttons})
    return {**card, "stamp": stamp, "buttons": [*buttons, dict(HIDE_BUTTON)]}
