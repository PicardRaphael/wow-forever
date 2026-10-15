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
    "naowh_weights": "Naowh : poids",  # CJ1, bloc 5 : poids des statistiques (NFSW1)
    "companion_scale": "Forever Companion : échelle",  # échelle Pawn v1
    "naowh_bis": "Naowh : BiS",  # liste BiS personnelle (!NBIS1!)
}
WHERE = {
    "naowh_weights": "Naowh Forever, Stat Weights, « Import weights »",
    "companion_scale": "Forever Companion, Options, « Import scale… »",
    "naowh_bis": "Naowh Forever, fenêtre BiS, « Import a list »",
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
    gear = []  # CJ1, bloc 5 : résultats de forever_gear (poids, échelle, liste BiS)
    if isinstance(value.get("naowh"), str) and str(value["naowh"]).startswith("NFSW1:"):
        gear.append(typed_link("naowh_weights", str(value["naowh"])))
    if isinstance(value.get("pawn"), str) and str(value["pawn"]).startswith("( Pawn:"):
        gear.append(typed_link("companion_scale", str(value["pawn"])))
    if isinstance(export, str) and export.startswith("!NBIS1!"):
        gear.append(typed_link("naowh_bis", export))
    if gear:
        out["gear"] = gear
    return out


def _gear_section(
    deps: Deps, context: Mapping[str, str], cls: str, level: int, who: str
) -> tuple[list[str], list[dict[str, str]]]:
    """CJ1, bloc 5 : liens d'équipement de « Exports » : poids du Mage et échelle (Naowh, Forever Companion), liste BiS
    personnelle (Naowh) ; spécialisation : celle de Naowh pour la classe (Givre pour le Mage), dite comme supposée."""
    from forever.bridge.gear_level import _talents
    from forever.errors import ForeverError
    from forever.gear import gear_report
    from forever.pipeline.gear_sources import read_naowh_bis
    from forever.store import load_version

    if deps.wow_dir is None:
        return ["- Équipement : dossier du jeu inconnu (FOREVER_WOW_DIR), aucun export."], []
    races = load_version(deps).read_json("races.json").get("races") or {}
    sent = str(context.get("race") or "")
    race = next((n for n, r in races.items() if sent in (n, r.get("client_file"))), "Orc")
    faction = str(context.get("faction") or "").lower() or None
    token = cls.upper()
    lists, _ = read_naowh_bis(deps.wow_dir / "Interface" / "AddOns")
    keys = [k for k, s in lists.items() if s.class_token == token]
    spec = "frost-mage" if "frost-mage" in keys else (keys[0] if keys else None)
    lines: list[str] = []
    links: list[dict[str, str]] = []
    if token == "MAGE":
        try:
            weights = gear_report(deps, "weights", class_name=cls, level=level, race=race,
                                  spec=spec or "frost-mage", name=f"Forever · {who} · niveau {level}",
                                  **_talents(deps, context))  # fmt: skip
        except ForeverError as err:
            lines.append(f"- Poids du Mage : {err.message}")
        else:
            links += [typed_link("naowh_weights", weights["naowh"]), typed_link("companion_scale", weights["pawn"])]
            lines.append(
                f"- Poids du Mage au niveau {level} : [Naowh : poids] dans {WHERE['naowh_weights']} ; "
                f"[Forever Companion : échelle] dans {WHERE['companion_scale']}."
            )
    if spec is None:
        lines.append("- Liste BiS : aucune liste de Naowh Forever pour cette classe.")
        return lines, links
    try:
        bis = gear_report(deps, "bis", class_name=cls, level=level, race=race, spec=spec, faction=faction,
                          name=f"Forever · {who} · BiS", **_talents(deps, context))  # fmt: skip
    except ForeverError as err:
        lines.append(f"- Liste BiS : {err.message}")
        return lines, links
    if bis["export"]:
        links.append(typed_link("naowh_bis", bis["export"]))
        lines.append(
            f"- Liste BiS ({spec}, supposée : demande ta liste BiS avec ta spécialisation pour en changer ; poids : "
            f"{bis['weights_source']}) : [Naowh : BiS] dans {WHERE['naowh_bis']}."
        )
    else:
        lines.append(f"- Liste BiS ({spec}) : aucune liste dans les addons.")
    return lines, links


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
    gear_lines, gear_links = _gear_section(deps, context, cls, level, who)
    lines += gear_lines
    links += gear_links
    if context.get("eui") != "on":
        pass  # décision 274 : EllesmereUI jamais proposé d'office (/fb eui on pour le rallumer)
    elif role not in ROLE_LABELS:
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
