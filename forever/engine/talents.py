"""Talents : valeur d'un rang, points disponibles, légalité d'un build."""

from __future__ import annotations

from typing import Any

from forever.engine.model import ClassKnowledge, GameData, Points, TalentRules


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


def tier_points_required(gd: GameData, tier: int) -> int:
    """Points à dépenser dans l'arbre avant de prendre un talent du palier `tier`.

    Registre : G3"""
    return gd.constants.talents.points_per_tier * (tier - 1)


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


def build_points(gd: GameData, pts: Points, level: int, talented_bonus: int = 0) -> dict[str, Any]:
    """Points par arbre (`by_tree`), dépensés (`total`), disponibles au niveau (`available`) et non dépensés
    (`unspent`), pour que les outils rendent les totaux (T06b).

    Registre : G3"""
    by_tree = tree_split(gd, pts)
    total = sum(by_tree.values())
    available = points_available(gd, level, talented_bonus)
    return {"by_tree": by_tree, "total": total, "available": available, "unspent": available - total}


def check_class_build(
    knowledge: ClassKnowledge, rules: TalentRules, pts: Points, level: int, talented_bonus: int = 0
) -> list[str]:
    """Erreurs de légalité d'un build d'une des 9 classes (liste vide : légal), d'après son savoir décodé du client
    (`classes.json`) : points disponibles au niveau, rangs maximaux, points exigés par palier dans l'arbre,
    prérequis (requis : tous au maximum ; suffisants : un au maximum). Palier inconnu : palier communautaire s'il
    existe (probable), sinon légalité non décidable (erreur).

    Registre : G3"""
    per_tier = rules.points_per_tier
    known = {t["key"]: t for tree in knowledge.trees for t in tree["talents"]}
    by_node = {t["node_id"]: t for t in known.values()}

    def tier_of(t: Any) -> int | None:
        if t.get("tier") is not None:
            return int(t["tier"])
        community = t.get("tier_community")
        return int(community["tier"]) if community else None

    err = []
    total = sum(pts.values())
    available = max(0, level - (rules.first_level - 1) + talented_bonus)
    if total > available:
        err.append(f"{total} points pour {available} disponibles au niveau {level}")
    for k, r in pts.items():
        if r <= 0:
            continue
        if k not in known:
            err.append(f"talent inconnu : {k}")
            continue
        t = known[k]
        if r > t["max"]:
            err.append(f"{t['name']} : {r}/{t['max']}")
        tier = tier_of(t)
        if tier is None:
            err.append(f"{t['name']} : palier inconnu (nœud hors grille), légalité non décidable")
            continue
        before = sum(
            v
            for kk, v in pts.items()
            if kk in known and known[kk]["tree"] == t["tree"] and (tier_of(known[kk]) or tier) < tier
        )
        if before < per_tier * (tier - 1):
            err.append(f"{t['name']} (palier {tier}) exige {per_tier * (tier - 1)} points avant, {before} dépensés")
        required = [by_node[p["node_id"]] for p in t["prereqs"] if p["kind"] == "required" and p["node_id"] in by_node]
        sufficient = [
            by_node[p["node_id"]] for p in t["prereqs"] if p["kind"] != "required" and p["node_id"] in by_node
        ]
        for p in required:
            if pts.get(p["key"], 0) < p["max"]:
                err.append(f"{t['name']} exige {p['name']} au maximum")
        if sufficient and not any(pts.get(p["key"], 0) >= p["max"] for p in sufficient):
            names = " ou ".join(p["name"] for p in sufficient)
            err.append(f"{t['name']} exige {names} au maximum")
    return err
