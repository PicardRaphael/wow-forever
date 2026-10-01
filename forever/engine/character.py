"""Modèle de personnage : stats estimées par niveau et race, remplacées par la fiche du personnage si fournie."""

from __future__ import annotations

from forever.engine.model import Character, CharacterOverrides, GameData

PERCENT = 100.0  # conversion d'unité : l'Intelligence par critique est exprimée pour 1 %


def int_per_crit(gd: GameData, level: int) -> float:
    """Intelligence pour 1 % de critique des sorts au niveau donné (niveau borné aux extrémités de la table) : lue
    dans le client en mode forever (`character_scaling.json`), sinon interpolation estimée (`mechanics.json`).

    Registre : A5"""
    by_level = gd.constants.character.spell_crit_per_int_by_level
    if by_level:
        ratio = by_level[max(1, min(len(by_level), level)) - 1]  # critique (fraction) par point d'Intelligence
        if ratio > 0:
            return 1 / (PERCENT * ratio)
    t = gd.constants.character.int_per_crit
    clamped = max(t.level_min, min(t.level_max, level))
    return t.at_min + (t.at_max - t.at_min) * (clamped - t.level_min) / (t.level_max - t.level_min)


def character(gd: GameData, level: int, race: str = "Orc", overrides: CharacterOverrides | None = None) -> Character:
    """Stats du personnage. `overrides` (fiche du personnage) remplace toute estimation.

    Registre : A5, B9, G1, G2"""
    over: CharacterOverrides = overrides or {}
    m = gd.constants.character
    L = level
    iv, sv = m.intellect, m.spirit
    intellect = over.get(
        "intellect", iv.base + iv.per_level * (L - 1) + iv.late_bonus_per_level * max(0, L - iv.late_from_level)
    )
    spirit = over.get(
        "spirit",
        (sv.base + sv.per_level * (L - 1) + sv.late_bonus_per_level * max(0, L - sv.late_from_level))
        * (1 + gd.racials.spirit_pct.get(race, 0.0)),
    )
    sp = over.get("sp", m.spell_power_per_level * L if L >= m.spell_power_from_level else 0.0)
    if m.base_mana_by_level:
        base_mana = m.base_mana_by_level[max(1, min(len(m.base_mana_by_level), L)) - 1]
    else:
        base_mana = m.base_mana + m.base_mana_per_level * (L - 1)
    # la mana part de la mana de base calculée, même si la fiche fournit la mana de base (comme le seed)
    mana = (
        base_mana
        + min(intellect, m.mana_first_points)
        + m.mana_per_point_after * max(0.0, intellect - m.mana_first_points)
    )
    mana *= 1 + gd.racials.mana_pct.get(race, 0.0)
    if "spell_crit" in over:
        crit = over["spell_crit"]
    else:
        crit = m.crit_base + intellect / int_per_crit(gd, L) / PERCENT + over.get("crit_gear", 0.0)
        if over.get("sword"):
            crit += gd.racials.sword_crit.get(race, 0.0)
    return Character(
        level=L,
        race=race,
        intellect=intellect,
        spirit=spirit,
        sp=sp,
        base_mana=over.get("base_mana", base_mana),
        mana=over.get("mana", mana),
        crit=crit,
        hit_gear=over.get("hit_gear", 0.0),
        haste=over.get("haste", 0.0),
        hp=over.get("hp", m.hp_base + m.hp_per_level * L + m.hp_per_level_squared * L * L),
        armor=over.get(
            "armor", m.armor_per_agility * (m.agility_base + m.agility_per_level * L) + m.armor_per_level * L
        ),
        spirit_regen=(m.regen_base + spirit / m.regen_spirit_divisor) / m.regen_tick_s,
        overrides=over,
    )
