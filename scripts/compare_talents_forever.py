"""Compare les arbres de talents d'un `classes.json` à ceux de Talents Forever (`Data.lua`), hors ligne (T08c, bloc G).

    uv run python scripts/compare_talents_forever.py --classes <classes.json> [--classes-ref <classes.json>]
        [--data-lua <TalentsForeverBook/Data.lua>] [--out docs/research/guerrier-T08c-talents-forever.md]

Lecture locale de `Data.lua` par `forever/pipeline/lua_table.py` (défaut : `<FOREVER_WOW_DIR>/Interface/AddOns/
TalentsForeverBook/Data.lua`) ; rien de l'addon n'est recopié : le rapport ne porte que des comptes et la liste des
écarts (nœud, champ, valeur de forever, valeur de Talents Forever). Champs comparés par nœud (`node`) : nom, arbre,
rangée (`tier`/`row`), colonne, rangs (`max`), sort et prérequis (`req` : rang du talent requis dans la liste de son
arbre, 1 pour le premier). `--classes-ref` : second fichier (version installée) comparé de même, pour mesurer ce que
change la candidate. Lecteur durable : FA1."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.pipeline.lua_table import parse_lua_value_at

FIELDS = ("name", "tree", "tier", "col", "max", "spell", "prereq")
ADDON = ("Interface", "AddOns", "TalentsForeverBook", "Data.lua")


def tf_classes(path: Path) -> tuple[dict[str, Any], dict[str, dict[int, dict[str, Any]]]]:
    text = path.read_text(encoding="utf-8")
    start = text.index("{", text.index("TalentsForeverBookData = "))  # première table seulement (structure des arbres)
    doc, _ = parse_lua_value_at(text, start)
    assert isinstance(doc, dict)
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
    head = {k: doc.get(k) for k in ("build", "generated", "codeVersion")}
    return head, out


def ours(path: Path) -> dict[str, dict[int, dict[str, Any]]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
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


def render(head: dict[str, Any], label: str, results: dict[str, dict[str, Any]], ref: dict[str, Any] | None) -> str:
    lines = [
        "# Arbres de talents : forever face à Talents Forever (T08c)",
        "",
        (
            "Généré par `uv run python scripts/compare_talents_forever.py` (lecture locale, agrégats et écarts "
            "seulement ; rien de l'addon n'est recopié)."
        ),
        "",
        (
            f"- Talents Forever : `Data.lua` build {head.get('build')}, généré le {head.get('generated')} (codes "
            f"v{head.get('codeVersion')})."
        ),
        f"- forever : {label}.",
        "- Champs comparés par nœud : nom, arbre, rangée, colonne, rangs, sort, prérequis.",
        "",
        "| Classe | Talents forever | Talents TF | Identiques | Écarts (nœuds) | Seulement forever | Seulement TF |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cls, r in sorted(results.items()):
        nodes = len({g["node"] for g in r["gaps"]})
        lines.append(
            f"| {cls} | {r['forever']} | {r['tf']} | {r['same']} | {nodes} | {len(r['only_forever'])} | "
            f"{len(r['only_tf'])} |"
        )
    if ref is not None:
        lines += ["", f"Référence : {ref['label']} (avant les correctifs du serveur) :", ""]
        lines += [
            f"- {cls} : {r['same']} identiques, {len({g['node'] for g in r['gaps']})} nœud(s) en écart, "
            f"{len(r['only_forever'])} seulement forever, {len(r['only_tf'])} seulement TF"
            for cls, r in sorted(ref["results"].items())
            if r["gaps"] or r["only_forever"] or r["only_tf"]
        ] or ["- aucun écart"]
    lines += ["", "## Écarts", ""]
    any_gap = False
    for cls, r in sorted(results.items()):
        if not (r["gaps"] or r["only_forever"] or r["only_tf"]):
            continue
        any_gap = True
        lines.append(f"### {cls}")
        lines.append("")
        if r["only_forever"]:
            lines.append(f"- Nœuds seulement dans forever : {', '.join(map(str, r['only_forever']))}")
        if r["only_tf"]:
            lines.append(f"- Nœuds seulement dans Talents Forever : {', '.join(map(str, r['only_tf']))}")
        if r["moved"]:
            lines.append(
                "- Même talent (nom, arbre, rangée, colonne, rangs, sort), autre nœud : "
                + ", ".join(f"{m['name']} (forever {m['forever']}, TF {m['tf']})" for m in r["moved"])
            )
        by_field = Counter(g["field"] for g in r["gaps"])
        if by_field:
            lines.append("- Champs en écart : " + ", ".join(f"{f} {n}" for f, n in sorted(by_field.items())))
            lines += ["", "| Nœud | Champ | forever | Talents Forever |", "| --- | --- | --- | --- |"]
            lines += [f"| {g['node']} | {g['field']} | {g['forever']} | {g['tf']} |" for g in r["gaps"]]
        lines.append("")
    if not any_gap:
        lines.append("Aucun écart.")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--classes", type=Path, required=True)
    parser.add_argument("--label", default="candidate avec les correctifs du serveur")
    parser.add_argument("--classes-ref", type=Path)
    parser.add_argument("--ref-label", default="version installée")
    parser.add_argument("--data-lua", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    wow = os.environ.get("FOREVER_WOW_DIR")
    data_lua = args.data_lua or (Path(wow).joinpath(*ADDON) if wow else None)
    if data_lua is None or not data_lua.is_file():
        raise SystemExit("Data.lua de Talents Forever introuvable : --data-lua ou FOREVER_WOW_DIR")
    head, tf = tf_classes(data_lua)
    mine = ours(args.classes)
    results = {cls: compare(mine.get(cls, {}), nodes) for cls, nodes in tf.items()}
    ref = None
    if args.classes_ref is not None:
        base = ours(args.classes_ref)
        ref = {"label": args.ref_label, "results": {c: compare(base.get(c, {}), n) for c, n in tf.items()}}
    text = render(head, args.label, results, ref)
    if args.out:
        args.out.write_bytes(text.encode("utf-8"))
        print(f"écrit : {args.out}")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
