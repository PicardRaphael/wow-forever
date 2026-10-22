"""Écarts aux règles de fusion tranchés par la veille (décision 296) : un écart que `forever install` refuse (valeur
d'un talent ou d'un sort que la version installée tenait, talent ou sort ajouté ou retiré) oppose une observation du
dépôt aux données du client.

- Observation faite sur une version plus ancienne que celle du client : remplacée par les données du client, l'écart
  devient une entrée de `confirmed_changes.json` (décision 296) et une note de la carte « Mis à jour » (« talent X
  retiré par la version Y ; ton observation datait de X »).
- Observation faite sur la même version : elle garde la priorité ; la candidate est corrigée sur une copie
  (`keep_observations`) et l'écart est signalé, sans bloquer le reste. Une valeur portée par un correctif du serveur
  (champ `hotfix` de l'entité du client) n'est pas une observation : elle est appliquée et dite.
- Sort retiré par une nouvelle version (décision 297) : tranché comme un talent ; la fusion le garde, marqué
  « retiré par la version », et plus aucune recommandation ne le propose.
- Écart d'un autre fichier : non tranché, l'installation reste refusée (intégrité) ; aucun autre fichier ne produit
  d'écart refusé aujourd'hui (fichiers des classes, tables et valeurs remplacés ou comparés en entier).

Version d'une observation : celle des données installées qui la portent (`version_from` du plan d'installation).
Fonctions pures, sauf `keep_observations` qui écrit une copie de la candidate."""

from __future__ import annotations

import copy
import json
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.pipeline.builds import version_key

KINDS = {"talents.json": "talent", "spells.json": "spell"}
KIND_FR = {"talent": "talent", "spell": "sort"}
DECISION = "décision 296"


class Resolution(NamedTuple):
    accepted: list[dict[str, Any]]  # entrées de confirmed_changes.json
    kept: list[Mapping[str, Any]]  # écarts où l'observation garde la priorité
    notes: list[str]  # phrases de la carte « Mis à jour »
    unresolved: list[Mapping[str, Any]]  # écarts non tranchés : installation toujours refusée


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _talents(doc: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(doc, dict):
        return {}
    return {t["key"]: t for tree in doc.get("trees", []) for t in tree.get("talents", [])}


def _spells(doc: Any) -> dict[str, dict[str, Any]]:
    return dict(doc.get("spells", {})) if isinstance(doc, dict) else {}


def _entities(vdir: Path, kind: str) -> dict[str, dict[str, Any]]:
    if kind == "talent":
        return _talents(_read(vdir / "talents.json"))
    return _spells(_read(vdir / "spells.json"))


def _change(kind: str, r: Mapping[str, Any]) -> dict[str, Any]:
    path = str(r["path"])
    if "." in path:
        key, field = path.split(".", 1)
        return {"key": key, "change": "modified", "field": field, "old": r["before"], "new": r["after"]}
    if r["before"] is None:
        return {"key": path, "change": "added", "field": None, "old": None, "new": path}
    return {"key": path, "change": "removed", "field": None, "old": path, "new": None}


def _plain(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, list | dict) else str(value)


def resolve(
    refused: Sequence[Mapping[str, Any]],
    *,
    version_from: str,
    version_to: str,
    candidate_vdir: Path,
    names: Mapping[str, str],
) -> Resolution:
    """Écarts refusés tranchés par la règle de la décision 296 (voir le module)."""
    older = version_key(version_from) < version_key(version_to)
    cand = {kind: _entities(candidate_vdir, kind) for kind in ("talent", "spell")}
    accepted: list[dict[str, Any]] = []
    kept: list[Mapping[str, Any]] = []
    notes: list[str] = []
    unresolved: list[Mapping[str, Any]] = []
    for r in refused:
        kind = KINDS.get(str(r.get("file")))
        if kind is None:
            unresolved.append(r)
            continue
        c = _change(kind, r)
        entity = cand[kind].get(c["key"]) or {}
        name = names.get(c["key"]) or str(entity.get("name") or c["key"])
        what = f"{KIND_FR[kind]} {name}"
        hotfix = "hotfix" in entity
        if not older and not hotfix:
            kept.append(r)
            field = c["field"] or ("retiré par le client" if c["change"] == "removed" else "ajouté par le client")
            shown = f" ({_plain(r['before'])}) garde la priorité sur le client ({_plain(r['after'])})"
            if c["field"] is None:
                shown = " garde la priorité"
            notes.append(f"écart signalé : {what}, {field} : ton observation de {version_from}{shown}")
            continue
        if hotfix and not older:
            why = f"par un correctif du serveur de la version {version_to}"
        else:
            why = f"par la version {version_to} ; ton observation datait de {version_from}"
        accepted.append(
            {
                "kind": kind,
                **c,
                "nature": "correctif_serveur" if hotfix and not older else "client",
                "decision": f"{DECISION} : {what} {why} (forever update, sans session)",
            }
        )
        if c["change"] == "removed":
            notes.append(f"{what} retiré {why}")
        elif c["change"] == "added":
            notes.append(f"{what} ajouté {why}")
        else:
            notes.append(f"{what} : {c['field']} {_plain(r['before'])} → {_plain(r['after'])} {why}")
    return Resolution(accepted, kept, notes, unresolved)


def _field_base(field: str) -> str:
    return field.split("[", 1)[0].split(".", 1)[0]


def keep_observations(
    candidate_root: Path, version: str, base_vdir: Path, kept: Sequence[Mapping[str, Any]], dest: Path
) -> Path:
    """Copie de la candidate (`dest`, remplacée) où chaque écart gardé reprend la valeur du dépôt : champ de l'entité
    recopié, talent ou sort retiré par le client remis, ajouté par le client ôté ; manifeste réécrit. Rend `dest`."""
    from forever.manifest import write_manifest

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(candidate_root, dest)
    vdir = dest / version
    docs = {name: _read(vdir / name) for name in KINDS}
    repo = {name: _read(base_vdir / name) for name in KINDS}
    for r in kept:
        name = str(r["file"])
        kind, c = KINDS[name], _change(KINDS[name], r)
        doc, base = docs[name], repo[name]
        if kind == "talent":
            mine, theirs = _talents(doc), _talents(base)
        else:
            mine, theirs = doc["spells"], base["spells"]
        key = c["key"]
        if c["change"] == "modified" and key in mine and key in theirs:
            field = _field_base(str(c["field"]))
            if field in theirs[key]:
                mine[key][field] = copy.deepcopy(theirs[key][field])
            else:
                mine[key].pop(field, None)
        elif c["change"] == "added":
            if kind == "talent":
                for tree in doc["trees"]:
                    tree["talents"] = [t for t in tree["talents"] if t["key"] != key]
            else:
                doc["spells"].pop(key, None)
        elif c["change"] == "removed" and key in theirs:
            if kind == "talent":
                tree_name = next(tr["name"] for tr in base["trees"] if any(t["key"] == key for t in tr["talents"]))
                for tree in doc["trees"]:
                    if tree["name"] == tree_name:
                        tree["talents"].append(copy.deepcopy(theirs[key]))
            else:
                doc["spells"][key] = copy.deepcopy(theirs[key])
    for name, doc in docs.items():
        if doc is not None:
            (vdir / name).write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(dest)
    return dest
