"""Rendements décroissants des contrôles en PvP (PV1, bloc C) : durée effective d'applications successives.

Fonction pure. Règles du serveur (paliers, fenêtre de remise à zéro et son point de départ, plafond de durée sur un
joueur) lues dans `pvp_rules.json` (`gamedata.dr_rules`, certitude `suppose`) ; catégorie de chaque contrôle : masque
`DiminishType` du client (`classes.json`, certain), 0 pour un contrôle sans catégorie. Les applications visent un
joueur (PvP) : les rendements contre les PNJ ne sont pas modélisés."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DrRules:
    """Règles du serveur : multiplicateurs des applications successives (au-delà : immunité), fenêtre de remise à
    zéro en secondes et son point de départ (`fin` de l'effet précédent ou `application`), plafond de durée sur un
    joueur (None : aucun)."""

    steps: tuple[float, ...]
    window_s: float
    window_from: str
    pvp_cap_s: float | None


@dataclass(frozen=True)
class Application:
    """Contrôle appliqué à l'instant `time_s` (secondes), de catégorie `category` (masque du client, 0 : aucune),
    de durée pleine `duration_s` ; `pvp_duration_s` : durée PvP du client quand elle existe."""

    time_s: float
    category: int
    duration_s: float
    pvp_duration_s: float | None = None


@dataclass(frozen=True)
class DrResult:
    """Durée effective, palier atteint (à partir de 1 ; None sans catégorie ou en immunité), immunité."""

    duration_s: float
    step: int | None
    immune: bool


def effective_durations(rules: DrRules, applications: Sequence[Application]) -> list[DrResult]:
    """Durée effective de chaque application, dans l'ordre de leurs instants. Registre : K1, K3."""
    raise NotImplementedError
