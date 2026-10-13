"""Modèle d'XP de Forever (T04d, bloc C) : XP d'un monstre et d'une quête, repos, donjon, élite, groupe.

Fonctions pures. Chaque règle vient des données de la version (`gd.xp`, clés `xp.*` de `mechanics.json` et palier
« Rested » de `character_scaling.json` ; XP de base d'un monstre : colonne `PerKill` de la GameTable `xp` décodée,
sinon `leveling.mob_xp`) ; chaque résultat porte la liste des termes appliqués avec leur certitude et leur source.
Aucun chiffre de jeu ici. Unités : points d'XP (nombres à virgule, arrondis à l'affichage seulement), heures."""

from __future__ import annotations

from dataclasses import dataclass, field

from forever.engine import leveling
from forever.engine.model import GameData, XpRules
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

    Registre : I6"""
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
) -> XpResult:
    """XP d'un monstre tué : base, écart de niveau, élite, donjon, groupe, puis repos (dans la limite du réservoir).

    Registre : I6, I10, I11, I13, D7"""
    if gd.xp is None and mob_level == player_level and not (elite or dungeon or party or rested_pool):
        base, base_term = base_kill_xp(gd, player_level)
        return XpResult(base, 0.0, (base_term,))  # version sans règles d'XP : monstre de même niveau seulement
    rules = xp_rules(gd)
    # niveau d'assiette : celui du joueur (individual), ou du plus haut membre du groupe (highest_member, variante)
    basis = player_level
    if party is not None and len(party.levels) > 1 and rules.group_level_basis == "highest_member":
        basis = max(party.levels)
    base, base_term = base_kill_xp(gd, basis)
    terms = [base_term]
    xp = base
    level = _level_factor(gd, rules, basis, mob_level)
    if mob_level != basis:
        terms.append(_term(rules, "xp.mob_level_difference", level))
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
    used = 0.0
    if rested_pool > 0 and xp > 0:
        used = min(xp * (rules.rested_factor - 1), rested_pool)
        terms.append(_term(rules, "xp.rested", (xp + used) / xp))
        xp += used
    return XpResult(xp, used, tuple(terms))


def quest_xp(gd: GameData, player_level: int, quest: QuestXpInput) -> XpResult:
    """XP d'une quête rendue : XP de base réduite selon l'écart de niveau ; jamais de repos.

    Registre : I12"""
    rules = xp_rules(gd)
    terms = [Term("quest_base_xp", quest.base_xp, quest.certainty, quest.source)]
    beyond = player_level - quest.level - rules.quest_full_diff
    factor = 1.0
    if beyond > 0:
        factor = rules.quest_reduction[min(beyond, len(rules.quest_reduction)) - 1]
        terms.append(_term(rules, "xp.quest_level_difference", factor))
    return XpResult(quest.base_xp * factor, 0.0, tuple(terms))


def rested_gain(gd: GameData, level: int, hours: float, *, inn: bool, pool: float = 0.0) -> float:
    """Réservoir de repos après `hours` heures hors ligne (auberge ou dehors), plafonné.

    Registre : D7"""
    rules = xp_rules(gd)
    level_xp = gd.xp_to_next[min(level, len(gd.xp_to_next)) - 1]
    per_period = rules.rested_gain_per_period * level_xp * (1.0 if inn else rules.rested_outdoor_ratio)
    gained = per_period * hours / rules.rested_period_h
    return min(pool + gained, rules.rested_cap_levels * level_xp)
