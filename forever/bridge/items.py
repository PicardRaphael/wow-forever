"""Objets, liens et infobulles envoyés par le jeu (P06b, bloc A, décision 235).

- Chaîne d'objet : corps d'un lien `item:…` sans le préfixe ni les champs vides ou nuls de fin ; champs `objet :
  enchantement : gemme 1 à 4 : suffixe aléatoire : identifiant unique : niveau du lien : spécialisation : modificateurs
  : contexte : nombre de bonus : bonus…`. Le suffixe aléatoire (négatif quand il dépend de l'identifiant unique)
  n'est que dans le lien.
- Équipement `gear` : `emplacement=chaîne=nom` séparés par `;` ; l'ancienne forme `emplacement:identifiant[:nom]` de
  P06a reste lue.
- Liens cités `links` : par lien (séparés par 0x1D), le corps du lien, son nom puis les lignes de son infobulle lues
  par `C_TooltipInfo.GetHyperlink` (séparés par 0x1C)."""

from __future__ import annotations

import re
from dataclasses import dataclass

LINK_SEP = "\x1d"
LINE_SEP = "\x1c"
LINK_KINDS = {"item": "objet", "spell": "sort", "quest": "quête", "talent": "talent"}


@dataclass(frozen=True)
class ItemString:
    item: int
    enchant: int = 0
    gems: tuple[int, ...] = ()
    suffix: int = 0
    unique: int = 0
    link_level: int | None = None
    bonus: tuple[int, ...] = ()


@dataclass(frozen=True)
class GearPiece:
    slot: int
    item: ItemString
    name: str
    chain: str  # chaîne d'objet telle qu'envoyée (sans `item:`)


@dataclass(frozen=True)
class GameLink:
    kind: str  # item, spell, quest, talent
    body: str  # `item:7909:…`
    name: str
    tooltip: tuple[str, ...] = ()


def parse_item_string(text: str) -> ItemString:
    """Champs d'une chaîne d'objet (« 7909:1883:0:0:0:0:-12:1234567:19 », avec ou sans `item:`) ; champs vides lus 0 ;
    ValueError si l'objet manque ou si un champ n'est pas un entier."""
    body = text.strip()
    body = body.removeprefix("item:")
    fields = body.split(":")
    if not fields[0]:
        raise ValueError(f"chaîne d'objet sans objet : {text!r}")
    values = [int(f) if f else 0 for f in fields]  # ValueError si un champ n'est pas un entier
    if values[0] <= 0:
        raise ValueError(f"identifiant d'objet invalide : {text!r}")

    def at(i: int) -> int:
        return values[i] if i < len(values) else 0

    count = max(0, at(12))
    return ItemString(
        item=values[0],
        enchant=at(1),
        gems=tuple(g for g in values[2:6] if g),
        suffix=at(6),
        unique=at(7),
        link_level=at(8) or None,
        bonus=tuple(values[13 : 13 + count]),
    )


_PIECE = re.compile(r"(\d+)([=:])(.*)", re.DOTALL)


def parse_gear(value: str) -> tuple[list[GearPiece], list[str]]:
    """Pièces d'équipement (nouvelle et ancienne forme) et morceaux mal formés, dans l'ordre reçu."""
    pieces: list[GearPiece] = []
    bad: list[str] = []
    for part in (p.strip() for p in str(value or "").split(";")):
        if not part:
            continue
        match = _PIECE.fullmatch(part)
        if match is None:
            bad.append(part)
            continue
        slot, sep, rest = int(match[1]), match[2], match[3]
        if sep == "=":
            chain, _, name = rest.partition("=")
        else:
            chain, _, name = rest.partition(":")
            if not chain.isdigit():
                bad.append(part)
                continue
        try:
            item = parse_item_string(chain)
        except ValueError:
            bad.append(part)
            continue
        pieces.append(GearPiece(slot=slot, item=item, name=name, chain=chain))
    return pieces, bad


def parse_links(value: str) -> list[GameLink]:
    """Liens cités dans la question ; un lien sans corps ni nom est ignoré."""
    links = []
    for part in str(value or "").split(LINK_SEP):
        fields = part.split(LINE_SEP)
        body = fields[0].strip()
        name = fields[1].strip() if len(fields) > 1 else ""
        if not body and not name:
            continue
        tooltip = tuple(line for line in fields[2:] if line.strip())
        links.append(GameLink(kind=body.split(":", 1)[0], body=body, name=name, tooltip=tooltip))
    return links


def links_lines(links: list[GameLink]) -> list[str]:
    """Lignes du message à la conversation : « [Nom] (objet item:…) : ligne 1 / ligne 2 … »."""
    lines = []
    for link in links:
        line = f"[{link.name}] ({LINK_KINDS.get(link.kind, link.kind)} {link.body})"
        if link.tooltip:
            line += " : " + " / ".join(link.tooltip)
        lines.append(line)
    return lines
