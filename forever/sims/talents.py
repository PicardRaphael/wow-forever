"""Talents choisis au niveau 60 pour les simulateurs de la communauté (MS1, décision 301) : nos clés (talents décodés du
client) converties vers la chaîne de chaque moteur, et l'inverse, **par identifiant de sort, jamais par position**.
Aucun calcul de jeu ici, seulement la lecture des tables des deux dépôts épinglés.

- wowsims/forever lit `talentsString` champ par champ dans l'ordre du message `<Classe>Talents` de
  `proto/<classe>.proto` ; chaque champ porte `[(talent_spell_id) = N]`, relié au sort de nos talents.
- MythicSim lit, sous les règles de Forever, l'ordre du client écrit dans son code (`talent("champ", "Nom", rangs)`,
  tables de `MYTHICSIM_TABLES`). Le champ est relié au sort par l'arbre de son fork Go épinglé
  (`ui/sim/talents/trees/<classe>.json`, `fieldName` et `spellId`). Le nom du client de la table sert de contrôle :
  accepté s'il est celui de notre talent ou celui du fork, ou si le talent de ce nom chez wowsims porte le même sort
  (talent renommé, ex. Lightning Mastery) ; sinon le carré a changé de talent depuis le fork (ex. Call of Thunder à la
  place de Lava Burst) et reste sans correspondance.
- Un talent sans correspondance refuse la conversion en le nommant (jamais deviné)."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.errors import ForeverError, InvalidArgumentError

# Tables de l'ordre du client lues dans le code épinglé de MythicSim : classe -> (fichier, constantes des trois arbres).
# Les autres classes y suivent l'ordre du proto ou des règles propres (Paladin, Guerrier) : non converties ici.
MYTHICSIM_TABLES = {
    "Mage": ("src/classes/mage/prepare.rs", ("FOREVER_ARCANE", "FOREVER_FIRE", "FOREVER_FROST")),
    "Shaman": ("src/classes/shaman/prepare/layout.rs", ("ELEMENTAL", "ENHANCEMENT", "RESTORATION")),
}
_FIELD = re.compile(r"^\s*(?:int32|bool)\s+(\w+)\s*=\s*\d+\s*(?:\[\(talent_spell_id\)\s*=\s*(\d+)\])?\s*;")
_TABLE_ROW = re.compile(r'(?:new_)?talent\(\s*"(\w+)",\s*"([^"]+)",\s*(\d+)\s*\)')


class TalentConversionError(ForeverError):
    """Talent sans correspondance entre nos clés et la chaîne d'un moteur, ou classe dont l'ordre n'est pas lu."""

    def __init__(self, message: str, action: str = "choisir un build sans ce talent, ou un autre moteur") -> None:
        super().__init__("talents_unconverted", message, action)


@dataclass(frozen=True)
class Slot:
    """Une place d'un arbre du moteur : champ du proto, nom (du client pour MythicSim), notre clé (None : aucune)."""

    field: str
    name: str
    key: str | None
    max_ranks: int | None = None


@dataclass(frozen=True)
class EngineLayout:
    engine: str
    class_name: str
    trees: tuple[tuple[Slot, ...], ...]

    def decode(self, code: str) -> dict[str, int]:
        """Chaîne du moteur -> nos clés (rangs non nuls)."""
        out: dict[str, int] = {}
        segments = code.strip().split("-")
        if len(segments) > len(self.trees):
            raise TalentConversionError(f"{self.engine} : chaîne « {code} » de {len(segments)} arbres.")
        for t, seg in enumerate(segments):
            if len(seg) > len(self.trees[t]):
                raise TalentConversionError(f"{self.engine} : arbre {t + 1} de « {code} » plus long que l'arbre.")
            for i, ch in enumerate(seg):
                rank = int(ch) if ch.isdigit() else 0
                if not rank:
                    continue
                slot = self.trees[t][i]
                if slot.key is None:
                    raise TalentConversionError(
                        f"{self.engine} : {slot.name} ({slot.field}, arbre {t + 1}, place {i + 1}) n'a pas de talent "
                        f"correspondant dans les données du client ; chaîne « {code} »."
                    )
                out[slot.key] = rank
        return out

    def encode(self, talents: Mapping[str, int]) -> str:
        """Nos clés -> chaîne du moteur ; un talent pris sans place chez le moteur est refusé en le nommant."""
        where = {s.key: (t, i) for t, tree in enumerate(self.trees) for i, s in enumerate(tree) if s.key}
        missing = sorted(k for k, r in talents.items() if r and k not in where)
        if missing:
            raise TalentConversionError(
                f"{self.engine} : talent(s) sans place chez le moteur pour le {self.class_name} : {', '.join(missing)}."
            )
        digits = [["0"] * len(tree) for tree in self.trees]
        for key, rank in talents.items():
            if rank:
                t, i = where[key]
                digits[t][i] = str(int(rank))
        return "-".join("".join(d).rstrip("0") for d in digits).rstrip("-")


def client_trees(deps: Any, class_name: str) -> list[list[dict[str, Any]]]:
    """Talents du client de la classe, par arbre : clé, nom, sorts, rang maximal (données de la version courante)."""
    from forever.lookup import _class_knowledge

    _, knowledge, _ = _class_knowledge(deps, class_name)
    return [
        [
            {"key": t["key"], "name": t["name"], "max": t.get("max"),
             "spell_ids": [int(s) for s in [t.get("spell_id"), *(t.get("spell_ids") or [])] if s]}
            for t in tree["talents"]
        ]
        for tree in knowledge.trees
    ]  # fmt: skip


def _by_spell(client: Sequence[Sequence[Mapping[str, Any]]]) -> dict[int, Mapping[str, Any]]:
    return {sid: t for tree in client for t in tree for sid in t.get("spell_ids") or []}


def _proto_trees(path: Path, class_name: str) -> list[list[tuple[str, int | None]]]:
    """Champs du message `<Classe>Talents` par arbre (commentaire d'arbre), avec `talent_spell_id` s'il y en a un."""
    if not path.is_file():
        raise TalentConversionError(f"proto des talents introuvable : {path}.", "lancer `uv run forever sims update`")
    text = path.read_text(encoding="utf-8")
    head = f"message {class_name}Talents {{"
    if head not in text:
        raise TalentConversionError(f"message {class_name}Talents absent de {path.name}.")
    block = text.split(head, 1)[1].split("}", 1)[0]
    trees: list[list[tuple[str, int | None]]] = []
    for line in block.splitlines():
        if line.strip().startswith("//"):
            trees.append([])
            continue
        m = _FIELD.match(line)
        if m:
            if not trees:
                trees.append([])
            trees[-1].append((m.group(1), int(m.group(2)) if m.group(2) else None))
    return trees


def wowsims_layout(clone: Path, class_name: str, client: Sequence[Sequence[Mapping[str, Any]]]) -> EngineLayout:
    """Ordre de wowsims (`proto/<classe>.proto` du clone épinglé), relié à nos clés par `talent_spell_id`."""
    by_spell = _by_spell(client)
    trees = []
    for tree in _proto_trees(clone / "proto" / f"{class_name.lower()}.proto", class_name):
        row = []
        for name, sid in tree:
            hit = by_spell.get(sid) if sid else None
            row.append(Slot(name, name.replace("_", " ").title(), str(hit["key"]) if hit else None))
        trees.append(tuple(row))
    return EngineLayout("wowsims/forever", class_name, tuple(trees))


def _camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(w[:1].upper() + w[1:] for w in rest)


def _snake(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower().replace("'", "")).strip("_")


def _fork_tree(go: Path, class_name: str) -> dict[str, tuple[int | None, str]]:
    path = go / "ui" / "sim" / "talents" / "trees" / f"{class_name.lower()}.json"
    if not path.is_file():
        raise TalentConversionError(f"arbre des talents du fork Go introuvable : {path}.",
                                    "lancer `uv run forever sims update`")  # fmt: skip
    out: dict[str, tuple[int | None, str]] = {}
    for tree in json.loads(path.read_text(encoding="utf-8")):
        for t in tree.get("talents") or []:
            sid = t.get("spellId")
            if isinstance(sid, list):
                sid = sid[0] if sid else None
            out[str(t.get("fieldName"))] = (int(sid) if sid else None, str(t.get("fancyName") or ""))
    return out


def mythicsim_layout(
    engine: Path,
    go: Path,
    class_name: str,
    client: Sequence[Sequence[Mapping[str, Any]]],
    *,
    wowsims: Path | None = None,
) -> EngineLayout:
    """Ordre de MythicSim sous les règles de Forever (table de son code), relié à nos clés par le sort de l'arbre de
    son fork Go, nom du client contrôlé (voir le module) ; `wowsims` : clone de wowsims pour confirmer un renommage."""
    if class_name not in MYTHICSIM_TABLES:
        raise TalentConversionError(
            f"MythicSim : ordre des talents du {class_name} non lu par forever (tables lues : "
            f"{', '.join(MYTHICSIM_TABLES)}).",
            "choisir engine=wowsims pour cette classe",
        )
    rel, consts = MYTHICSIM_TABLES[class_name]
    path = engine / rel
    if not path.is_file():
        raise TalentConversionError(f"table des talents de MythicSim introuvable : {path}.",
                                    "lancer `uv run forever sims update`")  # fmt: skip
    text = path.read_text(encoding="utf-8")
    fork = _fork_tree(go, class_name)
    renamed: dict[str, int] = {}
    if wowsims is not None and (wowsims / "proto" / f"{class_name.lower()}.proto").is_file():
        renamed = {f: s for tree in _proto_trees(wowsims / "proto" / f"{class_name.lower()}.proto", class_name)
                   for f, s in tree if s}  # fmt: skip
    by_spell = _by_spell(client)
    trees = []
    for const in consts:
        head = f"const {const}: &["
        if head not in text:
            raise TalentConversionError(f"constante {const} absente de {rel} (MythicSim épinglé).")
        body = text.split(head, 1)[1].split("];", 1)[0]
        row = []
        for field, name, ranks in _TABLE_ROW.findall(body):
            sid, fancy = fork.get(_camel(field), (None, ""))
            hit = by_spell.get(sid) if sid else None
            same = hit is not None and (name in (hit["name"], fancy) or renamed.get(_snake(name)) == sid)
            row.append(Slot(field, name, str(hit["key"]) if hit and same else None, int(ranks)))
        trees.append(tuple(row))
    return EngineLayout("MythicSim", class_name, tuple(trees))


def parse_talents(text: str) -> dict[str, int]:
    """« clé=rang,… » (nos clés) -> dictionnaire."""
    out: dict[str, int] = {}
    for item in text.split(","):
        if not item.strip():
            continue
        key, sep, rank = item.partition("=")
        if not sep or not rank.strip().isdigit():
            raise InvalidArgumentError(f"Talent illisible : « {item.strip()} » (attendu clé=rang).",
                                       "donner talents en clé=rang séparés par des virgules")  # fmt: skip
        out[key.strip()] = int(rank)
    return out
