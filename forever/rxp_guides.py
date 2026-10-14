"""Parcours gratuits en clair de RestedXP pour Forever, lus en local pour les comparer à nos routes (RX1c, décision 268).

Exception encadrée à l'exclusion de RXPGuides : **une mesure, pas une source**. Seuls les fichiers
`RXPGuides/Guides/Forever/*.lua` de l'addon installé sont ouverts (et `dungeon/` sur demande) ; seuls les blocs
`RXPGuides.RegisterGuide([[…]])` dont le texte est un guide en clair (première ligne utile en `#`) sont analysés ;
tout autre bloc (guide chiffré ou encodé) est compté dans `refused` et jamais décodé ; les guides importés
(`RXPData`) ne sont jamais lus. Rien de ce module n'entre dans nos routes ni dans le dépôt : seules les quêtes
(identifiants du jeu), leurs conditions et l'ordre des arrêts servent au rejeu par notre simulation
(`forever/compare.py`) ; aucun texte d'étape n'est gardé.

Syntaxe relevée dans le code local de RXPGuides 4.11.23 (`ParseGuide` de `GuideLoader.lua`, `functions.xp`,
`stepLogic.XpRateCheck` de `RXPGuides.lua`) : en-tête `#clé valeur` et `<< filtre` avant la première étape ;
étapes ouvertes par `step` (`<< filtre` facultatif) ; commandes `.nom arguments` (filtre de ligne `<< …` en fin) ;
filtre = alternatives séparées par `/`, chacune une suite de jetons (classe, race, camp) tous vrais, `!` niant un
jeton ; `.xp N` farm jusqu'au niveau N, `.xp N,1` étape sautée au niveau N ou plus, `.xp <N,1` étape sautée sous le
niveau N."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from forever.errors import InvalidArgumentError

GUIDES_DIR = ("RXPGuides", "Guides", "Forever")
_BLOCK = re.compile(r"RegisterGuide\(\s*(\[(=*)\[(?P<long>.*?)\]\2\]|\"(?P<short>(?:[^\"\\]|\\.)*)\")", re.DOTALL)
_LEVELS = re.compile(r"^(\d+)-(\d+)")
_INT = re.compile(r"-?\d+")
_XP = re.compile(r"^(?P<op>[<>]?)\s*(?P<level>\d+)(?P<frac>[+.\-]?\d*)\s*(?:,\s*(?P<skip>-?\d+))?")
# Jetons de filtre qui ne désignent jamais le personnage comparé (saisons, modes, guides à sauter).
NEVER = frozenset({"skip", "sod", "som", "hc", "hardcore", "era", "tbc", "wotlk", "beta"})
RACES = {
    "undead": "Undead",
    "scourge": "Undead",
    "nightelf": "NightElf",
    # CJ1 : les deux races Skyborne portent le jeton du fichier du client (`#defaultfor Skyborne`)
    "highorderskyborne": "Skyborne",
    "windshaperskyborne": "Skyborne",
}
QUEST_COMMANDS = {"accept": "accept", "complete": "objective", "turnin": "turnin"}
GUARDS = ("isonquest", "isquestturnedin", "isquestcomplete", "isquestavailable")
DEFAULT_XP_RATE = 1.0  # taux d'XP de Forever pour `#xprate` (celui de RestedXP hors saison : 1)


class Who(NamedTuple):
    """Personnage comparé, aux noms de jetons de RestedXP (classe, race sans espace, camp)."""

    class_name: str
    race: str
    faction: str


@dataclass(frozen=True)
class Action:
    """Commande d'une étape gardée pour le rejeu : `accept`, `objective`, `turnin` (quête), `grind` (niveau)."""

    kind: str
    ref: int
    filter: str | None = None


@dataclass(frozen=True)
class Step:
    filter: str | None
    xp_rate: tuple[str, str | None] | None  # `#xprate` de l'étape et son filtre
    xp_guard: tuple[bool, int, str | None] | None  # (logique inversée, niveau, filtre) de `.xp N,saut`
    guards: tuple[tuple[str, int, str | None], ...]  # (`isonquest`…, quête, filtre)
    dungeon: bool  # étape de donjon (`.dungeon`) : écartée, nos comparaisons sont sans donjon
    actions: tuple[Action, ...]
    hardcore: bool = False  # étape `#hardcore` : écartée (Forever n'est pas un serveur hardcore)


@dataclass(frozen=True)
class Guide:
    name: str
    group: str | None
    defaultfor: str | None
    filter: str | None
    xp_rate: str | None
    next: tuple[tuple[str, str | None], ...]  # (nom, filtre) ; plusieurs noms d'une ligne : séparés par « ; »
    steps: tuple[Step, ...]
    file: str
    dungeon: bool = False

    @property
    def levels(self) -> tuple[int, int] | None:
        m = _LEVELS.match(self.name)
        return (int(m.group(1)), int(m.group(2))) if m else None


class Library(NamedTuple):
    guides: tuple[Guide, ...]
    files: int
    refused: int  # blocs qui ne sont pas des guides en clair (chiffrés, encodés) : comptés, jamais lus


class Chain(NamedTuple):
    guides: tuple[Guide, ...]
    missing: tuple[str, ...]  # suites annoncées absentes en clair (guides payants ou non livrés)


def _split_filter(line: str) -> tuple[str, str | None]:
    if "<<" in line:
        body, expr = line.split("<<", 1)
        return body.strip(), expr.strip() or None
    return line.strip(), None


def _token_true(token: str, who: Who) -> bool:
    low = token.lower()
    if low in NEVER:
        return False
    return low in {who.class_name.lower(), who.race.lower(), who.faction.lower()}


def applies(expr: str | None, who: Who) -> bool:
    """Filtre `<< …` de RestedXP vrai pour ce personnage : une des alternatives (`/`) dont tous les jetons sont vrais
    (`!` nie) ; un jeton inconnu (saison, mode) est faux."""
    if not expr:
        return True
    for alternative in expr.split("/"):
        tokens = alternative.split()
        if tokens and all((not _token_true(t[1:], who)) if t.startswith("!") else _token_true(t, who) for t in tokens):
            return True
    return False


def xp_rate_ok(spec: str | None, rate: float = DEFAULT_XP_RATE) -> bool:
    """Condition `#xprate` (`<1.99`, `>1.99`, `1.5-2`) vraie au taux d'XP donné (`stepLogic.XpRateCheck`)."""
    if not spec:
        return True
    m = re.match(r"^([<>]?)\s*(\d+\.?\d*)-?(\d*\.?\d*)", spec.strip())
    if not m:
        return True
    op, a, b = m.groups()
    low, high = 1.0, float("inf")
    if op == "<":
        low, high = 0.0, float(a) - 1e-4
    elif op == ">":
        low = float(a) + 1e-4
    else:
        low, high = float(a), float(b) if b else float("inf")
    return low <= rate <= high


def _first_int(args: str) -> int | None:
    m = _INT.search(args)
    return int(m.group()) if m else None


def _parse_step(lines: list[str], header: str) -> Step:
    _, step_filter = _split_filter(header[len("step") :])
    xp_rate: tuple[str, str | None] | None = None
    xp_guard: tuple[bool, int, str | None] | None = None
    guards: list[tuple[str, int, str | None]] = []
    actions: list[Action] = []
    dungeon = hardcore = False
    for raw in lines:
        line = raw.split("--", 1)[0].strip() if not raw.strip().startswith("--") else ""
        if line.startswith("#xprate"):
            xp_rate = _split_filter(line[len("#xprate") :])
            continue
        if line.split(" ", 1)[0] == "#hardcore":
            hardcore = True
            continue
        if not line.startswith("."):
            continue
        command, _, rest = line[1:].partition(" ")
        body, line_filter = _split_filter(rest)  # le filtre se place en fin de ligne, après le texte `>>`
        args = body.split(">>", 1)[0]
        command = command.lower()
        if command in QUEST_COMMANDS and (quest := _first_int(args)) is not None:
            actions.append(Action(QUEST_COMMANDS[command], quest, line_filter))
        elif command == "xp" and (m := _XP.match(args.strip())):
            level, skip = int(m.group("level")), m.group("skip")
            if skip is not None:  # saut négatif : logique inversée (`functions.xp` de RXPGuides)
                xp_guard = (m.group("op") == "<" or int(skip) < 0, level, line_filter)
            else:
                frac = m.group("frac")
                target = level - 1 if frac.startswith("-") else level  # « N-x » : à x points du niveau N
                actions.append(Action("grind", target, line_filter))
        elif command in GUARDS and (quest := _first_int(args)) is not None:
            guards.append((command, quest, line_filter))
        elif command == "dungeon":
            dungeon = True
    return Step(step_filter, xp_rate, xp_guard, tuple(guards), dungeon, tuple(actions), hardcore)


def parse_guide(text: str, file: str, *, dungeon: bool = False) -> Guide | None:
    """Guide en clair d'un bloc `RegisterGuide` ; None si le texte n'est pas un guide en clair (refusé)."""
    lines = text.splitlines()
    first = next((ln.strip() for ln in lines if ln.strip()), "")
    if not first.startswith("#") or not any(ln.strip().startswith("step") for ln in lines):
        return None
    head: dict[str, str] = {}
    nexts: list[tuple[str, str | None]] = []
    guide_filter: str | None = None
    steps: list[Step] = []
    current: tuple[str, list[str]] | None = None
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("step") and (len(stripped) == 4 or stripped[4] in " <"):
            if current is not None:
                steps.append(_parse_step(current[1], current[0]))
            current = (stripped, [])
            continue
        if current is not None:
            current[1].append(raw)
            continue
        if stripped.startswith("<<"):
            guide_filter = stripped[2:].strip() or None
        elif stripped.startswith("#next"):
            body, expr = _split_filter(stripped[len("#next") :])
            nexts.extend((name.strip().split("\\")[-1].strip(), expr) for name in body.split(";") if name.strip())
        elif stripped.startswith("#") and not stripped.startswith("#displayname"):
            key, _, value = stripped[1:].partition(" ")
            head.setdefault(key.lower(), _split_filter(value)[0])  # filtre de la valeur retiré
    if current is not None:
        steps.append(_parse_step(current[1], current[0]))
    name = head.get("name", "").strip()
    if not name:
        return None
    return Guide(
        name=name,
        group=head.get("group") or None,
        defaultfor=head.get("defaultfor") or None,
        filter=guide_filter,
        xp_rate=head.get("xprate") or None,
        next=tuple(nexts),
        steps=tuple(steps),
        file=file,
        dungeon=dungeon,
    )


def read_rxp_guides(addons: Path, *, dungeon_guides: bool = False) -> Library:
    """Guides en clair de `<addons>/RXPGuides/Guides/Forever` (fichiers triés ; `dungeon/` si demandé), lecture
    locale seule. `InvalidArgumentError` si RXPGuides n'y est pas installé."""
    root = addons.joinpath(*GUIDES_DIR)
    if not root.is_dir():
        raise InvalidArgumentError(
            f"Parcours RestedXP pour Forever introuvables ({root}).",
            "installer RXPGuides dans le dossier des addons du jeu, ou régler FOREVER_WOW_DIR",
        )
    files = sorted(root.glob("*.lua"), key=lambda p: p.name.lower())
    if dungeon_guides:
        files += sorted((root / "dungeon").glob("*.lua"), key=lambda p: p.name.lower())
    guides: list[Guide] = []
    refused = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root).as_posix()
        for m in _BLOCK.finditer(text):
            body = m.group("long")
            guide = parse_guide(body, rel, dungeon=rel.startswith("dungeon/")) if body is not None else None
            if guide is None:
                refused += 1
            else:
                guides.append(guide)
    return Library(tuple(guides), len(files), refused)


def _usable(guide: Guide, who: Who) -> bool:
    return applies(guide.filter, who) and xp_rate_ok(guide.xp_rate)


def _find(library: Library, name: str, who: Who, group: str | None) -> Guide | None:
    found = [g for g in library.guides if g.name == name and _usable(g, who)]
    found.sort(key=lambda g: g.group != group)
    return found[0] if found else None


def guide_chain(library: Library, who: Who, *, start: str | None = None) -> Chain:
    """Parcours suivi par ce personnage : guide de départ (`start`, partie du nom ; sinon le guide `#defaultfor` du
    personnage au plus bas niveau), puis chaque `#next` permis (le premier nom connu d'une ligne « ; »). Les suites
    absentes en clair sont rendues dans `missing`."""
    usable = [g for g in library.guides if _usable(g, who)]
    if start is not None:
        first = next((g for g in usable if start.lower() in g.name.lower()), None)
        if first is None:
            raise InvalidArgumentError(
                f"Aucun parcours RestedXP en clair nommé « {start} » pour ce personnage.",
                "voir forever route rxp-coverage",
            )
    else:
        defaults = [g for g in usable if g.defaultfor and applies(g.defaultfor, who)]
        if not defaults:
            raise InvalidArgumentError(
                "Aucun parcours RestedXP en clair pour ce personnage (classe, race, camp).",
                "voir forever route rxp-coverage, ou donner --start-guide",
            )
        first = min(defaults, key=lambda g: (g.levels or (999, 999), g.name))
    chain, current = [first], first
    missing: list[str] = []
    while True:
        names = [(n, expr) for n, expr in current.next if applies(expr, who)]
        nxt = None
        for name, _ in names:
            nxt = _find(library, name, who, current.group)
            if nxt is not None:
                break
        if nxt is None:
            missing.extend(name for name, _ in names[:1])
            break
        if nxt in chain:
            break
        chain.append(nxt)
        current = nxt
    return Chain(tuple(chain), tuple(missing))


def coverage(library: Library) -> list[dict[str, Any]]:
    """Jusqu'où vont les parcours en clair : pour chaque guide `#defaultfor`, la chaîne suivie (sans filtre de
    classe), son dernier niveau et la suite annoncée absente. Lecture des seuls en-têtes."""
    rows: list[dict[str, Any]] = []
    for g in library.guides:
        if not g.defaultfor:
            continue
        sides = [f for f in ("Alliance", "Horde") if applies(g.filter, Who("", "", f))]
        faction = sides[0] if len(sides) == 1 else "Alliance et Horde"
        if g.group and g.group.endswith(("(A)", "(H)")):  # groupe de RestedXP marqué par camp
            faction = "Alliance" if g.group.endswith("(A)") else "Horde"
        seen, current = [g], g
        missing: list[str] = []
        while True:
            names = [n for n, _ in current.next]
            nxt = next(
                (x for x in (_find_any(library, n, current.group) for n in names) if x is not None and x not in seen),
                None,
            )
            if nxt is None:
                missing.extend(n for n in names if _find_any(library, n, current.group) is None)
                break
            seen.append(nxt)
            current = nxt
        top = max((x.levels[1] for x in seen if x.levels), default=None)
        rows.append(
            {
                "faction": faction,
                "defaultfor": g.defaultfor,
                "start": g.name,
                "guides": [x.name for x in seen],
                "max_level": top,
                "missing": sorted(set(missing)),
                "dungeon": g.dungeon,
            }
        )
    # une chaîne qui commence dans une autre (guide `#defaultfor` atteint par un `#next`) n'est pas répétée
    inside = {(r["dungeon"], name) for r in rows for name in list(r["guides"])[1:]}
    return [r for r in rows if (r["dungeon"], r["start"]) not in inside]


def _find_any(library: Library, name: str, group: str | None) -> Guide | None:
    found = sorted((g for g in library.guides if g.name == name), key=lambda g: g.group != group)
    return found[0] if found else None


def who_for(class_name: str, race: str, faction: str) -> Who:
    """Jetons de RestedXP d'un personnage du profil (race sans espace : `Night Elf` -> `NightElf`)."""
    key = race.replace(" ", "").replace("-", "").lower()
    race_token = RACES.get(key, race.replace(" ", "").replace("-", ""))
    return Who(class_name.strip().capitalize(), race_token, faction.strip().capitalize())
