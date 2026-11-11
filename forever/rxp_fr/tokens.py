"""Découpage d'une ligne de guide RestedXP (FR1).

Une ligne se rend exactement par `prefix + text + suffix` : `prefix` ne se traduit jamais (retrait, commande et
arguments, marqueur `>>`, `+` ou `*`), `text` est le texte libre, `suffix` le filtre `<< …` et les blancs de fin.
Syntaxe relevée dans `GuideLoader.lua` de RXPGuides (lecture seule) : en-tête `#clé valeur`, étape `step`,
commande `.nom arguments >>texte << filtre`, lignes de texte `>>…`, `+…` (avertissement) et `*…` (précision).

Le texte devient un **gabarit** : chaque nom coloré (`|cRXP_FRIENDLY_…|r`…), icône (`|T…|t`), lien (`|H…|h…|h`),
nom entre crochets et nombre est remplacé par un jeton `{n}` ; les codes `|cRXP_WARN_` et `|r` d'un avertissement
restent dans le gabarit (texte à traduire). Une même phrase sert ainsi à toutes les étapes."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

# En-têtes dont la valeur se traduit (noms de guide, groupes) ; les autres en-têtes restent intacts.
TITLE_HEADERS = frozenset({"name", "displayname", "next", "group", "subgroup", "include"})
TEXT_MARKERS = (">>", "+", "*")
# Couleurs de RestedXP qui entourent un nom, et la sorte de nom : PNJ, objet, objet ou objet du monde à ramasser.
NAME_COLOURS = {"FRIENDLY": "npc", "ENEMY": "npc", "LOOT": "item", "BUY": "item", "PICK": "pick"}
_SLOT = re.compile(
    r"(?P<name>\|cRXP_(?P<colour>FRIENDLY|ENEMY|LOOT|BUY|PICK)_(?P<inner>.*?)\|r)"
    r"|(?P<icon>\|T[^|]*\|t|\|A[^|]*\|a)"
    r"|(?P<link>\|H[^|]*\|h.*?\|h)"
    r"|(?P<bracket>\[[^\[\]|]+\])"
    r"|(?P<number>(?<![\w.])\d+(?:\.\d+)?(?![\w]))"
)
_PLACEHOLDER = re.compile(r"\{\{|\}\}|\{(\d+)\}")
_ID = re.compile(r"^(?P<name>.*?)::(?P<id>\d+)$")


@dataclass(frozen=True)
class Line:
    kind: str  # blank, comment, step, header, command, text, other
    prefix: str
    text: str
    suffix: str
    command: str | None = None  # nom de la commande (`accept`) ou clé de l'en-tête (`next`)

    def render(self) -> str:
        return self.prefix + self.text + self.suffix


def _lead(head: str, rest: str) -> tuple[str, str]:
    """Blancs de tête du texte rangés dans le préfixe (`>> Accept …` : le texte commence au mot)."""
    text = rest.lstrip(" 	")
    return head + rest[: len(rest) - len(text)], text


def _split_suffix(rest: str) -> tuple[str, str]:
    """(texte, suffixe) : le suffixe commence aux blancs qui précèdent le premier `<<`, ou aux blancs de fin."""
    cut = rest.find("<<")
    if cut < 0:
        cut = len(rest)
    while cut > 0 and rest[cut - 1] in " \t\r":
        cut -= 1
    return rest[:cut], rest[cut:]


def parse_line(raw: str) -> Line:
    stripped = raw.strip()
    indent = raw[: len(raw) - len(raw.lstrip())]
    if not stripped:
        return Line("blank", raw, "", "")
    if stripped.startswith("--"):
        return Line("comment", raw, "", "")
    if stripped.startswith("step") and (len(stripped) == 4 or stripped[4] in " \t<"):
        return Line("step", raw, "", "")
    if stripped.startswith("#"):
        key = stripped[1:].split(None, 1)[0] if len(stripped) > 1 else ""
        if key.lower() in TITLE_HEADERS:
            head = raw[: raw.index("#") + 1 + len(key)]
            rest = raw[len(head) :]
            spaces = rest[: len(rest) - len(rest.lstrip(" \t"))]
            text, suffix = _split_suffix(rest[len(spaces) :])
            return Line("header", head + spaces, text, suffix, key.lower())
        return Line("header", raw, "", "", key.lower())
    if stripped.startswith("."):
        command = stripped[1:].split(None, 1)[0] if len(stripped) > 1 else ""
        at = raw.find(">>")
        if at >= 0:
            head, rest = _lead(raw[: at + 2], raw[at + 2 :])
            text, suffix = _split_suffix(rest)
            return Line("command", head, text, suffix, command)
        body, suffix = _split_suffix(raw)
        return Line("command", body, "", suffix, command)
    for marker in TEXT_MARKERS:
        if stripped.startswith(marker):
            head, rest = _lead(indent + marker, raw[len(indent) + len(marker) :])
            text, suffix = _split_suffix(rest)
            return Line("text", head, text, suffix)
    return Line("other", raw, "", "")


@dataclass(frozen=True)
class Slot:
    kind: str  # npc, item, pick, icon, link, bracket, number
    raw: str
    name: str | None = None  # nom anglais (sans identifiant ni crochets) des sortes nommées
    ident: int | None = None  # identifiant après `::`
    head: str = ""  # raw == head + name (+ "::id") + tail
    tail: str = ""

    def with_name(self, name: str) -> str:
        if self.name is None:
            return self.raw
        ident = f"::{self.ident}" if self.ident is not None else ""
        return self.head + name + ident + self.tail


@dataclass(frozen=True)
class Template:
    pattern: str
    slots: tuple[Slot, ...]


def _escape(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


def _named(kind: str, raw: str, head: str, inner: str, tail: str) -> Slot:
    if inner.startswith("[") and inner.endswith("]") and len(inner) > 2:
        head, inner, tail = head + "[", inner[1:-1], "]" + tail
    m = _ID.match(inner)
    if m:
        return Slot(kind, raw, m["name"], int(m["id"]), head, tail)
    return Slot(kind, raw, inner, None, head, tail)


def make_template(text: str) -> Template:
    parts: list[str] = []
    slots: list[Slot] = []
    pos = 0
    for m in _SLOT.finditer(text):
        parts.append(_escape(text[pos : m.start()]))
        raw = m.group()
        if m["name"]:
            colour = m["colour"]
            head = f"|cRXP_{colour}_"
            slot = _named(NAME_COLOURS[colour], raw, head, m["inner"], "|r")
        elif m["icon"]:
            slot = Slot("icon", raw)
        elif m["link"]:
            slot = Slot("link", raw)
        elif m["bracket"]:
            slot = Slot("bracket", raw, raw[1:-1], None, "[", "]")
        else:
            slot = Slot("number", raw)
        slots.append(slot)
        parts.append("{" + str(len(slots)) + "}")
        pos = m.end()
    parts.append(_escape(text[pos:]))
    return Template("".join(parts), tuple(slots))


def placeholders(pattern: str) -> list[int]:
    return [int(m[1]) for m in _PLACEHOLDER.finditer(pattern) if m[1] is not None]


def fill(pattern: str, values: Sequence[str]) -> str:
    """Gabarit rempli ; ValueError si un jeton désigne un emplacement absent."""

    def one(m: re.Match[str]) -> str:
        if m[1] is None:
            return m.group()[0]
        index = int(m[1])
        if not 1 <= index <= len(values):
            raise ValueError(f"jeton {{{index}}} sans valeur ({len(values)} emplacement(s))")
        return values[index - 1]

    return _PLACEHOLDER.sub(one, pattern)


def translatable(pattern: str) -> bool:
    """Le gabarit porte du texte à traduire (une lettre hors jetons et codes de couleur)."""
    bare = _PLACEHOLDER.sub("", pattern).replace("|cRXP_WARN_", "").replace("|r", "")
    return re.search(r"[A-Za-z]", bare) is not None
