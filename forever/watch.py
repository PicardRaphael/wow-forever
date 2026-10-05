"""Veille locale du poste (`forever watch`, T08b, bloc G) : hors ligne, rien n'est lancé.

Détecteurs, comparés au dernier passage (`<cache>/watch/state.json`) : build du client (`.build.info`), addons de
données (empreintes, court-circuit par taille et date), correctifs du serveur (`Logs/Hotfix.log`, relu seulement si sa
taille ou sa date change ; journal `hotfixes.json`), nouveaux journaux de combat (`WoWCombatLog-*.txt`) et sauvegardes
modifiées (ForeverLogger, Questie, Auctionator), et (T08c) correctifs du serveur de `Cache/ADB/enUS/DBCache.bin` non
appliqués à la révision installée (analysés seulement si le fichier ou la révision change). Chaque changement porte
les **actions proposées** (commande exacte,
réseau ou non) ; un nouveau build propose `forever notes` (décision 148 : lecture des notes à la main seulement).
`--report` écrit le résumé dans `<cache>/watch/report.json` (tâche planifiée Windows) ; la ligne de démarrage de
session en tire une ligne compacte."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forever.addons import DATA_ADDONS, _files, _folders, fingerprint
from forever.config import Deps
from forever.errors import DataSchemaError
from forever.pipeline import dbcache, hotfixes
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
        tracked = hotfixes.tracked_tables(_rules(deps))
        # sans règles lisibles, le journal n'est pas marqué lu : le passage suivant le relira (il est réécrit au
        # démarrage du client, ses lignes seraient sinon perdues)
        new["hotfix_log"] = stamp if tracked else old.get("hotfix_log")
        if tracked and old.get("hotfix_log") != stamp:
            lines = hotfixes.read_log(log)
            added = hotfixes.update_journal(deps.cache_dir, lines, tracked, new["build"], deps.now())
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
    cache_path = wow.joinpath(*(part.format(locale="enUS") for part in dbcache.DBCACHE_PATH))
    if cache_path.is_file():
        version, sources = _installed(deps)
        st = cache_path.stat()
        cache_stamp: dict[str, Any] = {
            "size": st.st_size,
            "mtime": st.st_mtime_ns,
            "version": version,
            "revision": sources.get("revision"),
        }
        previous = old.get("dbcache", {})
        if {k: previous.get(k) for k in cache_stamp} == cache_stamp:
            new["dbcache"] = previous
        else:
            event = _dbcache_event(deps, cache_path, version, sources)
            new["dbcache"] = {**cache_stamp, "pending": event["pending"] if event else 0}
            if event is not None:
                events.append(event)
    _write(state_path, new)
    result = {"events": events, "wow_dir": str(wow), "checked_at": format_utc(deps.now())}
    if report:
        _write(deps.cache_dir.joinpath(*REPORT), result)
    return result


def _installed(deps: Deps) -> tuple[str | None, dict[str, Any]]:
    from forever.manifest import SOURCES_NAME, version_dirs

    versions = version_dirs(deps.data_dir)
    if not versions:
        return None, {}
    return versions[-1], _read(deps.data_dir / versions[-1] / SOURCES_NAME)


def _dbcache_event(deps: Deps, path: Path, version: str | None, sources: dict[str, Any]) -> dict[str, Any] | None:
    """Correctifs applicables de `DBCache.bin` (tables lues par le pipeline) absents de la révision installée
    (`sources.json`, bloc `hotfixes`) ; un fichier d'un autre build est signalé non applicable."""
    from forever.pipeline.tables import TABLES

    try:
        cache = dbcache.read_dbcache(path)
    except DataSchemaError:  # fichier en cours d'écriture par le client ou tronqué : relu au passage suivant
        return None
    if version is None or not version.endswith(f".{cache.build}"):
        return {
            "kind": "hotfixes_dbcache",
            "pending": 0,
            "detail": f"DBCache.bin du build {cache.build} : correctifs d'un autre build, non applicables "
            f"(version installée {version or 'aucune'})",
            "actions": [_action("forever status", True, "fraîcheur des données et build publié")],
        }
    names = dbcache.table_names(dbcache.known_tables(_rules(deps)))
    applicable = dbcache.effective(cache.entries, names).applicable
    raw_block = sources.get("hotfixes")
    block: dict[str, Any] = raw_block if isinstance(raw_block, dict) else {}
    done = {(a.get("push"), a.get("table"), a.get("rec_id"), a.get("unique_id")) for a in block.get("applied", [])}
    absent = {
        (d.get("push"), d.get("table"), d.get("rec_id")) for d in block.get("listed", {}).get("delete_absent", [])
    }
    pending = [
        (t, r)
        for (t, r), e in applicable.items()
        if t in TABLES and (e.push_id, t, r, e.unique_id) not in done and (e.push_id, t, r) not in absent
    ]
    if not pending:
        return None
    tables = sorted({t for t, _ in pending})
    revision = sources.get("revision")
    when = sources.get("revised_at") or sources.get("collected_at") or "?"
    return {
        "kind": "hotfixes_dbcache",
        "pending": len(pending),
        "detail": f"{len(pending)} correctif(s) du serveur non appliqué(s) depuis la révision {revision} du {when} "
        f"(tables {', '.join(tables[:6])}{'…' if len(tables) > 6 else ''})",
        "actions": [
            _action("forever hotfixes --values", False, "valeurs corrigées, avant et après"),
            _action(f"forever decode --version {version} --hotfixes", False, "candidate avec les correctifs"),
            _action(f"forever diff {version} <candidate>", False, "valeurs changées, attribuées aux correctifs"),
            _action("forever install <candidate>", False, "révision suivante, après accord de l'utilisateur"),
        ],
    }


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
        fixes = old.get("dbcache", {})
        version, sources = _installed(deps)
        if (
            fixes.get("pending")
            and fixes.get("version") == version
            and fixes.get("revision") == sources.get("revision")
        ):
            parts.append(f"{fixes['pending']} correctif(s) du serveur non appliqué(s)")
        pending = [
            e for e in _read(deps.cache_dir.joinpath(*REPORT)).get("events", []) if e.get("kind") != "hotfixes_dbcache"
        ]
        if pending and not parts:
            parts += [str(e.get("detail")) for e in pending[:3]]
        if not parts:
            return None
        return ("Veille : " + " ; ".join(parts) + " : `forever watch` pour le détail").replace("\n", " ")
    except Exception:  # noqa: BLE001 : un hook ne doit jamais gêner la session
        return None
