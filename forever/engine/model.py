"""Types du moteur : données de la version (gelées) et résultats des calculs.

Les valeurs de jeu vivent dans `forever/data/` ; ces types ne font que les porter. `GameData` est construit hors du
moteur par `forever/gamedata.py`, après contrôle d'intégrité, puis passé en premier paramètre à chaque fonction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, NamedTuple, TypedDict

Points = Mapping[str, int]
"""Clé de talent -> rang pris."""

# Écoles touchées par les talents de givre et de feu (Givre-feu compte dans les deux : voir OPEN_QUESTIONS).
SCHOOL_FROST = frozenset({"frost", "frostfire"})
SCHOOL_FIRE = frozenset({"fire", "frostfire"})


class Rank(NamedTuple):
    """Rang d'un sort, dans l'ordre de `spells.json.rank_format` ; `position` commence à 1, comme `lookup`."""

    position: int
    level: int
    damage_min: float
    damage_max: float
    dot_total: float
    dot_duration_s: float
    cast_time_s: float
    mana: float | None
    cooldown_s: float


@dataclass(frozen=True)
class Spell:
    key: str
    school: str
    ranks: tuple[Rank, ...]
    range_yd: float | None
    talent: str | None
    channel: bool
    slow: float | None
    mana_pct_base: float | None
    frozen_mult: float | None
    projectile_speed: float | None
    slow_dur: tuple[float, ...] | None = None  # durée du ralenti par rang (spells.json)


@dataclass(frozen=True)
class Talent:
    key: str
    name: str
    tree: str
    tier: int
    col: int
    max_rank: int
    ranks: tuple[tuple[float, ...], ...]
    prereq: tuple[int, int] | None  # (palier, colonne) dans le même arbre


@dataclass(frozen=True)
class CombatRules:
    """Champs structurés de `leveling.json.combat_rules`."""

    gcd_s: float
    spell_miss_by_level_diff: Mapping[str, float]  # clé "-" : cible plus basse
    min_miss: float
    crit_mult_spell: float
    dot_can_crit: bool
    pushback_s: float = 0.0  # recul d'incantation par coup reçu


@dataclass(frozen=True)
class FixedCoefficient:
    """Coefficient fixe d'un sort : `value` direct, ou `cast_s` (durée équivalente divisée par le diviseur)."""

    value: float | None
    cast_s: float | None
    slowed: bool


@dataclass(frozen=True)
class CoefficientRules:
    cast_divisor: float
    cast_min_s: float
    cast_max_s: float
    slow_factor: float
    channel_cap_s: float
    low_level_threshold: int
    low_level_penalty_per_level: float
    fixed: Mapping[str, FixedCoefficient]
    low_level_default: bool  # pénalité des sorts de bas niveau appliquée par défaut en mode forever (T04e)
    ice_lance_source: str = "client"  # coefficient d'Ice Lance en forever : client ou seed (coefficient.fixed), T05


@dataclass(frozen=True)
class StatGrowth:
    """stat = base + per_level × (niveau - 1) + late_bonus_per_level × max(0, niveau - late_from_level)."""

    base: float
    per_level: float
    late_bonus_per_level: float
    late_from_level: int


@dataclass(frozen=True)
class IntPerCrit:
    level_min: int
    at_min: float
    level_max: int
    at_max: float


@dataclass(frozen=True)
class CharacterModel:
    crit_base: float
    int_per_crit: IntPerCrit
    intellect: StatGrowth
    spirit: StatGrowth
    spell_power_per_level: float
    spell_power_from_level: int
    base_mana: float
    base_mana_per_level: float
    mana_first_points: float
    mana_per_point_after: float
    hp_base: float
    hp_per_level: float
    hp_per_level_squared: float
    agility_base: float
    agility_per_level: float
    armor_per_agility: float
    armor_per_level: float
    regen_base: float
    regen_spirit_divisor: float
    regen_tick_s: float


@dataclass(frozen=True)
class TalentRules:
    first_level: int
    points_per_tier: int


@dataclass(frozen=True)
class Constants:
    """Constantes de `mechanics.json` (valeurs absentes des tables du client)."""

    coefficients: CoefficientRules
    character: CharacterModel
    talents: TalentRules
    crit_per_winters_chill_stack: float
    talent_rank_mana_ratio: float
    talent_rank_mana_default: float
    default_range_yd: float
    miss_per_level_below: float  # raté retiré par niveau d'écart sous la cible (écart négatif)
    regen_stacking: str = "sum"  # régénération d'Arcane Meditation et de l'armure : sum ou max (mana.regen_stacking)
    bonus_stacking: str = "multiplicative"  # bonus de dégâts : multiplicative ou additive (damage.bonus_stacking)


@dataclass(frozen=True)
class Racials:
    """Raciaux utilisés par le modèle de personnage (`racials.json`), par race."""

    sword_crit: Mapping[str, float]
    spirit_pct: Mapping[str, float]
    mana_pct: Mapping[str, float]


@dataclass(frozen=True)
class ScalingComponent:
    """Effet de dégâts d'un rang (`spell_scaling.json`) : `kind` direct, dot (× ticks, sur la durée) ou channel
    (× ticks, dans le coup) ; `bonus_coefficient` : part de la puissance des sorts par coup, par tic ou par éclair
    (EffectBonusCoefficient du client) ; `period_ms` : période des tics (0 pour un coup direct)."""

    spell_id: int
    index: int
    kind: str
    ticks: float
    base_level: int
    max_level: int
    base_points: float
    points_per_level: float
    variance: float
    bonus_coefficient: float
    period_ms: int


@dataclass(frozen=True)
class RankScaling:
    rank: int
    spell_id: int
    base_level: int
    spell_level: int
    max_level: int
    start_recovery_ms: int  # recharge globale déclenchée (SpellCooldowns.StartRecoveryTime)
    components: tuple[ScalingComponent, ...]


@dataclass(frozen=True)
class MonsterHp:
    """PV max d'un monstre à un niveau, avec sa certitude (`certain` mesuré, `probable`, `suppose` communautaire ou
    extrapolé) ; valeur fractionnaire possible pour le modèle interpolé du seed."""

    value: float
    certainty: str
    source: str


@dataclass(frozen=True)
class QuestieCorrection:
    """Correction PV Questie -> Forever (`monsters.json.questie_correction`) : rapport médian mesuré / Questie par
    niveau mesuré, droite des moindres carrés (rapport = max(1, pente × niveau + ordonnée)), plage des niveaux
    mesurés. `slope` et `intercept` absents : moins de deux niveaux au rapport supérieur à 1."""

    levels: Mapping[int, float]
    slope: float | None
    intercept: float | None
    level_min: int
    level_max: int


@dataclass(frozen=True)
class MonsterTable:
    """Table des monstres (`monsters.json`) : agrégat par niveau et PNJ mesurés (npc_id -> niveau -> PV)."""

    hp_by_level: Mapping[int, MonsterHp]
    npcs: Mapping[int, Mapping[int, MonsterHp]]
    correction: QuestieCorrection | None = None


@dataclass(frozen=True)
class MobModel:
    """Modèle de monstre du seed (`leveling.json.mob_model`) : PV d'ancrage par niveau (interpolés), coups, course."""

    hp_anchors: Mapping[int, float]
    swing_s: float
    crit: float
    crit_mult: float
    avoid_vs_mage: float
    run_speed: float
    melee_range: float
    certainty: str


@dataclass(frozen=True)
class QuestBand:
    """Couleurs de quête selon l'écart de niveau (`leveling.quest_band`) : seuils rouge, orange, jaune (niveau de
    quête - niveau du personnage) et lignes du niveau gris (niveau max, retrait ou None, diviseur ou 0)."""

    red_min_diff: int
    orange_min_diff: int
    yellow_min_diff: int
    gray_rows: tuple[tuple[int, int | None, int], ...]


@dataclass(frozen=True)
class LevelingConstants:
    """Constantes du leveling (`mechanics.json`, clés `leveling.*`), chiffres du seed sim_leveling.py."""

    mob_hit_per_level: float
    mob_hit_per_level_squared: float
    armor_base: float
    armor_per_attacker_level: float
    xp_base: float
    xp_per_level: float
    frostbite_freeze_s: float
    dot_tick_s: float
    ignite_aura_id: int  # identifiant de l'aura d'Ignite (tics dans les journaux)
    ignite_duration_s: float  # aura d'Ignite du client
    ignite_tick_s: float
    ignite_cumulative: int
    ignite_rule: str  # rolling : règle roulante (T04c, décision 2) ; independent : règle du seed (variante, T05)
    frost_nova_retreat_yd: float
    rest_hp_regen_fraction: float
    projectile_speed_default: float
    projectile_speed_instant: float
    analytic_min_cast_fraction: float
    analytic_freeze_cap: float
    analytic_winters_chill_casts: float
    default_level_diff: int
    default_nova_break: float
    default_run_between_s: float
    quest_band: QuestBand
    mob_source: str = "measured"  # PV des monstres par défaut des simulateurs (leveling.mob_source, T05)

    @property
    def ignite_ticks(self) -> int:
        """Tics d'un Ignite posé par un critique : durée / période de l'aura, arrondie (comme le seed)."""
        return round(self.ignite_duration_s / self.ignite_tick_s)


@dataclass(frozen=True)
class Restore:
    """Nourriture ou boisson conjurée : niveaux des rangs et (quantité, durée en s) par rang."""

    spell_levels: tuple[int, ...]
    restore: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class Utility:
    """Sorts utilitaires du leveling (`spells.json.utility`)."""

    frost_armor_duration_s: float
    frost_armor_swing_slow: float
    mage_armor_level: int
    mage_armor_regen: float
    water: Restore
    food: Restore


@dataclass(frozen=True)
class ArmorRank:
    """Rang d'une armure du Mage lu dans le client (`spell_scaling.json.utility`) : niveau d'apprentissage
    (`SpellLevels.BaseLevel`) et effets retenus par `decode_rules.json.utility_spells`."""

    kind: str  # frost_armor, ice_armor, mage_armor
    rank: int
    spell_id: int
    learned_level: int
    effects: Mapping[str, float]


@dataclass(frozen=True)
class FireVulnerability:
    """Aura posée sur la cible par Improved Scorch, lue dans le client (`spell_scaling.json.auras`) : dégâts subis
    des écoles `schools` augmentés de `pct_per_stack` % par cumul, jusqu'à `max_stacks` cumuls, pendant
    `duration_s`."""

    spell_id: int
    pct_per_stack: float
    max_stacks: int
    duration_s: float
    schools: tuple[str, ...]


class Variant(NamedTuple):
    """Valeur d'une hypothèse incertaine et sa source (champ `range` d'une entrée de `mechanics.json`)."""

    value: Any
    source: str


@dataclass(frozen=True)
class RespecRules:
    """Barème et valeur de la réinitialisation des talents : coût en or selon le nombre de réinitialisations déjà
    faites (`respec.json`, dernier palier répété), paliers observés sur la bêta (les suivants sont supposés), or gagné
    par heure selon le niveau (palier le plus proche en dessous) et trajet chez le maître de classe (`mechanics.json`,
    clés `respec.*`)."""

    schedule_gold: tuple[float, ...]
    beta_observed_resets: int
    gold_per_hour: Mapping[int, float]
    trip_minutes: float


@dataclass(frozen=True)
class BuildMethod:
    """Paramètres des builds par contexte (`mechanics.json`, clés `build.*`) : plafond de niveau de la bêta (au-delà,
    un build n'est pas vérifiable en jeu avant la sortie), confiance de l'intervalle apparié, graines de stabilité."""

    beta_level_cap: int
    confidence: float
    stability_seeds: int


@dataclass(frozen=True)
class GameData:
    """Données d'une version, pour la classe Mage (un espace par classe est prévu en T12)."""

    game_version: str
    spells: Mapping[str, Spell]
    talents: Mapping[str, Talent]  # ordre de talents.json (arbres puis talents)
    talent_at: Mapping[tuple[str, int, int], str]  # (arbre, palier, colonne) -> clé
    trees: tuple[str, ...]
    rules: CombatRules
    constants: Constants
    racials: Racials
    monsters: MonsterTable
    scaling: Mapping[str, tuple[RankScaling, ...]]  # clé de sort -> rangs (spell_scaling.json)
    mob_model: MobModel
    leveling: LevelingConstants
    utility: Utility
    armors: Mapping[str, tuple[ArmorRank, ...]]  # armures du client (spell_scaling.json.utility), par rang
    fire_vulnerability: FireVulnerability  # spell_scaling.json.auras (T04e)
    talent_cooldowns_s: Mapping[str, float]  # recharges des talents actifs (spell_scaling.json.talent_cooldowns, T05)
    respec: RespecRules
    build: BuildMethod
    # plages des hypothèses incertaines (champ range de mechanics.json), par clé de mechanics.json (T05)
    assumption_ranges: Mapping[str, tuple[Variant, ...]]


class CharacterOverrides(TypedDict, total=False):
    """Valeurs relevées sur la fiche du personnage : elles remplacent toute estimation."""

    intellect: float
    spirit: float
    sp: float
    base_mana: float
    mana: float
    spell_crit: float  # critique des sorts affiché (fraction)
    crit_gear: float
    sword: bool
    hit_gear: float
    haste: float
    hp: float
    armor: float


@dataclass(frozen=True)
class Character:
    level: int
    race: str
    intellect: float
    spirit: float
    sp: float
    base_mana: float
    mana: float
    crit: float
    hit_gear: float
    haste: float
    hp: float
    armor: float
    spirit_regen: float  # mana par seconde, hors règle d'incantation (combat_rules.five_second_rule)
    overrides: CharacterOverrides


class Buffs(TypedDict, total=False):
    crit: float
    dmg: float  # bonus de dégâts d'une source (fraction), par exemple les cumuls d'Arcane Blast
    dmg_sources: tuple[float, ...]  # bonus de dégâts d'autres sources distinctes (Arcane Power…), une par entrée
    fire_vulnerability: int  # cumuls de Fire Vulnerability sur la cible
    haste: float
    cost: float
    sp_pct: float
    sp_flat: float


class CastEstimate(TypedDict):
    key: str
    rank: Rank
    school: str
    hit: float
    crit: float
    crit_mult: float
    dmg_mult: float
    dmg: float
    direct_per_hit: float
    dot: float
    ignite: float
    mana: float
    cast_s: float
    range_yd: float
    cooldown_s: float
