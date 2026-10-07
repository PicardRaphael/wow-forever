"""Talents Forever installé (FA1, décision 209) : disposition de ses listes de talents, table de correspondance avec
nos talents, export de nos builds en code v6, builds populaires et comparaison.

La table est reconstruite à chaque appel depuis l'addon installé (jamais stockée dans `forever/data/`) : un talent
ajouté ou retiré par une mise à jour de l'addon est donc revu au prochain appel. Appariement strict : arbre au même
indice, même sort, même rangée, même colonne, une seule correspondance ; tout le reste est « sans correspondance »
avec sa raison, et bloque l'export de la classe au lieu d'être deviné. Lecture locale par
`forever/pipeline/lua_table.py`, jamais de Lua exécuté ; rien de l'addon n'est recopié dans le dépôt."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.build import BuildReport
from forever.config import Deps
from forever.tf_code import CODE_VERSION, SYMBOLS, TREES

ADDON_FOLDER = "TalentsForeverBook"
DATA_FILE = "Data.lua"
REASONS = ("seulement_forever", "seulement_talents_forever", "position_inconnue", "ambigu")
UNKNOWN_ROW_QUESTION = "CLS1"  # rangées du client inconnues (Démoniste), docs/OPEN_QUESTIONS.md
FINGERPRINT_LEN = 12


class BuildWithExport(BuildReport):
    """Rapport de `forever build` augmenté du bloc `export` (CLI et MCP ; `build_report` inchangé)."""

    export: dict[str, Any]


@dataclass(frozen=True)
class TfLayout:
    """Disposition d'une classe : notre clé par position de liste de l'addon (None : sans correspondance)."""

    file: str
    class_name: str
    slug: str
    tree_names: tuple[str, ...]
    trees: tuple[tuple[str | None, ...], ...]
    max_ranks: tuple[tuple[int, ...], ...]
    unmatched: tuple[dict[str, Any], ...] = ()
    renumbered: tuple[dict[str, Any], ...] = ()
    prereq_gaps: tuple[dict[str, Any], ...] = ()
    tree_name_gaps: tuple[dict[str, Any], ...] = ()
    blocked: str | None = None

    @property
    def exportable(self) -> bool:
        return self.blocked is None

    def position(self, key: str) -> tuple[int, int] | None:
        """(arbre, position de liste) d'une de nos clés, None sans correspondance."""
        for ti, tree in enumerate(self.trees):
            for i, k in enumerate(tree):
                if k == key:
                    return ti, i
        return None


@dataclass(frozen=True)
class TfAddon:
    folder: Path
    version: str | None
    head: dict[str, Any]
    fingerprint: str
    game_version: str
    layouts: dict[str, TfLayout]
    checks: tuple[str, ...] = ()
    popular: dict[str, Any] | None = None

    @property
    def supported(self) -> bool:
        """Génération des codes prise en charge (v6) et `Data.lua` lisible."""
        return not self.checks

    def describe(self) -> dict[str, Any]:
        """Identité de l'addon pour la provenance."""
        return {
            "addon": "Talents Forever",
            "version": self.version,
            "build": self.head.get("build"),
            "generated": self.head.get("generated"),
            "codeVersion": self.head.get("codeVersion"),
            "fingerprint": self.fingerprint,
        }


def addon_folder(deps: Deps) -> Path | None:
    """Dossier de l'addon dans le client (`Deps.wow_dir`), None s'il n'a pas de `Data.lua`."""
    if deps.wow_dir is None:
        return None
    folder = deps.wow_dir / "Interface" / "AddOns" / ADDON_FOLDER
    return folder if (folder / DATA_FILE).is_file() else None


def _our_classes(classes_json: Path) -> dict[str, tuple[str, dict[str, Any]]]:
    doc = json.loads(classes_json.read_text(encoding="utf-8"))
    return {str(c["file"]): (str(name), c) for name, c in doc["classes"].items()}


def _unmatched_text(u: Mapping[str, Any], version: str | None) -> str:
    tf = u.get("talents_forever") or {}
    if u["reason"] == "seulement_forever":
        mine = u.get("forever") or {}
        return (
            f"{u['name']} ({u['key']}, {u['tree']}, rangée {mine.get('row')}, colonne {mine.get('col')}) absent de "
            f"Talents Forever {version or '?'}"
        )
    if u["reason"] == "position_inconnue":
        return (
            f"{u['name']} ({u['key']}, {u['tree']}) : rangée inconnue dans nos données (question {UNKNOWN_ROW_QUESTION}), "
            f"rangée {tf.get('row')} chez Talents Forever"
        )
    if u["reason"] == "ambigu":
        return f"{u['name']} ({u['tree']}, rangée {tf.get('row')}, colonne {tf.get('col')}) : plusieurs correspondances"
    return f"{u['name']} ({u['tree']}, rangée {tf.get('row')}, colonne {tf.get('col')}) absent de nos données"


def _layout(
    file: str, class_name: str, tf_cls: Mapping[str, Any], mine: Mapping[str, Any], version: str | None
) -> TfLayout:
    tf_trees = list(tf_cls.get("trees") or [])
    my_trees = list(mine.get("trees") or [])
    problems: list[str] = []
    if len(tf_trees) != TREES or len(my_trees) != TREES:
        problems.append(f"{len(tf_trees)} arbre(s) chez Talents Forever et {len(my_trees)} chez nous, {TREES} attendus")
    total = sum(len(t.get("talents") or []) for t in tf_trees)
    if total > len(SYMBOLS):
        problems.append(f"{total} talents : le code v{CODE_VERSION} en écrit au plus {len(SYMBOLS)}")
    names: list[str] = []
    trees: list[tuple[str | None, ...]] = []
    max_ranks: list[tuple[int, ...]] = []
    unmatched: list[dict[str, Any]] = []
    renumbered: list[dict[str, Any]] = []
    prereq: list[dict[str, Any]] = []
    tree_names: list[dict[str, Any]] = []
    used: set[str] = set()
    referenced: set[str] = set()
    for ti, tree in enumerate(tf_trees):
        talents = list(tree.get("talents") or [])
        my_tree = my_trees[ti] if ti < len(my_trees) else {"name": None, "talents": []}
        my_talents = list(my_tree.get("talents") or [])
        tree_name = str(tree.get("name"))
        names.append(tree_name)
        if tree_name != my_tree.get("name"):
            tree_names.append({"index": ti, "talents_forever": tree_name, "forever": my_tree.get("name")})
        cells = [(t.get("row"), t.get("col")) for t in talents]
        if any(not isinstance(r, int) or not isinstance(c, int) for r, c in cells) or cells != sorted(cells):
            problems.append(f"liste de l'arbre {tree_name} non triée par rangée et colonne chez Talents Forever")
        keys: list[str | None] = []
        for t in talents:
            same = [
                m
                for m in my_talents
                if m.get("spell_id") == t.get("spell")
                and m.get("tier") == t.get("row")
                and m.get("col") == t.get("col")
            ]
            tf = {k: t.get(k) for k in ("row", "col", "spell", "node", "max")}
            if len(same) == 1 and same[0]["key"] not in used:
                m = same[0]
                keys.append(m["key"])
                used.add(m["key"])
                if t.get("node") != m.get("node_id"):
                    renumbered.append(
                        {
                            "key": m["key"],
                            "name": m["name"],
                            "forever": m.get("node_id"),
                            "talents_forever": t.get("node"),
                        }
                    )
                continue
            keys.append(None)
            spell = [m for m in my_talents if m.get("spell_id") == t.get("spell")]
            entry: dict[str, Any] = {
                "key": None,
                "name": t.get("name"),
                "tree": my_tree.get("name"),
                "talents_forever": tf,
            }
            if same:
                entry["reason"] = "ambigu"
            elif len(spell) == 1 and spell[0].get("tier") is None:
                entry.update(key=spell[0]["key"], name=spell[0]["name"], reason="position_inconnue")
                referenced.add(spell[0]["key"])
            else:
                entry["reason"] = "seulement_talents_forever"
            unmatched.append(entry)
        trees.append(tuple(keys))
        max_ranks.append(tuple(int(t.get("max") or 0) for t in talents))
        by_node = {m.get("node_id"): m["key"] for m in my_talents}
        mine_by_key = {m["key"]: m for m in my_talents}
        for i, t in enumerate(talents):
            key = keys[i]
            if key is None:
                continue
            req = t.get("req")
            theirs: str | None = None
            if isinstance(req, int) and 0 < req <= len(keys):
                if keys[req - 1] is None:
                    continue  # prérequis sur une position sans correspondance : écart déjà compté
                theirs = keys[req - 1]
            ours = by_node.get((mine_by_key[key].get("prereq") or {}).get("node_id"))
            if ours != theirs:
                prereq.append(
                    {"key": key, "name": mine_by_key[key]["name"], "forever": ours, "talents_forever": theirs}
                )
    for tree in my_trees:
        for m in tree.get("talents") or []:
            if m["key"] not in used and m["key"] not in referenced:
                unmatched.append(
                    {
                        "key": m["key"],
                        "name": m["name"],
                        "tree": tree.get("name"),
                        "reason": "seulement_forever",
                        "forever": {"row": m.get("tier"), "col": m.get("col"), "spell": m.get("spell_id")},
                    }
                )
    blocked = None
    if problems or unmatched:
        parts = problems + [_unmatched_text(u, version) for u in unmatched]
        blocked = (
            f"export bloqué ({class_name}) : "
            + " ; ".join(parts)
            + ". Talent sans correspondance jamais deviné ; table reconstruite à chaque appel, donc revérifiée à "
            "chaque mise à jour de l'addon"
        )
    return TfLayout(
        file=file,
        class_name=class_name,
        slug=class_name.lower(),
        tree_names=tuple(names),
        trees=tuple(trees),
        max_ranks=tuple(max_ranks),
        unmatched=tuple(unmatched),
        renumbered=tuple(renumbered),
        prereq_gaps=tuple(prereq),
        tree_name_gaps=tuple(tree_names),
        blocked=blocked,
    )


def load_addon(deps: Deps, *, folder: Path | None = None) -> TfAddon | None:
    """Addon installé lu et apparié aux données installées ; None s'il est absent. Un contrôle raté (génération des
    codes, fichier illisible) est noté dans `checks`, jamais levé."""
    from forever.addons import _version
    from forever.pipeline.talents_forever import read_head_and_doc, read_popular
    from forever.store import current_identity

    folder = folder or addon_folder(deps)
    if folder is None or not (folder / DATA_FILE).is_file():
        return None
    path = folder / DATA_FILE
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()[:FINGERPRINT_LEN]
    version = _version(folder)
    game_version = current_identity(deps.data_dir).game_version
    try:
        head, doc = read_head_and_doc(path)
        popular = read_popular(path)
    except (ValueError, KeyError, TypeError):
        return TfAddon(folder, version, {}, fingerprint, game_version, {}, ("illisible",), None)
    checks: list[str] = []
    if str(head.get("codeVersion")) != CODE_VERSION:
        checks.append("format_non_pris_en_charge")
    ours = _our_classes(deps.data_dir / game_version / "classes.json")
    layouts: dict[str, TfLayout] = {}
    for file, cls in (doc.get("classes") or {}).items():
        if str(file) not in ours or not isinstance(cls, dict):
            continue
        name, mine = ours[str(file)]
        layouts[name] = _layout(str(file), name, cls, mine, version)
    return TfAddon(folder, version, head, fingerprint, game_version, layouts, tuple(checks), popular)


def export_states(addon: TfAddon) -> dict[str, dict[str, Any]]:
    """État de l'export par classe : `possible`, `bloque` (talents sans correspondance nommés) ou
    `format_non_pris_en_charge`."""
    out: dict[str, dict[str, Any]] = {}
    for name, lay in addon.layouts.items():
        talents = sorted(str(u.get("key") or u.get("name")) for u in lay.unmatched)
        if not addon.supported:
            status = "format_non_pris_en_charge"
        else:
            status = "possible" if lay.exportable else "bloque"
        out[name] = {"status": status, "talents": talents}
    return out


def crosscheck_report(addon: TfAddon) -> dict[str, Any]:
    """Recoupement de nos arbres (données installées) avec ceux de l'addon : écarts classés, le client fait foi."""
    states = export_states(addon)
    classes: dict[str, Any] = {}
    for name, lay in addon.layouts.items():
        matched = sum(1 for tree in lay.trees for k in tree if k is not None)
        classes[name] = {
            "file": lay.file,
            "positions": sum(len(t) for t in lay.trees),
            "matched": matched,
            "forever": matched + sum(1 for u in lay.unmatched if u.get("key")),
            "export": states[name]["status"],
            "blocked": lay.blocked,
            "renumbered": list(lay.renumbered),
            "unmatched": list(lay.unmatched),
            "prereq": list(lay.prereq_gaps),
            "tree_names": list(lay.tree_name_gaps),
        }
    totals = {k: sum(len(c[k]) for c in classes.values()) for k in ("renumbered", "unmatched", "prereq", "tree_names")}
    return {
        "addon": addon.describe(),
        "game_version": addon.game_version,
        "checks": list(addon.checks),
        "classes": classes,
        "totals": totals,
    }


def _cell(value: Any) -> str:
    return "—" if value is None else str(value)


def render_crosscheck(report: Mapping[str, Any]) -> str:
    """Rapport Markdown déterministe du recoupement (`docs/research/talents-forever-FA1.md`)."""
    a = report["addon"]
    t = report["totals"]
    lines = [
        "# Arbres de talents : forever face à Talents Forever (FA1)",
        "",
        (
            "Généré par `uv run forever talents tf crosscheck --out <fichier>` (lecture locale, écarts seulement ; rien de "
            "l'addon n'est recopié). Le client fait foi : un écart est signalé, jamais tranché par l'addon."
        ),
        "",
        (
            f"- Talents Forever {a['version']} : `Data.lua` build {a['build']}, généré le {a['generated']}, codes "
            f"v{a['codeVersion']}, empreinte `{a['fingerprint']}`."
        ),
        f"- forever : données installées {report['game_version']}.",
        "- Appariement : arbre au même indice, même sort, même rangée, même colonne.",
        (
            f"- Écarts : nœuds numérotés autrement {t['renumbered']}, sans correspondance {t['unmatched']}, prérequis "
            f"{t['prereq']}, noms d'arbres {t['tree_names']}."
        ),
    ]
    if report.get("checks"):
        lines.append(f"- Contrôles de l'addon en échec : {', '.join(report['checks'])}.")
    lines += [
        "",
        "| Classe | Positions TF | Talents forever | Appariés | Export |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, c in sorted(report["classes"].items()):
        lines.append(f"| {name} | {c['positions']} | {c['forever']} | {c['matched']} | {c['export']} |")
    lines += ["", "## Écarts", ""]
    for name, c in sorted(report["classes"].items()):
        if not (c["renumbered"] or c["unmatched"] or c["prereq"] or c["tree_names"]):
            continue
        lines += [f"### {name}", ""]
        for g in c["tree_names"]:
            lines.append(
                f"- Nom d'arbre (cosmétique, arbres appariés par indice) : arbre {g['index'] + 1}, forever "
                f"« {g['forever']} », Talents Forever « {g['talents_forever']} »."
            )
        for g in c["renumbered"]:
            lines.append(
                f"- Nœud numéroté autrement : {g['name']} (`{g['key']}`), forever {g['forever']}, Talents Forever "
                f"{g['talents_forever']}."
            )
        for u in c["unmatched"]:
            side, pos = (
                ("Talents Forever", u["talents_forever"]) if u.get("talents_forever") else ("forever", u["forever"])
            )
            lines.append(
                f"- Sans correspondance ({u['reason']}) : {u['name']} (`{_cell(u.get('key'))}`, {u['tree']} ; position "
                f"chez {side} : rangée {_cell(pos.get('row'))}, colonne {_cell(pos.get('col'))}, sort "
                f"{_cell(pos.get('spell'))})."
            )
        for g in c["prereq"]:
            lines.append(
                f"- Prérequis : {g['name']} (`{g['key']}`), forever `{_cell(g['forever'])}`, Talents Forever "
                f"`{_cell(g['talents_forever'])}`."
            )
        if c["blocked"]:
            lines.append(f"- Export : {c['blocked']}.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_build(
    addon: TfAddon | None,
    class_name: str,
    level: int,
    talents: Mapping[str, int],
    order: Sequence[str] | None,
    talented_bonus: int = 0,
) -> dict[str, Any]:
    raise NotImplementedError


def attach_export(deps: Deps, report: BuildReport, talented_bonus: int = 0) -> BuildWithExport:
    raise NotImplementedError


def render_export(block: Mapping[str, Any]) -> list[str]:
    raise NotImplementedError


def decode_code(addon: TfAddon, deps: Deps, code: str) -> dict[str, Any]:
    raise NotImplementedError
