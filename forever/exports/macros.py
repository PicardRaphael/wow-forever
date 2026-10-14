"""Macros par classe (EX1, bloc D, décision 195) : texte de macros au format d'import de Naowh Forever (`!NFM1!`),
calculé depuis le catalogue `macros.yaml` (clés de sorts) et les sorts de la classe appris au niveau (`classes.json`,
noms anglais du client enUS). Seulement `/cast`, `/use`, `/stopcasting`, `/startattack` et `#showtooltip` : jamais
`/run`, `/script`, `/dump` ni commande d'un autre addon. `/cast` sans rang (le jeu prend le meilleur rang appris :
`suppose`, question MAC1). Notre addon ne crée, n'édite ni ne lance aucune macro : le joueur colle la chaîne."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from functools import cache
from importlib import resources
from typing import Any

import yaml

from forever.config import Deps
from forever.engine.model import GameData

ALLOWED_COMMANDS = ("/cast", "/use", "/stopcasting", "/startattack")
TEMPLATES: dict[str, tuple[str, ...]] = {
    "help": ("#showtooltip", "/cast [@mouseover,help,nodead][] {spell}"),
    "focus": ("#showtooltip", "/cast [@focus,harm,nodead][] {spell}"),
    "interrupt": ("#showtooltip", "/stopcasting", "/cast {spell}"),
    "melee": ("#showtooltip", "/startattack", "/cast {spell}"),
}
NAME_PREFIX = "F "
NAME_BYTES = 16  # borne du nom chez Naowh (`C.NAME_MAX`), reprise de forever/exports/naowh.py
IMPORT_STEPS = "en jeu : /nf, Profiles, Import (ou la fenêtre Macros de Naowh), coller le code ; hors combat"
MANUAL_STEPS = "sans Naowh Forever : /macro, Nouveau, puis coller chaque texte ci-dessous"


@dataclass(frozen=True)
class Macro:
    name: str
    body: str
    spell: str
    template: str


@cache
def catalogue() -> dict[str, list[dict[str, str]]]:
    """Catalogue `macros.yaml` : classe → entrées `{template, spell}`."""
    text = resources.files("forever.exports").joinpath("macros.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    return {str(cls): [dict(e) for e in entries] for cls, entries in data.items()}


def macro_violations(body: str) -> list[str]:
    """Lignes interdites d'un corps de macro : toute commande hors de `ALLOWED_COMMANDS` (dont `/run`, `/script`,
    `/dump`), toute directive `#` autre que `#showtooltip`."""
    bad = []
    for line in body.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("#"):
            if text.split()[0] != "#showtooltip":
                bad.append(text)
            continue
        command = text.split()[0].split("[")[0].lower()
        if command not in ALLOWED_COMMANDS:
            bad.append(text)
    return bad


def _short_name(spell_name: str) -> str:
    raw = (NAME_PREFIX + spell_name).encode("utf-8")[:NAME_BYTES]
    return raw.decode("utf-8", errors="ignore").rstrip()


def _learned_level(spell: Mapping[str, Any]) -> int | None:
    """Premier niveau d'apprentissage connu (rang du client) ; un niveau absent ou nul reste inconnu."""
    levels = [int(r["level"]) for r in spell.get("ranks") or [] if r.get("level")]
    return min(levels) if levels else None


def class_macros(gd: GameData, class_name: str, level: int, talents: Mapping[str, int] | None = None) -> list[Macro]:
    """Macros du catalogue dont le sort est appris au niveau (sort de talent : seulement si le talent est pris),
    dans l'ordre du catalogue, sans doublon de nom."""
    from forever.profile import normalize_class

    cls = normalize_class(class_name)
    knowledge = gd.classes.get(cls)
    if knowledge is None:
        return []
    taken = {k for k, r in (talents or {}).items() if r > 0}
    out: list[Macro] = []
    names: set[str] = set()
    for entry in catalogue().get(cls, []):
        spell = knowledge.spells.get(entry["spell"])
        if spell is None:
            continue
        first = _learned_level(spell)
        if first is None or first > level:
            continue
        if spell.get("talent") is not None and spell["talent"] not in taken:
            continue
        body = "\n".join(line.format(spell=spell["name"]) for line in TEMPLATES[entry["template"]])
        name = _short_name(str(spell["name"]))
        if name in names or macro_violations(body):
            continue
        names.add(name)
        out.append(Macro(name=name, body=body, spell=entry["spell"], template=entry["template"]))
    return out


def macros_export(deps: Deps, class_name: str, level: int, talents: Mapping[str, int] | None = None) -> dict[str, Any]:
    """Code `!NFM1!` des macros de la classe au niveau, avec le texte brut à coller sans Naowh ; `code` vaut None
    s'il n'y a aucune macro. Certitude `suppose` (choix de catalogue, `/cast` sans rang : question MAC1)."""
    from forever.exports.naowh import NAOWH_VERSION, naowh_macros
    from forever.gamedata import build_game_data
    from forever.profile import normalize_class
    from forever.provenance import local_provenance
    from forever.store import load_version

    cls = normalize_class(class_name)
    macros = class_macros(build_game_data(load_version(deps)), cls, level, talents)
    code = naowh_macros([(m.name, m.body) for m in macros]) if macros else None
    text = "\n\n".join(f"{m.name} :\n{m.body}" for m in macros)
    notes = [
        f"format !NFM1! relevé dans Naowh Forever {NAOWH_VERSION} (module Macros), jamais importé en jeu",
        "macros : catalogue court de forever (forever/exports/macros.yaml), utilité supposée",
        "/cast sans rang : le jeu lance le meilleur rang appris (supposé, question MAC1)",
        "sorts appris au niveau : premier rang de classes.json (noms anglais du client enUS)",
    ]
    return {
        "kind": "naowh_macros",
        "class": cls,
        "level": level,
        "code": code,
        "macros": [asdict(m) for m in macros],
        "text": text,
        "reason": None if macros else f"aucune macro du catalogue apprise au niveau {level}",
        "import": IMPORT_STEPS,
        "manual": MANUAL_STEPS,
        "addon": {"name": "Naowh Forever", "version": NAOWH_VERSION, "format": "!NFM1!"},
        "certainty": "suppose",
        "provenance": local_provenance(deps, certainty="suppose", assumptions=notes),
    }


def render_macros(block: Mapping[str, Any]) -> list[str]:
    """Lignes de `forever export naowh-macros` : code, puis le texte brut de chaque macro."""
    if not block["code"]:
        return [f"Macros {block['class']} : {block['reason']}"]
    lines = [f"Naowh Forever (macros) : {block['code']} ({block['certainty']}) · {block['import']}"]
    lines.append(f"  {block['manual']} :")
    lines += [f"  {line}" for line in block["text"].splitlines()]
    return lines
