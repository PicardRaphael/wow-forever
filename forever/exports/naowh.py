"""Chaînes d'import de Naowh Forever (EX1) : builds de talents `!NFB1!` (module Training).

Format relevé dans Naowh Forever 1.1.12 (`NaowhForever_Training/Builds.lua`, tous droits réservés, jamais recopié) :
table `{v=1, class, name, spec, points}` passée par le codec commun (`forever/exports/codec.py`). Les bornes ci-dessous
sont celles du format de l'addon (nombre d'entrées, longueur des textes), pas des règles du jeu : une entrée hors
bornes lève une erreur nommée, jamais une chaîne que Naowh rejetterait."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
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


BIS_PREFIX = "!NBIS1!"
BIS_VERSION = 4  # liste ordonnée par emplacement (`ORDERED` de NaowhForever_BiS/BiS/Sharing.lua)
BIS_TEXT_MAX = 40
BIS_MAX_ID = 2**31
WEIGHTS_PREFIX = "NFSW1"
WEIGHTS_MAX = 1000  # poids refusé à partir de cette valeur (`SW.MAX_WORTH`)


@dataclass(frozen=True)
class NaowhBis:
    """Liste BiS relue d'une chaîne `!NBIS1!` : objet par emplacement d'inventaire, objets de repli par emplacement."""

    name: str
    spec: str
    slots: dict[int, int]
    extra: dict[int, tuple[int, ...]]


def _item_id(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < BIS_MAX_ID:
        raise ExportFormatError(f"identifiant d'objet invalide : {value!r}")
    return value


def _bis_slot(slot: Any) -> int:
    from forever.exports.naowh_keys import BIS_SLOTS

    if isinstance(slot, bool) or not isinstance(slot, int) or slot not in BIS_SLOTS:
        raise ExportFormatError(f"emplacement {slot!r} hors de la liste BiS de Naowh")
    return slot


def _spec_key(spec: Any) -> str:
    from forever.exports.naowh_keys import SPEC_KEYS

    if spec not in SPEC_KEYS:
        raise ExportFormatError(f"spécialisation « {spec} » inconnue de Naowh Forever")
    return str(spec)


def naowh_bis(name: str, spec: str, slots: Mapping[int, int], extra: Mapping[int, Sequence[int]]) -> str:
    """Chaîne `!NBIS1!` (v=4, liste ordonnée) : objet par emplacement d'inventaire et objets de repli dans l'ordre ;
    emplacement hors liste (dont la chemise), identifiant invalide ou spécialisation inconnue : `ExportFormatError`.
    Remplie par T10a seulement (EX1 prépare le format)."""
    table = {
        "v": BIS_VERSION,
        "name": build_text(name),
        "spec": _spec_key(spec),
        "slots": {_bis_slot(s): _item_id(i) for s, i in slots.items()},
        "extra": {_bis_slot(s): [_item_id(i) for i in ids] for s, ids in extra.items()},
    }
    return pack(BIS_PREFIX, table)


def _indexed(value: Any) -> dict[Any, Any]:
    """Table relue : `list` (clés 1..n) ou `dict`."""
    if isinstance(value, list):
        return dict(enumerate(value, 1))
    if isinstance(value, dict):
        return value
    raise ExportFormatError("table attendue")


def read_naowh_bis(text: str) -> NaowhBis:
    """Liste BiS relue d'une chaîne `!NBIS1!` en v=4 ; toute autre version est refusée (forever n'écrit que v=4)."""
    data = unpack(BIS_PREFIX, text, NAOWH_LIMITS)
    if not isinstance(data, dict) or data.get("v") != BIS_VERSION:
        raise ExportFormatError(f"liste BiS de version inconnue (attendu v={BIS_VERSION})")
    name, spec = data.get("name"), data.get("spec")
    slots = {_bis_slot(s): _item_id(i) for s, i in _indexed(data.get("slots")).items()}
    extra_raw = data.get("extra")
    extra = (
        {_bis_slot(s): tuple(_item_id(i) for i in _indexed(ids).values()) for s, ids in _indexed(extra_raw).items()}
        if extra_raw is not None
        else {}
    )
    return NaowhBis(
        name=build_text(name) if isinstance(name, str) else "",
        spec=str(spec) if isinstance(spec, str) else "",
        slots=slots,
        extra=extra,
    )


def _weight_text(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ExportFormatError(f"poids illisible : {value!r}")
    if not math.isfinite(value) or value < 0 or value >= WEIGHTS_MAX:
        raise ExportFormatError(f"poids {value!r} hors de [0, {WEIGHTS_MAX}[")
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return text or "0"


def naowh_weights(spec_key: str, weights: Mapping[str, float]) -> str:
    """Ligne `NFSW1:<spécialisation>:<stat>=<poids>,…` (texte clair) : poids en chiffres et point seulement (jamais
    de notation `e`), dans [0, 1000[, clés de statistiques de Naowh ; remplie par T10a seulement."""
    from forever.exports.naowh_keys import STAT_KEYS

    key = _spec_key(spec_key)
    parts = []
    for stat in STAT_KEYS:
        if stat in weights:
            parts.append(f"{stat}={_weight_text(weights[stat])}")
    unknown = sorted(set(weights) - set(STAT_KEYS))
    if unknown:
        raise ExportFormatError(f"statistique inconnue de Naowh Forever : {', '.join(unknown)}")
    return f"{WEIGHTS_PREFIX}:{key}:{','.join(parts)}"


def read_naowh_weights(text: str) -> tuple[str, dict[str, float]]:
    """(spécialisation, poids) d'une ligne `NFSW1:` ; refus d'une clé, d'une statistique ou d'un poids illisibles."""
    from forever.exports.naowh_keys import STAT_KEYS

    match = re.fullmatch(r"\s*" + WEIGHTS_PREFIX + r":([A-Za-z0-9-]+):([A-Za-z0-9=.,-]*)\s*", text)
    if match is None:
        raise ExportFormatError("ligne qui n'est pas une ligne de poids NFSW1")
    key = _spec_key(match.group(1))
    out: dict[str, float] = {}
    for part in filter(None, match.group(2).split(",")):
        found = re.fullmatch(r"([A-Za-z0-9]+)=([0-9.]+)", part)
        if found is None or found.group(1) not in STAT_KEYS:
            raise ExportFormatError(f"poids illisible : {part}")
        try:
            value = float(found.group(2))
        except ValueError:
            raise ExportFormatError(f"poids illisible : {part}") from None
        if value >= WEIGHTS_MAX:
            raise ExportFormatError(f"poids {part} au-delà de {WEIGHTS_MAX}")
        out[found.group(1)] = value
    return key, out
