"""Cartes « À valider » publiées par le pont (P06b, décision 235) : `{id, kind, title, lines, buttons}`, rendues par
l'addon dans le panneau « À valider (n) ». Un bouton porte `action` (envoyée en `a=<action>` après un second clic de
confirmation) ou `explain` (question fixe passée par la file).

Bloc A : carte de test de `forever bridge selftest --card`, écrite dans `<cache>/bridge/cards/selftest.json` (le pont
en marche réécrit les emplacements à chaque publication : il relit ce fichier lui-même), retirée après une action ou
au bout de `SELFTEST_TTL_S` secondes. Bloc B : cartes des attentes de `forever update`."""

from __future__ import annotations

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
        """Carte de test, puis cartes des attentes ouvertes de `forever update`."""
        from forever.update import list_pending

        return read_selftest_cards(self.cache_dir, now=self.now()) + update_cards(list_pending(self.cache_dir))

    def done(self, card_id: str) -> None:
        if card_id.startswith(SELFTEST_PREFIX):
            clear_selftest_card(self.cache_dir)


NAMES_PER_LINE = 10  # PNJ nommés par ligne d'une carte (au-delà : « … et N autre(s) »)
TITLES = {
    "install_version": "Nouvelle version des données {version}",
    "install_revision": "Nouvelle révision des données {version}",
    "measures": "Mesures des journaux ({version})",
    "network": "Attente réseau ({version})",
    "hotfixes_unread": "Correctifs du serveur à lire ({version})",
    "addon_data": "Données d'addon : {addon}",
    "network_dbd": "Dispositions des tables à télécharger ({version})",
    "column_names": "Noms de colonnes à traiter ({version})",
}
SELF_CLEARING = {
    "network": "attente réseau : se lève seule au prochain passage réussi",
}
OPEN = ("en_attente", "approuvée")


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
        lines.append(f"Builds : non rejoués ({builds.get('reason')})")
    return lines


def card_lines(entry: dict[str, Any]) -> list[str]:
    """Lignes d'une carte, rédigées par le pont depuis les champs de l'attente."""
    from forever.update import summary_text

    kind = entry.get("kind")
    commands = [str(c) for c in entry.get("commands") or []]
    if kind in SELF_CLEARING:
        return [SELF_CLEARING[str(kind)]]
    if kind == "hotfixes_unread":
        return [f"correctifs du serveur à lire jusqu'au {entry.get('until')}"]
    lines: list[str] = []
    if kind in ("install_version", "install_revision"):
        lines.append(f"version {entry.get('version')}, révision {entry.get('revision')}")
        text = summary_text(entry.get("summary"))
        lines += [part for part in text.split(" ; ") if part] if text else []
    elif kind == "measures":
        lines += _measure_lines(entry.get("summary"))
    if entry.get("action") == "bloqué" or kind in ("column_names", "addon_data", "network_dbd"):
        reasons = [str(r) for r in entry.get("reasons") or []]
        if reasons and not lines:
            lines.append(reasons[0])
        lines.append(f"à traiter sur le PC : {commands[0] if commands else 'forever update status'}")
    if not lines:
        lines = [str(r) for r in entry.get("reasons") or []][:1] or [str(entry.get("id"))]
    return lines


def update_cards(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cartes des attentes ouvertes (`en_attente`, `approuvée`), dans l'ordre reçu."""
    from forever.bridge.actions import approvable

    cards = []
    for entry in entries:
        if entry.get("state") not in OPEN:
            continue
        card_id = str(entry.get("id"))
        lines = card_lines(entry)
        if entry.get("state") == "approuvée":
            lines.append("approuvée : prise au prochain passage de forever update")
        buttons: list[dict[str, Any]] = []
        if approvable(entry):
            buttons += [
                {"key": "approve", "label": "Valider", "action": f"approve:{card_id}", "confirm": True},
                {"key": "reject", "label": "Refuser", "action": f"reject:{card_id}", "confirm": True},
            ]
        buttons.append({"key": "explain", "label": "Expliquer", "explain": True})
        title = TITLES.get(str(entry.get("kind")), "Attente de forever update ({version})")
        cards.append(
            {
                "id": card_id,
                "kind": "update",
                "title": title.format(version=entry.get("version"), addon=entry.get("addon")),
                "lines": lines,
                "buttons": buttons,
            }
        )
    return cards
