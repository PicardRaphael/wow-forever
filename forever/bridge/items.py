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
    raise NotImplementedError


def parse_gear(value: str) -> tuple[list[GearPiece], list[str]]:
    """Pièces d'équipement (nouvelle et ancienne forme) et morceaux mal formés, dans l'ordre reçu."""
    raise NotImplementedError


def parse_links(value: str) -> list[GameLink]:
    """Liens cités dans la question ; un lien sans corps ni nom est ignoré."""
    raise NotImplementedError


def links_lines(links: list[GameLink]) -> list[str]:
    """Lignes du message à la conversation : « [Nom] (objet item:…) : ligne 1 / ligne 2 … »."""
    raise NotImplementedError
