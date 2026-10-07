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
from typing import Any, cast

from forever.build import BuildReport
from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.provenance import Certainty, Provenance
from forever.tf_code import CODE_VERSION, SYMBOLS, TREES, TfPlan, code_of, decode, encode, link

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
    forever_tree_names: tuple[str, ...] = ()

    @property
    def exportable(self) -> bool:
        return self.blocked is None

    def unmatched_at(self, tree: int, index: int) -> dict[str, Any] | None:
        """Écart de l'addon à une position de liste sans correspondance."""
        return next((u for u in self.unmatched if u.get("position") == [tree, index]), None)

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
                if t.get("max") != m.get("max"):
                    problems.append(
                        f"{m['name']} ({m['key']}) : rang maximal {m.get('max')} chez nous, {t.get('max')} chez "
                        "Talents Forever"
                    )
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
                "position": [ti, len(keys) - 1],
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
        forever_tree_names=tuple(str(t.get("name")) for t in my_trees),
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


MAGE = "Mage"  # seule classe dont forever calcule le build (T05)
NO_ORDER_NOTE = (
    "ordre non calculé pour ce contexte (l'optimiseur ne rend un ordre qu'en leveling) : Talents Forever place les "
    "points arbre par arbre"
)
STATUS_LABELS = {
    "ok": "code prêt",
    "absent": "addon absent",
    "bloque": "export bloqué",
    "format_non_pris_en_charge": "format non pris en charge",
    "ordre_incoherent": "ordre incohérent",
}


def tf_provenance(deps: Deps, addon: TfAddon | None, certainty: Certainty, notes: Sequence[str] = ()) -> Provenance:
    """Provenance d'un résultat tiré de l'addon : données installées et identité de l'addon en hypothèse."""
    from forever.provenance import local_provenance

    if addon is None:
        note = "Talents Forever absent du client"
    else:
        a = addon.describe()
        note = (
            f"Talents Forever {a['version']} (Data.lua build {a['build']}, généré le {a['generated']}, codes "
            f"v{a['codeVersion']}, empreinte {a['fingerprint']}), lecture locale"
        )
    return local_provenance(deps, certainty=certainty, assumptions=[note, *notes])


def _export_provenance(addon: TfAddon | None, talented_bonus: int) -> dict[str, Any]:
    ident: dict[str, Any] = (
        addon.describe()
        if addon is not None
        else {"addon": "Talents Forever", "version": None, "build": None, "generated": None, "codeVersion": None}
    )
    ident.setdefault("fingerprint", None)
    note = None
    if talented_bonus > 0:
        note = (
            f"bonus Legacy « Talented » de {talented_bonus} point(s) (hypothèse) : niveau du code = niveau du build ; "
            "l'addon lit le rang de Talented en jeu et doit y trouver le même rang"
        )
    return {
        "format": f"v{CODE_VERSION}",
        **ident,
        "verified_in_game": False,  # procédure de test en jeu : docs/ADDON.md, section 7
        "talented_note": note,
    }


def _order_mismatch(talents: Mapping[str, int], order: Sequence[str]) -> list[str]:
    counts: dict[str, int] = {}
    for key in order:
        counts[key] = counts.get(key, 0) + 1
    keys = set(counts) | {k for k, r in talents.items() if r > 0}
    return sorted(k for k in keys if counts.get(k, 0) != max(0, talents.get(k, 0)))


def export_build(
    addon: TfAddon | None,
    class_name: str,
    level: int,
    talents: Mapping[str, int],
    order: Sequence[str] | None,
    talented_bonus: int = 0,
) -> dict[str, Any]:
    """Bloc `export.talents_forever` d'un build : code v6, lien, commande d'import, ordre compris s'il est calculé ;
    sinon le statut et sa raison (addon absent, export bloqué, génération non prise en charge, ordre incohérent),
    jamais un code deviné. Certitude `probable` : format réimplémenté et recoupé par va-et-vient, pas encore relu en
    jeu."""
    block: dict[str, Any] = {
        "status": "ok",
        "reason": None,
        "code": None,
        "link": None,
        "import": None,
        "level": level,
        "order_included": False,
        "order_note": None,
        "closest_popular": None,
        "certainty": None,
        "provenance": _export_provenance(addon, talented_bonus),
    }

    def refuse(status: str, reason: str) -> dict[str, Any]:
        block.update(status=status, reason=reason)
        return block

    if addon is None:
        return refuse(
            "absent",
            f"Talents Forever absent du client (dossier Interface/AddOns/{ADDON_FOLDER}) : aucun code, rien deviné",
        )
    if not addon.supported:
        return refuse(
            "format_non_pris_en_charge",
            f"Talents Forever {addon.version} : codes de génération « {addon.head.get('codeVersion')} » "
            f"({', '.join(addon.checks)}) ; forever écrit la génération {CODE_VERSION} seulement",
        )
    layout = addon.layouts.get(class_name)
    if layout is None:
        return refuse("bloque", f"classe {class_name} absente de Talents Forever {addon.version}")
    if not layout.exportable:
        return refuse("bloque", str(layout.blocked))
    ranks = [[0] * len(tree) for tree in layout.trees]
    for key, rank in talents.items():
        if rank <= 0:
            continue
        pos = layout.position(key)
        if pos is None:
            return refuse("bloque", f"{key} sans correspondance chez Talents Forever {addon.version}")
        if rank > layout.max_ranks[pos[0]][pos[1]]:
            return refuse(
                "bloque",
                f"{key} au rang {rank}, au-delà du maximum {layout.max_ranks[pos[0]][pos[1]]} chez Talents Forever",
            )
        ranks[pos[0]][pos[1]] = rank
    steps: list[tuple[int, int]] = []
    if order:
        wrong = _order_mismatch(talents, order)
        if wrong:
            return refuse(
                "ordre_incoherent",
                "ordre incohérent : pas de l'ordre différents des rangs du build pour " + ", ".join(wrong),
            )
        for key in order:
            pos = layout.position(key)
            if pos is None:
                return refuse("bloque", f"{key} sans correspondance chez Talents Forever {addon.version}")
            steps.append(pos)
    plan = TfPlan(layout.slug, level, tuple(tuple(t) for t in ranks), tuple(steps) or None)
    try:
        code = encode(plan)
    except ValueError as err:
        return refuse("bloque", str(err))
    block.update(
        code=code,
        link=link(code),
        order_included=bool(steps),
        order_note=None if steps else NO_ORDER_NOTE,
        certainty="probable",
    )
    block["import"] = f"/tf import {code}"
    return block


def attach_export(deps: Deps, report: BuildReport, talented_bonus: int = 0) -> BuildWithExport:
    """Rapport de build augmenté du bloc `export` (appelé par la CLI et le MCP ; `build_report` n'en sait rien)."""
    addon = load_addon(deps)
    order = [str(s["talent"]) for s in report["order"] if s.get("talent")]
    block = export_build(addon, MAGE, report["level"], report["talents"], order or None, talented_bonus)
    if addon is not None and addon.popular and MAGE in addon.layouts:
        try:
            popular = popular_builds(addon, deps, MAGE)
        except InvalidArgumentError:
            popular = None
        if popular is not None:
            block["closest_popular"] = closest_popular(addon, popular, MAGE, report["talents"])
    return cast(BuildWithExport, {**report, "export": {"talents_forever": block}})


def render_export(block: Mapping[str, Any]) -> list[str]:
    """Lignes « Talents Forever » de la sortie texte de `forever build`."""
    if block["status"] != "ok":
        return [f"Talents Forever : {STATUS_LABELS.get(block['status'], block['status'])} : {block['reason']}"]
    prov = block["provenance"]
    lines = [
        (
            f"Talents Forever : {block['code']} · lien {block['link']} · import en jeu {block['import']} "
            f"({block['certainty']}, format {prov['format']}, addon {prov['version']})"
        )
    ]
    if block.get("order_note"):
        lines.append(f"  {block['order_note']}")
    if prov.get("talented_note"):
        lines.append(f"  {prov['talented_note']}")
    c = block.get("closest_popular")
    if c:
        scope = "même spécialisation" if c["same_spec"] else "toutes spécialisations"
        lines.append(
            f"  Build populaire le plus proche ({scope}) : n° {c['rank']} {c['spec']}, {c['missing_points']} point(s) "
            f"du nôtre absent(s), {c['points_to_add']} à ajouter (écart {c['total_gap']}), {c['link']} "
            f"({c['certainty']}, relevé du {c['asOf']})"
        )
    return lines


def decode_code(addon: TfAddon, deps: Deps, code: str) -> dict[str, Any]:
    """Build d'un code ou d'un lien Talents Forever : classe, niveau, points en nos clés, ordre, légalité sur le
    client ; une position sans correspondance rend le build « non vérifiable » (talent nommé), jamais deviné."""
    from forever.lookup import check_talents

    raw = code_of(code)
    slug = raw.split("/", 1)[0]
    layout = next((lay for lay in addon.layouts.values() if lay.slug == slug), None)
    if layout is None:
        known = sorted(lay.slug for lay in addon.layouts.values())
        raise InvalidArgumentError(
            f"Code Talents Forever d'une classe inconnue « {slug} ».", "classes : " + ", ".join(known)
        )
    try:
        plan = decode(raw, layout.max_ranks, layout.slug)
    except ValueError as err:
        raise InvalidArgumentError(
            f"Code Talents Forever illisible : {err}.", "coller le code ou le lien tel quel"
        ) from err

    talents, unverifiable, split, order = _read_plan(layout, plan)
    names = layout.forever_tree_names or layout.tree_names
    by_tree = {str(names[ti]): n for ti, n in enumerate(split)}
    legal: bool | None = None
    errors: list[str] = []
    legality = "non vérifiable"
    note = None
    if plan.legacy:
        note = "segments Legacy présents : points de bonus (Talented) inconnus, légalité non vérifiable"
    elif not unverifiable:
        check = check_talents(deps, layout.class_name, talents, plan.level)
        legal, errors = bool(check["legal"]), list(check["errors"])
        legality = "légal" if legal else "illégal"
    return {
        "kind": "tf_decode",
        "class": layout.class_name,
        "level": plan.level,
        "code": raw,
        "link": link(raw),
        "talents": talents,
        "points_by_tree": by_tree,
        "order": order,
        "legacy": list(plan.legacy) if plan.legacy else None,
        "legal": legal,
        "legality": legality,
        "errors": errors,
        "unverifiable": unverifiable,
        "note": note,
        "certainty": "probable",
        "provenance": tf_provenance(deps, addon, "probable"),
    }


POPULAR_NOTE = "builds populaires : choix de joueurs relevés par Talents Forever (décision 127), au mieux supposé"


def require_addon(deps: Deps) -> TfAddon:
    """Addon installé, ou erreur d'argument en français (CLI et MCP)."""
    addon = load_addon(deps)
    if addon is None:
        where = deps.wow_dir / "Interface" / "AddOns" / ADDON_FOLDER if deps.wow_dir else "FOREVER_WOW_DIR non réglé"
        raise InvalidArgumentError(
            f"Talents Forever introuvable ({where}).", "installer l'addon Talents Forever ou régler FOREVER_WOW_DIR"
        )
    return addon


def _read_plan(layout: TfLayout, plan: TfPlan) -> tuple[dict[str, int], list[str], list[int], list[str] | None]:
    """Points en nos clés, positions sans correspondance (nommées), points par arbre, ordre en nos clés."""

    def name_at(ti: int, i: int) -> str:
        key = layout.trees[ti][i]
        if key is not None:
            return key
        u = layout.unmatched_at(ti, i) or {}
        return str(u.get("key") or u.get("name") or f"position {i + 1} de l'arbre {ti + 1}")

    talents: dict[str, int] = {}
    unverifiable: list[str] = []
    for ti, tree in enumerate(plan.ranks):
        for i, rank in enumerate(tree):
            if not rank:
                continue
            key = layout.trees[ti][i]
            if key is None:
                unverifiable.append(name_at(ti, i))
            else:
                talents[key] = rank
    order = [name_at(ti, i) for ti, i in plan.order] if plan.order else None
    return talents, unverifiable, [sum(t) for t in plan.ranks], order


def _tree_index(layout: TfLayout, name: Any) -> int | None:
    """Indice de l'arbre nommé par l'addon (spécialisation `lead`), jamais apparié par nom à nos arbres."""
    return layout.tree_names.index(name) if name in layout.tree_names else None


def _popular_entry(layout: TfLayout, gd: Any, b: Mapping[str, Any]) -> dict[str, Any]:
    from forever.engine.talents import check_class_build

    code = str(b.get("code"))
    idx = _tree_index(layout, b.get("lead"))
    entry: dict[str, Any] = {
        "rank": b.get("rank"),
        "spec": b.get("lead"),
        "tree_index": idx,
        "tree": layout.forever_tree_names[idx] if idx is not None and idx < len(layout.forever_tree_names) else None,
        "code": code,
        "link": link(code),
        "import": f"/tf import {code}",
        "level": None,
        "points_by_tree": None,
        "talents": {},
        "legality": "illisible",
        "errors": [],
        "unverifiable": [],
    }
    try:
        plan = decode(code, layout.max_ranks, layout.slug)
    except ValueError as err:
        entry["errors"] = [str(err)]
        return entry
    talents, unverifiable, by_tree, _ = _read_plan(layout, plan)
    entry.update(level=plan.level, points_by_tree=by_tree, talents=talents, unverifiable=unverifiable)
    if unverifiable:
        entry["legality"] = "non vérifiable"
        return entry
    errors = check_class_build(gd.classes[layout.class_name], gd.constants.talents, talents, plan.level)
    entry.update(legality="illégal" if errors else "légal", errors=list(errors))
    return entry


def popular_builds(addon: TfAddon, deps: Deps, class_name: str | None = None) -> dict[str, Any]:
    """Builds populaires de l'addon par classe (part de chaque spécialisation, date `asOf`, fenêtre, nombre de builds
    relevés), chacun avec son lien, ses points en nos clés et sa légalité sur le client ; certitude `suppose`."""
    from forever.gamedata import build_game_data
    from forever.profile import normalize_class
    from forever.store import load_version

    if not addon.popular:
        raise InvalidArgumentError(
            f"Builds populaires absents de Talents Forever {addon.version} (bloc popular de Data.lua).",
            "mettre à jour l'addon Talents Forever",
        )
    wanted = normalize_class(class_name) if class_name else None
    if wanted is not None and wanted not in addon.layouts:
        raise InvalidArgumentError(
            f"Classe {wanted} absente de Talents Forever {addon.version}.", "choisir une autre classe"
        )
    gd = build_game_data(load_version(deps))
    classes: dict[str, Any] = {}
    for name, layout in addon.layouts.items():
        block = addon.popular.get(layout.file)
        if (wanted is not None and name != wanted) or not isinstance(block, dict):
            continue
        spec = [
            {"name": s[0], "pct": s[1], "tree_index": _tree_index(layout, s[0])}
            for s in block.get("spec") or []
            if isinstance(s, list) and len(s) == 2
        ]
        classes[name] = {
            "file": layout.file,
            "builds": block.get("builds"),
            "window": block.get("window"),
            "asOf": block.get("asOf"),
            "full": block.get("full"),
            "spec": spec,
            "top": [_popular_entry(layout, gd, b) for b in block.get("top") or [] if isinstance(b, dict)],
        }
    dates = sorted({str(c["asOf"]) for c in classes.values()})
    notes = [POPULAR_NOTE, f"relevés du {', '.join(dates) or '?'} (fenêtre par classe : champ window)"]
    return {
        "kind": "tf_popular",
        "addon": addon.describe(),
        "classes": classes,
        "certainty": "suppose",
        "provenance": tf_provenance(deps, addon, "suppose", notes),
    }


def closest_popular(
    addon: TfAddon, popular: Mapping[str, Any], class_name: str, talents: Mapping[str, int]
) -> dict[str, Any] | None:
    """Build populaire le plus proche du nôtre : même spécialisation (arbre le plus chargé du nôtre ; à défaut tous,
    avec une note), classé par nos points absents du sien (Σ max(0, nous − lui)), puis l'écart total
    (Σ |nous − lui|), puis son rang. Un build populaire non vérifiable (position sans correspondance) est écarté."""
    block = (popular.get("classes") or {}).get(class_name)
    layout = addon.layouts.get(class_name)
    if not block or layout is None:
        return None
    ours = {k: v for k, v in talents.items() if v > 0}
    split = [sum(ours.get(k, 0) for k in tree if k) for tree in layout.trees]
    spec = max(range(len(split)), key=lambda i: (split[i], -i)) if any(split) else None
    candidates = [b for b in block["top"] if not b["unverifiable"] and b["legality"] != "illisible"]
    same = [b for b in candidates if spec is not None and b["tree_index"] == spec]
    pool = same or candidates
    if not pool:
        return None
    rows = []
    for b in pool:
        theirs = b["talents"]
        keys = sorted(set(ours) | set(theirs))
        diffs = [
            {"key": k, "ours": ours.get(k, 0), "theirs": theirs.get(k, 0)}
            for k in keys
            if ours.get(k, 0) != theirs.get(k, 0)
        ]
        missing = sum(max(0, d["ours"] - d["theirs"]) for d in diffs)
        to_add = sum(max(0, d["theirs"] - d["ours"]) for d in diffs)
        rows.append((missing, missing + to_add, b["rank"], b, diffs, to_add))
    missing, total, _, best, diffs, to_add = min(rows, key=lambda r: (r[0], r[1], r[2]))
    note = (
        None if same else "aucun build populaire de la même spécialisation : comparaison à tous les builds de la classe"
    )
    if all(b.get("level") == best.get("level") for b in pool) and best.get("level") is not None:
        note = (note + " ; " if note else "") + (
            f"builds populaires relevés au niveau {best['level']} : à un niveau plus bas, les points absents disent si "
            "notre build est une étape de sa route"
        )
    return {
        "rank": best["rank"],
        "spec": best["spec"],
        "tree_index": best["tree_index"],
        "same_spec": bool(same),
        "code": best["code"],
        "link": best["link"],
        "import": best["import"],
        "legality": best["legality"],
        "missing_points": missing,
        "points_to_add": to_add,
        "total_gap": total,
        "differences": sorted(diffs, key=lambda d: (-abs(d["theirs"] - d["ours"]), d["key"])),
        "note": note,
        "asOf": block.get("asOf"),
        "window": block.get("window"),
        "certainty": "suppose",
    }
