"""Espérance d'un lancer : agrège toucher, critique, dégâts, temps et mana."""

from __future__ import annotations

from forever.engine.model import Buffs, CastEstimate, Character, GameData, Points


def expected_cast(
    gd: GameData,
    key: str,
    level: int,
    pts: Points,
    ch: Character,
    level_diff: int = 0,
    *,
    frozen: bool = False,
    wc_stacks: int = 0,
    buffs: Buffs | None = None,
    frozen_mult: bool = True,
) -> CastEstimate | None:
    """Espérance d'un sort : dégâts (toucher, critique, multiplicateurs, DoT qui critiquent, Ignite), mana
    (Frost Channeling, Master of Elements, Clearcasting), temps d'incantation, portée. None si le sort n'est pas appris.

    Registre : A17, A18, B12, B17, C2"""
    raise NotImplementedError
