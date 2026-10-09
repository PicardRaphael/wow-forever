"""Mise en forme restreinte des réponses (P06a, décision 212 amendée le 2026-10-09) : l'addon sait rendre les lignes
`## titre`, `- élément` et les passages `**en évidence**` ; toute autre syntaxe Markdown est convertie ou retirée
avant publication."""

from __future__ import annotations

import re

_HEADING = re.compile(r"^\s*#{1,6}\s+(.*)$")
_BULLET = re.compile(r"^(\s*)[*+•]\s+(.*)$")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_UNDERSCORE_BOLD = re.compile(r"__(.+?)__")
_STAR_ITALIC = re.compile(r"(?<![*\w])\*(?!\*)([^*\n]+?)(?<!\*)\*(?![*\w])")
_UNDERSCORE_ITALIC = re.compile(r"(?<![_\w])_(?!_)([^_\n]+?)(?<!_)_(?![_\w])")


def _line(line: str) -> str | None:
    if line.strip().startswith("```"):
        return None
    if _TABLE_RULE.match(line) and "-" in line:
        return None
    if line.strip().startswith("|"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        line = " · ".join(c for c in cells if c)
    heading = _HEADING.match(line)
    if heading:
        line = "## " + heading.group(1).strip()
    bullet = _BULLET.match(line)
    if bullet:
        line = "- " + bullet.group(2)
    line = _LINK.sub(r"\1", line)
    line = _UNDERSCORE_BOLD.sub(r"**\1**", line)
    line = _STAR_ITALIC.sub(r"\1", line)
    line = _UNDERSCORE_ITALIC.sub(r"\1", line)
    return line.replace("`", "").rstrip()


def normalize_reply(text: str) -> str:
    """Réponse ramenée à la mise en forme que l'addon rend ; lignes vides réduites à une, bords retirés."""
    lines = [out for line in text.replace("\r\n", "\n").split("\n") if (out := _line(line)) is not None]
    collapsed: list[str] = []
    for line in lines:
        if not line and collapsed and not collapsed[-1]:
            continue
        collapsed.append(line)
    return "\n".join(collapsed).strip("\n")
