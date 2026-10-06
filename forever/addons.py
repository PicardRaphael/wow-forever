"""Versions et empreintes des addons de données installés (`forever addons status`, T08b, bloc D, décision 124).

Pour chaque addon suivi : version du `.toc` (le `_Camelot.toc` d'abord), empreinte de ses fichiers de données
(`.lua` et `.json`, hors `.bak`, dans son dossier et ceux de ses modules), relevé précédent dans
`<cache>/addons/state.json`, statut `nouveau`, `inchangé`, `changé` ou `absent`. La version seule ne suffit pas :
AtlasLoot change de contenu à chaîne de version identique. Un fichier dont la taille et la date n'ont pas changé
n'est pas relu (empreinte du relevé précédent). Seul Questie a un lecteur : ses agrégats (PNJ, quêtes, XP des quêtes)
sont comparés au relevé précédent ; pour les autres, les fichiers ajoutés, retirés ou modifiés seulement.

Lecture locale seulement ; aucune valeur de jeu dans ce module ni dans le dépôt (les agrégats restent dans le cache)."""

from __future__ import annotations

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
    "ZoneLevelForever": AddonSpec(("ZoneLevelForever",), "lecteur à venir (décision 133)"),
    "Auctionator": AddonSpec(("Auctionator",), "forever/pipeline/auctionator.py (SavedVariables)"),
    "ForeverLogger": AddonSpec(("ForeverLogger",), "forever/pipeline/addon_sv.py (SavedVariables)"),
    "ForeverBestiary": AddonSpec(  # CH0 : bêtes, carte communautaire, guide de l'entraînement des familiers
        ("ForeverBestiary",),
        "forever/pipeline/bestiary.py",
        ("forever/data/<version>/pets.json (recoupement)", "forever/data/<version>/pet_rules.json (Guide.lua)"),
        "forever pets crosscheck, puis relire Data/Guide.lua et comparer pet_rules.json",
    ),
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
    return {"addons_dir": str(root) if root else None, "saved": save, "addons": report}


def fingerprint_folder(folder: Path) -> str:
    """Empreinte d'un dossier d'addon (méthode de `fingerprint`), sans relevé précédent."""
    return fingerprint(_files(folder.parent, [folder], {}))


# --- T08d, bloc D : addons d'interface, addons non inventoriés, version de contenu, inventaire -----------------

UI_ADDONS: tuple[str, ...] = ("EllesmereUI*", "Leatrix_Maps", "ForeverMapFix")  # notés sans lecture hors du .toc


def content_version(name: str, folder: Path) -> dict[str, Any] | None:
    """Version du contenu portée par les données de l'addon (Talents Forever, Forever Companion), sinon None."""
    raise NotImplementedError


def untracked_addons(addons_dir: Path) -> list[dict[str, Any]]:
    """Dossiers ni suivis ni modules d'un addon suivi : `interface`, `pas_un_addon` ou `non_inventorié`."""
    raise NotImplementedError


def inventory(folder: Path) -> dict[str, Any]:
    """Métadonnées du `.toc`, licence, fichiers et empreintes, en-têtes de génération, clés des tables globales ;
    aucune valeur, rien n'est écrit."""
    raise NotImplementedError
