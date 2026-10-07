"""Addon Talents Forever synthétique pour les tests (FA1) : `Data.lua` reconstruit dans un dossier temporaire.

Rien de l'addon réel n'est copié : les arbres sont rebâtis depuis `classes.json` (nos talents, nos rangées, nos
colonnes, nos rangs, nos sorts) dans l'ordre des listes de Talents Forever relevé par
`tests/fixtures/talents_forever/layout.json`, avec ses seuls écarts (nœud numéroté autrement, prérequis, position
sans correspondance) ; le bloc `popular` vient de `popular.json` (agrégats). Le vrai lecteur
(`forever/talents_forever.py`) lit ensuite ce fichier comme il lirait l'addon installé."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "talents_forever"
ADDON_FOLDER = "TalentsForeverBook"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _lua(value: Any, indent: int = 0) -> str:
    pad = "  " * (indent + 1)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        if not value:
            return "{}"
        items = [_lua(v, indent + 1) for v in value]
        return "{\n" + ",\n".join(pad + i for i in items) + "\n" + "  " * indent + "}"
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{k} = {_lua(v, indent + 1)}" for k, v in value.items()]
        return "{\n" + ",\n".join(pad + i for i in items) + "\n" + "  " * indent + "}"
    raise TypeError(type(value))


def _our_classes(classes_json: Path) -> dict[str, dict[str, Any]]:
    doc = json.loads(classes_json.read_text(encoding="utf-8"))
    return {c["file"]: c for c in doc["classes"].values()}


def build_doc(classes_json: Path, layout: dict[str, Any], popular: dict[str, Any]) -> dict[str, Any]:
    """Structure de `Data.lua` (en-tête, arbres, bloc `popular`) rebâtie depuis nos données et la fixture."""
    ours = _our_classes(classes_json)
    classes: dict[str, Any] = {}
    for file, lay in layout["classes"].items():
        mine = ours[file]
        trees = []
        for ti, tree_lay in enumerate(lay["trees"]):
            by_key = {t["key"]: t for t in mine["trees"][ti]["talents"]}
            by_node = {t["node_id"]: t for t in mine["trees"][ti]["talents"]}
            talents: list[dict[str, Any]] = []
            for pos in tree_lay["positions"]:
                if "tf" in pos:
                    tf = pos["tf"]
                    talents.append({k: tf[k] for k in ("name", "max", "row", "col", "node", "spell")})
                else:
                    t = by_key[pos["key"]]
                    talents.append(
                        {
                            "name": t["name"],
                            "max": t["max"],
                            "row": t["tier"],
                            "col": t["col"],
                            "node": pos.get("node", t["node_id"]),
                            "spell": t["spell_id"],
                        }
                    )
            index_by_node = {}
            for i, pos in enumerate(tree_lay["positions"]):
                node = pos["tf"]["node"] if "tf" in pos else by_key[pos["key"]]["node_id"]
                index_by_node[node] = i + 1
            for i, pos in enumerate(tree_lay["positions"]):
                if "req" in pos:
                    req = pos["req"]
                elif "tf" in pos:
                    req = None
                else:
                    pre = (by_key[pos["key"]].get("prereq") or {}).get("node_id")
                    req = index_by_node.get(pre) if pre in by_node else None
                if req is not None:
                    talents[i]["req"] = req
            trees.append({"name": tree_lay["name"], "talents": talents})
        classes[file] = {"name": lay["name"], "trees": trees}
    head = popular["addon"]
    return {
        "build": head["build"],
        "generated": head["generated"],
        "codeVersion": head["codeVersion"],
        "site": "talentsforever.com",
        "classes": classes,
        "popular": copy.deepcopy(popular["classes"]),
    }


def write_addon(
    wow_dir: Path,
    classes_json: Path,
    *,
    layout: dict[str, Any] | None = None,
    popular: dict[str, Any] | None = None,
    mutate: Callable[[dict[str, Any]], None] | None = None,
    with_popular: bool = True,
) -> Path:
    """Écrit `<wow_dir>/Interface/AddOns/TalentsForeverBook/` (`.toc` et `Data.lua`) ; rend le dossier de l'addon.

    `mutate` modifie la structure avant l'écriture (code d'une autre génération, liste désordonnée…)."""
    layout = layout if layout is not None else load_fixture("layout.json")
    popular = popular if popular is not None else load_fixture("popular.json")
    doc = build_doc(classes_json, layout, popular)
    if mutate is not None:
        mutate(doc)
    pop = doc.pop("popular")
    folder = wow_dir / "Interface" / "AddOns" / ADDON_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    toc = f"## Interface: 16001\n## Title: Talents Forever (fixture)\n## Version: {popular['addon']['version']}\n"
    (folder / f"{ADDON_FOLDER}.toc").write_bytes(toc.encode("utf-8"))
    text = "-- Generated by tests/talents_forever_data.py (fixture). Do not edit by hand.\n"
    text += f"TalentsForeverBookData = {_lua(doc)}\n"
    if with_popular:
        text += "-- BEGIN popular\n"
        text += f"TalentsForeverBookData.popular = {_lua(pop)}\n"
        text += "-- END popular\n"
    (folder / "Data.lua").write_bytes(text.encode("utf-8"))
    return folder
