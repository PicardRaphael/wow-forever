"""Échelle de statistiques au format texte Pawn v1, telle que Forever Companion l'importe (Options, « Import
scale… », `Scales.ParsePawn` de Forever Companion 1.0.0, relevé le 2026-10-15) : `( Pawn: v1: "<nom>": Class=<Classe>,
<Stat>=<poids>, … )`. Noms des statistiques et ordre d'affichage de `Scales.STATS` (toucher et critique : 1 point = 1 %).
Format réimplémenté d'après l'observation, aucun code de l'addon repris. Aucun chiffre de jeu ici."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping

from forever.exports.codec import ExportFormatError

PAWN_STATS = (
    "Strength", "Agility", "Stamina", "Intellect", "Spirit", "Ap", "Rap", "FeralAp", "HitRating", "CritRating",
    "MeleeDps", "MeleeSpeed", "RangedDps", "RangedSpeed", "SpellPower", "SpellDamage", "Healing", "ArcaneSpellDamage",
    "FireSpellDamage", "FrostSpellDamage", "HolySpellDamage", "NatureSpellDamage", "ShadowSpellDamage",
    "SpellHitRating", "SpellCritRating", "SpellPenetration", "Mp5", "Hp5", "Armor", "DefenseRating", "DodgeRating",
    "ParryRating", "BlockRating", "BlockValue",
)  # fmt: skip
WEIGHT_MAX = 1000.0  # bornes des poids écrits (mêmes que NFSW1)
_SCALE = re.compile(r'^\(\s*Pawn\s*:\s*v1\s*:\s*"([^"]*)"\s*:\s*(.*?)\s*\)\s*$', re.DOTALL)


def _number(value: float) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ExportFormatError(f"poids illisible : {value!r}")
    if not 0 <= value < WEIGHT_MAX:
        raise ExportFormatError(f"poids {value!r} hors de [0, {WEIGHT_MAX:g}[")
    text = f"{float(value):.3f}".rstrip("0").rstrip(".")
    return text or "0"


def pawn_scale(label: str, class_token: str, weights: Mapping[str, float]) -> str:
    """Échelle Pawn v1 déterministe (ordre de Forever Companion), nom sans guillemet, poids nuls omis."""
    unknown = sorted(set(weights) - set(PAWN_STATS))
    if unknown:
        raise ExportFormatError(f"statistique inconnue de Forever Companion : {', '.join(unknown)}")
    parts = [f"Class={class_token.strip().capitalize()}"]
    parts += [f"{stat}={_number(weights[stat])}" for stat in PAWN_STATS if weights.get(stat)]
    name = label.replace('"', "'")
    return f'( Pawn: v1: "{name}": {", ".join(parts)} )'


def read_pawn_scale(text: str) -> tuple[str, str | None, dict[str, float]]:
    """(nom, classe, poids) d'une échelle Pawn v1 ; refus d'un texte qui n'en est pas une ou d'une statistique
    inconnue."""
    m = _SCALE.match(text.strip())
    if m is None:
        raise ExportFormatError("texte qui n'est pas une échelle Pawn v1")
    cls: str | None = None
    weights: dict[str, float] = {}
    for part in filter(None, (p.strip() for p in m.group(2).split(","))):
        key, sep, raw = part.partition("=")
        if not sep:
            raise ExportFormatError(f"poids illisible : {part}")
        if key == "Class":
            cls = raw
        elif key == "Spec":
            continue
        elif key in PAWN_STATS:
            weights[key] = float(raw)
        else:
            raise ExportFormatError(f"statistique inconnue : {key}")
    return m.group(1), cls, weights
