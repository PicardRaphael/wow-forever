"""Bonus d'XP de Forever pour toutes les classes (T04f) : catalogue lu dans `xp_bonuses.json`, état des bonus d'un
personnage, « quel bonus prendre maintenant » (écart d'XP par heure calculé par le moteur, jamais par un modèle de
langage), consultation (`forever lookup xp_bonuses`, `forever_lookup(kind="xp_bonuses")`).

Aucun chiffre de jeu ici : les valeurs viennent des données de la version, les écarts de `forever/engine/xp.py`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from forever.config import Deps
from forever.engine.model import GameData, XpBonusAura
from forever.engine.xp import (
    ActiveAura,
    XpBonusState,
    session_xp,
    sleeping_bag_state,
    tent_rested,
    xp_bonus_data,
)
from forever.errors import InvalidArgumentError

DEFAULT_SESSION_H = 2.0  # durée de séance par défaut (paramètre des outils, pas une valeur du jeu)
BONUS_NAMES = ("sleeping_bag", "food")  # bonus nommés des outils (forever sim leveling --bonus)
ACCESS = ("item", "legacy", "food", "camp", "none")
_RANK = {"certain": 2, "probable": 1, "suppose": 0}
FOOD_EXAMPLES = 3  # nourritures citées dans un conseil


def _min(*values: str) -> str:
    return min(values, key=lambda c: _RANK.get(c, 0))


def _certainty(a: XpBonusAura) -> str:
    return _min(a.meaning_certainty, a.access_certainty)


@dataclass(frozen=True)
class BonusAdvice:
    """Bonus absent mais accessible, et ce qu'il rapporte sur la séance (XP par heure en plus)."""

    key: str  # sleeping_bag, food, tent
    name: str
    xp_h_gain: float
    how: str
    certainty: str


def bonus_state(
    gd: GameData,
    names: Sequence[str] = (),
    *,
    auras: Sequence[ActiveAura] = (),
    legacy_ranks: Mapping[int, int] | None = None,
    sleeping_bag_stacks: int | None = None,
) -> XpBonusState:
    """État des bonus : auras données (contexte du jeu), plus les bonus nommés (`sleeping_bag` : Well-Rested juste
    après le sac, `sleeping_bag_stacks` cumuls ou le maximum ; `food` : nourriture nutritive renouvelée).
    InvalidArgumentError pour un nom inconnu."""
    unknown = sorted(set(names) - set(BONUS_NAMES))
    if unknown:
        raise InvalidArgumentError(
            f"Bonus d'XP inconnu : {', '.join(unknown)}.",
            f"choisir parmi {', '.join(BONUS_NAMES)} (les bonus sans source joueur ne s'appliquent jamais)",
        )
    active = list(auras)
    if "sleeping_bag" in names:
        bag = sleeping_bag_state(gd, sleeping_bag_stacks or None).auras[0]
        active = [a for a in active if a.spell_id != bag.spell_id] + [bag]
    return XpBonusState(auras=tuple(active), food="food" in names, legacy_ranks=dict(legacy_ranks or {}))


def active_bonuses(gd: GameData, state: XpBonusState) -> list[dict[str, Any]]:
    """Bonus actifs de l'état, chacun avec son accès, sa certitude et son temps restant ; `applied` faux pour une
    aura sans source joueur (jamais appliquée)."""
    data = xp_bonus_data(gd)
    auras = list(state.auras)
    if state.food:
        auras += [ActiveAura(a.spell_id) for a in data.auras.values() if a.access == "food"]
    out = []
    for active in auras:
        a = data.auras.get(active.spell_id)
        if a is None:
            continue
        bag = data.sleeping_bag
        key = (
            "sleeping_bag"
            if bag is not None and a.spell_id == bag.aura
            else "food"
            if a.access == "food"
            else f"aura.{a.spell_id}"
        )
        out.append(
            {
                "key": key,
                "spell_id": a.spell_id,
                "name": a.name,
                "stacks": min(active.stacks, a.max_stacks),
                "max_stacks": a.max_stacks,
                "remaining_s": active.remaining_s,
                "access": a.access,
                "applied": a.access != "none",
                "effects": [{"key": e.key, "value_pct": e.value} for e in a.effects if e.value],
                "certainty": _certainty(a),
            }
        )
    return out


def _gain(
    gd: GameData,
    before: XpBonusState,
    after: XpBonusState,
    *,
    level: int,
    base_xp_h: float,
    kill_share: float,
    hours: float,
    pool_before: float,
    pool_after: float,
) -> float:
    def rate(state: XpBonusState, pool: float) -> float:
        return session_xp(
            gd,
            base_xp_h=base_xp_h,
            kill_share=kill_share,
            hours=hours,
            state=state,
            rested_pool=pool,
            level=level,
        ).xp_h

    return rate(after, pool_after) - rate(before, pool_before)


def best_bonus(
    gd: GameData,
    state: XpBonusState,
    *,
    level: int,
    base_xp_h: float,
    kill_share: float,
    hours: float = DEFAULT_SESSION_H,
    rested_pool: float = 0.0,
) -> list[BonusAdvice]:
    """Bonus absents mais accessibles à `level` (sac de couchage, nourriture nutritive de son niveau, tente du camp),
    rangés par XP par heure gagnée sur la séance ; seuls ceux qui rapportent quelque chose sont rendus.

    Registre : D5, D9, E3"""
    data = xp_bonus_data(gd)
    if base_xp_h <= 0:
        return []
    common = {"level": level, "base_xp_h": base_xp_h, "kill_share": kill_share, "hours": hours}
    active_ids = {a.spell_id for a in state.auras}
    out: list[BonusAdvice] = []
    bag = data.sleeping_bag
    if bag is not None and level >= bag.required_level and bag.aura not in active_ids:
        after = replace(state, auras=(*state.auras, *sleeping_bag_state(gd).auras))
        gain = _gain(gd, state, after, pool_before=rested_pool, pool_after=rested_pool, **common)
        out.append(
            BonusAdvice(
                "sleeping_bag",
                bag.name,
                gain,
                f"pose {bag.name} et reste assis dedans jusqu'à {bag.max_stacks} cumuls de {data.auras[bag.aura].name}",
                _certainty(data.auras[bag.aura]),
            )
        )
    foods = [f for f in data.food if f.required_level <= level]
    food_auras = [a for a in data.auras.values() if a.access == "food"]
    if not state.food and foods and food_auras:
        gain = _gain(gd, state, replace(state, food=True), pool_before=rested_pool, pool_after=rested_pool, **common)
        top = max(f.required_level for f in foods)
        names = sorted({f.name for f in foods if f.required_level == top})[:FOOD_EXAMPLES]
        source = data.sources.get("xp.food_bonus")
        out.append(
            BonusAdvice(
                "food",
                food_auras[0].name,
                gain,
                f"mange une nourriture nutritive de ton niveau ({', '.join(names)})",
                _min(_certainty(food_auras[0]), source.certainty if source else "suppose"),
            )
        )
    if data.tent_threshold_pct is not None:
        raised = tent_rested(gd, level, rested_pool)
        if raised > rested_pool:
            gain = _gain(gd, state, state, pool_before=rested_pool, pool_after=raised, **common)
            source = data.sources.get("xp.camp_tent")
            out.append(
                BonusAdvice(
                    "tent",
                    "Camp Tent",
                    gain,
                    "monte une tente près d'un feu de camp avant la séance (repos remonté)",
                    source.certainty if source else "suppose",
                )
            )
    return sorted((b for b in out if b.xp_h_gain > 0), key=lambda b: -b.xp_h_gain)


def bonus_advice_sentence(advice: Sequence[BonusAdvice]) -> str:
    """Phrase de conseil construite à partir des chiffres de l'outil."""
    if not advice:
        return "aucun bonus d'XP de plus à prendre pour cette séance"
    best = advice[0]
    return f"prends {best.name} : environ {round(best.xp_h_gain)} XP par heure de plus ({best.how})"


def catalog(gd: GameData) -> list[dict[str, Any]]:
    """Chaque aura d'XP du client : effets, durée, cumul, accès, source, certitude, appliquée ou non."""
    data = xp_bonus_data(gd)
    return [
        {
            "spell_id": a.spell_id,
            "name": a.name,
            "effects": [
                {"key": e.key, "applies_to": e.applies_to, "value_pct": e.value, "ranks": list(e.ranks)}
                for e in a.effects
            ],
            "duration_s": a.duration_s,
            "max_stacks": a.max_stacks,
            "access": a.access,
            "applied": a.access != "none",
            "source": f"client {gd.game_version} : sort {a.spell_id} (xp_bonuses.json)",
            "certainty": _certainty(a),
        }
        for a in sorted(data.auras.values(), key=lambda a: a.spell_id)
    ]


def lookup_xp_bonuses(deps: Deps, *, access: str | None = None) -> dict[str, Any]:
    """Consultation des bonus d'XP de la version installée, avec la provenance.

    Registre : D5, D7, D9, D10, E3"""
    from forever.freshness import freshness_for_version
    from forever.gamedata import build_game_data
    from forever.provenance import make_provenance
    from forever.store import load_version

    if access is not None and access not in ACCESS:
        raise InvalidArgumentError(f"Accès inconnu : {access}.", f"choisir parmi {', '.join(ACCESS)}")
    data = load_version(deps)
    gd = build_game_data(data)
    bonuses = [b for b in catalog(gd) if access is None or b["access"] == access]
    raw = data.read_json("xp_bonuses.json")
    xp = xp_bonus_data(gd)
    food = sorted(xp.food, key=lambda f: (f.required_level, f.name))
    by_level: dict[str, list[str]] = {}
    for f in food:
        by_level.setdefault(str(f.required_level), []).append(f.name)
    stacking = xp.sources.get("xp.bonus_stacking")
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty="suppose" if any(b["certainty"] == "suppose" for b in bonuses) else "probable",
        assumptions=[
            *fresh["assumptions"],
            (
                f"cumul des bonus : {xp.stacking} des pourcentages, puis repos sur l'XP majorée (xp.bonus_stacking, "
                f"{stacking.certainty if stacking else 'suppose'}, question LVL12)"
            ),
            "accès none : aucune source joueur dans le client ; bonus listé, jamais appliqué (décision 262)",
            "sens des codes d'aura déduit des descriptions des sorts (probable)",
        ],
    )
    return {
        "bonuses": bonuses,
        "sleeping_bag": raw.get("sleeping_bag"),
        "food": {"count": len(food), "by_required_level": by_level},
        "camp": raw.get("camp"),
        "conditions": raw.get("conditions"),
        "stacking": {"mode": xp.stacking, "rested_after": xp.rested_after},
        "provenance": provenance,
    }


def xp_watch(gd: GameData) -> dict[str, list[int]]:
    raise NotImplementedError


def legacy_rested_spell(gd: GameData) -> int | None:
    raise NotImplementedError


def legacy_ranks_from_logger(gd: GameData, legacy: Mapping[str, Any] | None) -> dict[int, int]:
    raise NotImplementedError
