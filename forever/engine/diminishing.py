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
    """Durée effective de chaque application, dans l'ordre donné (trié par instant). Base : durée PvP du client si
    présente, sinon durée pleine, bornée par le plafond PvP ; puis multiplicateur du palier de la catégorie ; au-delà
    du dernier palier, immunité (durée nulle) jusqu'à la remise à zéro. Registre : K1, K3."""
    if rules.window_from not in ("fin", "application"):
        raise ValueError(f"point de départ de la fenêtre inconnu : {rules.window_from}")
    count: dict[int, int] = {}
    reference: dict[int, float] = {}
    out: list[DrResult] = []
    for app in sorted(applications, key=lambda a: a.time_s):
        base = app.pvp_duration_s if app.pvp_duration_s is not None else app.duration_s
        if rules.pvp_cap_s is not None:
            base = min(base, rules.pvp_cap_s)
        if app.category == 0:
            out.append(DrResult(base, None, False))
            continue
        if app.category in reference and app.time_s - reference[app.category] >= rules.window_s:
            count[app.category] = 0
        n = count.get(app.category, 0) + 1
        count[app.category] = n
        if n > len(rules.steps):
            out.append(DrResult(0.0, None, True))
            reference[app.category] = app.time_s
            continue
        duration = base * rules.steps[n - 1]
        out.append(DrResult(duration, n, False))
        reference[app.category] = app.time_s + duration if rules.window_from == "fin" else app.time_s
    return out
