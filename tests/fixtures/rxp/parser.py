"""Analyseur de test des guides RestedXP (RX1, bloc D), écrit d'après la structure de `ParseGuide` et `parseLine`
(RXPGuides 4.11.23, `GuideLoader.lua`) : en-tête de lignes `#clé valeur` et `<< camp` avant la première étape, puis
étapes ouvertes par `step` ; dans une étape, le texte après le premier `>>`, une commande `.nom arguments` aux
arguments séparés par des virgules. Aucun texte de RestedXP ici."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

KNOWN = {"goto", "accept", "complete", "turnin", "xp"}
_INT = re.compile(r"^-?\d+$")
_NUM = re.compile(r"^-?\d+(\.\d+)?$")


@dataclass
class Command:
    name: str
    args: list[str]
    text: str | None


@dataclass
class Step:
    commands: list[Command] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)  # lignes de texte seul (`>>texte`)


@dataclass
class Guide:
    header: dict[str, str]
    faction: str | None
    steps: list[Step]


def parse(text: str) -> Guide:
    header: dict[str, str] = {}
    faction = None
    steps: list[Step] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("--"):
            continue
        if line == "step" or line.startswith("step "):
            steps.append(Step())
            continue
        if not steps:
            if line.startswith("<<"):
                faction = line[2:].strip()
            elif line.startswith("#"):
                key, _, value = line[1:].partition(" ")
                header[key] = value.strip()
            else:
                raise ValueError(f"ligne d'en-tête inconnue : {line}")
            continue
        body, sep, after = line.partition(">>")
        text_part = after.strip() if sep else None
        body = body.strip()
        if body.startswith("."):
            name, _, args = body[1:].partition(" ")
            parts = [a.strip() for a in args.split(",") if a.strip()] if args.strip() else []
            steps[-1].commands.append(Command(name, parts, text_part))
        elif text_part is not None and not body:
            steps[-1].texts.append(text_part)
        else:
            raise ValueError(f"ligne d'étape inconnue : {line}")
    return Guide(header, faction, steps)


def errors(guide: Guide, raw: str) -> list[str]:
    """Défauts d'un guide : en-tête, commandes inconnues, arguments invalides, caractères réservés."""
    out = []
    for key in ("name", "group"):
        if not guide.header.get(key):
            out.append(f"en-tête sans #{key}")
    if "forever" not in guide.header and "classic" not in guide.header:
        out.append("en-tête sans #forever ni #classic")
    if not guide.steps:
        out.append("aucune étape")
    for i, step in enumerate(guide.steps, 1):
        if not step.commands and not step.texts:
            out.append(f"étape {i} vide")
        for c in step.commands:
            if c.name not in KNOWN:
                out.append(f"étape {i} : commande inconnue .{c.name}")
            elif c.name in ("accept", "turnin") and not (len(c.args) == 1 and _INT.match(c.args[0])):
                out.append(f"étape {i} : .{c.name} sans identifiant de quête")
            elif c.name == "complete" and not (len(c.args) == 2 and all(_INT.match(a) for a in c.args)):
                out.append(f"étape {i} : .complete sans quête et objectif")
            elif c.name == "goto":
                ok = len(c.args) == 3 and _INT.match(c.args[0]) and all(_NUM.match(a) for a in c.args[1:])
                if not ok or not all(0 <= float(a) <= 100 for a in c.args[1:]):
                    out.append(f"étape {i} : .goto invalide {c.args}")
            elif c.name == "xp" and not (len(c.args) == 1 and _INT.match(c.args[0])):
                out.append(f"étape {i} : .xp sans niveau")
    for n, line in enumerate(raw.splitlines(), 1):
        stripped = line.strip()
        if "--" in line and not stripped.startswith("--"):
            out.append(f"ligne {n} : « -- » (commentaire de RestedXP) dans le texte")
        if "<<" in line and not stripped.startswith("<<"):
            out.append(f"ligne {n} : « << » (camp ou classe) dans le texte")
        if "|" in line:
            out.append(f"ligne {n} : « | » (séquence d'interface)")
    return out
