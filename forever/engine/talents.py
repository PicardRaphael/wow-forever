"""Talents : valeur d'un rang, points disponibles, légalité d'un build."""

from __future__ import annotations

from forever.engine.model import GameData, Points


def talent_value(gd: GameData, pts: Points, key: str, i: int = 0, default: float = 0.0) -> float:
    """Valeur `i` du rang pris (défaut si le talent n'est pas pris) ; rang borné au nombre de rangs connus.

    Registre : G3"""
    r = pts.get(key, 0)
    if r <= 0:
        return default
    ranks = gd.talents[key].ranks
    v = ranks[min(r, len(ranks)) - 1]
    return v[i] if i < len(v) else default


def points_available(gd: GameData, level: int, talented_bonus: int = 0) -> int:
    """Points de talent disponibles au niveau donné ; le bonus Legacy « Talented » avance le premier point.

    Registre : G3"""
    return max(0, level - (gd.constants.talents.first_level - 1) + talented_bonus)


def check_build(gd: GameData, pts: Points, level: int, talented_bonus: int = 0) -> list[str]:
    """Erreurs de légalité en français (liste vide : build légal).

    Registre : G3"""
    per_tier = gd.constants.talents.points_per_tier
    err = []
    total = sum(pts.values())
    available = points_available(gd, level, talented_bonus)
    if total > available:
        err.append(f"{total} points pour {available} disponibles au niveau {level}")
    for k, r in pts.items():
        if r <= 0:
            continue
        if k not in gd.talents:
            err.append(f"talent inconnu : {k}")
            continue
        t = gd.talents[k]
        if r > t.max_rank:
            err.append(f"{t.name} : {r}/{t.max_rank}")
        before = sum(
            v
            for kk, v in pts.items()
            if kk in gd.talents and gd.talents[kk].tree == t.tree and gd.talents[kk].tier < t.tier
        )
        if before < per_tier * (t.tier - 1):
            err.append(f"{t.name} (palier {t.tier}) exige {per_tier * (t.tier - 1)} points avant, {before} dépensés")
        if t.prereq:
            pk = gd.talent_at.get((t.tree, *t.prereq))
            if pk and pts.get(pk, 0) < gd.talents[pk].max_rank:
                err.append(f"{t.name} exige {gd.talents[pk].name} au maximum")
    return err


def legal_additions(gd: GameData, pts: Points, level: int, talented_bonus: int = 0) -> list[str]:
    """Talents auxquels on peut ajouter un point maintenant, dans l'ordre de `talents.json`.

    Registre : G3"""
    out: list[str] = []
    if sum(pts.values()) >= points_available(gd, level, talented_bonus):
        return out
    if check_build(gd, pts, level, talented_bonus):  # build illégal : les ajouts qui le rendent légal
        for k in gd.talents:
            p2 = dict(pts)
            p2[k] = p2.get(k, 0) + 1
            if not check_build(gd, p2, level, talented_bonus):
                out.append(k)
        return out
    # build légal : ajouter un point ne peut rompre que les contraintes du talent ajouté (rang, palier, prérequis)
    per_tier = gd.constants.talents.points_per_tier
    spent: dict[tuple[str, int], int] = {}
    for kk, v in pts.items():
        if v > 0 and kk in gd.talents:
            t = gd.talents[kk]
            spent[(t.tree, t.tier)] = spent.get((t.tree, t.tier), 0) + v
    for k, t in gd.talents.items():
        if pts.get(k, 0) + 1 > t.max_rank:
            continue
        before = sum(v for (tree, tier), v in spent.items() if tree == t.tree and tier < t.tier)
        if before < per_tier * (t.tier - 1):
            continue
        if t.prereq:
            pk = gd.talent_at.get((t.tree, *t.prereq))
            if pk and pts.get(pk, 0) < gd.talents[pk].max_rank:
                continue
        out.append(k)
    return out


def tree_split(gd: GameData, pts: Points) -> dict[str, int]:
    """Points dépensés par arbre.

    Registre : G3"""
    s = dict.fromkeys(gd.trees, 0)
    for k, r in pts.items():
        s[gd.talents[k].tree] += r
    return s
