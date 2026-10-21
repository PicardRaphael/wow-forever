"""Registre des sources et fraîcheur (plan « Sources d'abord », étape a ; décisions 288 et 291).

Chaque source dit si elle est à jour pour la version du jeu installée :
- par son **contenu** quand c'est possible : notre moteur du Mage (talent suivi dont le texte du client ne correspond
  plus à aucune règle de lecture `talent_models` : l'ancien sens serait gardé en silence) ; Talents Forever (export
  bloqué par la table de recoupement : arbres de l'addon différents des nôtres) ;
- sinon par sa **date ou son build** contre la date de publication du build installé (« par la version ») : une
  source en prose (rotations de Forever Companion) ou une liste datée (BiS de Naowh).

`choose` prend la première source à jour dans l'ordre du domaine ; les sources écartées le sont avec leur raison et la
réponse dit « calcul en cours de mise à jour » ; sans source à jour, la meilleure, « antérieure au patch » ; jamais
une panne. Aucune valeur de jeu ici."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, TypedDict

Status = Literal["à jour", "en retard", "inconnue", "absente"]
Basis = Literal["contenu", "version"]


class Freshness(TypedDict):
    source: str  # identifiant stable de la source
    label: str  # nom en mots de joueur
    domain: str  # builds, rotations, poids, bis, equipement, routes, metiers, reputations, export
    classes: list[str]  # classes couvertes (« * » : toutes)
    status: Status
    basis: Basis
    detail: list[str]  # entrées en cause (talents, nœuds, dates)


class Choice(TypedDict):
    chosen: Freshness | None
    set_aside: list[Freshness]
    note: str


ENGINE = "moteur"


def _fresh(source: str, label: str, domain: str, classes: list[str], status: Status, basis: Basis,
           detail: list[str]) -> Freshness:  # fmt: skip
    return {"source": source, "label": label, "domain": domain, "classes": classes, "status": status,
            "basis": basis, "detail": detail}  # fmt: skip


def engine_freshness(talents_doc: Mapping[str, Any], rules: Mapping[str, Any]) -> Freshness:
    """Moteur du Mage : en retard si un talent suivi par `talent_models` a un texte du client qu'aucune de ses règles
    ne reconnaît (pas de marqueur `model` alors que des règles existent)."""
    tracked = {k: v for k, v in (rules.get("talent_models") or {}).items() if isinstance(v, list) and v}
    late = []
    for tree in talents_doc.get("trees", []):
        for t in tree.get("talents", []):
            rows = tracked.get(t.get("key"))
            if not rows:
                continue
            text = str((t.get("source") or {}).get("client_desc") or t.get("desc") or "")
            if not any(str(r.get("contains")) in text for r in rows if isinstance(r, Mapping)) and not t.get("model"):
                late.append(f"{t.get('name') or t.get('key')} : texte du client sans règle de lecture connue")
    status: Status = "en retard" if late else "à jour"
    return _fresh(ENGINE, "moteur du Mage", "builds", ["Mage"], status, "contenu", late)


def tf_freshness(states: Mapping[str, Mapping[str, Any]], version: str | None) -> list[Freshness]:
    """Talents Forever, par classe, d'après l'état de son export (`talents_forever.export_states`)."""
    label = f"Talents Forever {version or '?'}"
    out = []
    for cls, state in sorted(states.items()):
        status = str(state.get("status"))
        if status == "possible":
            out.append(_fresh(f"talents_forever:{cls}", label, "builds", [cls], "à jour", "contenu", []))
        elif status == "format_non_pris_en_charge":
            detail = ["génération des codes de l'addon non prise en charge"]
            out.append(_fresh(f"talents_forever:{cls}", label, "builds", [cls], "en retard", "contenu", detail))
        else:
            talents, seen = [], set()  # positions de l'addon (nom) et talents à nous (clé) : un seul nom par talent
            for t in state.get("talents") or []:
                norm = "".join(str(t).split()).lower()
                if norm not in seen:
                    seen.add(norm)
                    talents.append(str(t))
            detail = [f"sans correspondance : {', '.join(talents)}"] if talents else ["arbres différents des nôtres"]
            out.append(_fresh(f"talents_forever:{cls}", label, "builds", [cls], "en retard", "contenu", detail))
    return out


def dated_freshness(source: str, label: str, domain: str, classes: list[str], data_date: str | None,
                    build_date: str | None) -> Freshness:  # fmt: skip
    """Source datée : à jour si ses données datent du jour de publication du build ou après, en retard avant ;
    inconnue sans l'une des deux dates. Fraîcheur « par la version » : elle ne dit pas que le contenu a suivi."""
    if not data_date or not build_date:
        return _fresh(source, label, domain, classes, "inconnue", "version", ["date des données ou du build inconnue"])
    if str(data_date)[:10] >= str(build_date)[:10]:
        return _fresh(source, label, domain, classes, "à jour", "version", [])
    detail = [f"données du {str(data_date)[:10]}, antérieures au build publié le {str(build_date)[:10]}"]
    return _fresh(source, label, domain, classes, "en retard", "version", detail)


def choose(candidates: Sequence[Freshness]) -> Choice:
    """Première source à jour dans l'ordre donné ; les précédentes écartées avec leur raison."""
    if not candidates:
        return {"chosen": None, "set_aside": [], "note": "aucune source pour ce domaine"}
    aside: list[Freshness] = []
    for c in candidates:
        if c["status"] == "à jour":
            if not aside:
                return {"chosen": c, "set_aside": [], "note": ""}
            why = " ; ".join(f"{a['label']} en retard ({', '.join(a['detail']) or a['status']})" for a in aside)
            return {"chosen": c, "set_aside": aside, "note": f"calcul en cours de mise à jour : {why} ; réponse de "
                    f"{c['label']}"}  # fmt: skip
        aside.append(c)
    best = candidates[0]
    why = ", ".join(best["detail"]) or best["status"]
    return {"chosen": best, "set_aside": [], "note": f"{best['label']} : source antérieure au patch ({why})"}


def sources_report(deps: Any) -> list[Freshness]:
    """Fraîcheur des sources de la version installée : moteur du Mage (données), Talents Forever et addons datés
    (lecture locale du dossier du jeu quand il est connu)."""
    from forever.store import load_version

    data = load_version(deps)
    rules = data.read_json("decode_rules.json")
    out = [engine_freshness(data.read_json("talents.json"), rules)]
    if deps.wow_dir is None:
        sims = wowsims_freshness(Path(deps.cache_dir), _build_date(deps, data.game_version))
        return [*out, sims] if sims is not None else out
    try:
        from forever.talents_forever import export_states, load_addon

        addon = load_addon(deps)
    except Exception:  # noqa: BLE001 : un addon illisible ne casse jamais le relevé
        addon = None
    if addon is not None:
        out += tf_freshness(export_states(addon), addon.version)
    build_date = _build_date(deps, data.game_version)
    out += _dated_addons(deps, build_date)
    sims = wowsims_freshness(Path(deps.cache_dir), build_date)
    if sims is not None:
        out.append(sims)
    return out


def _build_date(deps: Any, version: str) -> str | None:
    from forever.freshness import freshness_for_version

    f = freshness_for_version(deps, version, allow_network=False)
    return f["latest_created_at"] if f.get("latest_version") == version else None


def wowsims_freshness(cache_dir: Path, build_date: str | None) -> Freshness | None:
    """wowsims/forever (décisions 293 et 294) : daté par le commit épinglé contre la date de publication du build ;
    None tant qu'il n'est pas compilé (`forever sims update`)."""
    from forever.pipeline.wowsims_build import pinned

    pin = pinned(cache_dir)
    if pin is None:
        return None
    fresh = dated_freshness("wowsims", "wowsims/forever (niveau 60)", "calculs", ["*"], pin.get("committed_at"),
                            build_date)  # fmt: skip
    fresh["detail"] = [*fresh["detail"], f"commit {str(pin['commit'])[:12]} compilé tel quel"]
    return fresh


def _dated_addons(deps: Any, build_date: str | None) -> list[Freshness]:
    """Addons lus par le plan « Sources d'abord » : Forever Companion par son contenu, classe par classe (talents de
    ses arbres inconnus de nos données ; sa date à défaut), poids par défaut de Naowh par leur date, SkillUp Forever
    par le build de ses données."""
    from forever.addons import content_version
    from forever.pipeline.companion import read_companion
    from forever.pipeline.gear_sources import read_naowh_weights
    from forever.pipeline.skillup import read_skillup
    from forever.store import load_version

    addons = Path(deps.wow_dir) / "Interface" / "AddOns"
    out: list[Freshness] = []
    data = load_version(deps)
    guide = read_companion(addons, data.read_json("classes.json")["classes"])
    if guide is not None and guide["classes"]:
        for cls, entry in sorted(guide["classes"].items()):
            if entry["unmatched"]:
                detail = [f"talents inconnus de nos données : {', '.join(entry['unmatched'])}"]
                out.append(
                    _fresh(f"companion:{cls}", "Forever Companion", "builds", [cls], "en retard", "contenu", detail)
                )
            else:
                out.append(_fresh(f"companion:{cls}", "Forever Companion", "builds", [cls], "à jour", "contenu", []))
    elif (addons / "ForeverCompanion").is_dir():
        meta = content_version("ForeverCompanion", addons / "ForeverCompanion") or {}
        out.append(dated_freshness("companion", "Forever Companion", "builds", ["*"], meta.get("updated"),
                                   build_date))  # fmt: skip
    weights = read_naowh_weights(addons)
    if weights is not None:  # poids par défaut de Naowh (niveau 60, écrits à la main) : fraîcheur par leur date
        out.append(dated_freshness("naowh_weights", "Naowh Forever (poids par défaut)", "poids", ["*"],
                                   weights.updated, build_date))  # fmt: skip
    skill = read_skillup(addons)
    if skill is not None:
        build = skill.get("build")
        if build == data.game_version:
            out.append(_fresh("skillup", "SkillUp Forever", "metiers", ["*"], "à jour", "version", []))
        else:
            detail = [f"données tirées du build {build or '?'}, jeu {data.game_version}"]
            out.append(_fresh("skillup", "SkillUp Forever", "metiers", ["*"], "en retard", "version", detail))
    return out
