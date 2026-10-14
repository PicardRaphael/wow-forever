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


def game_base(deps: Deps, name: str) -> str | None:
    """Dernier profil de base reçu du jeu pour ce personnage (`ellesmere_base_game`), sinon None."""
    from forever.profile import character_values, load_profile, resolve_path

    raw = load_profile(resolve_path(deps))["characters"].get(name)
    value = character_values(raw).get("ellesmere_base_game") if isinstance(raw, dict) else None
    return value if isinstance(value, str) and value else None


def keep_base(deps: Deps, name: str, realm: str, base: str) -> None:
    """Nouveau profil de base choisi en jeu (/fb base) écrit au profil forever du personnage, source `jeu`, au clic sur
    « Exports » (décision 269) : il remplace le choix précédent, quelle qu'en soit la source ; le même choix renvoyé
    à chaque clic ne réécrit rien (une commande `--ellesmere-base` postérieure est gardée)."""
    from forever.profile import apply_game_fields, load_profile, make_field, resolve_path, save_profile
    from forever.timefmt import format_utc

    path, at = resolve_path(deps), format_utc(deps.now())
    apply_game_fields(path, name, realm, {"ellesmere_base_game": base}, source="jeu", at=at, client_build=None)
    doc = load_profile(path)
    doc["characters"][name]["ellesmere_base"] = make_field(base, "jeu", at)
    save_profile(path, doc)


def exports_reply(
    deps: Deps, context: Mapping[str, str], last: Sequence[Mapping[str, str]]
) -> tuple[str, list[dict[str, str]]]:
    """Réponse du bouton « Exports » pour le personnage du contexte : texte (une ligne par export, ce qui manque
    dit) et liens typés à copier."""
    from forever.bridge.context import CLASS_NAMES, describe_talents, talent_table
    from forever.errors import InvalidArgumentError
    from forever.exports.ellesmere import ROLE_LABELS, ellesmere_export
    from forever.exports.macros import macros_export
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
    macros = macros_export(deps, cls, level, talents)
    if macros["code"]:
        links.append(typed_link("naowh_macros", macros["code"]))
        lines.append(f"- Macros de la classe au niveau {level} vers Naowh Forever ; {macros['import']}.")
    else:
        lines.append(f"- Macros : {macros['reason']}.")
    role = str(context.get("role") or "")
    realm = str(context.get("realm") or "")
    if role not in ROLE_LABELS:
        lines.append("- Profil EllesmereUI : aucun rôle choisi pour ce personnage (/fb role dps, heal ou tank).")
    elif not realm:
        lines.append("- Profil EllesmereUI : royaume absent du contexte du jeu.")
    else:
        sent = str(context.get("eui_base") or "").strip() or None
        chosen = sent if sent is not None and sent != game_base(deps, who) else None  # choix nouveau en jeu
        try:
            eui = ellesmere_export(
                deps, who, realm, cls, level, role, base_name=chosen, talents=talents, choice="jeu" if chosen else None
            )
        except InvalidArgumentError as err:
            lines.append(f"- Profil EllesmereUI : {err.message} ({err.action}).")
        else:
            if chosen is not None:
                keep_base(deps, who, realm, chosen)
            base = eui["base"]["name"]
            how = (
                f"profil de base « {base} »"
                if eui["base"]["choice"] in ("jeu", "personnage")
                else f"profil de base « {base} », le profil actif : choisir celui du personnage par /fb base <profil>"
            )
            links.append(typed_link("ellesmere", eui["code"], f"EllesmereUI : {ROLE_LABELS[role]}"))
            lines.append(f"- Profil EllesmereUI « {eui['profile_name']} » ({how}) ; {eui['import']}.")
    if last:
        lines.append("- Dernier build donné dans le chat : ses liens ci-dessous (Talents Forever, Naowh).")
        links.extend(dict(link) for link in last)
    else:
        lines.append("- Build conseillé : aucun dans cette session ; cliquer d'abord « Talents ».")
    lines.append("- Chaque lien s'ouvre dans le panneau : copier, puis coller dans l'addon (certitude probable).")
    return "\n".join(lines), links
