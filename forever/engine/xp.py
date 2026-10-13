"""Modèle d'XP de Forever (T04d, bloc C) : XP d'un monstre et d'une quête, repos, donjon, élite, groupe.

Fonctions pures. Chaque règle vient des données de la version (`gd.xp`, clés `xp.*` de `mechanics.json` et palier
« Rested » de `character_scaling.json` ; XP de base d'un monstre : colonne `PerKill` de la GameTable `xp` décodée,
sinon `leveling.mob_xp`) ; chaque résultat porte la liste des termes appliqués avec leur certitude et leur source.
Aucun chiffre de jeu ici. Unités : points d'XP (nombres à virgule, arrondis à l'affichage seulement), heures."""

from __future__ import annotations

from dataclasses import dataclass, field

from forever.engine.model import GameData, XpRules


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


def xp_rules(gd: GameData) -> XpRules:
    """Règles d'XP de la version ; DataSchemaError si la version ne les porte pas."""
    raise NotImplementedError


def base_kill_xp(gd: GameData, level: int) -> tuple[float, Term]:
    """XP d'un monstre normal de même niveau que le joueur de niveau `level` (client, sinon règle).

    Registre : I6"""
    raise NotImplementedError


def gray_level(gd: GameData, player_level: int) -> int:
    """Niveau de monstre le plus haut encore gris (aucune XP) pour `player_level` (règle de Classic, I7).

    Registre : I6"""
    raise NotImplementedError


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
    raise NotImplementedError


def quest_xp(gd: GameData, player_level: int, quest: QuestXpInput) -> XpResult:
    """XP d'une quête rendue : XP de base réduite selon l'écart de niveau ; jamais de repos.

    Registre : I12"""
    raise NotImplementedError


def rested_gain(gd: GameData, level: int, hours: float, *, inn: bool, pool: float = 0.0) -> float:
    """Réservoir de repos après `hours` heures hors ligne (auberge ou dehors), plafonné.

    Registre : D7"""
    raise NotImplementedError
