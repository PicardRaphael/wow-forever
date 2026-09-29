"""Build d'un contexte de fin de partie à un niveau donné (donjon, raid ; T05, décision 84) : départs multiples (un par
arbre et par hybride), recherche locale (déplacer un point en gardant la légalité) jusqu'à un optimum local, tri à
l'analytique, décision au Monte Carlo apparié.

Métrique d'un contexte à plusieurs scénarios (`build.contexts`) : dégâts totaux / durée totale retenue, combat par
combat au Monte Carlo (le i-ème boss avec le i-ème paquet) ; rotation choisie par scénario, talents communs.

Registre : I5"""

from __future__ import annotations

import math
import random
import statistics
from typing import Any, NamedTuple

from forever.engine.model import CharacterOverrides, GameData, Points
from forever.engine.spells import best_rank
from forever.engine.talents import check_build, legal_additions, points_available
from forever.optimize.decide import decide
from forever.optimize.leveling import BuildChoice, build_choices
from forever.sim.encounter import AOE_FILLERS, EncounterResult, encounter_analytic, encounter_fight
from forever.sim.leveling_mc import McStats

GAIN_EPSILON = 1e-9  # marge de méthode : un gain plus petit n'est pas une amélioration (erreurs d'arrondi)


class Candidate(NamedTuple):
    """Build candidat : talents, choix par scénario, valeur analytique du contexte, statistiques du Monte Carlo
    (None avant la décision)."""

    points: dict[str, int]
    choices: dict[str, BuildChoice]
    analytic: float
    stats: McStats | None


def context_scenarios(gd: GameData, context: str) -> tuple[str, ...]:
    """Scénarios d'un contexte (`build.contexts`) ; ValueError si le contexte est inconnu.

    Registre : I5"""
    if context not in gd.build.contexts:
        raise ValueError(f"contexte inconnu « {context} » ({', '.join(gd.build.contexts)} attendu)")
    return gd.build.contexts[context]


def scenario_choices(gd: GameData, scenario: str, level: int, pts: Points) -> list[BuildChoice]:
    """Choix du build pour un scénario : rotations à une cible (armures, `ab_stacks`, `ab_dump`, `hs_stacks`) et, pour
    un paquet, la rotation de zone avec chaque sort de remplissage appris.

    Registre : I1, I5"""
    out = build_choices(gd, level, pts, full=True)
    sc = gd.build.scenarios[scenario]
    if sc.targets > 1:
        armors = sorted({c.armor for c in out}, key=[c.armor for c in out].index)
        fillers = [f for f in AOE_FILLERS if best_rank(gd, f, level, pts) is not None]
        out = [BuildChoice("aoe", armor, aoe_filler=f) for armor in armors for f in fillers] + out
    return out


def _scenario_best(
    gd: GameData,
    scenario: str,
    level: int,
    pts: Points,
    race: str,
    over: CharacterOverrides | None,
    options: dict[str, Any],
) -> tuple[EncounterResult, BuildChoice]:
    best: tuple[float, int, EncounterResult, BuildChoice] | None = None
    for i, c in enumerate(scenario_choices(gd, scenario, level, pts)):
        try:
            r = encounter_analytic(gd, scenario, level, pts, race, c.rotation, over, **options, **c.options())
        except ValueError:  # rotation impossible à ce niveau
            continue
        if best is None or (-r["dps"], i) < (-best[0], best[1]):
            best = (r["dps"], i, r, c)
    if best is None:
        raise ValueError(f"aucune rotation possible pour {scenario} au niveau {level}")
    return best[2], best[3]


def context_analytic(
    gd: GameData,
    context: str,
    level: int,
    pts: Points,
    race: str = "Orc",
    over: CharacterOverrides | None = None,
    **options: Any,
) -> tuple[float, dict[str, BuildChoice]]:
    """(dégâts par seconde du contexte, meilleur choix par scénario) à l'analytique : dégâts totaux / durée totale
    retenue des scénarios, chacun avec son meilleur choix.

    Registre : H3, H5, I5"""
    dmg = dur = 0.0
    choices: dict[str, BuildChoice] = {}
    for s in context_scenarios(gd, context):
        r, c = _scenario_best(gd, s, level, pts, race, over, options)
        dmg, dur, choices[s] = dmg + r["dmg"], dur + r["duration_s"], c
    return (dmg / dur if dur > 0 else 0.0), choices


def context_mc(
    gd: GameData,
    context: str,
    level: int,
    pts: Points,
    choices: dict[str, BuildChoice],
    race: str = "Orc",
    n: int = 200,
    seed: int = 12345,
    over: CharacterOverrides | None = None,
    **options: Any,
) -> McStats:
    """Dégâts par seconde du contexte, combat par combat (un combat de chaque scénario par tirage), graine fixe.

    Registre : I5, J2"""
    if n < 2:
        raise ValueError(f"n = {n} : au moins deux combats pour une dispersion (n ≥ 2)")
    scenarios = context_scenarios(gd, context)
    rng = random.Random(seed)
    values = []
    for _ in range(n):
        dmg = dur = 0.0
        for s in scenarios:
            c = choices[s]
            r = encounter_fight(gd, s, level, pts, race, c.rotation, rng, None, over, **options, **c.options())
            dmg, dur = dmg + r["dmg"], dur + r["duration_s"]
        values.append(dmg / dur if dur > 0 else 0.0)
    sd = statistics.stdev(values)
    return McStats(statistics.mean(values), sd, sd / math.sqrt(n), n, tuple(values))


def neighbors(gd: GameData, pts: Points, level: int, talented_bonus: int = 0) -> list[dict[str, int]]:
    """Builds voisins : un point retiré d'un talent et placé sur un autre, builds légaux seulement, dans l'ordre de
    `talents.json` (déterministe).

    Registre : G3, I5"""
    out: list[dict[str, int]] = []
    seen = {_sig(pts)}
    for k in gd.talents:
        if pts.get(k, 0) <= 0:
            continue
        less = {kk: v for kk, v in pts.items() if v > 0}
        less[k] -= 1
        if not less[k]:
            del less[k]
        for j in legal_additions(gd, less, level, talented_bonus):
            n = {**less, j: less.get(j, 0) + 1}
            sig = _sig(n)
            if sig in seen or check_build(gd, n, level, talented_bonus):
                continue
            seen.add(sig)
            out.append(n)
    return out


def _sig(pts: Points) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((k, v) for k, v in pts.items() if v > 0))


def _tier_key(gd: GameData, k: str) -> tuple[int, int]:
    """Départage des égalités du glouton : palier le plus bas d'abord (il débloque les suivants), puis l'ordre de
    `talents.json`."""
    return gd.talents[k].tier, list(gd.talents).index(k)


def optimize_context(
    gd: GameData,
    context: str,
    level: int,
    race: str = "Orc",
    *,
    shortlist: int = 4,
    mc_n: int = 200,
    seed: int = 12345,
    depth: int = 2,
    over: CharacterOverrides | None = None,
    talented_bonus: int = 0,
    **options: Any,
) -> list[Candidate]:
    """Candidats classés du contexte au niveau donné (meilleur d'abord) : un départ glouton par arbre et par paire
    d'arbres (anticipation de `depth` points quand aucun point n'améliore, pour franchir un palier), recherche locale
    au meilleur voisin jusqu'à l'optimum local, tri à l'analytique, Monte Carlo apparié sur les `shortlist` meilleurs
    (gagnant par `decide`, puis les autres finalistes par moyenne), le reste sans Monte Carlo.

    Registre : I5"""
    context_scenarios(gd, context)
    cache: dict[tuple[tuple[str, int], ...], tuple[float, dict[str, BuildChoice]]] = {}

    def value(pts: Points) -> float:
        sig = _sig(pts)
        if sig not in cache:
            cache[sig] = context_analytic(gd, context, level, pts, race, over, **options)
        return cache[sig][0]

    total = points_available(gd, level, talented_bonus)

    def greedy(trees: tuple[str, ...]) -> dict[str, int]:
        pts: dict[str, int] = {}

        def allowed(p: Points) -> list[str]:
            cands = legal_additions(gd, p, level, talented_bonus)
            inside = [k for k in cands if gd.talents[k].tree in trees]
            return inside or cands

        def look(p: dict[str, int], d: int) -> float:
            for _ in range(d):
                cands = allowed(p)
                if not cands:
                    break
                k = max(cands, key=lambda c: (value({**p, c: p.get(c, 0) + 1}), [-x for x in _tier_key(gd, c)]))
                p = {**p, k: p.get(k, 0) + 1}
            return value(p)

        while sum(pts.values()) < total:
            cands = allowed(pts)
            if not cands:
                break
            now = value(pts)
            gains = {k: value({**pts, k: pts.get(k, 0) + 1}) - now for k in cands}
            if max(gains.values()) > GAIN_EPSILON:
                k = max(cands, key=lambda c: (gains[c], [-x for x in _tier_key(gd, c)]))
            else:  # aucun point n'améliore : anticipation pour franchir un palier
                k = max(
                    cands,
                    key=lambda c: (look({**pts, c: pts.get(c, 0) + 1}, depth), [-x for x in _tier_key(gd, c)]),
                )
            pts[k] = pts.get(k, 0) + 1
        return pts

    def local_search(pts: dict[str, int]) -> dict[str, int]:
        current, v = pts, value(pts)
        while True:
            best, best_v = None, v
            for n in neighbors(gd, current, level, talented_bonus):
                nv = value(n)
                if nv > best_v + GAIN_EPSILON:
                    best, best_v = n, nv
            if best is None:
                return current
            current, v = best, best_v

    starts = [(t,) for t in gd.trees] + [(a, b) for i, a in enumerate(gd.trees) for b in gd.trees[i + 1 :]]
    optima: dict[tuple[tuple[str, int], ...], dict[str, int]] = {}
    for trees in starts:
        opt = local_search(greedy(trees))
        optima.setdefault(_sig(opt), opt)
    ranked = sorted(optima.values(), key=lambda p: (-value(p), _sig(p)))
    cands = [Candidate(p, cache[_sig(p)][1], value(p), None) for p in ranked]
    finalists = cands[: max(0, shortlist)]
    if len(finalists) < 2 or not mc_n:
        return cands
    stats = {
        _sig(c.points): context_mc(gd, context, level, c.points, c.choices, race, mc_n, seed, over, **options)
        for c in finalists
    }
    by_sig = {_sig(c.points): c for c in finalists}
    d = decide(
        list(by_sig),
        lambda s, _seed: stats[s],
        lambda s: by_sig[s].analytic,
        seed=seed,
        confidence=gd.build.confidence,
        lower_is_better=False,
    )
    rest = sorted((s for s in by_sig if s not in (d.winner, d.runner_up)), key=lambda s: (-stats[s].mean, s))
    ordered = [by_sig[s]._replace(stats=stats[s]) for s in (d.winner, d.runner_up, *rest)]
    return ordered + cands[len(finalists) :]


# --- PvP (bloc G) ------------------------------------------------------------------------------------------------

PVP_CONTEXTS = {"pvp-bg": "bg", "pvp-world": "world"}  # contexte -> poids du profil (pvp.weights)


def seed_pvp_greedy(
    gd: GameData,
    level: int,
    race: str = "Orc",
    beam: int = 4,
    weights: dict[str, float] | None = None,
    *,
    rules: str = "seed",
) -> Candidate:
    """Optimiseur PvP glouton du seed (`optimize.pvp`) : faisceau point par point noté par le profil PvP.

    Registre : I5"""
    raise NotImplementedError
