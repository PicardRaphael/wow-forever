"""Chaînes d'import de Naowh Forever (EX1) : builds de talents `!NFB1!` (module Training).

Format relevé dans Naowh Forever 1.1.12 (`NaowhForever_Training/Builds.lua`, tous droits réservés, jamais recopié) :
table `{v=1, class, name, spec, points}` passée par le codec commun (`forever/exports/codec.py`). Les bornes ci-dessous
sont celles du format de l'addon (nombre d'entrées, longueur des textes), pas des règles du jeu : une entrée hors
bornes lève une erreur nommée, jamais une chaîne que Naowh rejetterait."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

NAOWH_VERSION = "1.1.12"
BUILD_PREFIX = "!NFB1!"
BUILD_VERSION = 1
BUILD_MAX_POINTS = 51  # borne du format (`C.MAX_POINTS` de NaowhForever_Training)
BUILD_TEXT_MAX = 40  # octets gardés du nom et de la spécialisation (`C.BUILD_NAME_MAX`)


@dataclass(frozen=True)
class NaowhBuild:
    """Build relu d'une chaîne `!NFB1!` : classe (identifiant du client), nom, spécialisation, nœuds (un par point)."""

    class_id: int
    name: str
    spec: str
    points: tuple[int, ...]


def build_text(text: str) -> str:
    """Nom ou spécialisation comme Naowh les garde : `|`, retours chariot et sauts de ligne retirés, coupé à
    `BUILD_TEXT_MAX` octets sans couper un caractère UTF-8."""
    raise NotImplementedError


def naowh_build(class_id: int, name: str, spec: str, points: Sequence[int]) -> str:
    raise NotImplementedError


def read_naowh_build(text: str) -> NaowhBuild:
    raise NotImplementedError
