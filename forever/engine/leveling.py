"""Niveaux utiles au leveling : couleur d'une quête selon l'écart de niveau, bande des niveaux de quête utiles.

Chiffres dans `mechanics.json` (`leveling.quest_band`, règle de Classic, suppose) ; aucune constante ici."""

from __future__ import annotations

from typing import Literal

from forever.engine.model import GameData

QuestColor = Literal["gray", "green", "yellow", "orange", "red"]
USEFUL_COLORS: tuple[QuestColor, ...] = ("green", "yellow", "orange")


def gray_level(gd: GameData, player_level: int) -> int:
    """Niveau de quête le plus haut encore gris pour `player_level` : ligne de `gray_rows` qui couvre le niveau
    (la dernière au-delà), niveau - retrait - niveau // diviseur, 0 sans retrait.

    Registre : I7"""
    rows = gd.leveling.quest_band.gray_rows
    _up_to, minus, per = next((row for row in rows if player_level <= row[0]), rows[-1])
    if minus is None:
        return 0
    return player_level - minus - (player_level // per if per else 0)


def quest_color(gd: GameData, player_level: int, quest_level: int) -> QuestColor:
    """Couleur d'une quête de niveau `quest_level` pour un personnage de niveau `player_level` : rouge, orange,
    jaune selon l'écart (seuils de `leveling.quest_band`), puis verte au-dessus du niveau gris, grise sinon.

    Registre : I7"""
    band = gd.leveling.quest_band
    diff = quest_level - player_level
    if diff >= band.red_min_diff:
        return "red"
    if diff >= band.orange_min_diff:
        return "orange"
    if diff >= band.yellow_min_diff:
        return "yellow"
    return "green" if quest_level > gray_level(gd, player_level) else "gray"


def level_band(gd: GameData, player_level: int) -> tuple[int, int]:
    """(plus bas, plus haut) niveaux de quête utiles (verts, jaunes, orange).

    Registre : I7"""
    return gray_level(gd, player_level) + 1, player_level + gd.leveling.quest_band.red_min_diff - 1
