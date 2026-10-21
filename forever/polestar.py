"""Guides de Polestar, squelette des routes au-delà des parcours gratuits de RestedXP (plan « Sources d'abord », étape
d ; décision 289).

Les fichiers `.guide` (format v1, `docs/GUIDE_FORMAT.md` de Polestar) sont lus dans le clone en cache
(`<cache>/third_party/polestar`, commit épinglé dans la provenance), en lecture seule, pour un usage privé (GPL-3.0) :
rien n'en est recopié dans le dépôt, l'addon n'est jamais installé ni exécuté. Chaque guide de la catégorie Leveling
est traduit dans la structure des parcours de RestedXP (`forever.rxp_guides.Guide`) pour le même rejeu et la même
base adaptée (`forever.compare`) : quêtes prises, objectifs, rendus et niveaux à atteindre ; les conditions `only`
deviennent des filtres de RestedXP ; le contenu de groupe est écarté comme les donjons de RestedXP (nos routes ajoutent
les donjons avec leurs quêtes elles-mêmes). Aucune valeur de jeu ici."""

from __future__ import annotations

import itertools
import re
import shlex
from dataclasses import replace
from pathlib import Path

from forever.rxp_guides import Action, Guide, Library, Step

GUIDES = ("guides", "forever")
ATTRIBUTION = "Polestar Guides (fitzforge/polestar, GPL-3.0, usage privé ; commit {commit})"
CLASSES = frozenset({"warrior", "paladin", "hunter", "rogue", "priest", "shaman", "mage", "warlock", "druid"})
FACTIONS = frozenset({"alliance", "horde"})
_LEVELS = re.compile(r"^(\d+)\s*-\s*(\d+)$")
_QUEST_LINK = re.compile(r"^(\d+)(?:\.\d+)?$")


def _strip(line: str) -> str:
    """Ligne sans note du joueur (` -- `) ni commentaire d'auteur (`#` en tête ou après un blanc)."""
    if " -- " in line:
        line = line.split(" -- ", 1)[0]
    out, quoted = [], False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        if ch == "#" and not quoted and (i == 0 or line[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).rstrip()


def condition(spec: str) -> str | None:
    """Condition `only` de Polestar (classes OU, races OU, camps OU ; groupes ET ; `!` nie) en filtre de RestedXP
    (alternatives `/` de jetons tous vrais)."""
    names = [n.strip().lower() for n in spec.split(",") if n.strip()]
    if not names:
        return None
    pos_cls = [n for n in names if n in CLASSES]
    neg = [n for n in names if n.startswith("!")]
    factions = [n for n in names if n in FACTIONS]
    races = [n for n in names if n not in CLASSES and n not in FACTIONS and not n.startswith("!")]
    alternatives = []
    none: list[str | None] = [None]
    for c, r, f in itertools.product(pos_cls or none, races or none, factions or none):
        tokens = [t for t in (c, r, f) if t] + neg
        alternatives.append(" ".join(tokens))
    return "/".join(a for a in alternatives if a) or None


def _both(a: str | None, b: str | None) -> str | None:
    """Conjonction de deux filtres de RestedXP (chaque alternative de l'un avec chaque alternative de l'autre)."""
    if not a or not b:
        return a or b
    return "/".join(f"{x} {y}" for x in a.split("/") for y in b.split("/"))


def _tokens(line: str) -> list[str]:
    try:
        return shlex.split(line, posix=True)
    except ValueError:
        return line.split()


def _goal(tokens: list[str]) -> tuple[Action | None, str | None]:
    """Action rejouée d'une ligne d'objectif et son filtre `only` ; None pour un objectif sans quête ni niveau ou du
    contenu de groupe."""
    if not tokens:
        return None, None
    word = tokens[0].lower()
    rest = [t.lower() for t in tokens[1:]]
    if "group" in rest:
        return None, None
    flt = None
    if "only" in rest:
        i = rest.index("only")
        flt = condition(tokens[i + 2]) if i + 2 < len(tokens) else None
    first = tokens[1] if len(tokens) > 1 else ""
    if word in ("accept", "turnin", "complete") and first.isdigit():
        kind = {"accept": "accept", "turnin": "turnin", "complete": "objective"}[word]
        return Action(kind, int(first), flt), flt
    if word in ("kill", "collect") and "quest" in rest:
        i = rest.index("quest")
        m = _QUEST_LINK.match(tokens[i + 2]) if i + 2 < len(tokens) else None
        if m:
            return Action("objective", int(m.group(1)), flt), flt
    if word == "level" and first.isdigit():
        return Action("grind", int(first), flt), flt
    return None, flt


def parse_polestar(text: str, file: str) -> Guide | None:
    """Guide de leveling traduit (nom « <min>-<max> <titre> », filtre de l'en-tête, suites par identifiant de
    guide) ; None pour un guide d'une autre catégorie ou sans niveaux."""
    header: dict[str, str] = {}
    steps: list[Step] = []
    current: list[str] | None = None
    raw: list[str] = []
    for line in text.splitlines():
        clean = _strip(line)
        if not clean.strip():
            continue
        if not line[:1].isspace():
            if current is not None:
                steps.append(_step(current, raw))
            key, _, value = clean.partition(" ")
            if key.lower() == "step":
                current, raw = [], [line.rstrip()]
                continue
            if current is None:
                header[key.lower()] = value.strip()
            continue
        if current is not None:
            current.append(clean.strip())
            raw.append(line.rstrip())
    if current is not None:
        steps.append(_step(current, raw))
    if header.get("category", "Leveling").lower() != "leveling":
        return None
    m = _LEVELS.match(header.get("levels", ""))
    if m is None:
        return None
    flt = None
    for key in ("faction", "race", "class"):
        if header.get(key):
            flt = _both(flt, condition(header[key]))
    nexts = tuple((n.strip(), None) for n in header.get("next", "").split(",") if n.strip())
    name = f"{m.group(1)}-{m.group(2)} {header.get('title') or header.get('guide') or file}"
    return Guide(
        name=name,
        group="Polestar",
        defaultfor=None,
        filter=flt,
        xp_rate=None,
        next=nexts,
        steps=tuple(steps),
        file=f"{header.get('guide', '')}|{file}",
    )


def _step(lines: list[str], raw: list[str]) -> Step:
    flt = None
    actions: list[Action] = []
    for line in lines:
        tokens = _tokens(line)
        if tokens and tokens[0].lower() == "only":
            flt = condition(" ".join(tokens[1:]))
            continue
        action, _ = _goal(tokens)
        if action is not None:
            actions.append(action)
    # aucune ligne brute : la syntaxe de Polestar n'est pas celle de RestedXP ; le corps livré est réécrit depuis les
    # actions (`forever.compare._adapted_lines`)
    return Step(filter=flt, xp_rate=None, xp_guard=None, guards=(), dungeon=False, actions=tuple(actions))


def read_polestar_guides(clone: Path) -> Library:
    """Guides de leveling de Polestar (`guides/forever/**.guide`), suites résolues en noms de guides ; bibliothèque
    vide sans le clone."""
    folder = clone.joinpath(*GUIDES)
    guides: list[Guide] = []
    files = 0
    for path in sorted(folder.rglob("*.guide")) if folder.is_dir() else []:
        files += 1
        g = parse_polestar(path.read_text(encoding="utf-8"), path.relative_to(clone).as_posix())
        if g is not None:
            guides.append(g)
    by_id = {g.file.split("|", 1)[0]: g.name for g in guides}
    resolved = [replace(g, next=tuple((by_id.get(n, n), f) for n, f in g.next)) for g in guides]
    return Library(tuple(resolved), files, 0)
