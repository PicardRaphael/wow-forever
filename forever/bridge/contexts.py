"""Contextes réels gardés par le pont (P06b, bloc A, choix 13 du plan) : l'événement `message` du journal porte le
contexte complet envoyé par le jeu, `simc_export` l'export SimulationCraft collé (anonymisé). `forever bridge contexts
last` montre le dernier contexte relié (équipement complet, liens) ; `forever bridge contexts export <dossier>` écrit
chaque contexte distinct au format des fixtures (`clé=valeur`, fins de ligne LF) et chaque export, pour le banc
d'essai. Le journal est dans le cache de l'utilisateur, jamais dans le dépôt."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forever.bridge.items import LINK_KINDS, parse_gear, parse_links
from forever.bridge.journal import Journal
from forever.bridge.record import context_lines

DAYS = 3660  # tout le journal


def _stamp(at: str) -> str:
    return "".join(c for c in str(at) if c.isalnum())


def _contexts(journal: Journal) -> list[dict[str, Any]]:
    return [e for e in journal.recent("message", days=DAYS) if isinstance(e.get("context"), dict) and e["context"]]


def last_context(journal: Journal) -> dict[str, Any] | None:
    """Dernier événement `message` qui porte un contexte."""
    found = _contexts(journal)
    return found[-1] if found else None


def describe_context(context: Mapping[str, str]) -> list[str]:
    """Lignes lisibles : `clé=valeur`, équipement pièce par pièce (champs du lien), liens et leur infobulle."""
    lines = []
    for line in context_lines({k: v for k, v in context.items() if k not in ("gear", "links")}).split("\n"):
        if line:
            lines.append(f"  {line}")
    if context.get("gear"):
        pieces, bad = parse_gear(context["gear"])
        lines.append(f"  équipement ({len(pieces)} pièce(s)) :")
        for piece in pieces:
            item = piece.item
            extras = [f"objet {item.item}"]
            if item.enchant:
                extras.append(f"enchantement {item.enchant}")
            if item.gems:
                extras.append("gemmes " + "/".join(str(g) for g in item.gems))
            if item.suffix:
                extras.append(f"suffixe aléatoire {item.suffix}")
            if item.unique:
                extras.append(f"identifiant unique {item.unique}")
            lines.append(f"    {piece.slot} : {piece.name or '(sans nom)'} ({', '.join(extras)})")
        for part in bad:
            lines.append(f"    mal formé : {part}")
    if context.get("links"):
        links = parse_links(context["links"])
        lines.append(f"  liens cités ({len(links)}) :")
        for link in links:
            lines.append(f"    [{link.name}] {LINK_KINDS.get(link.kind, link.kind)} {link.body}")
            lines += [f"      {text}" for text in link.tooltip]
    return lines


def export_contexts(journal: Journal, folder: Path) -> dict[str, Any]:
    """Écrit les contextes distincts et les exports SimulationCraft du journal ; rend les comptes et les fichiers."""
    folder.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    seen: set[str] = set()
    contexts = 0
    for event in _contexts(journal):
        text = context_lines(event["context"]) + "\n"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        name = f"{_stamp(event.get('at', ''))}_{event.get('id', 0)}.txt"
        (folder / name).write_bytes(text.encode("utf-8"))
        written.append(name)
        contexts += 1
    exports = 0
    for event in journal.recent("simc_export", days=DAYS):
        if not isinstance(event.get("text"), str):
            continue
        name = f"simc_{_stamp(event.get('at', ''))}_{event.get('id', 0)}.txt"
        (folder / name).write_bytes(event["text"].replace("\r\n", "\n").encode("utf-8"))
        written.append(name)
        exports += 1
    return {"folder": str(folder), "contexts": contexts, "exports": exports, "files": written}
