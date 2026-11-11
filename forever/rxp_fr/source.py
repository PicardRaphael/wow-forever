"""Fichiers de guides RestedXP pour Forever (FR1) : anglais (`Guides/Forever`), français (`lang/Guides-frFR/forever`),
guides alignés et glossaire relevé dans les guides que RestedXP a déjà traduits. Lecture locale seule.

Un guide français de RestedXP est rapproché de son guide anglais par sa **signature** : la suite de ses commandes et
de leurs arguments (hors noms de `.target` / `.mob` et texte de `.timer`, que RestedXP traduit) et ses étapes ; même
signature d'abord, puis la plus proche (révision voisine du même guide). Le glossaire lit les lignes alignées par
leurs parties jamais traduites (blocs communs), ligne à ligne. Les fichiers déjà écrits par
FR1 (marqueur en tête) ne sont jamais relus comme source : la version de RestedXP sauvegardée avant la première
écriture les remplace (`originals`)."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from forever.rxp_fr.memory import TITLE
from forever.rxp_fr.names import Key
from forever.rxp_fr.patterns import QUEST_PREFIXES
from forever.rxp_fr.tokens import Line, make_template, parse_line, placeholders
from forever.rxp_guides import _BLOCK

EN_DIR = ("RXPGuides", "Guides", "Forever")
FR_DIR = ("RXPGuides", "lang", "Guides-frFR", "forever")
TOC = ("RXPGuides", "RXPGuides.toc")
GUARD = 'if GetLocale() ~= "frFR" then return end'
MARKER = "-- FR1 forever"
UNTRANSLATED_COMMANDS = frozenset({"target", "mob"})  # arguments en nom, traduits sans `::id` (question Q2)
TEXT_ARG_COMMANDS = frozenset({"timer"})  # `.timer N,texte` : RestedXP traduit le texte après la virgule
SAME_GUIDE = 0.8  # signatures au moins aussi proches : deux révisions du même guide (méthode de rapprochement)
_PH = re.compile(r"\{\{|\}\}|\{(\d+)\}")


@dataclass(frozen=True)
class Piece:
    raw: str  # texte hors guide (préambule, appel `RegisterGuide([[`, fin `]])`) ou guide refusé
    body: str | None = None  # texte d'un guide en clair (entre `[[` et `]]`)


def _clear(body: str) -> bool:
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    return bool(lines) and lines[0].startswith("#") and any(parse_line(ln).kind == "step" for ln in lines)


def split_file(text: str) -> list[Piece]:
    pieces: list[Piece] = []
    pos = 0
    for m in _BLOCK.finditer(text):
        body = m.group("long")
        if body is None or not _clear(body):
            continue  # guide chiffré ou encodé : laissé dans le texte brut, jamais lu
        pieces.append(Piece(text[pos : m.start("long")]))
        pieces.append(Piece("", body))
        pos = m.end("long")
    pieces.append(Piece(text[pos:]))
    return pieces


def guide_bodies(text: str) -> list[str]:
    return [p.body for p in split_file(text) if p.body is not None]


def refused_blocks(text: str) -> int:
    return sum(1 for m in _BLOCK.finditer(text) if m.group("long") is None or not _clear(m.group("long")))


def header(body: str, key: str) -> list[str]:
    return [ln.text for ln in map(parse_line, body.splitlines()) if ln.kind == "header" and ln.command == key]


def line_key(line: Line) -> str:
    """Partie d'une ligne que RestedXP ne traduit jamais : commande et arguments (sans les noms de `.target` /
    `.mob`, sans le texte de `.timer`), nature de la ligne, clé d'un en-tête."""
    command = (line.command or "").lower()
    if line.kind == "command":
        if command in UNTRANSLATED_COMMANDS:
            return "." + command
        head = line.prefix.strip().removesuffix(">>").strip()
        if command in TEXT_ARG_COMMANDS:
            head = head.split(",", 1)[0]
        return head + line.suffix.strip()
    if line.kind == "header":
        return "#" + command
    return line.kind


def signature(body: str) -> tuple[str, ...]:
    out: list[str] = []
    for raw in body.splitlines():
        line = parse_line(raw)
        if line.kind == "step" or (
            line.kind == "command" and (line.command or "").lower() not in UNTRANSLATED_COMMANDS
        ):
            out.append(line_key(line))
    return tuple(out)


def similarity(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    if a == b:
        return 1.0
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    return matcher.ratio() if matcher.quick_ratio() >= SAME_GUIDE else 0.0


def match_guides(english: list[str], french: list[str]) -> dict[int, str]:
    """Indice du guide anglais -> guide français de RestedXP : même signature d'abord, puis signature la plus
    proche (au moins `SAME_GUIDE`, révision voisine du même guide) ; chaque guide servi une fois."""
    en_sig = [signature(b) for b in english]
    fr_sig = [signature(b) for b in french]
    out: dict[int, str] = {}
    free = set(range(len(french)))
    for i, sig in enumerate(en_sig):
        same = next((j for j in sorted(free) if fr_sig[j] == sig), None)
        if same is not None:
            out[i] = french[same]
            free.discard(same)
    for i, sig in enumerate(en_sig):
        if i in out or not free:
            continue
        score, j = max((similarity(sig, fr_sig[j]), j) for j in free)
        if score >= SAME_GUIDE:
            out[i] = french[j]
            free.discard(j)
    return out


def aligned_lines(en_body: str, fr_body: str) -> Iterator[tuple[Line, Line]]:
    """Paires de lignes alignées par leurs parties jamais traduites (blocs communs), même si RestedXP a ajouté ou
    retiré des lignes dans sa révision."""
    a = [parse_line(x) for x in en_body.splitlines()]
    b = [parse_line(x) for x in fr_body.splitlines()]
    if len(a) == len(b):
        yield from zip(a, b, strict=True)
        return
    matcher = SequenceMatcher(None, [line_key(x) for x in a], [line_key(x) for x in b], autojunk=False)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            yield a[block.a + k], b[block.b + k]


def read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


@dataclass(frozen=True)
class Target:
    rel: str
    en_path: Path
    fr_path: Path
    english: int  # guides en clair du fichier anglais
    french: int  # guides en clair du fichier français de RestedXP
    ours: bool  # le fichier français en place a été écrit par FR1


def english_files(addons: Path) -> Iterator[tuple[str, Path]]:
    root = addons.joinpath(*EN_DIR)
    if not root.is_dir():
        return
    files = sorted(root.glob("*.lua"), key=lambda p: p.name.lower())
    files += sorted((root / "dungeon").glob("*.lua"), key=lambda p: p.name.lower())
    for path in files:
        yield path.relative_to(root).as_posix(), path


def restedxp_french(addons: Path, rel: str, originals: Mapping[str, str] | None) -> str:
    """Texte français de RestedXP pour `rel` : le fichier en place, ou sa sauvegarde s'il a été écrit par FR1."""
    path = addons.joinpath(*FR_DIR, rel)
    if is_ours(path):
        return (originals or {}).get(rel, "")
    return read_text(path) if path.is_file() else ""


def is_ours(path: Path) -> bool:
    if not path.is_file():
        return False
    head = read_text(path).split("\n", 2)
    return len(head) > 1 and head[1].startswith(MARKER)


def targets(addons: Path, originals: Mapping[str, str] | None = None) -> list[Target]:
    """Fichiers dont le français de RestedXP a moins de guides en clair que l'anglais (ou déjà écrits par FR1)."""
    out: list[Target] = []
    for rel, en_path in english_files(addons):
        fr_path = addons.joinpath(*FR_DIR, rel)
        ours = is_ours(fr_path)
        english = len(guide_bodies(read_text(en_path)))
        french = len(guide_bodies(restedxp_french(addons, rel, originals)))
        if english > french or ours:
            out.append(Target(rel, en_path, fr_path, english, french, ours))
    return out


def rxp_version(addons: Path) -> str | None:
    toc = addons.joinpath(*TOC)
    if not toc.is_file():
        return None
    m = re.search(r"^## Version:\s*(\S+)", read_text(toc), re.MULTILINE)
    return m[1] if m else None


# --- glossaire -------------------------------------------------------------------------------------------------


@dataclass
class Glossary:
    names: dict[str, dict[Key, str]] = field(default_factory=dict)
    phrases: dict[str, str] = field(default_factory=dict)


def renumber(pattern: str, mapping: Mapping[int, int]) -> str:
    return _PH.sub(lambda m: m.group() if m[1] is None else "{" + str(mapping[int(m[1])]) + "}", pattern)


def align_text(en_text: str, fr_text: str) -> tuple[str, str, list[tuple[str, Key, str]]] | None:
    """(gabarit anglais, gabarit français aux jetons de l'anglais, noms rapprochés (sorte, anglais, français)) ; None
    si les emplacements ne se rapprochent pas tous (icône retirée, nom ajouté…)."""
    en, fr = make_template(en_text), make_template(fr_text)
    if len(en.slots) != len(fr.slots):
        return None
    used: set[int] = set()
    mapping: dict[int, int] = {}
    names: list[tuple[str, Key, str]] = []
    by_kind: dict[str, list[int]] = defaultdict(list)
    for i, slot in enumerate(en.slots, 1):
        by_kind[slot.kind].append(i)
    for j, slot in enumerate(fr.slots, 1):
        candidates = [i for i in by_kind.get(slot.kind, []) if i not in used]
        if slot.name is None:
            candidates = [i for i in candidates if en.slots[i - 1].raw == slot.raw]
        if not candidates:
            return None
        i = candidates[0]
        used.add(i)
        mapping[j] = i
        src = en.slots[i - 1]
        if slot.name is not None and src.name is not None and slot.name != src.name:
            names.append((slot.kind, src.name, slot.name))
            if src.ident is not None and src.ident == slot.ident:
                names.append((slot.kind, src.ident, slot.name))
    french = renumber(fr.pattern, mapping)
    if sorted(placeholders(french)) != sorted(placeholders(en.pattern)):
        return None
    return en.pattern, french, names


class _Collector:
    def __init__(self) -> None:
        self.names: dict[str, dict[Key, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
        self.phrases: dict[str, Counter[str]] = defaultdict(Counter)

    def name(self, kind: str, en: Key, fr: str) -> None:
        if fr and en != fr:
            self.names[kind][en][fr] += 1

    def phrase(self, en: str, fr: str) -> None:
        if en != fr:
            self.phrases[en][fr] += 1

    def text(self, en_text: str, fr_text: str, *, title: bool = False) -> None:
        found = align_text(en_text, fr_text)
        if found is None:
            return
        en, fr, names = found
        self.phrase(TITLE + en if title else en, fr)
        for kind, a, b in names:
            self.name(kind, a, b)

    def lines(self, en: Line, fr: Line) -> None:
        if en.kind != fr.kind or en.command != fr.command:
            return
        command = (en.command or "").lower()
        if en.kind == "header" and command in ("name", "displayname"):
            self.name("guide", en.text.strip(), fr.text.strip())
        elif en.kind == "header" and command == "next":
            a, b = en.text.split(";"), fr.text.split(";")
            if len(a) == len(b):
                for x, y in zip(a, b, strict=True):
                    self.name("guide", x.strip(), y.strip())
        elif en.kind == "header" and command in ("group", "subgroup"):
            self.text(en.text.strip(), fr.text.strip(), title=True)
        elif en.kind == "command" and command in QUEST_PREFIXES and en.text and fr.text:
            en_prefix, fr_prefix = QUEST_PREFIXES[command]
            ident = re.search(r"\d+", en.prefix)
            if en.text.startswith(en_prefix) and fr.text.startswith(fr_prefix) and ident:
                title = fr.text[len(fr_prefix) :].strip()
                self.name("quest", int(ident.group()), title)
                self.name("quest_title", en.text[len(en_prefix) :].strip(), title)
        elif en.kind == "command" and command in TEXT_ARG_COMMANDS and not en.text:
            en_timer, fr_timer = timer_text(en), timer_text(fr)
            if en_timer and fr_timer:
                self.text(en_timer, fr_timer)
        elif en.kind == "command" and command in UNTRANSLATED_COMMANDS and not en.text:
            a = _args(en.prefix, en.command or "")
            b = _args(fr.prefix, fr.command or "")
            if len(a) == len(b):
                for x, y in zip(a, b, strict=True):
                    if "::" not in x and "::" not in y:
                        self.name("npc", x.strip(), y.strip())
        elif en.text and fr.text:
            self.text(en.text, fr.text)

    def result(self) -> Glossary:
        names = {k: {en: c.most_common(1)[0][0] for en, c in d.items()} for k, d in self.names.items()}
        phrases = {en: c.most_common(1)[0][0] for en, c in self.phrases.items()}
        return Glossary(names, phrases)


def timer_text(line: Line) -> str:
    """Texte d'une ligne `.timer N,texte` (vide s'il n'y en a pas)."""
    return line.prefix.split(",", 1)[1] if "," in line.prefix else ""


def _args(prefix: str, command: str) -> list[str]:
    rest = prefix.strip()[1 + len(command) :]
    return rest.split(",") if rest.strip() else []


def glossary(addons: Path, originals: Mapping[str, str] | None = None) -> Glossary:
    """Noms et phrases relevés dans les guides anglais et français de RestedXP rapprochés et de même longueur."""
    found = _Collector()
    for rel, en_path in english_files(addons):
        french = restedxp_french(addons, rel, originals)
        if not french:
            continue
        en_guides = guide_bodies(read_text(en_path))
        for i, fr_body in match_guides(en_guides, guide_bodies(french)).items():
            for x, y in aligned_lines(en_guides[i], fr_body):
                found.lines(x, y)
    return found.result()
