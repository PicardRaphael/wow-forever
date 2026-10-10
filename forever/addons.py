"""Versions et empreintes des addons de données installés (`forever addons status`, T08b, bloc D, décision 124).

Pour chaque addon suivi : version du `.toc` (le `_Camelot.toc` d'abord), empreinte de ses fichiers de données
(`.lua` et `.json`, hors `.bak`, dans son dossier et ceux de ses modules), relevé précédent dans
`<cache>/addons/state.json`, statut `nouveau`, `inchangé`, `changé` ou `absent`. La version seule ne suffit pas :
AtlasLoot change de contenu à chaîne de version identique. Un fichier dont la taille et la date n'ont pas changé
n'est pas relu (empreinte du relevé précédent). Seul Questie a un lecteur : ses agrégats (PNJ, quêtes, XP des quêtes)
sont comparés au relevé précédent ; pour les autres, les fichiers ajoutés, retirés ou modifiés seulement.

Lecture locale seulement ; aucune valeur de jeu dans ce module ni dans le dépôt (les agrégats restent dans le cache)."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.timefmt import format_utc

STATE_NAME = "state.json"
SCHEMA_VERSION = 1
DATA_SUFFIXES = (".lua", ".json")


@dataclass(frozen=True)
class AddonSpec:
    folders: tuple[str, ...]  # dossier principal puis motifs des modules
    reader: str  # lecteur du projet, ou tranche qui l'écrira
    depends: tuple[str, ...] = ()  # agrégats du dépôt qui en dépendent
    action: str = ""  # commande proposée quand l'addon change


DATA_ADDONS: Mapping[str, AddonSpec] = {
    "Questie": AddonSpec(
        ("Questie",),
        "forever/pipeline/questie.py",
        ("forever/data/<version>/monsters.json questie_correction", "consultations zones et XP des quêtes"),
        "forever measures refresh (relire et proposer la mise à jour de monsters.json)",
    ),
    "AtlasLootClassic": AddonSpec(("AtlasLootClassic", "AtlasLootClassic_*"), "lecteur en DJ1"),
    "ForeverDungeonJournal": AddonSpec(("ForeverDungeonJournal",), "lecteur en DJ1"),
    "GearQuestForever": AddonSpec(("GearQuestForever", "GearQuestForever_*"), "lecteur en DJ1 (recoupement)"),
    "ForeverGuide": AddonSpec(("ForeverGuide",), "lecteur à venir (décision 133)"),
    "LegacyForever": AddonSpec(("LegacyForever",), "lecteur en LG1"),
    # Décision 228 : ZoneLevelForever renommé par son auteur (« Formerly Zone Level »), même table de zones
    "ZoneInfoForever": AddonSpec(("ZoneInfoForever",), "lecteur à venir (décision 133)"),
    "Auctionator": AddonSpec(("Auctionator",), "forever/pipeline/auctionator.py (SavedVariables)"),
    "ForeverBestiary": AddonSpec(  # CH0 : bêtes, carte communautaire, guide de l'entraînement des familiers
        ("ForeverBestiary",),
        "forever/pipeline/bestiary.py",
        ("forever/data/<version>/pets.json (recoupement)", "forever/data/<version>/pet_rules.json (Guide.lua)"),
        "forever pets crosscheck, puis relire Data/Guide.lua et comparer pet_rules.json",
    ),
    # T08d : avancé de FA1 (décision 172), version de contenu dans Data.lua ; FA1 (décision 209) : table de
    # correspondance reconstruite à chaque appel, aucun agrégat du dépôt n'en dépend (plus d'attente addon_data)
    "TalentsForeverBook": AddonSpec(
        ("TalentsForeverBook",),
        "forever/talents_forever.py",
        (),
        "forever talents tf crosscheck",
    ),
    "ForeverCompanion": AddonSpec(("ForeverCompanion",), "inventaire T08d, lecteur à venir"),
    "NaowhForever": AddonSpec(("NaowhForever", "NaowhForever_*"), "lecteur à venir (inventaire proposé en T08d)"),
    # Décision 227 : module d'AtlasLoot Classic Forever (« AtlasLoot Forever [BiS ToolTip] »), base ClassDataBase de
    # listes BiS par classe ; source communautaire, au mieux suppose
    "AtlasBIStooltips": AddonSpec(("AtlasBIStooltips",), "lecteur en T10a (listes BiS de la communauté, suppose)"),
    # Décision 228 (inventaire du 2026-10-10) : origine des données non déclarée pour FojjiCore ; tables générées depuis
    # wago.tools et CMaNGOS pour les deux addons de cjber
    "FojjiCore": AddonSpec(
        ("FojjiCore", "FojjiCore_*"),
        "lecteur à venir (DungeonJournal, SpellRanks : recoupement, au mieux suppose)",
    ),
    "ShortestPathForever": AddonSpec(("ShortestPathForever",), "lecteur à venir (trajets et transports, suppose)"),
    "SkillUpForever": AddonSpec(("SkillUpForever",), "lecteur à venir (paliers des métiers, recoupement du client)"),
}
_VERSION = re.compile(r"^## Version:\s*(.+?)\s*$", re.MULTILINE)


def _version(folder: Path) -> str | None:
    tocs = sorted(folder.glob("*_Camelot.toc")) + sorted(p for p in folder.glob("*.toc") if "_Camelot" not in p.name)
    for toc in tocs:
        try:
            m = _VERSION.search(toc.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if m:
            return m.group(1)
    return None


def _folders(addons_dir: Path, spec: AddonSpec) -> list[Path]:
    found: list[Path] = []
    for pattern in spec.folders:
        found += sorted(p for p in addons_dir.glob(pattern) if p.is_dir() and p not in found)
    return found


def _files(addons_dir: Path, folders: list[Path], previous: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for folder in folders:
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in DATA_SUFFIXES:
                continue
            rel = path.relative_to(addons_dir).as_posix()
            st = path.stat()
            old = previous.get(rel)
            if isinstance(old, dict) and old.get("size") == st.st_size and old.get("mtime") == st.st_mtime_ns:
                out[rel] = old  # court-circuit : taille et date inchangées
                continue
            out[rel] = {
                "size": st.st_size,
                "mtime": st.st_mtime_ns,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    return out


def fingerprint(files: Mapping[str, Mapping[str, Any]]) -> str:
    """SHA-256 de la liste triée des SHA-256 des fichiers, 12 premiers caractères (`tasks/inventaire-addons.md`)."""
    joined = "\n".join(sorted(str(f["sha256"]) for f in files.values()))
    return hashlib.sha256(joined.encode("ascii")).hexdigest()[:12]


def _questie_aggregates(folder: Path) -> dict[str, Any]:
    """PNJ (niveaux et PV), nombre de quêtes et de quêtes à XP : agrégats gardés dans le cache, jamais dans le dépôt."""
    from forever.pipeline.questie import read_questie

    db = read_questie(folder)
    npcs = {str(n.id): [n.min_level, n.max_level, n.min_level_health, n.max_level_health] for n in db.npcs().values()}
    quests = db.quests()
    with_xp = sum(1 for q in quests if db.quest_xp(q) is not None)
    return {"version": db.info.version, "npcs": npcs, "quests": len(quests), "quests_with_xp": with_xp}


def _aggregate_diff(old: Mapping[str, Any] | None, new: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not old:
        return []
    out: list[dict[str, Any]] = []
    a, b = old.get("npcs", {}), new.get("npcs", {})
    out += [{"kind": "npc_removed", "id": int(k)} for k in sorted(set(a) - set(b), key=int)]
    out += [{"kind": "npc_added", "id": int(k)} for k in sorted(set(b) - set(a), key=int)]
    out += [{"kind": "npc_changed", "id": int(k)} for k in sorted(set(a) & set(b), key=int) if a[k] != b[k]]
    for key in ("quests", "quests_with_xp", "version"):
        if old.get(key) != new.get(key):
            out.append({"kind": key, "before": old.get(key), "after": new.get(key)})
    return out


def state_path(cache_dir: Path) -> Path:
    return cache_dir / "addons" / STATE_NAME


def load_state(cache_dir: Path) -> dict[str, Any]:
    try:
        doc = json.loads(state_path(cache_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc.get("addons", {}) if isinstance(doc, dict) else {}


def addons_status(deps: Deps, *, save: bool = False, addons_dir: Path | None = None) -> dict[str, Any]:
    """Relevé des addons suivis ; `save` enregistre le relevé (sinon rien n'est écrit)."""
    root = addons_dir or (deps.wow_dir / "Interface" / "AddOns" if deps.wow_dir else None)
    previous = load_state(deps.cache_dir)
    report: list[dict[str, Any]] = []
    state: dict[str, Any] = {}
    for name, spec in DATA_ADDONS.items():
        old = previous.get(name) or {}
        folders = _folders(root, spec) if root is not None and root.is_dir() else []
        if not folders:
            report.append({"name": name, "status": "absent", "reader": spec.reader})
            if old:
                state[name] = old
            continue
        assert root is not None
        files = _files(root, folders, old.get("files", {}))
        fp = fingerprint(files)
        version = _version(folders[0])
        before = set(old.get("files", {}))
        changes = {
            "added": sorted(set(files) - before),
            "removed": sorted(before - set(files)),
            "modified": sorted(k for k in set(files) & before if files[k]["sha256"] != old["files"][k].get("sha256")),
        }
        status = "nouveau" if not old else ("inchangé" if fp == old.get("fingerprint") else "changé")
        entry: dict[str, Any] = {
            "name": name,
            "status": status,
            "version": version,
            "previous_version": old.get("version"),
            "fingerprint": fp,
            "previous_fingerprint": old.get("fingerprint"),
            "files": changes if old else {"added": [], "removed": [], "modified": []},
            "count": len(files),
            "reader": spec.reader,
        }
        record: dict[str, Any] = {"version": version, "fingerprint": fp, "files": files}
        if name == "Questie":
            cached = old.get("aggregates")
            aggregates: dict[str, Any] = (
                cached if status == "inchangé" and isinstance(cached, dict) else _questie_aggregates(folders[0])
            )
            entry["aggregates_diff"] = _aggregate_diff(old.get("aggregates"), aggregates)
            record["aggregates"] = aggregates
        if name in CONTENT_VERSIONS:
            cached_cv = old.get("content_version")
            cv = cached_cv if status == "inchangé" and cached_cv else content_version(name, folders[0])
            entry["content_version"] = cv
            entry["previous_content_version"] = old.get("content_version")
            record["content_version"] = cv
        if name == "TalentsForeverBook" and status != "inchangé":
            entry["recheck"] = _talents_recheck(deps, folders[0])
        if status == "changé" and spec.depends:
            # un agrégat du dépôt en dépend : attente d'accord proposée (forever update, T08d)
            entry["proposal"] = {"kind": "addon_data", "depends": list(spec.depends), "action": spec.action}
        if spec.depends:
            entry["depends"] = list(spec.depends)
        if spec.action:
            entry["action"] = spec.action
        report.append(entry)
        state[name] = record
    if save:
        path = state_path(deps.cache_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"schema_version": SCHEMA_VERSION, "saved_at": format_utc(deps.now()), "addons": state}
        path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    present = root is not None and root.is_dir()
    untracked = untracked_addons(root) if present and root is not None else []
    own = own_addons(root) if present and root is not None else []
    return {
        "addons_dir": str(root) if root else None,
        "saved": save,
        "addons": report,
        "untracked": untracked,
        "own": own,
    }


def fingerprint_folder(folder: Path) -> str:
    """Empreinte d'un dossier d'addon (méthode de `fingerprint`), sans relevé précédent."""
    return fingerprint(_files(folder.parent, [folder], {}))


# --- T08d, bloc D : addons d'interface, addons non inventoriés, version de contenu, inventaire -----------------

# Notés sans lecture hors du .toc ; décision 228 : addons d'interface seule de l'inventaire du 2026-10-10
UI_ADDONS: tuple[str, ...] = (
    "EllesmereUI*",
    "Leatrix_Maps",
    "ForeverMapFix",
    "AppelSwingsForever",
    "BetterForeverChat",
    "DeleteCheapestItem",
    "ExtendedVendorForever",
    "FontMagic",
    "ForeverMove",
    "Simulationcraft",
)

# Décision 227 : addons du projet et de l'utilisateur, jamais « à inventorier » ni lus comme sources (un seul relevé
# de version par groupe) ; la réserve d'emplacements et les sondes vont avec ForeverBridge.
OWN_ADDONS: Mapping[str, tuple[tuple[str, ...], str]] = {
    "ForeverLogger": (
        ("ForeverLogger",),
        "addon du dépôt (addon/), SavedVariables lues par forever/pipeline/addon_sv.py",
    ),
    "ForeverBridge": (("ForeverBridge",), "pont de P06a, installé par forever bridge install"),
    "RaphCompletionist": (
        ("RaphCompletionist",),
        "addon de l'utilisateur, dossier de la conversation « addons » prévue en P06b",
    ),
}
BRIDGE_SLOTS = "ForeverBridge_S[0-9][0-9][0-9]"  # réserve d'emplacements (forever/bridge/slots.py)
BRIDGE_PROBES = "ForeverBridge_Probe*"  # sondes (forever/bridge/install.py)
# Addons connus et exclus des données du projet : signalés comme tels, jamais « à inventorier ».
EXCLUDED_ADDONS: Mapping[str, str] = {
    "RXPGuides": "RestedXP : guides payants, licence non commerciale, exclu des données du projet (décision 227)",
    "Tamed": "données de Classic seulement (tables de Forever vides), pas pour Forever (décision 228)",
    "AlexAtlasLoot": (
        "butin de Forever relevé par les joueurs, mais sa licence interdit d'en copier les tables dans une base de "
        "données : exclu jusqu'à la décision de l'utilisateur (décision 228)"
    ),
}
# Dossiers qui ne sont pas des addons, jamais lus comme tels, même avec un .toc.
NOT_ADDONS: Mapping[str, str] = {
    "ForeverCompletionist": "projet de développement de l'utilisateur (outil d'inventaire), à déplacer hors des addons",
}


CONTENT_VERSIONS = ("TalentsForeverBook", "ForeverCompanion")
_TOC_FIELD = re.compile(r"^##\s*([\w-]+)\s*:\s*(.*?)\s*$", re.MULTILINE)
_GLOBAL_TABLE = re.compile(r"^([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*=\s*\{", re.MULTILINE)
_LICENSE_FILES = ("LICENSE*", "LICENCE*", "COPYING*")


def content_version(name: str, folder: Path) -> dict[str, Any] | None:
    """Version du contenu portée par les données de l'addon (Talents Forever, Forever Companion), sinon None.

    Lecture par `lua_table`, jamais par du Lua exécuté ; None si le fichier manque ou ne se lit pas."""
    from forever.pipeline.lua_table import parse_lua_value_at

    try:
        if name == "TalentsForeverBook":
            from forever.pipeline.talents_forever import read_head_and_doc

            head, _ = read_head_and_doc(folder / "Data.lua")
            return head
        if name == "ForeverCompanion":
            text = (folder / "Data" / "Meta.lua").read_text(encoding="utf-8")
            meta, _ = parse_lua_value_at(text, text.index("{", text.index("ForeverCompanionData.meta =")))
            return {k: meta.get(k) for k in ("dataVersion", "updated")} if isinstance(meta, dict) else None
    except (OSError, ValueError, KeyError):
        return None
    return None


def _talents_recheck(deps: Deps, folder: Path) -> dict[str, Any] | None:
    """Recoupement des arbres de Talents Forever avec `classes.json` installé (comptes par nœud) et, depuis FA1, écarts
    de la table de correspondance, génération des codes et état de l'export par classe (possible ou bloqué, talents
    en cause)."""
    from forever.pipeline.talents_forever import crosscheck
    from forever.store import current_identity
    from forever.talents_forever import crosscheck_report, export_states, load_addon

    try:
        version = current_identity(deps.data_dir).game_version
        totals: dict[str, Any] = crosscheck(folder / "Data.lua", deps.data_dir / version / "classes.json")["totals"]
        addon = load_addon(deps, folder=folder)
        if addon is not None:
            totals.update(crosscheck_report(addon)["totals"])
            totals["code_version"] = addon.head.get("codeVersion")
            totals["code_version_supported"] = addon.supported
            totals["export"] = export_states(addon)
    except Exception:  # noqa: BLE001 : la relecture ne doit jamais casser le relevé
        return None
    return totals


def _matches(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def untracked_addons(addons_dir: Path) -> list[dict[str, Any]]:
    """Dossiers ni suivis ni modules d'un addon suivi : `interface`, `pas_un_addon` ou `non_inventorié`.

    Seul le `.toc` est lu (version) ; aucun autre fichier d'un addon d'interface n'est ouvert."""
    tracked = tuple(p for spec in DATA_ADDONS.values() for p in spec.folders)
    out: list[dict[str, Any]] = []
    for folder in sorted(p for p in addons_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if _matches(folder.name, tracked) or _own(folder.name) is not None:
            continue
        if folder.name in NOT_ADDONS:
            out.append(
                {"folder": folder.name, "status": "pas_un_addon", "version": None, "note": NOT_ADDONS[folder.name]}
            )
            continue
        if folder.name in EXCLUDED_ADDONS:
            note = EXCLUDED_ADDONS[folder.name]
            out.append({"folder": folder.name, "status": "exclu", "version": _version(folder), "note": note})
            continue
        if ".bak" in folder.name.lower():  # copie de sauvegarde d'un addon (ForeverLogger.bak-<date>) : jamais lue
            out.append({"folder": folder.name, "status": "sauvegarde", "version": None})
            continue
        if not any(folder.glob("*.toc")):
            out.append({"folder": folder.name, "status": "pas_un_addon", "version": None})
        elif _matches(folder.name, UI_ADDONS):
            out.append({"folder": folder.name, "status": "interface", "version": _version(folder)})
        else:
            out.append(
                {
                    "folder": folder.name,
                    "status": "non_inventorié",
                    "version": _version(folder),
                    "action": f"forever addons inventory {folder.name}",
                }
            )
    return out


def _own(name: str) -> str | None:
    """Groupe de l'addon du projet auquel appartient le dossier (`ForeverBridge` pour un emplacement ou une sonde)."""
    if _matches(name, (BRIDGE_SLOTS, BRIDGE_PROBES)):
        return "ForeverBridge"
    return next((group for group, (folders, _) in OWN_ADDONS.items() if _matches(name, folders)), None)


def own_addons(addons_dir: Path) -> list[dict[str, Any]]:
    """Addons du projet présents, un par groupe : version du `.toc` principal, emplacements et sondes du pont."""
    groups: dict[str, dict[str, Any]] = {}
    for folder in sorted(p for p in addons_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        group = _own(folder.name)
        if group is None:
            continue
        entry = groups.setdefault(group, {"folder": group, "version": None, "note": OWN_ADDONS[group][1]})
        if folder.name == group:
            entry["version"] = _version(folder)
        elif _matches(folder.name, (BRIDGE_SLOTS,)):
            entry["slots"] = entry.get("slots", 0) + 1
        elif _matches(folder.name, (BRIDGE_PROBES,)):
            entry["probes"] = entry.get("probes", 0) + 1
    return [groups[g] for g in sorted(groups)]


def _toc(folder: Path) -> dict[str, str]:
    tocs = sorted(folder.glob(f"{folder.name}*.toc")) or sorted(folder.glob("*.toc"))
    if not tocs:
        return {}
    text = tocs[0].read_text(encoding="utf-8", errors="replace")
    return {m.group(1): m.group(2) for m in _TOC_FIELD.finditer(text)}


def _header(text: str) -> list[str]:
    """Commentaires de tête (en-tête de génération), cinq lignes au plus."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if out:
                break
            continue
        if not stripped.startswith("--"):
            break
        comment = stripped.lstrip("-").strip()
        if comment:
            out.append(comment)
    return out[:5]


def _global_keys(text: str) -> dict[str, list[str]]:
    """Clés de premier niveau des tables globales affectées en tête de ligne (aucune valeur)."""
    from forever.pipeline.lua_table import parse_lua_value_at

    out: dict[str, list[str]] = {}
    for m in _GLOBAL_TABLE.finditer(text):
        try:
            value, _ = parse_lua_value_at(text, m.end() - 1)
        except ValueError:
            continue
        if isinstance(value, dict):
            out[m.group(1)] = sorted(str(k) for k in value)
    return out


def inventory(folder: Path) -> dict[str, Any]:
    """Métadonnées du `.toc`, licence, fichiers et empreintes, en-têtes de génération, clés des tables globales ;
    aucune valeur, rien n'est écrit."""
    toc = _toc(folder)
    license_files = sorted(p.name for pattern in _LICENSE_FILES for p in folder.glob(pattern) if p.is_file())
    license: dict[str, Any] | None = None
    if license_files:
        license = {"source": license_files[0], "name": None}
    elif toc.get("X-License"):
        license = {"source": "X-License", "name": toc["X-License"]}
    files = _files(folder.parent, [folder], {})
    listed: list[dict[str, Any]] = []
    globals_: dict[str, list[str]] = {}
    for rel, meta in sorted(files.items()):
        path = folder.parent / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        listed.append(
            {
                "path": path.relative_to(folder).as_posix(),
                "size": meta["size"],
                "sha256": meta["sha256"],
                "header": _header(text),
            }
        )
        if path.suffix.lower() == ".lua":
            globals_.update(_global_keys(text))
    saved = [s.strip() for s in toc.get("SavedVariables", "").split(",") if s.strip()]
    return {
        "folder": folder.name,
        "toc": toc,
        "saved_variables": saved,
        "license": license,
        "files": {"count": len(listed), "total_size": sum(f["size"] for f in listed), "list": listed},
        "fingerprint": fingerprint(files),
        "globals": globals_,
    }
