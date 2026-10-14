"""Exports vers les addons d'interface dans le pont (EX1, bloc C) : liens typés d'une réponse (`links` de
l'emplacement : Talents Forever, code Naowh…), chacun copiable depuis le panneau d'action, et réponse du bouton
« Exports » rédigée par le pont sans le modèle (comme le résumé d'une attente, décision 235)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps

LABELS = {
    "talents_forever": "Talents Forever",
    "naowh_build": "Naowh : build",
    "naowh_macros": "Naowh : macros",
    "ellesmere": "EllesmereUI",
}


def typed_link(kind: str, text: str, label: str | None = None) -> dict[str, str]:
    """Lien typé de l'emplacement : `{kind, label, text}`."""
    return {"kind": kind, "label": label or LABELS[kind], "text": text}


def _naowh(block: Any) -> dict[str, str] | None:
    if (
        isinstance(block, Mapping)
        and block.get("status") in ("ok", "ordre_genere")
        and isinstance(block.get("code"), str)
    ):
        return typed_link("naowh_build", str(block["code"]))
    return None


def typed_links(value: Any) -> dict[str, list[dict[str, str]]]:
    """Liens typés d'un résultat d'outil forever, rangés comme `AgentResult.links` : `build` (export de
    `forever_build`), `closest` (build populaire le plus proche), `check` (`build_check`), `export`
    (`forever_lookup(kind="export")`)."""
    out: dict[str, list[dict[str, str]]] = {}
    if not isinstance(value, Mapping):
        return out
    export = value.get("export")
    if isinstance(export, Mapping):
        items = []
        tf = export.get("talents_forever")
        if isinstance(tf, Mapping) and tf.get("status") == "ok" and isinstance(tf.get("link"), str):
            items.append(typed_link("talents_forever", str(tf["link"])))
        if (code := _naowh(export.get("naowh"))) is not None:
            items.append(code)
        if items:
            out["build"] = items
    closest = value.get("closest")
    if isinstance(closest, Mapping):
        items = [typed_link("talents_forever", str(closest["link"]))] if isinstance(closest.get("link"), str) else []
        if (code := _naowh(closest.get("naowh"))) is not None:
            items.append(code)
        if items:
            out["closest"] = items
    if value.get("kind") == "build_check" and (code := _naowh(value.get("naowh"))) is not None:
        out["check"] = [code]
    if value.get("kind") == "naowh_build" and (code := _naowh(value)) is not None:
        out["export"] = [code]
    return out


def exports_reply(
    deps: Deps, context: Mapping[str, str], last: Sequence[Mapping[str, str]]
) -> tuple[str, list[dict[str, str]]]:
    """Réponse du bouton « Exports » pour le personnage du contexte : texte (une ligne par export, ce qui manque
    dit) et liens typés à copier."""
    from forever.bridge.context import CLASS_NAMES, describe_talents, talent_table
    from forever.exports.talents import naowh_export

    token = str(context.get("class") or "")
    level_text = str(context.get("level") or "")
    if token not in CLASS_NAMES or not level_text.isdigit():
        return "Exports : personnage inconnu (classe ou niveau absent du contexte du jeu).", []
    cls, level = CLASS_NAMES[token], int(level_text)
    who = str(context.get("name") or cls)
    lines = [f"## Exports de {who} ({cls} niveau {level})"]
    links: list[dict[str, str]] = []
    reading = describe_talents(talent_table(deps), token, str(context.get("talents") or ""))
    talents = {t.key: t.rank for t in reading.known if t.rank > 0}
    if not talents:
        lines.append("- Build actuel : aucun talent placé, pas de code Naowh.")
    else:
        block = naowh_export(deps, cls, level, talents, name=f"{who} actuel")
        if block["code"]:
            links.append(typed_link("naowh_build", block["code"], "Naowh : build actuel"))
            note = f" ({block['order_note']})" if block["order_note"] else ""
            lines.append(f"- Build actuel vers Naowh Forever{note} ; {block['import']}.")
        else:
            lines.append(f"- Build actuel : export Naowh bloqué : {block['reason']}.")
    if last:
        lines.append("- Dernier build donné dans le chat : ses liens ci-dessous (Talents Forever, Naowh).")
        links.extend(dict(link) for link in last)
    else:
        lines.append("- Build conseillé : aucun dans cette session ; cliquer d'abord « Talents ».")
    lines.append("- Chaque lien s'ouvre dans le panneau : copier, puis coller dans l'addon (certitude probable).")
    return "\n".join(lines), links
