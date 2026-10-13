"""Modèle d'XP de Forever (T04d, bloc C) : XP d'un monstre et d'une quête, repos, donjon, élite, groupe.

Fonctions pures. Chaque règle vient des données de la version (`gd.xp`, clés `xp.*` de `mechanics.json` et palier
« Rested » de `character_scaling.json` ; XP de base d'un monstre : colonne `PerKill` de la GameTable `xp` décodée,
sinon `leveling.mob_xp`) ; chaque résultat porte la liste des termes appliqués avec leur certitude et leur source.
Aucun chiffre de jeu ici. Unités : points d'XP (nombres à virgule, arrondis à l'affichage seulement), heures."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from forever.engine import leveling
from forever.engine.model import GameData, XpBonusAura, XpBonusData, XpRules
from forever.errors import DataSchemaError


@dataclass(frozen=True)
class Term:
    """Un terme appliqué à l'XP : règle (clé de `mechanics.json` ou source du client), facteur, certitude, source."""

    rule: str
    factor: float
    certainty: str
    source: str


@dataclass(frozen=True)
class XpResult:
    xp: float  # XP gagnée, repos compris
    rested_used: float = 0.0  # XP prise au réservoir de repos
    terms: tuple[Term, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Party:
    """Niveaux des membres du groupe, joueur compris (un seul niveau : seul)."""

    levels: tuple[int, ...]


@dataclass(frozen=True)
class QuestXpInput:
    """XP de base d'une quête (avant l'écart de niveau) et sa provenance : client (quête vue), addon ou Questie."""

    level: int
    base_xp: float
    source: str
    certainty: str


CLIENT_KILL_XP = "client : GameTable xp, colonne PerKill (character_scaling.json kill_xp)"


def xp_rules(gd: GameData) -> XpRules:
    """Règles d'XP de la version ; DataSchemaError si la version ne les porte pas."""
    if gd.xp is None:
        raise DataSchemaError(
            f"Règles d'XP absentes des données de {gd.game_version} (mechanics.json, clés xp.*).",
            "installer une version de données de T04d ou plus récente",
        )
    return gd.xp


def _term(rules: XpRules, key: str, factor: float) -> Term:
    src = rules.sources.get(key)
    return Term(key, factor, src.certainty if src else "suppose", src.source if src else key)


def base_kill_xp(gd: GameData, level: int) -> tuple[float, Term]:
    """XP d'un monstre normal de même niveau que le joueur de niveau `level` (client, sinon règle).

    Registre : I6"""
    table = gd.leveling.kill_xp_by_level
    if table and 1 <= level <= len(table):
        return table[level - 1], Term("kill_xp", table[level - 1], "certain", CLIENT_KILL_XP)
    lv = gd.leveling
    value = lv.xp_base + lv.xp_per_level * level
    return value, Term("leveling.mob_xp", value, "suppose", "règle de Classic (leveling.mob_xp)")


def gray_level(gd: GameData, player_level: int) -> int:
    """Niveau de monstre le plus haut encore gris (aucune XP) pour `player_level` (règle de Classic, I7).

    Registre : I6, I7"""
    return leveling.gray_level(gd, player_level)


def _zero_difference(rules: XpRules, player_level: int) -> int:
    for top, zd in rules.zero_difference:
        if player_level <= top:
            return zd
    return rules.zero_difference[-1][1]


def _level_factor(gd: GameData, rules: XpRules, player_level: int, mob_level: int) -> float:
    if mob_level >= player_level:
        return 1 + rules.higher_per_level * min(mob_level - player_level, rules.higher_max_diff)
    if mob_level <= gray_level(gd, player_level):
        return 0.0
    return 1 - (player_level - mob_level) / _zero_difference(rules, player_level)


def mob_kill_xp(
    gd: GameData,
    player_level: int,
    mob_level: int,
    *,
    elite: bool = False,
    dungeon: bool = False,
    party: Party | None = None,
    rested_pool: float = 0.0,
    bonuses: XpBonusState | None = None,
    creature_type: int | None = None,
) -> XpResult:
    """XP d'un monstre tué : base, écart de niveau, élite, donjon, groupe, puis repos (dans la limite du réservoir).

    Registre : I6, I10, I11, I13, D7"""
    if gd.xp is None and mob_level == player_level and not (elite or dungeon or party or rested_pool or bonuses):
        base, base_term = base_kill_xp(gd, player_level)
        return XpResult(base, 0.0, (base_term,))  # version sans règles d'XP : monstre de même niveau seulement
    rules = xp_rules(gd)
    # niveau d'assiette : celui du joueur (individual), ou du plus haut membre du groupe (highest_member, variante)
    basis = player_level
    if party is not None and len(party.levels) > 1 and rules.group_level_basis == "highest_member":
        basis = max(party.levels)
    lower = mob_level < basis and mob_level > gray_level(gd, basis)
    # monstre plus bas : XP de base au niveau du monstre (xp.lower_mob_base, relevés du joueur) ou du joueur
    base, base_term = base_kill_xp(gd, mob_level if lower and rules.lower_base == "mob" else basis)
    terms = [base_term]
    xp = base
    level = _level_factor(gd, rules, basis, mob_level)
    if mob_level != basis:
        terms.append(_term(rules, "xp.mob_level_difference", level))
        if lower:
            terms.append(_term(rules, "xp.lower_mob_base", base / base_kill_xp(gd, basis)[0]))
        xp *= level
    if elite:
        terms.append(_term(rules, "xp.elite_factor", rules.elite_factor))
        xp *= rules.elite_factor
    if dungeon:
        terms.append(_term(rules, "xp.dungeon_kill_bonus", 1 + rules.dungeon_bonus))
        xp *= 1 + rules.dungeon_bonus
    if party is not None and len(party.levels) > 1:
        size = len(party.levels)
        rate = rules.group_rates[min(size, len(rules.group_rates)) - 1]
        share = rate * player_level / sum(party.levels)
        terms.append(_term(rules, "xp.group", share))
        xp *= share
    before_bonus = xp
    if bonuses is not None:  # T04f : bonus d'XP des auras, après groupe et donjon (D10)
        factor, bonus_terms = xp_multiplier(gd, bonuses, source="kill", creature_type=creature_type)
        if factor != 1.0:
            terms += bonus_terms
            xp *= factor
    used = 0.0
    if rested_pool > 0 and xp > 0:
        rested_after = gd.xp_bonuses.rested_after if gd.xp_bonuses is not None else True
        used = min((xp if rested_after else before_bonus) * (rules.rested_factor - 1), rested_pool)
        terms.append(_term(rules, "xp.rested", (xp + used) / xp))
        xp += used
    return XpResult(xp, used, tuple(terms))


def quest_xp(gd: GameData, player_level: int, quest: QuestXpInput, *, bonuses: XpBonusState | None = None) -> XpResult:
    """XP d'une quête rendue : XP de base réduite selon l'écart de niveau ; jamais de repos.

    Registre : I12"""
    rules = xp_rules(gd)
    terms = [Term("quest_base_xp", quest.base_xp, quest.certainty, quest.source)]
    beyond = player_level - quest.level - rules.quest_full_diff
    factor = 1.0
    if beyond > 0:
        factor = rules.quest_reduction[min(beyond, len(rules.quest_reduction)) - 1]
        terms.append(_term(rules, "xp.quest_level_difference", factor))
    xp = quest.base_xp * factor
    if bonuses is not None:  # T04f : bonus d'XP des quêtes (D10)
        bonus, bonus_terms = xp_multiplier(gd, bonuses, source="quest")
        if bonus != 1.0:
            terms += bonus_terms
            xp *= bonus
    return XpResult(xp, 0.0, tuple(terms))


def rested_gain(gd: GameData, level: int, hours: float, *, inn: bool, pool: float = 0.0, legacy_rank: int = 0) -> float:
    """Réservoir de repos après `hours` heures hors ligne (auberge ou dehors), plafonné.

    `legacy_rank` : rang du perk Legacy Well Rested (T04f) : gain multiplié par (1 + valeur du rang).

    Registre : D7, D5"""
    rules = xp_rules(gd)
    per_period = rules.rested_gain_per_period * _level_xp(gd, level) * (1.0 if inn else rules.rested_outdoor_ratio)
    gained = per_period * hours / rules.rested_period_h * (1 + _legacy_rested(gd, legacy_rank, "rested_gain"))
    return min(pool + gained, rested_cap(gd, level, legacy_rank))


def _level_xp(gd: GameData, level: int) -> float:
    return float(gd.xp_to_next[min(level, len(gd.xp_to_next)) - 1])


# --- T04f : bonus d'XP (registre : D5, D7, D9, D10, E3) ---------------------------------------------------------


@dataclass(frozen=True)
class ActiveAura:
    """Aura d'XP active : sort du client, cumuls, temps restant (None : sans fin connue)."""

    spell_id: int
    stacks: int = 1
    remaining_s: float | None = None


@dataclass(frozen=True)
class XpBonusState:
    """Bonus d'XP du personnage à un instant : auras actives, nourriture nutritive (renouvelée), rangs des perks
    Legacy (sort du perk -> rang), tente disponible."""

    auras: tuple[ActiveAura, ...] = ()
    food: bool = False
    legacy_ranks: Mapping[int, int] = field(default_factory=dict)
    tent_ready: bool = False


@dataclass(frozen=True)
class SessionXp:
    """Séance de jeu déroulée pas à pas : XP par heure moyenne, XP totale, repos consommé, part de chaque bonus."""

    xp_h: float
    base_xp_h: float
    hours: float
    total_xp: float
    rested_used: float
    by_bonus: Mapping[str, float]  # XP gagnée grâce à chaque bonus (clé : xp_bonus.<sort> ou xp.rested)
    terms: tuple[Term, ...]


PERCENT = 100.0  # conversion d'unité : pourcentage du client -> fraction
_RANK = {"certain": 2, "probable": 1, "suppose": 0}
STACKING_RULE = "xp.bonus_stacking"


def _min_certainty(*values: str) -> str:
    return min(values, key=lambda c: _RANK.get(c, 0))


def xp_bonus_data(gd: GameData) -> XpBonusData:
    """Bonus d'XP de la version ; DataSchemaError si elle ne les porte pas (`xp_bonuses.json`, `xp.bonus_*`)."""
    if gd.xp_bonuses is None:
        raise DataSchemaError(
            f"Bonus d'XP absents des données de {gd.game_version} (xp_bonuses.json, mechanics.json xp.bonus_*).",
            "installer une version de données de T04f ou plus récente",
        )
    return gd.xp_bonuses


def _active(state: XpBonusState, data: XpBonusData) -> list[ActiveAura]:
    """Auras actives de l'état, avec l'aura de nourriture quand `food` (bonus permanent tant que la nourriture
    nutritive est renouvelée, xp.food_bonus)."""
    active = list(state.auras)
    if state.food:
        for a in data.auras.values():
            if a.access == "food" and all(x.spell_id != a.spell_id for x in active):
                active.append(ActiveAura(a.spell_id))
    return active


def _applied(
    data: XpBonusData, auras: list[ActiveAura], source: str, creature_type: int | None
) -> list[tuple[XpBonusAura, float]]:
    """(aura, part ajoutée) de chaque aura applicable à `source` ; une aura sans source joueur (`none`) ou épuisée
    n'entre jamais ; cumuls bornés au maximum du client."""
    out: dict[int, tuple[XpBonusAura, float]] = {}
    for active in auras:
        a = data.auras.get(active.spell_id)
        if a is None or a.access == "none" or (active.remaining_s is not None and active.remaining_s <= 0):
            continue
        stacks = max(0, min(active.stacks, a.max_stacks))
        for e in a.effects:
            if e.applies_to != source or not e.value:
                continue
            if e.key == "creature_type_kill_xp_pct" and e.misc != creature_type:
                continue
            prev = out.get(a.spell_id, (a, 0.0))[1]
            out[a.spell_id] = (a, prev + e.value * stacks / PERCENT)
    return [v for v in out.values() if v[1]]


def _bonus_term(a: XpBonusAura, part: float) -> Term:
    return Term(
        f"xp_bonus.{a.spell_id}",
        1 + part,
        _min_certainty(a.meaning_certainty, a.access_certainty),
        f"client : {a.name} (sort {a.spell_id}, xp_bonuses.json)",
    )


def _stacking_term(data: XpBonusData, factor: float) -> Term:
    src = data.sources.get(STACKING_RULE)
    return Term(STACKING_RULE, factor, src.certainty if src else "suppose", src.source if src else STACKING_RULE)


def _combine(parts: list[float], mode: str) -> float:
    if mode == "multiplicative":
        return math.prod(1 + p for p in parts)
    return 1 + sum(parts)


def xp_multiplier(
    gd: GameData,
    state: XpBonusState | None,
    *,
    source: str,
    mode: str | None = None,
    creature_type: int | None = None,
) -> tuple[float, tuple[Term, ...]]:
    """Facteur des bonus d'XP actifs pour `source` (`kill` ou `quest`) : somme des pourcentages (règle
    xp.bonus_stacking ; `mode` « multiplicative » : variante) ; un terme par bonus, plus la règle de cumul quand
    plusieurs bonus se cumulent.

    Registre : D9, D10, E3"""
    if state is None:
        return 1.0, ()
    data = xp_bonus_data(gd)
    applied = _applied(data, _active(state, data), source, creature_type)
    if not applied:
        return 1.0, ()
    factor = _combine([p for _, p in applied], mode or data.stacking)
    terms = [_bonus_term(a, p) for a, p in applied]
    if len(applied) > 1:
        terms.append(_stacking_term(data, factor))
    return factor, tuple(terms)


def _legacy_rested(gd: GameData, rank: int, applies_to: str) -> float:
    """Part ajoutée par le perk Legacy de repos au rang `rank` (0 : aucun) au gain ou au plafond du repos."""
    if rank <= 0:
        return 0.0
    for a in xp_bonus_data(gd).auras.values():
        if a.access != "legacy":
            continue
        for e in a.effects:
            if e.applies_to == applies_to and e.ranks:
                return e.ranks[min(rank, len(e.ranks)) - 1] / PERCENT
    return 0.0


def rested_cap(gd: GameData, level: int, legacy_rank: int = 0) -> float:
    """Plafond du réservoir de repos, relevé par le perk Legacy Well Rested (xp.legacy_rested).

    Registre : D7, D5"""
    rules = xp_rules(gd)
    return rules.rested_cap_levels * _level_xp(gd, level) * (1 + _legacy_rested(gd, legacy_rank, "rested_cap"))


def tent_rested(gd: GameData, level: int, pool: float) -> float:
    """Réservoir après la tente du camp : remonté au seuil lu (pourcentage d'un niveau), inchangé au-dessus
    (xp.camp_tent).

    Registre : D5"""
    data = xp_bonus_data(gd)
    if data.tent_threshold_pct is None:
        return pool
    return max(pool, data.tent_threshold_pct / PERCENT * _level_xp(gd, level))


def sleeping_bag_state(gd: GameData, stacks: int | None = None) -> XpBonusState:
    """État juste après le sac de couchage : Well-Rested à `stacks` cumuls (défaut : le maximum du client), durée
    entière.

    Registre : D9"""
    data = xp_bonus_data(gd)
    bag = data.sleeping_bag
    if bag is None:
        raise DataSchemaError(f"Sac de couchage absent des données de {gd.game_version} (xp_bonuses.json).")
    return XpBonusState(auras=(ActiveAura(bag.aura, stacks or bag.max_stacks, data.auras[bag.aura].duration_s),))


def _covered(active: list[ActiveAura], elapsed: float, dt_s: float) -> list[tuple[ActiveAura, float]]:
    """Part du pas couverte par chaque aura encore active."""
    out = []
    for a in active:
        share = 1.0 if a.remaining_s is None else min(max((a.remaining_s - elapsed) / dt_s, 0.0), 1.0)
        if share > 0:
            out.append((a, share))
    return out


def session_xp(
    gd: GameData,
    *,
    base_xp_h: float,
    kill_share: float,
    hours: float,
    state: XpBonusState | None,
    rested_pool: float,
    level: int,
    step_s: float = 60.0,
) -> SessionXp:
    """Séance de `hours` heures à `base_xp_h` d'XP par heure sans bonus (part `kill_share` venue des monstres, le
    reste des quêtes), déroulée par pas de `step_s` secondes : chaque aura compte sur son temps restant, le repos
    s'applique aux monstres jusqu'à épuisement du réservoir. Rend l'XP par heure moyenne et la part de chaque bonus
    (`level` : niveau du personnage, gardé pour les règles qui en dépendent).

    Registre : D7, D9, D10, E3"""
    if hours <= 0:
        raise ValueError("durée de séance positive attendue")
    steps = max(1, math.ceil(hours * 3600 / step_s))
    dt_s = hours * 3600 / steps
    data = xp_bonus_data(gd) if state is not None else None
    rules = xp_rules(gd) if rested_pool > 0 else None
    pool, used_total, total = rested_pool, 0.0, 0.0
    by: dict[str, float] = defaultdict(float)
    terms: dict[str, Term] = {}
    active = _active(state, data) if state is not None and data is not None else []
    for i in range(steps):
        kill = base_xp_h * dt_s / 3600 * kill_share
        quest = base_xp_h * dt_s / 3600 * (1 - kill_share)
        gained, kill_after = kill + quest, kill
        if data is not None:
            now = _covered(active, i * dt_s, dt_s)
            weights = {a.spell_id: w for a, w in now}
            for amount, source in ((kill, "kill"), (quest, "quest")):
                applied = [(a, p * weights[a.spell_id]) for a, p in _applied(data, [a for a, _ in now], source, None)]
                if not amount or not applied:
                    continue
                factor = _combine([p for _, p in applied], data.stacking)
                extra = amount * (factor - 1)
                weight = sum(p for _, p in applied)
                for a, p in applied:
                    by[f"xp_bonus.{a.spell_id}"] += extra * p / weight
                    terms.setdefault(f"xp_bonus.{a.spell_id}", _bonus_term(a, p))
                if len(applied) > 1:
                    terms.setdefault(STACKING_RULE, _stacking_term(data, factor))
                gained += extra
                if source == "kill":
                    kill_after = kill * factor
        if rules is not None and pool > 0 and kill > 0:
            rested_after = data.rested_after if data is not None else True
            used = min((kill_after if rested_after else kill) * (rules.rested_factor - 1), pool)
            pool -= used
            used_total += used
            gained += used
            by["xp.rested"] += used
            terms.setdefault("xp.rested", _term(rules, "xp.rested", rules.rested_factor))
        total += gained
    return SessionXp(
        xp_h=total / hours,
        base_xp_h=base_xp_h,
        hours=hours,
        total_xp=total,
        rested_used=used_total,
        by_bonus={k: v for k, v in by.items() if v},
        terms=tuple(terms.values()),
    )
