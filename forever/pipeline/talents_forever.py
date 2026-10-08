"""Talents Forever (`TalentsForeverBook/Data.lua`) : arbres lus et recoupés avec `classes.json` (T08d, bloc D).

Lecture locale par `forever/pipeline/lua_table.py`, jamais par du Lua exécuté ; rien de l'addon n'est recopié dans
le dépôt : seuls des comptes et des écarts sortent d'ici. Fonctions reprises de `scripts/compare_talents_forever.py`
(T08c), qui les appelle. Champs comparés par nœud (`node`) : nom, arbre, rangée, colonne, rangs, sort et prérequis
(`req` : rang du talent requis dans la liste de son arbre, 1 pour le premier)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forever.pipeline.lua_table import parse_lua_value_at

FIELDS = ("name", "tree", "tier", "col", "max", "spell", "prereq")
HEAD = ("build", "generated", "codeVersion")
GLOBAL = "TalentsForeverBookData = "
POPULAR = "TalentsForeverBookData.popular ="


def read_head_and_doc(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Première table de `Data.lua` (structure des arbres) et son en-tête."""
    text = path.read_text(encoding="utf-8")
    start = text.index("{", text.index(GLOBAL))
    doc, _ = parse_lua_value_at(text, start)
    if not isinstance(doc, dict):
        raise ValueError(f"{path} : table {GLOBAL.strip(' =')} attendue")  # noqa: TRY004 : contenu illisible
    return {k: doc.get(k) for k in HEAD}, doc


def read_popular(path: Path) -> dict[str, Any] | None:
    """Bloc `popular` de `Data.lua` (affecté après la table principale, rafraîchi chaque jour par l'addon), None s'il
    manque (FA1)."""
    text = path.read_text(encoding="utf-8")
    at = text.find(POPULAR)
    if at < 0:
        return None
    value, _ = parse_lua_value_at(text, text.index("{", at))
    if not isinstance(value, dict):
        raise ValueError(f"{path} : table {POPULAR.strip(' =')} attendue")  # noqa: TRY004 : contenu illisible
    return value


def read_trees(path: Path) -> tuple[dict[str, Any], dict[str, dict[int, dict[str, Any]]]]:
    """En-tête (`build`, `generated`, `codeVersion`) et nœuds par fichier de classe de `Data.lua`."""
    head, doc = read_head_and_doc(path)
    out: dict[str, dict[int, dict[str, Any]]] = {}
    for file, cls in doc["classes"].items():
        nodes: dict[int, dict[str, Any]] = {}
        for tree in cls["trees"]:
            talents = tree["talents"]
            for t in talents:
                if "node" not in t:
                    continue
                req = t.get("req")
                prereq = talents[int(req) - 1].get("node") if isinstance(req, int) and 0 < req <= len(talents) else None
                nodes[int(t["node"])] = {
                    "name": t.get("name"),
                    "tree": tree.get("name"),
                    "tier": t.get("row"),
                    "col": t.get("col"),
                    "max": t.get("max"),
                    "spell": t.get("spell"),
                    "prereq": prereq,
                }
        out[str(file)] = nodes
    return head, out


def our_trees(classes_json: Path) -> dict[str, dict[int, dict[str, Any]]]:
    """Nœuds de `classes.json` par fichier de classe."""
    doc = json.loads(classes_json.read_text(encoding="utf-8"))
    out: dict[str, dict[int, dict[str, Any]]] = {}
    for cls in doc["classes"].values():
        nodes: dict[int, dict[str, Any]] = {}
        for tree in cls["trees"]:
            for t in tree["talents"]:
                prereq = (t.get("prereq") or {}).get("node_id")
                nodes[int(t["node_id"])] = {
                    "name": t.get("name"),
                    "tree": tree.get("name"),
                    "tier": t.get("tier"),
                    "col": t.get("col"),
                    "max": t.get("max"),
                    "spell": t.get("spell_id"),
                    "prereq": prereq,
                }
        out[str(cls["file"])] = nodes
    return out


def compare(mine: dict[int, dict[str, Any]], theirs: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Comptes et écarts entre deux jeux de nœuds."""
    only_mine = sorted(set(mine) - set(theirs))
    only_theirs = sorted(set(theirs) - set(mine))
    gaps = []
    for node in sorted(set(mine) & set(theirs)):
        for f in FIELDS:
            if mine[node][f] != theirs[node][f]:
                gaps.append({"node": node, "field": f, "forever": mine[node][f], "tf": theirs[node][f]})
    same = len(set(mine) & set(theirs)) - len({g["node"] for g in gaps})
    # même talent (nom, arbre, rangée, colonne, rangs, sort) porté par un autre nœud des deux côtés
    key = ("name", "tree", "tier", "col", "max", "spell")
    by_value = {tuple(theirs[n][k] for k in key): n for n in theirs}
    moved = []
    for node in sorted(set(mine)):
        other = by_value.get(tuple(mine[node][k] for k in key))
        if other is not None and other != node:
            moved.append({"name": mine[node]["name"], "forever": node, "tf": other})
    return {"forever": len(mine), "tf": len(theirs), "same": same, "only_forever": only_mine,
            "only_tf": only_theirs, "gaps": gaps, "moved": moved}  # fmt: skip


def crosscheck(data_lua: Path, classes_json: Path) -> dict[str, Any]:
    """Recoupement résumé : en-tête de Talents Forever et, par classe, comptes (aucune valeur de l'addon)."""
    head, theirs = read_trees(data_lua)
    mine = our_trees(classes_json)
    classes: dict[str, dict[str, int]] = {}
    for cls, nodes in sorted(theirs.items()):
        r = compare(mine.get(cls, {}), nodes)
        classes[cls] = {
            "forever": r["forever"],
            "tf": r["tf"],
            "same": r["same"],
            "gap_nodes": len({g["node"] for g in r["gaps"]}),
            "only_forever": len(r["only_forever"]),
            "only_tf": len(r["only_tf"]),
            "moved": len(r["moved"]),
        }
    totals = {
        k: sum(c[k] for c in classes.values())
        for k in ("forever", "tf", "same", "gap_nodes", "only_forever", "only_tf", "moved")
    }
    return {"head": head, "classes": classes, "totals": totals}


def tf_positions(path: Path) -> dict[str, Any]:
    """Positions de Talents Forever pour confirmer un nœud garé (décision 211) : `label` (version du `.toc`, en-tête
    et empreinte de `Data.lua`) et, par fichier de classe, une liste par arbre (même indice que nos onglets) de
    `[sort, rangée, colonne]`."""
    import hashlib

    head, doc = read_head_and_doc(path)
    version = "?"
    for toc in sorted(path.parent.glob("*.toc")):
        for line in toc.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("## Version:"):
                version = line.split(":", 1)[1].strip()
    sha = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    label = (
        f"Talents Forever {version} (Data.lua build {head.get('build')}, généré le {head.get('generated')}, "
        f"empreinte {sha})"
    )
    classes: dict[str, list[list[list[int]]]] = {}
    for file, cls in doc["classes"].items():
        classes[str(file)] = [
            [[int(t["spell"]), int(t["row"]), int(t["col"])] for t in tree["talents"] if "spell" in t]
            for tree in cls["trees"]
        ]
    return {"label": label, "classes": classes}
