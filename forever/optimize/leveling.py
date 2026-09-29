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
from forever.engine.talents import check_build, legal_additions, points_available, tier_points_required
from forever.optimize.decide import gap_dict, paired_gap, tie_break
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import AB_DUMPS, ROTATIONS, McStats, arcane_plan, mc, mc_stats

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
    choix complet du build ; en mode forever (T06b, décision D7), la décision : second candidat de l'état, écart
    apparié (étape − second), significativité, talent modélisé, origine (`DECIDED_BY`). Mode seed : None."""

    level: int
    talent: str | None
    time_s: float
    rotation: str
    choice: BuildChoice
    runner_up: str | None = None
    gap: dict[str, Any] | None = None
    significant: bool | None = None
    modeled: bool | None = None
    decided_by: str | None = None


class _Eval(NamedTuple):
    """Candidat présélectionné d'un état du faisceau : score de présélection, talent, build, additions de
    l'anticipation, temps retenu, choix, statistiques du Monte Carlo (None : passe sans Monte Carlo)."""

    look: float
    talent: str | None
    points: dict[str, int]
    picks: tuple[str, ...]
    time_s: float
    choice: BuildChoice
    stats: McStats | None


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


def _rollout_path(
    gd: GameData,
    level: int,
    pts: Points,
    race: str,
    over: CharacterOverrides | None,
    depth: int,
    rules: str,
    bonus: int,
    opts: dict[str, Any],
) -> tuple[float, tuple[str, ...]]:
    """(temps au dernier niveau, talents ajoutés dans l'ordre) de l'anticipation gloutonne."""
    p = dict(pts)
    picks: list[str] = []
    for d in range(depth):
        lv = level + d + 1
        cands = legal_additions(gd, p, lv, bonus)
        if not cands:
            break

        def time_with(k: str, lv: int = lv) -> float:
            return best_choice(gd, lv, {**p, k: p.get(k, 0) + 1}, race, over, rules=rules, **opts)[0]

        best = min(cands, key=time_with)
        p[best] = p.get(best, 0) + 1
        picks.append(best)
    return best_choice(gd, min(gd.level_cap, level + depth), p, race, over, rules=rules, **opts)[0], tuple(picks)


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
) -> tuple[float, BuildChoice, McStats | None]:
    """Temps retenu pour un candidat présélectionné : seed, un Monte Carlo par rotation (le plus court) ; forever, la
    meilleure combinaison complète à l'analytique, passée une fois au Monte Carlo (échantillons gardés pour le
    départage, T06b) ; sans Monte Carlo, l'analytique."""
    if not mc_n:
        t, c = best_choice(gd, level, pts, race, over, rules=rules, full=rules != "seed", **options)
        return t, c, None
    sim = {"rules": rules, **options}
    if rules == "seed":
        t, rot = min((mc(gd, level, pts, race, r, mc_n, seed, over, **sim)["total"], r) for r in SEED_ROTATIONS)
        return t, BuildChoice(rot), None
    _, choice = best_choice(gd, level, pts, race, over, rules=rules, full=True, **options)
    st = mc_stats(gd, level, pts, race, choice.rotation, mc_n, seed, over, **sim, **choice.options())
    return st.mean, choice, st


def _opens_tier(
    gd: GameData,
    pts: Points,
    key: str,
    picks: Sequence[str],
    modeled: frozenset[str],
    rivals: Sequence[str] = (),
) -> bool:
    """Point de passage vers un palier : le point porte son arbre au seuil d'un palier que l'anticipation ouvre sur un
    talent modélisé de ce palier (T06b, décision D7)."""
    tree = gd.talents[key].tree
    before = sum(r for k, r in pts.items() if gd.talents[k].tree == tree)
    after = before + 1
    opened = {t for t in {x.tier for x in gd.talents.values()} if before < tier_points_required(gd, t) <= after}
    return any(p in modeled and gd.talents[p].tree == tree and gd.talents[p].tier in opened for p in picks)


def _shortlist(pre: Sequence[Any], shortlist: int, modeled: frozenset[str] | None) -> list[Any]:
    raise NotImplementedError("T06b : présélection à égalité")


def _state_meta(
    gd: GameData, evals: Sequence[_Eval], pts: Points, modeled: frozenset[str] | None
) -> list[dict[str, Any] | None]:
    """Décision de chaque candidat d'un état du faisceau (mode forever) ; None : candidat écarté (non modélisé à
    égalité avec un modélisé, hors point de passage vers un palier)."""

    def is_mod(k: str | None) -> bool:
        return k is not None and modeled is not None and k in modeled

    if len(evals) == 1:
        e = evals[0]
        return [
            {
                "runner_up": None,
                "gap": None,
                "significant": None,
                "modeled": is_mod(e.talent),
                "decided_by": "seul_candidat",
            }
        ]
    if any(e.stats is None for e in evals):
        out: list[dict[str, Any] | None] = []
        for e in evals:
            other = min((x for x in evals if x is not e), key=lambda x: x.time_s)
            out.append(
                {
                    "runner_up": other.talent,
                    "gap": None,
                    "significant": None,
                    "modeled": is_mod(e.talent),
                    "decided_by": "analytique",
                }
            )
        return out
    conf = gd.build.confidence
    stats = [e.stats for e in evals if e.stats is not None]
    d = tie_break([(e.talent or "", st) for e, st in zip(evals, stats, strict=True)], modeled, conf)
    rows = d["rows"]
    tied_modeled = any(r["modeled"] and not r["significant"] for r in rows)
    chosen = next(i for i, e in enumerate(evals) if (e.talent or "") == d["choice"])
    out = []
    for i, (e, row) in enumerate(zip(evals, rows, strict=True)):
        if i == chosen:
            gap = d["gap"]
            out.append(
                {
                    "runner_up": d["runner_up"],
                    "gap": gap,
                    "significant": gap["significant"] if gap else None,
                    "modeled": row["modeled"],
                    "decided_by": d["decided_by"],
                }
            )
            continue
        g = gap_dict(paired_gap(stats[i], stats[chosen], conf))
        tied = not row["significant"]
        passage = (
            e.talent is not None
            and not row["modeled"]
            and modeled is not None
            and _opens_tier(gd, pts, e.talent, e.picks, modeled)
        )
        if tied and not row["modeled"] and tied_modeled and not passage:
            out.append(None)
            continue
        out.append(
            {
                "runner_up": d["choice"],
                "gap": g,
                "significant": g["significant"],
                "modeled": row["modeled"],
                "decided_by": "passage_palier" if passage and tied and tied_modeled else "anticipation",
            }
        )
    return out


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
    modeled: frozenset[str] | None = None,
    **options: Any,
) -> LevelingPath:
    """Meilleur ordre des talents de `lfrom` à `lto` (faisceau, anticipation, Monte Carlo sur la présélection) ;
    ValueError si le build de départ est illégal au niveau `lfrom`.

    En mode forever, plusieurs départs : le faisceau libre et un faisceau par arbre (points placés dans l'arbre tant
    qu'un talent y est prenable), le chemin le plus court gagne ; un faisceau peu profond ne voit pas le gain d'un
    arbre qui ne paie qu'au troisième palier. Mode seed : le faisceau du seed seul (parité).

    Registre : I5, I6"""
    start_pts = {k: v for k, v in (start or {}).items() if v}
    errors = check_build(gd, start_pts, lfrom, talented_bonus)
    if errors:
        raise ValueError(f"build de départ illégal au niveau {lfrom} : {' ; '.join(errors)}")
    common: dict[str, Any] = {
        "beam": beam,
        "depth": depth,
        "shortlist": shortlist,
        "mc_n": mc_n,
        "seed": seed,
        "rules": rules,
        "start": start_pts,
        "over": over,
        "talented_bonus": talented_bonus,
        "modeled": modeled,
        **options,
    }
    focuses: list[str | None] = [None] if rules == "seed" else [None, *gd.trees]
    paths = [_beam_search(gd, race, lfrom, lto, focus=f, **common) for f in focuses]
    return min(paths, key=lambda path: path.hours_equiv)


def _beam_search(
    gd: GameData,
    race: str,
    lfrom: int,
    lto: int,
    *,
    focus: str | None,
    beam: int,
    depth: int,
    shortlist: int,
    mc_n: int,
    seed: int,
    rules: str,
    start: dict[str, int],
    over: CharacterOverrides | None,
    talented_bonus: int,
    modeled: frozenset[str] | None = None,
    **options: Any,
) -> LevelingPath:
    """Faisceau du seed ; `focus` : arbre où placer les points tant qu'un de ses talents est prenable. Mode forever :
    décision de chaque étape (`_state_meta`) et non modélisé écarté à égalité avec un modélisé (T06b)."""
    start_pts = start
    beams: list[tuple[float, dict[str, int], list[Step]]] = [(0.0, dict(start_pts), [])]
    for level, last in _passes(gd, lfrom, lto, sum(start_pts.values()), talented_bonus):
        # plusieurs points au même niveau (bonus Talented, build de départ) : une étape par point, le temps du niveau
        # compté une seule fois, sur le build de fin de niveau (Monte Carlo sur cette dernière étape seulement)
        weight = level_weight(gd, level) if last else 0.0
        nxt: list[tuple[float, float, dict[str, int], list[Step]]] = []
        for score, pts, hist in beams:
            legal = legal_additions(gd, pts, level, talented_bonus)
            inside = [k for k in legal if focus is not None and gd.talents[k].tree == focus]
            cands: list[str | None] = [*(inside or legal)] or [None]
            pre = []
            for k in cands:
                p2 = dict(pts)
                if k:
                    p2[k] = p2.get(k, 0) + 1
                t_now = best_choice(gd, level, p2, race, over, rules=rules, **options)[0]
                d = min(depth, gd.level_cap - level)
                look, picks = (
                    _rollout_path(gd, level, p2, race, over, d, rules, talented_bonus, options)
                    if depth and level < lto
                    else (t_now, ())
                )
                pre.append((NOW_WEIGHT * t_now + LOOK_WEIGHT * look, k, p2, picks))
            pre.sort(key=lambda x: x[0])
            evals = []
            for look, k, p2, picks in pre[:shortlist]:
                t_now, choice, st = _decide_step(gd, level, p2, race, over, rules, mc_n if last else 0, seed, options)
                evals.append(_Eval(look, k, p2, picks, t_now, choice, st))
            metas: list[dict[str, Any] | None] = (
                _state_meta(gd, evals, pts, modeled) if rules != "seed" else [{} for _ in evals]
            )
            for e, meta in zip(evals, metas, strict=True):
                if meta is None:
                    continue
                step = Step(level, e.talent, round(e.time_s, 2), e.choice.rotation, e.choice, **meta)
                nxt.append((score + e.time_s * weight, e.look, e.points, [*hist, step]))
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
