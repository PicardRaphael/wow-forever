"""Talents envoyés par le jeu reliés aux clés de forever (P06a, sonde en jeu E du 2026-10-09). L'addon envoie
`nœud:rang` (identifiants de nœud de `C_Traits`, rangs achetés) ; `classes.json` relie chaque nœud à un talent
(tables TraitNode et TraitNodeEntry du client, même build que les données). Le pont ajoute la traduction au message,
pour que la conversation passe ces clés à `current` de `forever_build` sans rien deviner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from forever.config import Deps

# Jeton de classe du jeu (`UnitClassBase`) → nom de la classe dans `classes.json`.
CLASS_NAMES = {
    "WARRIOR": "Warrior",
    "PALADIN": "Paladin",
    "HUNTER": "Hunter",
    "ROGUE": "Rogue",
    "PRIEST": "Priest",
    "SHAMAN": "Shaman",
    "MAGE": "Mage",
    "WARLOCK": "Warlock",
    "DRUID": "Druid",
}


@dataclass(frozen=True)
class KnownTalent:
    key: str
    name: str
    rank: int
    max: int


@dataclass(frozen=True)
class TalentReading:
    known: list[KnownTalent] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)


TalentTable = Mapping[str, Mapping[int, tuple[str, str, int]]]


def talent_table(deps: Deps) -> dict[str, dict[int, tuple[str, str, int]]]:
    """Jeton de classe → nœud → (clé, nom anglais du client, rang maximal), d'après `classes.json`."""
    from forever.store import load_version

    data = load_version(deps)
    classes = data.read_json("classes.json")["classes"]
    out: dict[str, dict[int, tuple[str, str, int]]] = {}
    for token, name in CLASS_NAMES.items():
        trees = (classes.get(name) or {}).get("trees") or []
        out[token] = {
            int(t["node_id"]): (str(t["key"]), str(t["name"]), int(t["max"]))
            for tree in trees
            for t in tree["talents"]
            if t.get("node_id") is not None
        }
    return out


def describe_talents(table: TalentTable, class_token: str, text: str) -> TalentReading:
    """Talents `nœud:rang` du jeu, dans l'ordre reçu ; ce qui ne se relie à aucun talent reste dans `unknown`."""
    nodes = table.get(class_token, {})
    reading = TalentReading()
    for part in (p.strip() for p in str(text or "").split(",")):
        if not part:
            continue
        node, sep, rank = part.partition(":")
        if sep and node.isdigit() and rank.isdigit() and int(node) in nodes:
            key, name, top = nodes[int(node)]
            reading.known.append(KnownTalent(key, name, int(rank), top))
        else:
            reading.unknown.append(part)
    return reading


def talents_line(reading: TalentReading) -> str:
    """« clé:rang (Nom rang/max), … » ; les nœuds non reconnus sont nommés à part."""
    parts = [f"{t.key}:{t.rank} ({t.name} {t.rank}/{t.max})" for t in reading.known]
    text = ", ".join(parts) or "aucun talent reconnu"
    if reading.unknown:
        text += f" ; nœuds non reconnus : {', '.join(reading.unknown)}"
    return text
