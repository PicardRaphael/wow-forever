"""Veille locale du poste (`forever watch`, T08b, bloc G) : hors ligne, rien n'est lancé.

Détecteurs, comparés au dernier passage (`<cache>/watch/state.json`) : build du client (`.build.info`), addons de
données (empreintes, court-circuit par taille et date), correctifs du serveur (`Logs/Hotfix.log`, relu seulement si sa
taille ou sa date change ; journal `hotfixes.json`), nouveaux journaux de combat (`WoWCombatLog-*.txt`) et sauvegardes
modifiées (ForeverLogger, Questie, Auctionator). Chaque changement porte les **actions proposées** (commande exacte,
réseau ou non) ; un nouveau build propose `forever notes` (décision 148 : lecture des notes à la main seulement).
`--report` écrit le résumé dans `<cache>/watch/report.json` (tâche planifiée Windows) ; la ligne de démarrage de
session en tire une ligne compacte."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forever.addons import DATA_ADDONS, _files, _folders, fingerprint
from forever.config import Deps
from forever.pipeline import hotfixes
from forever.pipeline.client_builds import read_build_info
from forever.timefmt import format_utc

STATE = ("watch", "state.json")
REPORT = ("watch", "report.json")
SV_NAMES = ("ForeverLogger.lua", "Questie.lua", "Auctionator.lua")


def _read(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _write(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def _action(command: str, network: bool, why: str) -> dict[str, Any]:
    return {"command": command, "network": network, "why": why}


def _rules(deps: Deps) -> dict[str, Any]:
    from forever.pipeline.decode import load_rules

    try:
        return load_rules(deps.data_dir)[1]
    except Exception:  # noqa: BLE001 : la veille ne doit jamais échouer sur des règles absentes
        return {}


def watch(deps: Deps, *, report: bool = False) -> dict[str, Any]:
    """Un passage de veille ; écrit l'état du passage (et le rapport avec `report`), ne lance rien."""
    state_path = deps.cache_dir.joinpath(*STATE)
    old = _read(state_path)
    new: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    wow = deps.wow_dir
    if wow is None or not wow.is_dir():
        return {"events": [], "wow_dir": None, "checked_at": format_utc(deps.now())}
    build = read_build_info(wow)
    new["build"] = build.build if build else None
    if new["build"] != old.get("build"):
        b = new["build"] or "inconnu"
        events.append(
            {
                "kind": "client_build",
                "detail": f"client {b} (précédent : {old.get('build') or 'aucun relevé'})",
                "actions": [
                    _action("forever status", True, "fraîcheur des données"),
                    _action(f"forever fetch --version {b}", True, "tables du nouveau build"),
                    _action(f"forever decode --version {b}", False, "version candidate"),
                    _action("forever notes", True, "notes officielles du nouveau build (lancement à la main, D1)"),
                ],
            }
        )
    addons_dir = wow / "Interface" / "AddOns"
    old_addons = old.get("addons", {})
    new_addons: dict[str, Any] = {}
    changed: list[str] = []
    for name, spec in DATA_ADDONS.items():
        folders = _folders(addons_dir, spec) if addons_dir.is_dir() else []
        if not folders:
            continue
        files = _files(addons_dir, folders, old_addons.get(name, {}).get("files", {}))
        new_addons[name] = {"fingerprint": fingerprint(files), "files": files}
        if old_addons.get(name, {}).get("fingerprint") != new_addons[name]["fingerprint"]:
            changed.append(name)
    new["addons"] = new_addons
    if changed:
        events.append(
            {
                "kind": "addons",
                "detail": f"{len(changed)} addon(s) nouveau(x) ou changé(s) : {', '.join(changed)}",
                "actions": [_action("forever addons status --save", False, "versions, fichiers et agrégats")],
            }
        )
    log = wow.joinpath(*hotfixes.HOTFIX_LOG)
    if log.is_file():
        st = log.stat()
        stamp = {"size": st.st_size, "mtime": st.st_mtime_ns}
        new["hotfix_log"] = stamp
        if old.get("hotfix_log") != stamp:
            lines = hotfixes.parse_hotfix_log(log.read_text(encoding="utf-8", errors="replace"), hotfixes.log_year(log))
            added = hotfixes.update_journal(
                deps.cache_dir, lines, hotfixes.tracked_tables(_rules(deps)), new["build"], deps.now()
            )
            if added:
                tables = sorted({str(e["table"]) for e in added})
                events.append(
                    {
                        "kind": "hotfixes",
                        "detail": f"{len(added)} correctif(s) nouveau(x) : {', '.join(tables)}",
                        "actions": [_action("forever hotfixes --since-install", False, "tables et entités touchées")],
                    }
                )
    elif "hotfix_log" in old:
        new["hotfix_log"] = old["hotfix_log"]
    logs_dir = wow / "Logs"
    names = sorted(p.name for p in logs_dir.glob("WoWCombatLog-*.txt")) if logs_dir.is_dir() else []
    new["combat_logs"] = names
    fresh = sorted(set(names) - set(old.get("combat_logs", [])))
    if fresh:
        events.append(
            {
                "kind": "combat_logs",
                "detail": f"{len(fresh)} journal(aux) de combat à mesurer",
                "actions": [
                    _action(f'forever logs measure "{logs_dir}"', False, "mesures des journaux"),
                    _action("forever measures refresh", False, "mise à jour proposée des mesures"),
                ],
            }
        )
    svs: dict[str, int] = {}
    for path in sorted((wow / "WTF" / "Account").glob("*/SavedVariables/*.lua")):
        if path.name in SV_NAMES:
            svs[path.relative_to(wow).as_posix()] = path.stat().st_mtime_ns
    new["saved_variables"] = svs
    touched = sorted(k for k, v in svs.items() if old.get("saved_variables", {}).get(k) != v)
    if touched:
        events.append(
            {
                "kind": "saved_variables",
                "detail": f"{len(touched)} sauvegarde(s) d'addon modifiée(s)",
                "actions": [_action("forever profile import --dry-run", False, "profil depuis les sauvegardes")],
            }
        )
    _write(state_path, new)
    result = {"events": events, "wow_dir": str(wow), "checked_at": format_utc(deps.now())}
    if report:
        _write(deps.cache_dir.joinpath(*REPORT), result)
    return result


def watch_line(deps: Deps) -> str | None:
    """Ligne compacte de la session quand quelque chose a changé depuis le dernier passage (build du client) ou
    qu'un rapport de la tâche planifiée attend ; None sinon. Ne lève jamais."""
    try:
        wow = deps.wow_dir
        if wow is None or not wow.is_dir():
            return None
        old = _read(deps.cache_dir.joinpath(*STATE))
        parts: list[str] = []
        build = read_build_info(wow)
        if build is not None and old and build.build != old.get("build"):
            parts.append(f"client {build.build} installé")
        pending = _read(deps.cache_dir.joinpath(*REPORT)).get("events", [])
        if pending and not parts:
            parts += [str(e.get("detail")) for e in pending[:3]]
        if not parts:
            return None
        return ("Veille : " + " ; ".join(parts) + " : `forever watch` pour le détail").replace("\n", " ")
    except Exception:  # noqa: BLE001 : un hook ne doit jamais gêner la session
        return None
