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
    "Hunter": (
        "src/classes/hunter/prepare.rs",
        ("FOREVER_BEAST_MASTERY", "FOREVER_MARKSMANSHIP", "FOREVER_SURVIVAL"),
    ),
    "Druid": ("src/classes/druid/prepare.rs", ("FOREVER_BALANCE", "FOREVER_FERAL_COMBAT", "FOREVER_RESTORATION")),
    "Rogue": ("src/classes/rogue/prepare.rs", ("FOREVER_ASSASSINATION", "FOREVER_COMBAT", "FOREVER_SUBTLETY")),
    "Warrior": ("src/classes/warrior/prepare/talent_ranks.rs", ("FOREVER_ARMS", "FOREVER_FURY", "PROTECTION")),
    "Paladin": ("src/classes/paladin/prepare/hotfix_113554.rs", ("HOLY", "PROTECTION", "RETRIBUTION")),
}
# Classes que MythicSim lit, sous les règles de Forever aussi, dans l'ordre des numéros de champ du proto de son fork Go
# (`fill_talents`, un arbre après l'autre selon `TALENT_TREE_SIZES` de ce fichier) : le champ est relié au sort par
# l'arbre du fork, comme pour les tables.
MYTHICSIM_PROTO_ORDER = {
    "Warlock": "src/classes/warlock/prepare.rs",
    "Priest": "src/classes/priest/prepare.rs",
}
_TREE_SIZES = re.compile(r"TALENT_TREE_SIZES:\s*\[usize;\s*3\]\s*=\s*\[(\d+),\s*(\d+),\s*(\d+)\]")
# Options du champ : `talent_spell_id`, puis d'autres options possibles (`talent_max_rank` depuis le commit 64b21da).
_FIELD = re.compile(r"^\s*(?:int32|bool)\s+(\w+)\s*=\s*\d+\s*(?:\[([^\]]*)\])?\s*;")
_OPTION = re.compile(r"\((\w+)\)\s*=\s*(\d+)")
# ligne de table, sur une ligne ou coupée par rustfmt (virgule finale)
_TABLE_ROW = re.compile(r'(?:new_)?talent\(\s*"(\w+)",\s*"([^"]+)",\s*(\d+)\s*,?\s*\)')


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


def _proto_trees(path: Path, class_name: str) -> list[list[tuple[str, int | None, int | None]]]:
    """Champs du message `<Classe>Talents` par arbre (commentaire d'arbre), avec `talent_spell_id` et
    `talent_max_rank` s'il y en a."""
    if not path.is_file():
        raise TalentConversionError(f"proto des talents introuvable : {path}.", "lancer `uv run forever sims update`")
    text = path.read_text(encoding="utf-8")
    head = f"message {class_name}Talents {{"
    if head not in text:
        raise TalentConversionError(f"message {class_name}Talents absent de {path.name}.")
    block = text.split(head, 1)[1].split("}", 1)[0]
    trees: list[list[tuple[str, int | None, int | None]]] = []
    for line in block.splitlines():
        if line.strip().startswith("//"):
            trees.append([])
            continue
        m = _FIELD.match(line)
        if m:
            if not trees:
                trees.append([])
            options = {k: int(v) for k, v in _OPTION.findall(m.group(2) or "")}
            trees[-1].append((m.group(1), options.get("talent_spell_id"), options.get("talent_max_rank")))
    return trees


def wowsims_layout(clone: Path, class_name: str, client: Sequence[Sequence[Mapping[str, Any]]]) -> EngineLayout:
    """Ordre de wowsims (`proto/<classe>.proto` du clone épinglé), relié à nos clés par `talent_spell_id`."""
    by_spell = _by_spell(client)
    trees = []
    for tree in _proto_trees(clone / "proto" / f"{class_name.lower()}.proto", class_name):
        row = []
        for name, sid, max_ranks in tree:
            hit = by_spell.get(sid) if sid else None
            row.append(Slot(name, name.replace("_", " ").title(), str(hit["key"]) if hit else None, max_ranks))
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
    if class_name in MYTHICSIM_PROTO_ORDER:
        return _mythicsim_proto_layout(engine, go, class_name, client)
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
                   for f, s, _ in tree if s}  # fmt: skip
    by_spell = _by_spell(client)
    trees = []
    for index, const in enumerate(consts):
        # talent propre à Forever absent de l'arbre du fork Go : relié par le nom du client écrit dans la table, s'il
        # est unique dans le même arbre du client (jamais quand le fork porte un autre sort à ce champ)
        names: dict[str, list[Mapping[str, Any]]] = {}
        for t in client[index] if index < len(client) else []:
            names.setdefault(str(t["name"]), []).append(t)
        head = f"const {const}: &["
        if head not in text:
            raise TalentConversionError(f"constante {const} absente de {rel} (MythicSim épinglé).")
        body = text.split(head, 1)[1].split("];", 1)[0]
        row = []
        for field, name, ranks in _TABLE_ROW.findall(body):
            sid, fancy = fork.get(_camel(field), (None, ""))
            hit = by_spell.get(sid) if sid else None
            same = hit is not None and (name in (hit["name"], fancy) or renamed.get(_snake(name)) == sid)
            key = str(hit["key"]) if hit and same else None
            if key is None and sid is None and len(names.get(name, [])) == 1:
                key = str(names[name][0]["key"])
            row.append(Slot(field, name, key, int(ranks)))
        trees.append(tuple(row))
    return EngineLayout("MythicSim", class_name, tuple(trees))


def _mythicsim_proto_layout(
    engine: Path, go: Path, class_name: str, client: Sequence[Sequence[Mapping[str, Any]]]
) -> EngineLayout:
    """Ordre de MythicSim pour une classe lue par numéro de champ (`MYTHICSIM_PROTO_ORDER`) : champs du message
    `<Classe>Talents` du proto du fork Go dans l'ordre, arbres de la taille de `TALENT_TREE_SIZES` du moteur (un écart
    refuse), champ relié à notre talent par le sort de l'arbre du fork ; sans sort ou sans talent du client : aucune
    correspondance (refus s'il est pris)."""
    prepare = engine / MYTHICSIM_PROTO_ORDER[class_name]
    if not prepare.is_file():
        raise TalentConversionError(
            f"code de MythicSim introuvable : {prepare}.", "lancer `uv run forever sims update`"
        )
    m = _TREE_SIZES.search(prepare.read_text(encoding="utf-8"))
    if m is None:
        raise TalentConversionError(f"TALENT_TREE_SIZES absent de {prepare.name} (MythicSim épinglé).")
    sizes = [int(n) for n in m.groups()]
    trees = _proto_trees(go / "proto" / f"{class_name.lower()}.proto", class_name)
    if [len(t) for t in trees] != sizes:
        raise TalentConversionError(
            f"MythicSim : arbres du proto du fork ({[len(t) for t in trees]}) différents de TALENT_TREE_SIZES {sizes} "
            f"pour le {class_name}."
        )
    fork = _fork_tree(go, class_name)
    by_spell = _by_spell(client)
    out = []
    for tree in trees:
        row = []
        for field, _sid, _max in tree:
            sid, fancy = fork.get(_camel(field), (None, ""))
            hit = by_spell.get(sid) if sid else None
            row.append(Slot(field, fancy or field, str(hit["key"]) if hit else None))
        out.append(tuple(row))
    return EngineLayout("MythicSim", class_name, tuple(out))


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
