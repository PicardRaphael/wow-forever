"""Rapport Markdown d'un changement de données (futur corps de PR de T08), déterministe à horloge fixe."""

from __future__ import annotations

import json

from forever.pipeline.diff import Change, VersionDiff
from forever.pipeline.verify import VerifyReport
from forever.provenance import format_provenance_line

SECTIONS = (
    ("talent", "Talents", "Talent"),
    ("spell", "Sorts", "Sort"),
    ("file", "Fichiers", "Fichier"),
    ("scaling", "Valeurs de spell_scaling.json", "Sort, rang ou section"),
    ("character", "Valeurs de character_scaling.json", "Classe, niveau ou section"),
)
CHANGES_FR = {"added": "ajouté", "removed": "retiré", "modified": "modifié"}
KINDS_FR = {
    "talent": "talent(s)",
    "spell": "sort(s)",
    "file": "fichier(s)",
    "scaling": "valeur(s) de spell_scaling.json",
    "character": "valeur(s) de character_scaling.json",
}


def _cell(value: object) -> str:
    if value is None:
        return "—"
    return "`" + json.dumps(value, ensure_ascii=False).replace("|", "\\|") + "`"


def _row(c: Change) -> str:
    return f"| {c['key']} | {CHANGES_FR[c['change']]} | {c['field'] or '—'} | {_cell(c['old'])} | {_cell(c['new'])} |"


def render_report(diff: VersionDiff, verify: VerifyReport | None = None) -> str:
    """Titre « data: A → B », résumé chiffré, sections Talents / Sorts / Fichiers (tableaux), vérification,
    hypothèses, ligne de provenance en dernier."""
    lines = [f"# data: {diff['a']} → {diff['b']}", ""]
    total = len(diff["changes"])
    if total:
        detail = ", ".join(f"{diff['counts'].get(k, 0)} {KINDS_FR[k]}" for k, _, _ in SECTIONS)
        lines += [f"{total} changement(s) : {detail}.", ""]
    else:
        lines += ["Aucun changement.", ""]
    for kind, title, label in SECTIONS:
        rows = [c for c in diff["changes"] if c["kind"] == kind]
        if not rows:
            continue
        lines += [
            f"## {title}",
            "",
            f"| {label} | Changement | Champ | Avant | Après |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines += [_row(c) for c in rows]
        lines.append("")
    if verify is not None:
        lines += ["## Vérification", "", f"{verify['source']} : {'ok' if verify['ok'] else 'ÉCHEC'}"]
        lines += [f"- erreur : {e}" for e in verify["errors"]]
        lines += [f"- avertissement : {w}" for w in verify["warnings"]]
        lines.append("")
    assumptions = diff["provenance"]["assumptions"]
    lines += ["## Hypothèses", ""]
    lines += [f"- {a}" for a in assumptions] if assumptions else ["- aucune"]
    lines += ["", format_provenance_line(diff["provenance"])]
    return "\n".join(lines) + "\n"
