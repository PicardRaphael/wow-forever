"""Build du Mage par contexte pour la CLI (`forever build`) et le serveur MCP (`forever_build`) : talents et ordre
d'apprentissage, choix du build (rotation, armure, cumuls), raison de chaque choix, alternative la plus proche avec
écart apparié et intervalle, stabilité, sensibilité aux hypothèses incertaines, respec, angles morts, certitude et
provenance (T05, décisions 79 à 89).

Aucun calcul ici : l'optimiseur (`forever/optimize/`) cherche et décide, les simulateurs (`forever/sim/`) évaluent,
le moteur (`forever/engine/`) porte les règles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any, TypedDict, cast

from forever.config import Deps
from forever.engine.blind_spots import modeled_talents, select_blind_spots
from forever.engine.model import CharacterOverrides, GameData, Preset
from forever.engine.monsters import mob_hp
from forever.engine.pvp import pvp_score
from forever.engine.respec import respec_cost, respec_cost_certainty
from forever.engine.talents import build_points, check_build, legal_additions, tree_split
from forever.engine.variants import ASSUMPTIONS, assumption_range, current_value, with_assumption
from forever.errors import InvalidArgumentError
from forever.freshness import freshness_for_version
from forever.gamedata import RULES, build_game_data
from forever.leveling import (
    DEFAULT_RACE,
    DEFAULT_RACE_NOTE,
    check_level,
    check_race,
    check_talents,
    constants_certainty,
    damage_assumptions,
    given,
    ratio_assumption,
)
from forever.optimize.decide import Gap, gap_dict, paired_gap, tie_break
from forever.optimize.endgame import PVP_CONTEXTS, context_analytic, context_mc, neighbors, optimize_context
from forever.optimize.leveling import BuildChoice, best_choice, optimize_leveling
from forever.optimize.respec import advise_respec
from forever.provenance import Certainty, Provenance, make_provenance, min_certainty
from forever.registry import blind_spot_rules
from forever.registry import load as load_registry
from forever.sim.leveling_mc import McStats, mc_stats
from forever.store import VersionData, load_version

PERCENT = 100.0  # conversion d'unité : effets des angles morts en %
MIN_PAIRED_N = 2  # écart apparié : au moins deux combats

CONTEXTS = ("leveling", "dungeon", "raid", "pvp-bg", "pvp-world")


class BuildReport(TypedDict):
    context: str
    level: int
    race: str
    inputs: dict[str, Any]  # valeurs d'entrée et leur origine (T06b)
    scenario: dict[str, Any]
    talents: dict[str, int]
    talents_by_tree: dict[str, dict[str, int]]
    points: dict[str, Any]  # totaux : par arbre, dépensés, disponibles, non dépensés (T06b)
    order: list[dict[str, Any]]
    next_step: dict[str, Any] | None  # prochain talent depuis le build actuel (T06b)
    choices: dict[str, dict[str, Any]]
    metric: dict[str, Any]
    reasons: list[dict[str, Any]]
    alternative: dict[str, Any]
    stability: dict[str, Any]
    sensitivity: list[dict[str, Any]]
    respec: dict[str, Any]
    blind_spots: list[dict[str, Any]]
    certainty: str
    certainty_sources: dict[str, str]
    verifiable_in_game: bool
    assumptions: list[str]
    provenance: Provenance


SEED_OPTIONS: dict[str, Any] = {"mob_source": "seed", "spell_level": "rank"}
LABELS = {
    "leveling": "leveling",
    "dungeon": "donjon",
    "raid": "raid",
    "pvp-bg": "PvP champs de bataille",
    "pvp-world": "PvP monde ouvert",
}
ENDGAME = ("dungeon", "raid")
# Tant que la tranche T05b n'est pas faite : limite affichée sur chaque sortie de donjon et de raid.
MANA_NOTE = (
    "mana des combats longs non modélisée (Évocation, potions et gemmes de mana ; tranche T05b à venir) : "
    "classement de donjon et de raid fragile, angle mort B10"
)
Choices = dict[str, BuildChoice]


def _gap_dict(g: Gap) -> dict[str, Any]:
    return gap_dict(g)


def _mc_fields(stats: McStats | None) -> dict[str, Any]:
    return {
        "monte_carlo": stats.mean if stats else None,
        "sd": stats.sd if stats else None,
        "se": stats.se if stats else None,
        "n": stats.n if stats else 0,
    }


def _next_step(
    gd: GameData,
    level: int,
    race: str,
    current: Mapping[str, int] | None,
    over: CharacterOverrides | None,
    rules: str,
    mc_n: int,
    seed: int,
    bonus: int,
    modeled: frozenset[str] | None,
) -> dict[str, Any] | None:
    """Prochain talent depuis le build actuel (T06b, décision D7) : `current` légal au niveau `level` − 1, chaque
    addition légale au niveau `level` passée au Monte Carlo (même graine, meilleure combinaison du build), écart
    apparié au meilleur, départage (`tie_break`). Sans anticipation : jamais `passage_palier`. None : pas de
    `current`, `current` illégal au niveau précédent, mode seed ou Monte Carlo désactivé."""
    if current is None or rules != "forever" or mc_n < MIN_PAIRED_N or level - 1 < gd.constants.talents.first_level:
        return None
    base = {k: v for k, v in current.items() if v}
    if check_build(gd, base, level - 1, bonus):
        return None
    cands = legal_additions(gd, base, level, bonus)
    if not cands:
        return None
    measured = []
    choices = {}
    for k in cands:
        p2 = {**base, k: base.get(k, 0) + 1}
        _, choice = best_choice(gd, level, p2, race, over, rules=rules, full=True)
        choices[k] = choice
        measured.append(
            (k, mc_stats(gd, level, p2, race, choice.rotation, mc_n, seed, over, rules=rules, **choice.options()))
        )
    d = tie_break(measured, modeled, gd.build.confidence)
    rows = [{**r, "choice": dict(choices[r["talent"]]._asdict())} for r in d["rows"]]
    return {
        "level": level,
        "from": base,
        "choice": d["choice"],
        "decided_by": d["decided_by"],
        "runner_up": d["runner_up"],
        "gap": d["gap"],
        "n": mc_n,
        "seed": seed,
        "candidates": rows,
    }


def _order_points(gd: GameData, order: list[dict[str, Any]]) -> None:
    """Points par arbre et au total cumulés à chaque étape de l'ordre (T06b)."""
    acc: dict[str, int] = {}
    for step in order:
        if step["talent"]:
            acc[step["talent"]] = acc.get(step["talent"], 0) + 1
        split = tree_split(gd, acc)
        step["points_by_tree"] = split
        step["points_total"] = sum(split.values())


class _Metric:
    """Métrique d'un contexte sur des données (éventuellement une variante) : analytique, Monte Carlo, sens."""

    def __init__(
        self,
        gd: GameData,
        context: str,
        level: int,
        race: str,
        over: CharacterOverrides | None,
        rules: str,
        mc_n: int,
    ) -> None:
        self.gd, self.context, self.level, self.race, self.over, self.rules, self.mc_n = (
            gd,
            context,
            level,
            race,
            over,
            rules,
            mc_n,
        )
        self.sim = SEED_OPTIONS if rules == "seed" else {}
        self.pvp = context in PVP_CONTEXTS
        self.lower_is_better = context == "leveling"
        self._cache: dict[tuple[tuple[str, int], ...], tuple[float, Choices]] = {}

    def analytic(self, pts: Mapping[str, int]) -> tuple[float, Choices]:
        sig = tuple(sorted((k, v) for k, v in pts.items() if v > 0))
        if sig not in self._cache:
            gd, lv = self.gd, self.level
            if self.context == "leveling":
                t, c = best_choice(
                    gd, lv, pts, self.race, self.over, rules=self.rules, full=self.rules != "seed", **self.sim
                )
                self._cache[sig] = (t, {"leveling": c})
            elif self.pvp:
                weights = gd.pvp.weights[PVP_CONTEXTS[self.context]]
                self._cache[sig] = (pvp_score(gd, pts, lv, self.race, weights, self.over).score, {})
            else:
                self._cache[sig] = context_analytic(gd, self.context, lv, pts, self.race, self.over)
        return self._cache[sig]

    def oriented(self, value: float) -> float:
        """Valeur dans le sens « plus grand vaut mieux »."""
        return -value if self.lower_is_better else value

    def mc(self, pts: Mapping[str, int], choices: Choices, seed: int) -> McStats | None:
        if self.pvp:
            return None
        if self.context == "leveling":
            c = choices["leveling"]
            return mc_stats(
                self.gd,
                self.level,
                pts,
                self.race,
                c.rotation,
                self.mc_n,
                seed,
                self.over,
                rules=self.rules,
                **self.sim,
                **c.options(),
            )
        return context_mc(self.gd, self.context, self.level, pts, choices, self.race, self.mc_n, seed, self.over)

    def compare(self, a: Mapping[str, int], b: Mapping[str, int], seed: int) -> tuple[Gap, str, bool]:
        """(écart a - b, mode de décision, a meilleur que b) : Monte Carlo apparié, sinon analytique ; PvP :
        profil déterministe."""
        va, ca = self.analytic(a)
        vb, cb = self.analytic(b)
        sa, sb = self.mc(a, ca, seed), self.mc(b, cb, seed)
        conf = self.gd.build.confidence
        if sa is None or sb is None:
            d = va - vb
            return Gap(d, d, d, conf, d != 0), "profil", self.oriented(va) >= self.oriented(vb)
        gap = paired_gap(sa, sb, conf)
        if gap.significant:
            return gap, "monte_carlo", self.oriented(gap.mean) > 0
        return gap, "analytique", self.oriented(va) >= self.oriented(vb)


def _validate(
    gd: GameData,
    data: VersionData,
    context: str,
    level: int,
    race: str,
    current: Mapping[str, int] | None,
    respecs: int,
    preset: str,
    rules: str,
    talented_bonus: int,
) -> None:
    if context not in CONTEXTS:
        raise InvalidArgumentError(f"Contexte inconnu « {context} ».", f"choisir parmi {', '.join(CONTEXTS)}")
    cap = gd.level_cap
    first = gd.constants.talents.first_level
    check_level(level, cap)
    if level < first:
        raise InvalidArgumentError(
            f"Niveau {level} hors de {first}-{cap} : aucun point de talent avant le niveau {first}.",
            f"donner un niveau de {first} à {cap}",
        )
    check_race(data, race)
    if preset not in gd.build.presets:
        raise InvalidArgumentError(
            f"Nom de préréglage inconnu « {preset} ».", f"choisir parmi {', '.join(gd.build.presets)}"
        )
    if rules == "seed" and context != "leveling":
        raise InvalidArgumentError(
            f"rules seed : le mode seed ne couvre que le leveling (contexte {context}).", "choisir rules forever"
        )
    if talented_bonus < 0:
        raise InvalidArgumentError(f"Bonus Talented {talented_bonus} négatif.", "donner un nombre de points ≥ 0")
    if respecs < 0:
        raise InvalidArgumentError(f"{respecs} réinitialisations : nombre négatif.", "donner un nombre ≥ 0")
    if current:
        check_talents(gd, {k: v for k, v in current.items()}, gd.level_cap)  # clés connues, rangs positifs
        spent = sum(current.values())
        at = max(first, spent + first - 1 - talented_bonus)
        errors = check_build(gd, current, max(at, level), talented_bonus)
        if errors or at > level:
            detail = " ; ".join(errors) or f"{spent} points pour le niveau {level}"
            raise InvalidArgumentError(f"Build actuel illégal au niveau {level} : {detail}.", "corriger --current")


def _best_neighbor(m: _Metric, pts: Mapping[str, int], bonus: int) -> dict[str, int] | None:
    ns = neighbors(m.gd, pts, m.level, bonus)
    if not ns:
        return None
    return max(ns, key=lambda n: m.oriented(m.analytic(n)[0]))


def _reasons(m: _Metric, pts: dict[str, int], bonus: int, seed: int) -> list[dict[str, Any]]:
    gd = m.gd
    base = m.analytic(pts)[0]
    rows: list[dict[str, Any]] = []
    for k in [k for k in gd.talents if pts.get(k, 0) > 0]:
        less = {kk: v for kk, v in pts.items() if v > 0}
        less[k] -= 1
        if not less[k]:
            del less[k]
        moves = []
        for j in legal_additions(gd, less, m.level, bonus):
            cand = {**less, j: less.get(j, 0) + 1}
            if j != k and not check_build(gd, cand, m.level, bonus):
                moves.append((m.oriented(m.analytic(cand)[0]), j, cand))
        row: dict[str, Any] = {"talent": k, "name": gd.talents[k].name, "rank": pts[k], "tree": gd.talents[k].tree}
        if moves:
            best_v, j, cand = max(moves, key=lambda x: x[0])
            marginal = m.oriented(base) - best_v
            row.update(
                marginal=marginal,
                relative=marginal / abs(base) if base else None,
                moved_to=j,
                _cand=cand,
            )
        else:
            row.update(marginal=None, relative=None, moved_to=None, _cand=None)
        row["confirmed"] = None
        rows.append(row)
    heavy = sorted((r for r in rows if r["marginal"] is not None), key=lambda r: (-abs(r["marginal"]), r["talent"]))
    for r in heavy[:3]:
        gap, by, _ = m.compare(pts, r["_cand"], seed)
        r["confirmed"] = {**_gap_dict(gap), "decided_by": by}
    for r in rows:
        del r["_cand"]
    return rows


def _choices_dict(choices: Choices) -> dict[str, dict[str, Any]]:
    return {k: dict(c._asdict()) for k, c in choices.items()}


def _respec(
    gd: GameData,
    m: _Metric,
    context: str,
    level: int,
    race: str,
    build: dict[str, int],
    current: Mapping[str, int] | None,
    respecs: int,
    preset: Preset,
    over: CharacterOverrides | None,
    rules: str,
    bonus: int,
    seed: int,
) -> dict[str, Any]:
    cost, cert = respec_cost(gd, respecs), respec_cost_certainty(gd, respecs)
    first = gd.constants.talents.first_level
    if context == "leveling":
        if not current:
            return {
                "verdict": None,
                "level": None,
                "cost_gold": cost,
                "cost_certainty": cert,
                "note": "donner le build actuel (--current) pour un conseil de respec",
            }
        now = max(first, sum(current.values()) + first - 1 - bonus)
        a = advise_respec(
            gd,
            now,
            dict(current),
            level,
            race,
            preset=preset,
            n_previous=respecs,
            over=over,
            talented_bonus=bonus,
            rules=rules,
            **m.sim,
        )
        projected = {k: a.keep.points[k] for k in gd.talents if a.keep.points.get(k, 0) > 0}
        return {
            "verdict": a.verdict,
            "level": a.level,
            "current_level": now,
            # chemin conseillé depuis le build actuel jusqu'au niveau demandé (chemin gardé du conseil) : planification
            "projected": {
                "from_level": now,
                "to_level": level,
                "steps": [{"level": s.level, "talent": s.talent} for s in a.keep.steps],
                "talents": projected,
                "points": build_points(gd, projected, level, bonus),
            },
            "gain_hours": a.gain_hours,
            "cost_gold": a.cost_gold,
            "balance_gold": a.balance_gold,
            "gold_per_hour": a.gold_per_hour,
            "cost_certainty": a.cost_certainty,
            "by_level": [list(r) for r in a.by_level],
        }
    if current:
        reference, ref = "current", dict(current)
    else:
        path = optimize_leveling(
            gd,
            race,
            first,
            level,
            beam=preset.beam,
            depth=preset.depth,
            shortlist=preset.shortlist,
            mc_n=0,
            over=over,
            talented_bonus=bonus,
        )
        reference, ref = "leveling", path.points
    gap, by, better = m.compare(build, ref, seed)
    reset = better and gap.significant and ref != build
    return {
        "verdict": "réinitialiser" if reset else "garder",
        "reference": reference,
        "reference_talents": ref,
        "cost_gold": cost,
        "cost_certainty": cert,
        "gap": {**_gap_dict(gap), "decided_by": by},
    }


def build_report(
    deps: Deps,
    context: str,
    level: int | None = None,
    *,
    race: str | None = None,
    current: Mapping[str, int] | None = None,
    respecs: int = 0,
    sp: float | None = None,
    crit: float | None = None,
    preset: str = "rapide",
    seed: int = 12345,
    rules: str = "forever",
    sensitivity: bool = True,
    talented_bonus: int = 0,
) -> BuildReport:
    """Rapport de build complet pour un contexte et un niveau (InvalidArgumentError, message en français).

    `current` : build actuel (conseil de respec) ; `respecs` : réinitialisations déjà faites ; `sp`, `crit` : fiche
    remplacée ; `preset` : préréglage de l'optimiseur (`build.presets`) ; `talented_bonus` : points de talent du bonus
    Legacy « Talented » (hypothèse affichée) ; `race` absente : Orc, signalé dans `inputs` et les hypothèses ;
    `level` absent : niveau maximal des données (`level_cap`), signalé de même (question générale sans niveau)."""
    race_given = race
    race = race if race is not None else DEFAULT_RACE
    data = load_version(deps)
    if rules not in RULES:
        raise InvalidArgumentError(f"rules inconnu « {rules} ».", "choisir forever ou seed")
    gd = build_game_data(data, rules=rules)
    inputs = {
        "race": given(race_given, DEFAULT_RACE),
        "level": given(level, gd.level_cap),
        "current": given(dict(current) if current is not None else None, None),
    }
    level = level if level is not None else gd.level_cap
    _validate(gd, data, context, level, race, current, respecs, preset, rules, talented_bonus)
    p = gd.build.presets[preset]
    over_raw: dict[str, float] = {}
    if sp is not None:
        over_raw["sp"] = sp
    if crit is not None:
        over_raw["spell_crit"] = crit
    over = cast(CharacterOverrides, over_raw) if over_raw else None
    m = _Metric(gd, context, level, race, over, rules, p.mc_n)
    first = gd.constants.talents.first_level
    order: list[dict[str, Any]] = []
    rules_bs = blind_spot_rules(load_registry(deps.registry_path))
    modeled = modeled_talents(gd, rules_bs) if rules == "forever" else None
    next_step: dict[str, Any] | None = None
    try:
        if context == "leveling":
            next_step = _next_step(gd, level, race, current, over, rules, p.mc_n, seed, talented_bonus, modeled)
            path = optimize_leveling(
                gd,
                race,
                first,
                level,
                beam=p.beam,
                depth=p.depth,
                shortlist=p.shortlist,
                mc_n=p.mc_n,
                seed=seed,
                rules=rules,
                over=over,
                talented_bonus=talented_bonus,
                modeled=modeled,
                **m.sim,
            )
            build = dict(path.points)
            order = [
                {
                    "level": s.level,
                    "talent": s.talent,
                    "time_s": s.time_s,
                    "rotation": s.rotation,
                    "choice": dict(s.choice._asdict()),
                    "runner_up": s.runner_up,
                    "gap": s.gap,
                    "significant": s.significant,
                    "modeled": s.modeled,
                    "decided_by": s.decided_by,
                }
                for s in path.steps
            ]
            _order_points(gd, order)
            alt = _best_neighbor(m, build, talented_bonus)
        else:
            cands = optimize_context(
                gd,
                context,
                level,
                race,
                shortlist=p.shortlist,
                mc_n=p.mc_n,
                seed=seed,
                depth=p.depth,
                over=over,
                talented_bonus=talented_bonus,
            )
            build = dict(cands[0].points)
            alt = dict(cands[1].points) if len(cands) > 1 else _best_neighbor(m, build, talented_bonus)
    except ValueError as exc:
        raise InvalidArgumentError(f"{exc}.", "choisir un autre niveau ou un autre contexte") from exc
    build = {k: build[k] for k in gd.talents if build.get(k, 0) > 0}  # ordre de talents.json
    if alt is not None:
        alt = {k: alt[k] for k in gd.talents if alt.get(k, 0) > 0}
    value, choices = m.analytic(build)
    stats = m.mc(build, choices, seed)
    alternative: dict[str, Any] = {
        "talents": None,
        "points": None,
        "diff": {},
        "gap": None,
        "decided_by": None,
        "better": None,
        **_mc_fields(None),
    }
    winners: list[str] = []
    seeds = [seed + i for i in range(gd.build.stability_seeds)]
    if alt is not None:
        gap, by, better = m.compare(build, alt, seed)
        keys = [k for k in gd.talents if build.get(k, 0) != alt.get(k, 0)]
        alt_value, alt_choices = m.analytic(alt)
        alternative = {
            "talents": alt,
            "points": build_points(gd, alt, level, talented_bonus),
            "diff": {k: [build.get(k, 0), alt.get(k, 0)] for k in keys},
            "choices": _choices_dict(alt_choices),
            "analytic": alt_value,
            **_mc_fields(m.mc(alt, alt_choices, seed)),
            "gap": _gap_dict(gap),
            "decided_by": by,
            "better": "build" if better else "alternative",
        }
        winners = ["build" if m.compare(build, alt, s)[2] else "alternative" for s in seeds]
    rows: list[dict[str, Any]] = []
    if sensitivity and alt is not None:
        base_winner = alternative["better"]
        for name in ASSUMPTIONS:
            now_value = current_value(gd, name)
            variant = next(v for v in assumption_range(gd, name) if v.value != now_value)
            mv = _Metric(with_assumption(gd, name, variant.value), context, level, race, over, rules, p.mc_n)
            g, by, better = mv.compare(build, alt, seed)
            winner = "build" if better else "alternative"
            rows.append(
                {
                    "assumption": name,
                    "key": ASSUMPTIONS[name],
                    "value": now_value,
                    "variant": variant.value,
                    "source": variant.source,
                    "holds": winner == base_winner,
                    "winner": winner,
                    "gap": {**_gap_dict(g), "decided_by": by},
                }
            )
    spots = select_blind_spots(gd, rules_bs, context, level, build, near=alt, race=race, over=over)
    cap = gd.build.beta_level_cap
    options = {"rules": rules, "low_level_penalty": None}
    assumptions = _assumptions(gd, context, level, p, preset, seed, sp, crit, talented_bonus, build, options)
    if inputs["race"]["origin"] == "default":
        assumptions.insert(0, DEFAULT_RACE_NOTE)
    if inputs["level"]["origin"] == "default":
        assumptions.insert(0, f"niveau absent : niveau maximal des données ({level}, level_cap de spell_scaling.json)")
    if context == "leveling" and current is not None and next_step is None:
        assumptions.append(
            f"prochain talent (next_step) non calculé : il faut un build actuel légal au niveau {level - 1}, un point "
            f"à placer au niveau {level}, le mode forever et le Monte Carlo"
        )
    sources: dict[str, str] = {
        "talents et sorts (client)": "certain",
        "constantes du simulateur (leveling.*)": constants_certainty(data),
        "hypothèses incertaines (mechanics.json, range)": "suppose",
        "coût de la respec": respec_cost_certainty(gd, respecs),
    }
    if context == "leveling":
        sources["PV des monstres"] = mob_hp(gd, level, gd.leveling.mob_source).certainty  # type: ignore[arg-type]
    if context in ENDGAME:
        sources["scénarios"] = "suppose"
    if context in PVP_CONTEXTS:
        sources["profil PvP"] = "suppose"
    certainty = min_certainty(cast(Certainty, c) for c in sources.values())
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty=certainty,
        assumptions=[*fresh["assumptions"], *assumptions],
    )
    return {
        "context": context,
        "level": level,
        "race": race,
        "inputs": inputs,
        "scenario": _scenario(gd, context),
        "talents": build,
        "talents_by_tree": {tree: {k: v for k, v in build.items() if gd.talents[k].tree == tree} for tree in gd.trees},
        "points": build_points(gd, build, level, talented_bonus),
        "order": order,
        "next_step": next_step,
        "choices": _choices_dict(choices),
        "metric": {
            "name": {"leveling": "temps par monstre"}.get(context, "score PvP" if m.pvp else "dégâts par seconde"),
            "unit": "s" if context == "leveling" else ("points" if m.pvp else "dégâts/s"),
            "higher_is_better": not m.lower_is_better,
            "analytic": value,
            "monte_carlo": stats.mean if stats else None,
            "sd": stats.sd if stats else None,
            "se": stats.se if stats else None,
            "n": stats.n if stats else 0,
        },
        "reasons": _reasons(m, build, talented_bonus, seed),
        "alternative": alternative,
        "stability": {"seeds": seeds, "stable": len(set(winners)) <= 1, "winners": winners},
        "sensitivity": rows,
        "respec": _respec(gd, m, context, level, race, build, current, respecs, p, over, rules, talented_bonus, seed),
        "blind_spots": [
            {
                "id": b.id,
                "description": b.description,
                "status": b.status,
                "talents": list(b.talents),
                "effect_pct": b.effect * PERCENT if b.effect is not None else None,
                "estimate": "borne haute" if b.effect is not None else "non chiffré",
            }
            for b in spots
        ],
        "certainty": certainty,
        "certainty_sources": sources,
        "verifiable_in_game": level <= cap,
        "assumptions": assumptions,
        "provenance": provenance,
    }


def _scenario(gd: GameData, context: str) -> dict[str, Any]:
    if context in ENDGAME:
        return {
            "provisional": True,
            "scenarios": [dict(asdict(gd.build.scenarios[s])) for s in gd.build.contexts[context]],
            "weights": None,
        }
    if context in PVP_CONTEXTS:
        return {"provisional": False, "scenarios": [], "weights": dict(gd.pvp.weights[PVP_CONTEXTS[context]])}
    return {"provisional": False, "scenarios": [], "weights": None}


def _assumptions(
    gd: GameData,
    context: str,
    level: int,
    p: Preset,
    preset: str,
    seed: int,
    sp: float | None,
    crit: float | None,
    bonus: int,
    build: Mapping[str, int],
    options: Mapping[str, Any],
) -> list[str]:
    out = []
    sheet = "équipement : fiche de base par niveau (estimation du personnage ; équipement réel en T07 et T10)"
    if sp is not None or crit is not None:
        parts = [
            f"puissance des sorts {sp:g}" if sp is not None else "",
            f"critique {crit:g}" if crit is not None else "",
        ]
        sheet += ", remplacée par la fiche donnée : " + ", ".join(x for x in parts if x)
    out.append(sheet)
    cap = gd.build.beta_level_cap
    if level > cap:
        out.append(f"build au-delà du niveau {cap} (plafond de la bêta) : non vérifiable en jeu avant la sortie")
    out.append(f"bonus Legacy « Talented » : {bonus} point(s) de talent en plus (hypothèse de l'utilisateur)")
    if context == "leveling":
        out.append(
            "poids des niveaux : XP pour passer le niveau / XP d'un monstre du niveau (règle Classic ; XP par quête "
            "de Forever en T04d)"
        )
        out.append(f"ordre optimisé du niveau {gd.constants.talents.first_level} au niveau {level} (faisceau du seed)")
    if context in ENDGAME:
        for s in gd.build.contexts[context]:
            sc = gd.build.scenarios[s]
            out.append(
                f"scénario provisoire {s} (build.scenarios, suppose ; DJ1 et T09 à venir) : {sc.targets} cible(s), "
                f"niveau + {sc.level_offset}, {sc.duration_s:g} s au plus, tank présent, sans Évocation ni potion"
            )
        out.append(MANA_NOTE)
    if context in PVP_CONTEXTS:
        out.append("profil PvP du seed (EST) : modèle de scénarios, sans simulation de duel (pvp.profile, pvp.weights)")
    out += damage_assumptions(options, gd.constants.coefficients.low_level_default)
    out.append(ratio_assumption(gd))
    if build.get("arcanePower"):
        out.append("Arcane Power posée au pull dès que sa recharge est écoulée (décision 79)")
    if context in PVP_CONTEXTS:
        out.append(f"préréglage {preset} : profil déterministe (pas de Monte Carlo)")
    else:
        out.append(
            f"préréglage {preset} : décision au Monte Carlo (n = {p.mc_n}, graine {seed}, intervalle à "
            f"{str(gd.build.confidence).replace('.', ',')}), stabilité sur {gd.build.stability_seeds} graines"
        )
    return out
