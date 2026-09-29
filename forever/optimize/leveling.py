"""Ordre des talents pour le leveling (T05, décision 84) : faisceau sur les ordres légaux, présélection à l'analytique
avec anticipation gloutonne, décision au Monte Carlo ; score = somme des temps par monstre pondérés par l'XP de chaque
niveau (heures équivalentes).

Portage de seed/forever-mage/scripts/optimize.py (`leveling`, `rollout_value`, `score_plan`, `level_weight`) : en mode
seed (`rules="seed"`), les méthodes du seed à l'identique (rotations frost et fire, deux Monte Carlo par candidat).
En mode forever, les choix du build (rotation, armure, `ab_stacks`, `ab_dump`, `hs_stacks`) sont cherchés avec les
talents : évaluation rapide (rotations aux défauts) pour la présélection et l'anticipation, complète (toutes les
combinaisons légales) pour les finalistes, un seul Monte Carlo sur la meilleure combinaison.

Registre : I5, I6"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, NamedTuple

from forever.engine.armor import worn_armor
from forever.engine.buffs import hot_streak_rules
from forever.engine.model import CharacterOverrides, GameData, Points
from forever.engine.monsters import mob_xp
from forever.engine.talents import check_build, legal_additions, points_available
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import AB_DUMPS, ROTATIONS, arcane_plan, mc

# Paramètres de méthode du seed (optimize.py), pas des chiffres de jeu : poids du temps immédiat et de l'anticipation
# dans la présélection, poids de l'anticipation dans le tri du faisceau.
NOW_WEIGHT, LOOK_WEIGHT, BEAM_LOOK_WEIGHT = 0.5, 0.5, 0.25
SECONDS_PER_HOUR = 3600.0
SEED_ROTATIONS = ("frost", "fire")


class BuildChoice(NamedTuple):
    """Choix du build hors talents : rotation et paramètres des simulateurs (None : défaut du simulateur)."""

    rotation: str
    armor: str = "auto"
    ab_stacks: int | None = None
    ab_dump: str | None = None
    hs_stacks: int | None = None
    aoe_filler: str | None = None  # scénarios de paquet (rotation aoe)

    def options(self) -> dict[str, Any]:
        """Options des simulateurs correspondant au choix (clés non nulles, armure seulement si elle est forcée)."""
        out: dict[str, Any] = {}
        if self.armor != "auto":
            out["armor"] = self.armor
        for key in ("ab_stacks", "ab_dump", "hs_stacks", "aoe_filler"):
            if getattr(self, key) is not None:
                out[key] = getattr(self, key)
        return out


class Step(NamedTuple):
    """Étape du chemin : niveau, talent pris (None si aucun point), temps par monstre arrondi comme le seed, rotation,
    choix complet du build."""

    level: int
    talent: str | None
    time_s: float
    rotation: str
    choice: BuildChoice


class LevelingPath(NamedTuple):
    hours_equiv: float
    points: dict[str, int]
    steps: tuple[Step, ...]


class PlanScore(NamedTuple):
    hours_equiv: float
    steps: tuple[tuple[int, float, str], ...]
    points: dict[str, int]


def level_weight(gd: GameData, level: int) -> float:
    """Poids d'un niveau : XP pour passer au niveau suivant / XP d'un monstre du niveau (monstres par niveau) ; 0 au
    plafond (aucune XP à gagner), comme le seed.

    Registre : I5, I6"""
    xp = gd.xp_to_next
    return xp[level - 1] / mob_xp(gd, level) if level - 1 < len(xp) else 0.0


def _rotations(gd: GameData, level: int, pts: Points, rules: str) -> list[str]:
    if rules == "seed":
        return list(SEED_ROTATIONS)
    out = ["frost", "fire"]
    try:
        arcane_plan(gd, level, pts, None, None)
        out.append("arcane")
    except ValueError:
        pass
    return [r for r in ROTATIONS if r in out]


def _armors(gd: GameData, level: int) -> list[str]:
    out = ["frost"]
    try:
        worn_armor(gd, level, "mage")
        out.append("mage")
    except ValueError:
        pass
    return out


def build_choices(
    gd: GameData, level: int, pts: Points, *, rules: str = "forever", full: bool = False
) -> list[BuildChoice]:
    """Choix du build possibles à un niveau : rotations apprises (seed : frost, fire), et en évaluation complète les
    armures apprises, `ab_stacks` × `ab_dump` appris, `hs_stacks`.

    Registre : I1, I5"""
    rotations = _rotations(gd, level, pts, rules)
    if not full or rules == "seed":
        return [BuildChoice(r) for r in rotations]
    hs = hot_streak_rules(gd, pts)
    out: list[BuildChoice] = []
    for armor in _armors(gd, level):
        for rot in rotations:
            if rot == "arcane":
                top, _ = arcane_plan(gd, level, pts, None, None)
                for dump in AB_DUMPS:
                    try:
                        arcane_plan(gd, level, pts, None, dump)
                    except ValueError:
                        continue
                    out += [BuildChoice(rot, armor, n, dump) for n in range(top + 1)]
            elif rot == "fire" and hs is not None:
                out += [BuildChoice(rot, armor, hs_stacks=n) for n in range(1, hs[2] + 1)]
            else:
                out.append(BuildChoice(rot, armor))
    return out


def best_choice(
    gd: GameData,
    level: int,
    pts: Points,
    race: str = "Orc",
    over: CharacterOverrides | None = None,
    *,
    rules: str = "forever",
    full: bool = False,
    **options: Any,
) -> tuple[float, BuildChoice]:
    """(temps par monstre à l'analytique, choix) le plus court ; égalités départagées comme le seed (nom de rotation),
    puis par l'ordre de `build_choices`.

    Registre : I5"""
    sim = {"rules": rules, **options}
    scored = []
    for i, c in enumerate(build_choices(gd, level, pts, rules=rules, full=full)):
        try:
            total = kill_analytic(gd, level, pts, race, c.rotation, over, **sim, **c.options())["total"]
        except ValueError:  # combinaison impossible à ce niveau (sort principal non appris)
            continue
        scored.append((total, c.rotation, i, c))
    if not scored:
        raise ValueError(f"aucune rotation possible au niveau {level}")
    total, _, _, choice = min(scored, key=lambda x: x[:3])
    return total, choice


def _rollout(
    gd: GameData,
    level: int,
    pts: Points,
    race: str,
    over: CharacterOverrides | None,
    depth: int,
    rules: str,
    bonus: int,
    opts: dict[str, Any],
) -> float:
    """Anticipation gloutonne du seed : `depth` points ajoutés un par un au meilleur temps, temps au dernier niveau."""
    p = dict(pts)
    for d in range(depth):
        lv = level + d + 1
        cands = legal_additions(gd, p, lv, bonus)
        if not cands:
            break

        def time_with(k: str, lv: int = lv) -> float:
            return best_choice(gd, lv, {**p, k: p.get(k, 0) + 1}, race, over, rules=rules, **opts)[0]

        best = min(cands, key=time_with)
        p[best] = p.get(best, 0) + 1
    return best_choice(gd, min(gd.level_cap, level + depth), p, race, over, rules=rules, **opts)[0]


def _decide_step(
    gd: GameData,
    level: int,
    pts: Points,
    race: str,
    over: CharacterOverrides | None,
    rules: str,
    mc_n: int,
    seed: int,
    options: dict[str, Any],
) -> tuple[float, BuildChoice]:
    """Temps retenu pour un candidat présélectionné : seed, un Monte Carlo par rotation (le plus court) ; forever, la
    meilleure combinaison complète à l'analytique, passée une fois au Monte Carlo ; sans Monte Carlo, l'analytique."""
    if not mc_n:
        return best_choice(gd, level, pts, race, over, rules=rules, full=rules != "seed", **options)
    sim = {"rules": rules, **options}
    if rules == "seed":
        t, rot = min((mc(gd, level, pts, race, r, mc_n, seed, over, **sim)["total"], r) for r in SEED_ROTATIONS)
        return t, BuildChoice(rot)
    _, choice = best_choice(gd, level, pts, race, over, rules=rules, full=True, **options)
    return mc(gd, level, pts, race, choice.rotation, mc_n, seed, over, **sim, **choice.options())["total"], choice


def _passes(gd: GameData, lfrom: int, lto: int, spent: int, bonus: int) -> list[tuple[int, bool]]:
    """Passes du faisceau : (niveau, dernière passe du niveau) ; une passe par point à dépenser, au moins une par
    niveau (le seed : un point par niveau)."""
    out: list[tuple[int, bool]] = []
    for level in range(lfrom, lto + 1):
        n = max(1, points_available(gd, level, bonus) - spent)
        spent = max(spent, points_available(gd, level, bonus))
        out += [(level, i == n - 1) for i in range(n)]
    return out


def optimize_leveling(
    gd: GameData,
    race: str,
    lfrom: int,
    lto: int,
    *,
    beam: int = 3,
    depth: int = 4,
    shortlist: int = 4,
    mc_n: int = 200,
    seed: int = 12345,
    rules: str = "forever",
    start: Points | None = None,
    over: CharacterOverrides | None = None,
    talented_bonus: int = 0,
    **options: Any,
) -> LevelingPath:
    """Meilleur ordre des talents de `lfrom` à `lto` (faisceau, anticipation, Monte Carlo sur la présélection) ;
    ValueError si le build de départ est illégal au niveau `lfrom`.

    Registre : I5, I6"""
    start_pts = {k: v for k, v in (start or {}).items() if v}
    errors = check_build(gd, start_pts, lfrom, talented_bonus)
    if errors:
        raise ValueError(f"build de départ illégal au niveau {lfrom} : {' ; '.join(errors)}")
    beams: list[tuple[float, dict[str, int], list[Step]]] = [(0.0, dict(start_pts), [])]
    for level, last in _passes(gd, lfrom, lto, sum(start_pts.values()), talented_bonus):
        # plusieurs points au même niveau (bonus Talented, build de départ) : une étape par point, le temps du niveau
        # compté une seule fois, sur le build de fin de niveau (Monte Carlo sur cette dernière étape seulement)
        weight = level_weight(gd, level) if last else 0.0
        nxt: list[tuple[float, float, dict[str, int], list[Step]]] = []
        for score, pts, hist in beams:
            cands: list[str | None] = [*legal_additions(gd, pts, level, talented_bonus)] or [None]
            pre = []
            for k in cands:
                p2 = dict(pts)
                if k:
                    p2[k] = p2.get(k, 0) + 1
                t_now = best_choice(gd, level, p2, race, over, rules=rules, **options)[0]
                d = min(depth, gd.level_cap - level)
                look = (
                    _rollout(gd, level, p2, race, over, d, rules, talented_bonus, options)
                    if depth and level < lto
                    else t_now
                )
                pre.append((NOW_WEIGHT * t_now + LOOK_WEIGHT * look, k, p2))
            pre.sort(key=lambda x: x[0])
            for look, k, p2 in pre[:shortlist]:
                t_now, choice = _decide_step(gd, level, p2, race, over, rules, mc_n if last else 0, seed, options)
                step = Step(level, k, round(t_now, 2), choice.rotation, choice)
                nxt.append((score + t_now * weight, look, p2, [*hist, step]))
        nxt.sort(key=lambda x: x[0] + BEAM_LOOK_WEIGHT * x[1] * weight)
        seen: set[tuple[tuple[str, int], ...]] = set()
        beams = []
        for sc, _, p2, h in nxt:
            sig = tuple(sorted(p2.items()))
            if sig in seen:
                continue
            seen.add(sig)
            beams.append((sc, p2, h))
            if len(beams) >= beam:
                break
    sc, pts, hist = min(beams, key=lambda b: b[0])
    return LevelingPath(sc / SECONDS_PER_HOUR, pts, tuple(hist))


def score_plan(
    gd: GameData,
    plan: Sequence[tuple[int, str | None]],
    race: str = "Orc",
    over: CharacterOverrides | None = None,
    *,
    rules: str = "forever",
    talented_bonus: int = 0,
    **options: Any,
) -> PlanScore:
    """Heures équivalentes d'un plan (niveau, talent) : même métrique que `optimize_leveling`, analytique seulement ;
    ValueError si le plan est illégal à un niveau.

    Registre : I5"""
    pts: dict[str, int] = {}
    total = 0.0
    steps: list[tuple[int, float, str]] = []
    for level in range(min(lv for lv, _ in plan), max(lv for lv, _ in plan) + 1):
        for lv, k in plan:
            if lv == level and k:
                pts[k] = pts.get(k, 0) + 1
        errors = check_build(gd, pts, level, talented_bonus)
        if errors:
            raise ValueError(f"plan illégal au niveau {level} : {' ; '.join(errors)}")
        t, choice = best_choice(gd, level, pts, race, over, rules=rules, **options)
        total += t * level_weight(gd, level)
        steps.append((level, round(t, 2), choice.rotation))
    return PlanScore(total / SECONDS_PER_HOUR, tuple(steps), pts)
