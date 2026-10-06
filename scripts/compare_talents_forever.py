"""Compare les arbres de talents d'un `classes.json` à ceux de Talents Forever (`Data.lua`), hors ligne (T08c, bloc G).

    uv run python scripts/compare_talents_forever.py --classes <classes.json> [--classes-ref <classes.json>]
        [--data-lua <TalentsForeverBook/Data.lua>] [--out docs/research/guerrier-T08c-talents-forever.md]

Lecture locale de `Data.lua` par `forever/pipeline/lua_table.py` (défaut : `<FOREVER_WOW_DIR>/Interface/AddOns/
TalentsForeverBook/Data.lua`) ; rien de l'addon n'est recopié : le rapport ne porte que des comptes et la liste des
écarts (nœud, champ, valeur de forever, valeur de Talents Forever). Champs comparés par nœud (`node`) : nom, arbre,
rangée (`tier`/`row`), colonne, rangs (`max`), sort et prérequis (`req` : rang du talent requis dans la liste de son
arbre, 1 pour le premier). `--classes-ref` : second fichier (version installée) comparé de même, pour mesurer ce que
change la candidate. Lecteur : `forever/pipeline/talents_forever.py` (T08d) ; lecteur durable : FA1."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.pipeline.talents_forever import FIELDS, compare, our_trees, read_trees

__all__ = ["FIELDS", "compare", "main", "ours", "render", "tf_classes"]
ADDON = ("Interface", "AddOns", "TalentsForeverBook", "Data.lua")
tf_classes = read_trees  # lecteur déplacé dans forever/pipeline/talents_forever.py (T08d, bloc D)
ours = our_trees


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
