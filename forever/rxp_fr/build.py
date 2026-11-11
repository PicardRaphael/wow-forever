"""Assemblage d'un fichier de guides RestedXP en français (FR1).

Première ligne : garde-fou `if GetLocale() ~= "frFR" then return end` ; deuxième : marqueur FR1 (version du
générateur, empreinte de la source anglaise, version de RXPGuides, attribution). Puis le fichier anglais dans son
ordre : la garde anglaise (`RXP.enabledLocale`) retirée, chaque guide que RestedXP a traduit recopié tel quel, chaque
autre guide généré ligne à ligne (même nombre de lignes, commandes, identifiants, coordonnées et filtres intacts).
Encodage UTF-8 sans BOM, fins de ligne de la source.

Ce qui se traduit (relevé dans les 21 fichiers que RestedXP a traduits, plan FR1) : texte après `>>`, lignes `+` et
`*`, noms de guide et de groupe (`#name`, `#displayname`, `#next`, `#group`, `#subgroup`), titres de quête des
lignes `.accept` / `.turnin`, et les noms des arguments de `.target` / `.mob` sans `::id` (question Q2 ; RestedXP
résout un `Nom::id` par l'identifiant en jeu, et laisse en anglais les arguments de `.zone`, `.cast`, `.train`,
`.fly`, résolus par ses propres tables)."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from forever.rxp_fr.memory import TITLE, Memory
from forever.rxp_fr.names import Key, Name, NameTable
from forever.rxp_fr.patterns import PLACE_PHRASES, QUEST_PREFIXES, apply_patterns
from forever.rxp_fr.source import (
    GUARD,
    MARKER,
    TEXT_ARG_COMMANDS,
    UNTRANSLATED_COMMANDS,
    guide_bodies,
    match_guides,
    split_file,
)
from forever.rxp_fr.tokens import Line, Slot, fill, make_template, parse_line, translatable
from forever.rxp_fr.translator import Resolved, Translator, resolve

__all__ = ["GENERATOR_VERSION", "GUARD", "MARKER", "Report", "generate_file", "marker_info", "source_sha"]

GENERATOR_VERSION = 2  # 2 : noms entre crochets écartés, `[[` refusé (Lua 5.1 du jeu)
_EN_GUARD = re.compile(r"^[ \t]*local L = GetLocale\(\)[^\r\n]*enabledLocale[^\r\n]*(?:\r?\n)?", re.MULTILINE)
_MARK = re.compile(r"v(?P<version>\d+) source=(?P<source>[0-9a-f]{12})")
_LEVELS = re.compile(r"^((?:\{\d+\}(?:-\{\d+\})?\.?|\{\d+\}\.)\s+)(.+)$")
SLOT_KINDS: dict[str, tuple[str, ...]] = {
    "npc": ("npc",),
    "item": ("item",),
    "pick": ("pick", "item", "object"),
    "bracket": ("bracket", "spell", "item"),
}


def source_sha(english: str) -> str:
    return hashlib.sha256(english.encode("utf-8")).hexdigest()[:12]


def marker_info(text: str) -> dict[str, Any] | None:
    """Version du générateur et empreinte de la source anglaise lues dans le marqueur, ou None."""
    lines = text.split("\n", 2)
    if len(lines) < 2 or not lines[1].startswith(MARKER):
        return None
    m = _MARK.search(lines[1])
    return {"version": int(m["version"]), "source": m["source"]} if m else {"version": 0, "source": ""}


@dataclass
class Report:
    generated: int = 0
    copied: int = 0
    phrases: Counter[str] = field(default_factory=Counter)  # origine -> phrases distinctes
    quests: Counter[str] = field(default_factory=Counter)  # titres de quête : source ou « anglais »
    missing_phrases: list[str] = field(default_factory=list)
    missing_names: list[tuple[str, Key]] = field(default_factory=list)
    names: Counter[str] = field(default_factory=Counter)  # source -> noms traduits

    def as_dict(self) -> dict[str, Any]:
        return {
            "generated": self.generated,
            "copied": self.copied,
            "phrases": dict(self.phrases),
            "quests": dict(self.quests),
            "names": dict(self.names),
            "missing_phrases": list(self.missing_phrases),
            "missing_names": [{"kind": k, "name": n} for k, n in self.missing_names],
        }


class _Generator:
    def __init__(self, names: NameTable) -> None:
        self.names = names
        self.needed: dict[str, None] = {}
        self.resolved: dict[str, Resolved] = {}
        self.report = Report()

    # --- motifs : phrases types, lieux, titres de quête, noms de guide par zones -------------------------------

    def motif(self, key: str) -> str | None:
        if key.startswith(TITLE):
            return self._title_parts(key[len(TITLE) :])
        found = apply_patterns(key)
        if found is not None:
            return found
        for en, fr in PLACE_PHRASES.items():
            if key.startswith(en) and "{" not in key:
                place = self._zone(key[len(en) :].rstrip(".!"))
                if place is not None:
                    return fr + place.fr.replace("{", "{{").replace("}", "}}") + key[len(key.rstrip(".!")) :]
        for command, (en, fr) in QUEST_PREFIXES.items():
            del command
            if key.startswith(en) and "{" not in key:
                title = self.names.find("quest_title", key[len(en) :])
                if title is not None:
                    return fr + title.fr.replace("{", "{{").replace("}", "}}")
        return None

    def _zone(self, name: str) -> Name | None:
        """Nom de lieu : carte (UiMap) d'abord, puis zone (AreaTable)."""
        return self.names.find("zone", name) or self.names.find("area", name)

    def _title_parts(self, pattern: str) -> str | None:
        """Nom de guide « niveaux zone/zone » traduit par les noms de zone du client, s'ils le sont tous."""
        m = _LEVELS.match(pattern)
        head, rest = (m[1], m[2]) if m else ("", pattern)
        if "{" in rest:
            return None
        parts = []
        for part in rest.split("/"):
            found = self._zone(part.strip())
            if found is None:
                return None
            parts.append(found.fr.replace("{", "{{").replace("}", "}}"))
        return head + "/".join(parts)

    # --- lignes ---------------------------------------------------------------------------------------------------

    def _slot(self, slot: Slot) -> str:
        if slot.name is None:
            return slot.raw
        kinds = SLOT_KINDS[slot.kind]
        found = None
        if slot.ident is not None:
            found = self.names.find(kinds[0], slot.ident)
            if found is not None:
                self.names.used[found.source] += 1
        if found is None:
            found = self.names.lookup(kinds[0], slot.name, more=kinds[1:])
        return slot.with_name(found.fr) if found is not None else slot.raw

    def _text(self, text: str, collect: bool) -> str:
        tpl = make_template(text)
        if not translatable(tpl.pattern):
            return text if collect else fill(tpl.pattern, [self._slot(s) for s in tpl.slots])
        if collect:
            self.needed.setdefault(tpl.pattern)
            return text
        fr, _ = self.resolved.get(tpl.pattern, (None, "anglais"))
        return fill(fr if fr is not None else tpl.pattern, [self._slot(s) for s in tpl.slots])

    def _title(self, text: str, collect: bool, *, guide: bool) -> str:
        value = text.strip()
        if not value:
            return text
        lead, trail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()) :]
        group, _, name = value.rpartition("\\")
        # « Groupe\Guide » (`#next`, `#include`) : RestedXP range les guides par groupe et nom, les deux traduits
        prefix = self._title(group, collect, guide=False) + "\\" if group else ""
        if guide:
            found = self.names.find("guide", name)
            if found is not None:
                return lead + prefix + found.fr + trail
        tpl = make_template(name)
        key = TITLE + tpl.pattern
        if collect:
            self.needed.setdefault(key)
            return text
        fr, _ = self.resolved.get(key, (None, "anglais"))
        out = fill(fr, [s.raw for s in tpl.slots]) if fr is not None else name
        return lead + prefix + out + trail

    def _quest(self, line: Line, collect: bool) -> str | None:
        command = (line.command or "").lower()
        en_prefix, fr_prefix = QUEST_PREFIXES[command]
        ident = re.search(r"\d+", line.prefix)
        if not line.text.startswith(en_prefix) or ident is None:
            return None
        if collect:
            return line.text
        title = line.text[len(en_prefix) :]
        found = self.names.find("quest", int(ident.group())) or self.names.find("quest_title", title.strip())
        if found is None:
            self.names.missing[("quest", int(ident.group()))] += 1
            self.report.quests["anglais"] += 1
            return fr_prefix + title
        self.report.quests[found.source] += 1
        return fr_prefix + found.fr

    def _targets(self, line: Line) -> str:
        command = line.command or ""
        start = line.prefix.index("." + command) + 1 + len(command)
        head, args = line.prefix[:start], line.prefix[start:]
        spaces = args[: len(args) - len(args.lstrip())]
        out = []
        for name in args.strip().split(","):
            if "::" in name or not name.strip():
                out.append(name)
                continue
            found = self.names.lookup("npc", name.strip())
            out.append(name.replace(name.strip(), found.fr) if found is not None else name)
        return head + spaces + ",".join(out)

    def line(self, raw: str, collect: bool) -> str:
        line = parse_line(raw)
        command = (line.command or "").lower()
        if line.kind == "header" and line.text:
            if command == "next":
                parts = re.split(r"(;)", line.text)
                text = "".join(p if p == ";" else self._title(p, collect, guide=True) for p in parts)
            else:
                text = self._title(line.text, collect, guide=command in ("name", "displayname", "include"))
            return line.prefix + text + line.suffix
        if line.kind == "command" and command in UNTRANSLATED_COMMANDS and not collect:
            prefix = self._targets(line) if ">>" not in line.prefix else line.prefix
            text = self._text(line.text, collect) if line.text else ""
            return prefix + text + line.suffix
        if line.kind == "command" and command in TEXT_ARG_COMMANDS and not line.text and "," in line.prefix:
            head, _, text = line.prefix.partition(",")
            return head + "," + self._text(text, collect) + line.suffix
        if line.kind == "command" and command in QUEST_PREFIXES and line.text:
            done = self._quest(line, collect)
            if done is not None:
                return line.prefix + done + line.suffix
        if line.text:
            return line.prefix + self._text(line.text, collect) + line.suffix
        return raw

    def guide(self, body: str, eol: str, collect: bool) -> str:
        return eol.join(self.line(raw, collect) for raw in body.split(eol))


def generate_file(
    english: str,
    french: str | None,
    *,
    names: NameTable,
    memory: Memory,
    translator: Translator | None,
    meta: Mapping[str, Any],
    date: str = "",
) -> tuple[str, Report]:
    """(texte du fichier français, rapport) pour un fichier anglais et le français de RestedXP (guides recopiés)."""
    eol = "\r\n" if "\r\n" in english else "\n"
    pieces = split_file(english)
    english_guides = [p.body for p in pieces if p.body is not None]
    copies = match_guides(english_guides, guide_bodies(french or ""))
    gen = _Generator(names)
    plan: list[tuple[str, str]] = []  # (nature, texte) : brut, copie, génération
    index = 0
    for piece in pieces:
        if piece.body is None:
            plan.append(("raw", _EN_GUARD.sub("", piece.raw)))
            continue
        if index in copies:
            plan.append(("copy", copies[index]))  # texte de RestedXP tel quel (mêmes fins de ligne que la source)
            gen.report.copied += 1
        else:
            gen.guide(piece.body, eol, collect=True)
            plan.append(("gen", piece.body))
            gen.report.generated += 1
        index += 1
    gen.resolved = resolve(gen.needed, memory, translator, date=date, patterns=gen.motif)
    out = [GUARD, eol, _marker(english, meta), eol]
    for kind, text in plan:
        out.append(gen.guide(text, eol, collect=False) if kind == "gen" else text)
    report = gen.report
    report.phrases = Counter(origin for _, origin in gen.resolved.values())
    report.missing_phrases = sorted(k for k, (fr, _) in gen.resolved.items() if fr is None)
    report.missing_names = sorted(names.missing, key=lambda k: (k[0], str(k[1])))
    report.names = Counter(names.used)
    return "".join(out), report


def _marker(english: str, meta: Mapping[str, Any]) -> str:
    return (
        f"{MARKER} v{GENERATOR_VERSION} source={source_sha(english)} rxp={meta.get('rxp_version') or 'inconnue'} "
        "· traduction française générée pour un usage personnel, non officielle, des guides de RestedXP "
        "(CC BY-NC-SA 4.0, attribution : RestedXP) ; les guides que RestedXP a traduits sont recopiés tels quels"
    )
