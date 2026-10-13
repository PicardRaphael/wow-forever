"""Vérification passive du modèle d'XP sur les relevés du joueur (T04d, bloc G, décision 247).

`forever xp check` compare, sans rien écrire, le modèle d'XP (`forever/engine/xp.py`) aux gains relevés par
ForeverLogger : gains de monstre (niveau du monstre lu sur la cible relevée, sinon niveau fixe de la base de Questie
quand le nom désigne un seul PNJ de niveau fixe ; écartés et comptés sinon) et quêtes rendues (`xpReward` comparé à
l'XP du client pour une quête vue). Par règle : nombre de cas, écart médian, cas hors tolérance et verdict
(`vérifié`, `écart`, `à vérifier`) ; ce qui reste à vérifier renvoie à sa question ouverte. Jamais d'échec faute de
relevé : sans relevé, tout est « à vérifier ». Tolérance et cas minimaux : `measures.xp_check` de `mechanics.json`."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.engine.model import GameData
from forever.pipeline.addon_sv import LoggerDB

VERDICTS = ("vérifié", "écart", "à vérifier")
# Règle -> (libellé, question ouverte qui reste tant qu'elle n'est pas vérifiée)
RULES: dict[str, tuple[str, str]] = {
    "kill_xp": ("XP d'un monstre de même niveau (PerKill du client)", "LVL1"),
    "xp.mob_level_difference": ("écart de niveau du monstre", "LVL1"),
    "xp.elite_factor": ("monstres élites", "LVL8"),
    "xp.dungeon_kill_bonus": ("bonus des monstres de donjon", "LVL5"),
    "xp.group": ("XP en groupe", "LVL4"),
    "xp.rested": ("repos", "LVL10"),
    "quest_xp": ("XP des quêtes vues par le client (QuestXP × multiplicateur)", "LVL6"),
    "xp.quest_level_difference": ("XP des quêtes selon l'écart de niveau", "LVL7"),
}


def check_records(
    gd: GameData,
    rewards: dict[str, Any] | None,
    loggers: Sequence[LoggerDB],
    *,
    tolerance: float,
    min_cases: int,
    questie_levels: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Comparaison du modèle aux relevés : `{"rules": [...], "skipped": {...}, "to_verify": [...]}`."""
    raise NotImplementedError


def xp_check(deps: Deps, *, sv_dir: Path | None = None, questie_dir: Path | None = None) -> dict[str, Any]:
    """`forever xp check` : relevés de ForeverLogger de tous les comptes (ou de `sv_dir`), avec la provenance ; ne
    lève jamais faute de relevé."""
    raise NotImplementedError
