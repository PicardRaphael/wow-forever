"""Chaînes d'import de Naowh Forever (EX1) : builds de talents `!NFB1!` (module Training).

Format relevé dans Naowh Forever 1.1.12 (`NaowhForever_Training/Builds.lua`, tous droits réservés, jamais recopié) :
table `{v=1, class, name, spec, points}` passée par le codec commun (`forever/exports/codec.py`). Les bornes ci-dessous
sont celles du format de l'addon (nombre d'entrées, longueur des textes), pas des règles du jeu : une entrée hors
bornes lève une erreur nommée, jamais une chaîne que Naowh rejetterait."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from forever.exports.codec import NAOWH_LIMITS, ExportFormatError, pack, unpack

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
    clean = re.sub(r"[|\r\n]", "", text)
    raw = clean.encode("utf-8")[:BUILD_TEXT_MAX]
    return raw.decode("utf-8", errors="ignore")


def _check_points(points: Sequence[Any]) -> tuple[int, ...]:
    if not points:
        raise ExportFormatError("build sans aucun point : Naowh refuse un build vide")
    if len(points) > BUILD_MAX_POINTS:
        raise ExportFormatError(f"{len(points)} points : le format !NFB1! en porte au plus {BUILD_MAX_POINTS}")
    if any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in points):
        raise ExportFormatError("point qui n'est pas un nœud de talent (entier positif)")
    return tuple(int(n) for n in points)


def naowh_build(class_id: int, name: str, spec: str, points: Sequence[int]) -> str:
    """Chaîne `!NFB1!` d'un build : classe (identifiant du client), nom et spécialisation gardés comme chez Naowh,
    nœuds de talents dans l'ordre de prise, un par point ; `ExportFormatError` hors des bornes du format."""
    checked = _check_points(points)
    table = {"v": BUILD_VERSION, "class": class_id, "name": build_text(name), "spec": build_text(spec)}
    return pack(BUILD_PREFIX, {**table, "points": list(checked)})


def read_naowh_build(text: str) -> NaowhBuild:
    """Build relu d'une chaîne `!NFB1!` (bornes de lecture de Naowh) ; `ExportFormatError` en français sinon."""
    data = unpack(BUILD_PREFIX, text, NAOWH_LIMITS)
    if not isinstance(data, dict) or data.get("v") != BUILD_VERSION:
        raise ExportFormatError(f"build de version inconnue (attendu v={BUILD_VERSION})")
    class_id = data.get("class")
    if isinstance(class_id, bool) or not isinstance(class_id, int):
        raise ExportFormatError("classe absente ou illisible")
    points = data.get("points")
    if not isinstance(points, list):
        raise ExportFormatError("liste des points absente")
    name, spec = data.get("name"), data.get("spec")
    return NaowhBuild(
        class_id=class_id,
        name=build_text(name) if isinstance(name, str) else "",
        spec=build_text(spec) if isinstance(spec, str) else "",
        points=_check_points(points),
    )


MACRO_PREFIX = "!NFM1!"
MACRO_VERSION = 1
MACRO_NAME_MAX = 16  # octets du nom (`C.NAME_MAX` de NaowhForever_Macros)
MACRO_BODY_MAX = 255  # octets du corps (`C.LIMIT`)


def _check_macro(name: Any, body: Any) -> tuple[str, str]:

    if not isinstance(name, str) or not isinstance(body, str):
        raise ExportFormatError("macro sans nom ou sans corps")
    clean = re.sub(r"[|\r\n]", "", name)
    if not 1 <= len(clean.encode("utf-8")) <= MACRO_NAME_MAX:
        raise ExportFormatError(f"nom de macro « {name} » : de 1 à {MACRO_NAME_MAX} octets")
    if len(body.encode("utf-8")) > MACRO_BODY_MAX:
        raise ExportFormatError(f"corps de la macro « {clean} » au-delà de {MACRO_BODY_MAX} octets")
    return clean, body


def naowh_macros(macros: Sequence[tuple[str, str]]) -> str:
    """Chaîne `!NFM1!` de macros `(nom, corps)` ; `ExportFormatError` si une seule est hors bornes (Naowh rejette
    alors toute la chaîne) ou porte une commande interdite (`macro_violations`)."""
    from forever.exports.macros import macro_violations

    if not macros:
        raise ExportFormatError("aucune macro à exporter")
    out = []
    for name, body in macros:
        clean, checked = _check_macro(name, body)
        bad = macro_violations(checked)
        if bad:
            raise ExportFormatError(f"macro « {clean} » : commande interdite {bad[0]}")
        out.append({"name": clean, "body": checked})
    return pack(MACRO_PREFIX, {"v": MACRO_VERSION, "macros": out})


def read_naowh_macros(text: str) -> list[tuple[str, str]]:
    """Macros `(nom, corps)` relues d'une chaîne `!NFM1!` ; une seule macro invalide refuse toute la chaîne, comme
    Naowh."""
    data = unpack(MACRO_PREFIX, text, NAOWH_LIMITS)
    if not isinstance(data, dict) or data.get("v") != MACRO_VERSION or not isinstance(data.get("macros"), list):
        raise ExportFormatError(f"macros de version inconnue (attendu v={MACRO_VERSION})")
    if not data["macros"]:
        raise ExportFormatError("aucune macro dans la chaîne")
    out = []
    for m in data["macros"]:
        if not isinstance(m, dict):
            raise ExportFormatError("macro illisible")
        out.append(_check_macro(m.get("name"), m.get("body")))
    return out
