"""Monstres : PV par niveau (mesure, Questie corrigé, ou modèle du seed)."""

from __future__ import annotations

from typing import Literal

from forever.engine.model import GameData, MonsterHp, QuestieCorrection

MobSource = Literal["measured", "seed"]


def correction_ratio(correction: QuestieCorrection | None, level: int) -> tuple[float, str]:
    """Rapport PV Forever / PV Questie au niveau donné et sa certitude.

    Registre : H11"""
    raise NotImplementedError


def questie_ratio(gd: GameData, level: int) -> tuple[float, str]:
    """Rapport de correction des données de la version.

    Registre : H11"""
    raise NotImplementedError


def corrected_questie_hp(gd: GameData, questie_hp: float, level: int) -> MonsterHp:
    """PV Questie corrigés vers Forever.

    Registre : H11"""
    raise NotImplementedError


def mob_hp(gd: GameData, level: int, mob_source: MobSource = "measured") -> MonsterHp:
    """PV d'un monstre normal du niveau donné.

    Registre : H11"""
    raise NotImplementedError
