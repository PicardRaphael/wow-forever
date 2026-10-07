"""Code de build de Talents Forever, génération 6 (FA1, décision 209) : lecture et écriture sur une disposition
abstraite (rangs maximaux par arbre et par position de liste), sans aucune donnée de l'addon.

Format réimplémenté d'après la lecture de l'addon (aucune licence, décisions 172 et 196), décrit dans
`tasks/FA1-plan.md` : `<classe>/<niveau>/<arbre 1>-<arbre 2>-<arbre 3>[-<Legacy ×3>][-<ordre>]-6`. Un arbre est une
suite de chiffres de rang, un par position de sa liste, zéros finaux retirés (segment vide : aucun point). L'ordre
donne un symbole par suite de points consécutifs sur un même talent (position à plat sur les trois arbres), suivi d'un
compte `1`–`4` seulement si la suite ne prend pas tous les points restants de ce talent. Les segments Legacy sont
relus et réécrits tels quels (jamais produits par forever). Règle d'échange, pas une formule de combat : hors de
`forever/engine/`."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

CODE_VERSION = "6"
SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz056789"
COUNTS = "1234"
SITE = "https://talentsforever.com/"
TREES = 3
LEGACY = 3
_SLUG = re.compile(r"^[a-z]+$")
_TREE = re.compile(r"^[0-9]*$")
_LINK = re.compile(r"^(?:https?://)?(?:www\.)?talentsforever\.com/", re.IGNORECASE)


@dataclass(frozen=True)
class TfPlan:
    """Build lu ou à écrire : rangs par arbre et par position de liste, ordre (arbre, position) d'un pas par point."""

    class_slug: str
    level: int
    ranks: tuple[tuple[int, ...], ...]
    order: tuple[tuple[int, int], ...] | None = None
    legacy: tuple[str, ...] | None = None


def _flat(lengths: Sequence[int]) -> list[tuple[int, int]]:
    """(arbre, position) de chaque symbole, à plat sur les arbres ; plus de positions que de symboles : refus."""
    flat = [(ti, i) for ti, n in enumerate(lengths) for i in range(n)]
    if len(flat) > len(SYMBOLS):
        raise ValueError(f"disposition de {len(flat)} talents : le code v6 en écrit au plus {len(SYMBOLS)}")
    return flat


def _encode_order(plan: TfPlan, flat: list[tuple[int, int]]) -> str:
    assert plan.order is not None
    index = {p: n for n, p in enumerate(flat)}
    placed: dict[tuple[int, int], int] = {}
    for step in plan.order:
        if step not in index:
            raise ValueError(f"ordre incohérent : position {step} hors de la disposition")
        placed[step] = placed.get(step, 0) + 1
    for ti, tree in enumerate(plan.ranks):
        for i, rank in enumerate(tree):
            if placed.get((ti, i), 0) != rank:
                raise ValueError(f"ordre incohérent : {placed.get((ti, i), 0)} pas pour le rang {rank} en {(ti, i)}")
    out: list[str] = []
    done: dict[tuple[int, int], int] = {}
    n = 0
    while n < len(plan.order):
        step = plan.order[n]
        run = 1
        while n + run < len(plan.order) and plan.order[n + run] == step:
            run += 1
        remaining = plan.ranks[step[0]][step[1]] - done.get(step, 0)
        out.append(SYMBOLS[index[step]] + (str(run) if run < remaining else ""))
        done[step] = done.get(step, 0) + run
        n += run
    return "".join(out)


def encode(plan: TfPlan) -> str:
    """Code v6 d'un plan (ValueError en français : disposition trop grande, ordre incohérent)."""
    flat = _flat([len(t) for t in plan.ranks])
    if len(plan.ranks) != TREES:
        raise ValueError(f"{len(plan.ranks)} arbres : le code v6 en attend {TREES}")
    trees = ["".join(str(r) for r in tree).rstrip("0") for tree in plan.ranks]
    parts = [*trees]
    if plan.legacy is not None:
        parts += list(plan.legacy)
    if plan.order:
        parts.append(_encode_order(plan, flat))
    parts.append(CODE_VERSION)
    return f"{plan.class_slug}/{plan.level}/" + "-".join(parts)


def code_of(text: str) -> str:
    """Code nu d'un lien ou d'un code collé (adresse du site, suffixe `?…` ou `#…` et espaces retirés)."""
    code = text.strip()
    code = _LINK.sub("", code)
    for sep in ("?", "#"):
        code = code.split(sep, 1)[0]
    return code.strip()


def link(code: str) -> str:
    """Lien du site pour un code (sans le marqueur de visite propre à l'addon)."""
    return SITE + code


def _decode_order(segment: str, ranks: list[list[int]], flat: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    if not segment:
        raise ValueError("ordre vide")
    order: list[tuple[int, int]] = []
    done: dict[tuple[int, int], int] = {}
    n = 0
    while n < len(segment):
        ch = segment[n]
        sym = SYMBOLS.find(ch)
        if sym < 0 or sym >= len(flat):
            raise ValueError(f"ordre : symbole « {ch} » inconnu pour cette disposition")
        step = flat[sym]
        remaining = ranks[step[0]][step[1]] - done.get(step, 0)
        n += 1
        if n < len(segment) and segment[n] in COUNTS:
            count = int(segment[n])
            n += 1
        else:
            count = remaining
        if count <= 0 or count > remaining:
            raise ValueError(f"ordre : « {ch} » demande {count} point(s), {remaining} restant(s) sur ce talent")
        order += [step] * count
        done[step] = done.get(step, 0) + count
    for ti, tree in enumerate(ranks):
        for i, rank in enumerate(tree):
            if done.get((ti, i), 0) != rank:
                raise ValueError(f"ordre : {done.get((ti, i), 0)} point(s) placé(s) pour le rang {rank} en {(ti, i)}")
    return tuple(order)


def decode(code: str, max_ranks: Sequence[Sequence[int]], class_slug: str | None = None) -> TfPlan:
    """Plan d'un code v6 ou d'un lien, sur la disposition `max_ranks` (ValueError en français : génération non prise
    en charge, forme invalide, rang ou position hors de la disposition, ordre incohérent, autre classe)."""
    flat = _flat([len(t) for t in max_ranks])
    raw = code_of(code)
    pieces = raw.split("/")
    if len(pieces) != 3 or not _SLUG.match(pieces[0]) or not pieces[1].isdigit():
        raise ValueError(f"forme invalide : « {raw} » (attendu <classe>/<niveau>/<arbres>-{CODE_VERSION})")
    slug, level, body = pieces[0], int(pieces[1]), pieces[2]
    if class_slug is not None and slug != class_slug:
        raise ValueError(f"code d'une autre classe : « {slug} », classe « {class_slug} » attendue")
    parts = body.split("-")
    if parts[-1] != CODE_VERSION:
        raise ValueError(f"génération « {parts[-1]} » non prise en charge (seule la génération {CODE_VERSION} est lue)")
    parts = parts[:-1]
    if len(parts) not in (TREES, TREES + 1, TREES + LEGACY, TREES + LEGACY + 1):
        raise ValueError(f"forme invalide : {len(parts)} segment(s) avant la génération")
    if len(max_ranks) != TREES:
        raise ValueError(f"disposition de {len(max_ranks)} arbres : {TREES} attendus")
    ranks: list[list[int]] = []
    for ti, segment in enumerate(parts[:TREES]):
        if not _TREE.match(segment):
            raise ValueError(f"forme invalide : arbre {ti + 1} « {segment} » (chiffres seulement)")
        if len(segment) > len(max_ranks[ti]):
            raise ValueError(f"arbre {ti + 1} : {len(segment)} positions pour {len(max_ranks[ti])} dans la liste")
        tree = [int(c) for c in segment] + [0] * (len(max_ranks[ti]) - len(segment))
        for i, (rank, top) in enumerate(zip(tree, max_ranks[ti], strict=True)):
            if rank > top:
                raise ValueError(f"arbre {ti + 1}, position {i + 1} : rang {rank} au-delà du maximum {top}")
        ranks.append(tree)
    rest = parts[TREES:]
    legacy = tuple(rest[:LEGACY]) if len(rest) >= LEGACY else None
    order_segment = rest[LEGACY:] if legacy is not None else rest
    order = _decode_order(order_segment[0], ranks, flat) if order_segment else None
    return TfPlan(slug, level, tuple(tuple(t) for t in ranks), order, legacy)
