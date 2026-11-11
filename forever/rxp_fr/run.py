"""Orchestration de FR1 : `forever rxp traduire` (CLI) et sous-étape de la veille (`forever update`, étape
`addons`). Lecture locale seule (addons, tables du client en cache, Questie) ; aucune connexion réseau, aucune
traduction automatique (question Q1)."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.rxp_fr.build import GENERATOR_VERSION, generate_file, marker_info, source_sha
from forever.rxp_fr.install import originals, restore_originals, write_guides
from forever.rxp_fr.memory import Memory, memory_path
from forever.rxp_fr.names import NameTable, client_layer, questie_layer
from forever.rxp_fr.source import (
    EN_DIR,
    FR_DIR,
    english_files,
    glossary,
    guide_bodies,
    header,
    read_text,
    restedxp_french,
    rxp_version,
    targets,
)
from forever.rxp_fr.translator import Translator
from forever.rxp_fr.validate import validate_file

ASSUMPTIONS = (
    (
        "texte des guides traduit depuis l'anglais de RestedXP : phrases relevées dans ses propres traductions "
        "(restedxp), phrases types (motif), traduites en session (traduit) ou corrigées à la main (manuel) ; le "
        "reste reste en anglais"
    ),
    (
        "noms officiels : glossaire de RestedXP, tables frFR du client (certain), Questie frFR (suppose) ; un nom "
        "sans source reste en anglais"
    ),
    (
        "guides que RestedXP a traduits recopiés tels quels ; usage personnel, texte de RestedXP (CC BY-NC-SA 4.0) "
        "hors du dépôt"
    ),
)


def addons_dir(deps: Deps) -> Path:
    wow = deps.wow_dir
    addons = wow / "Interface" / "AddOns" if wow is not None else None
    if addons is None or not addons.joinpath(*EN_DIR).is_dir():
        raise InvalidArgumentError(
            f"Guides RestedXP pour Forever introuvables ({addons.joinpath(*EN_DIR) if addons else 'client absent'}).",
            "installer RXPGuides dans le dossier des addons du jeu, ou régler FOREVER_WOW_DIR",
        )
    return addons


def client_dir(deps: Deps) -> Path | None:
    """Tables du client en cache (`<cache>/wago/<version>/`) qui ont des noms frFR : la version des données
    installées si elle en a, sinon la plus récente."""
    from forever.pipeline.builds import version_key
    from forever.store import current_identity

    root = deps.cache_dir / "wago"
    found = [p for p in root.iterdir() if (p / "frFR").is_dir()] if root.is_dir() else []
    if not found:
        return None
    try:
        installed = current_identity(deps.data_dir).game_version
    except Exception:  # noqa: BLE001 : la version installée n'est qu'une préférence
        installed = None
    for path in found:
        if path.name == installed:
            return path

    def key(path: Path) -> tuple[int, ...]:
        try:
            return version_key(path.name)
        except Exception:  # noqa: BLE001
            return (0,)

    return max(found, key=key)


def _import(memory: Memory, path: Path, date: str) -> dict[str, int]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InvalidArgumentError(
            f"Lot de traductions illisible ({path}) : {exc}.", "donner un JSON {gabarit anglais: gabarit français}"
        ) from exc
    if not isinstance(doc, dict):
        raise InvalidArgumentError("Lot de traductions : objet JSON attendu.", "{gabarit anglais: gabarit français}")
    counts = Counter(
        "accepted" if isinstance(fr, str) and memory.put(str(en), fr, "traduit", date=date) else "refused"
        for en, fr in doc.items()
    )
    return {"accepted": counts["accepted"], "refused": counts["refused"]}


def translate_addons(
    deps: Deps,
    *,
    translator: Translator | None = None,
    simulate: bool = False,
    importing: Path | None = None,
    write_id: str | None = None,
) -> dict[str, Any]:
    """Génère, valide et (sauf simulation) écrit les fichiers français manquants ; rend le rapport."""
    addons = addons_dir(deps)
    date = deps.now().date().isoformat()
    mem_file = memory_path(deps)
    memory = Memory.load(mem_file)
    imported = _import(memory, importing, date) if importing is not None else None
    saved = originals(addons, deps.cache_dir)
    rxp = glossary(addons, saved)
    for en, fr in rxp.phrases.items():
        memory.put(en, fr, "restedxp", date=date)
    csv_dir = client_dir(deps)
    names = NameTable(
        [
            ("restedxp", rxp.names),
            ("client", client_layer(csv_dir) if csv_dir is not None else {}),
            ("questie", questie_layer(addons / "Questie")),
        ]
    )
    found = targets(addons, saved)
    version = rxp_version(addons)
    outputs: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    phrases: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    missing_phrases: set[str] = set()
    missing_names: set[tuple[str, str]] = set()
    for target in found:
        names.missing.clear()
        names.used.clear()
        english = read_text(target.en_path)
        text, report = generate_file(
            english,
            restedxp_french(addons, target.rel, saved),
            names=names,
            memory=memory,
            translator=translator,
            meta={"rxp_version": version},
            date=date,
        )
        outputs[target.rel] = text
        phrases.update(report.phrases)
        sources.update(report.names)
        missing_phrases.update(report.missing_phrases)
        missing_names.update((k, str(n)) for k, n in report.missing_names)
        rows.append(
            {
                "file": target.rel,
                "english_guides": target.english,
                "restedxp_guides": target.french,
                **{k: v for k, v in report.as_dict().items() if k not in ("missing_phrases", "missing_names")},
                "errors": [],
            }
        )
    english_names: set[str] = set()
    french_names: dict[str, set[str]] = {}
    for rel, path in english_files(addons):
        english_names |= {n.strip() for b in guide_bodies(read_text(path)) for n in header(b, "name")}
        fr_path = addons.joinpath(*FR_DIR, rel)
        text = outputs.get(rel) or (read_text(fr_path) if fr_path.is_file() else "")
        french_names[rel] = {n.strip() for b in guide_bodies(text) for n in header(b, "name")}
    errors: list[str] = []
    for row in rows:
        rel = row["file"]
        known = set().union(*(v for k, v in french_names.items() if k != rel))
        en_text = read_text(addons.joinpath(*EN_DIR, rel))
        theirs = guide_bodies(restedxp_french(addons, rel, saved))
        row["errors"] = validate_file(
            en_text, outputs[rel], known_names=known, english_names=english_names, restedxp=theirs
        )
        errors += [f"{rel} : {e}" for e in row["errors"]]
    if write_id is None:
        digest = hashlib.sha256("".join(f"{r}={source_sha(t)};" for r, t in sorted(outputs.items())).encode())
        write_id = f"rxp-fr-{digest.hexdigest()[:12]}"
    written: list[str] = []
    if not simulate and not errors:
        for rel, text in outputs.items():
            path = addons.joinpath(*FR_DIR, rel)
            if not path.is_file() or read_text(path) != text:
                write_guides(addons, rel, text, deps.cache_dir, write_id)
                written.append(rel)
    if not simulate:
        memory.save(mem_file)
    from forever.provenance import local_provenance

    return {
        "files": rows,
        "written": written,
        "errors": errors,
        "simulation": simulate,
        "write_id": write_id,
        "rxp_version": version,
        "client_tables": str(csv_dir) if csv_dir is not None else None,
        "phrases": dict(phrases),
        "names": dict(sources),
        "memory": dict(memory.origins()),
        "memory_path": str(mem_file),
        "imported": imported,
        "missing_phrases": sorted(missing_phrases),
        "missing_names": [{"kind": k, "name": n} for k, n in sorted(missing_names)],
        "provenance": local_provenance(deps, certainty="probable", assumptions=ASSUMPTIONS),
    }


def cancel(deps: Deps) -> dict[str, Any]:
    """Remet la version de RestedXP de chaque fichier écrit par FR1."""
    from forever.provenance import local_provenance

    addons = addons_dir(deps)
    restored = restore_originals(addons, deps.cache_dir)
    return {
        "restored": restored,
        "provenance": local_provenance(deps, certainty="certain", assumptions=["fichiers de RestedXP remis"]),
    }


def stale(deps: Deps) -> list[str]:
    """Fichiers à régénérer : français manquant chez RestedXP sans fichier FR1, ou fichier FR1 d'une autre source
    anglaise ou d'un autre générateur."""
    wow = deps.wow_dir
    if wow is None:
        return []
    addons = wow / "Interface" / "AddOns"
    if not addons.joinpath(*EN_DIR).is_dir():
        return []
    out: list[str] = []
    for target in targets(addons, originals(addons, deps.cache_dir)):
        if not target.ours:
            out.append(target.rel)
            continue
        info = marker_info(read_text(target.fr_path)) or {}
        if info.get("version") != GENERATOR_VERSION or info.get("source") != source_sha(read_text(target.en_path)):
            out.append(target.rel)
    return out


def watch(deps: Deps, *, dry_run: bool) -> dict[str, Any] | None:
    """Sous-étape de la veille : régénère si besoin ; écrit la fiche « Mis à jour » d'une écriture (annulable)."""
    from forever.update_installed import save_installed

    need = stale(deps)
    if not need:
        return None
    doc = translate_addons(deps, simulate=dry_run)
    if doc["written"] and not dry_run:
        generated = sum(r["generated"] for r in doc["files"])
        copied = sum(r["copied"] for r in doc["files"])
        english = doc["phrases"].get("anglais", 0)
        save_installed(
            deps.cache_dir,
            {
                "id": doc["write_id"],
                "kind": "rxp_fr",
                "version": doc["rxp_version"],
                "revision": None,
                "installed_at": deps.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sha": None,
                "summary": (
                    f"guides RestedXP en français : {', '.join(doc['written'])} ({generated} guide(s) générés, "
                    f"{copied} recopiés de RestedXP, {english} phrase(s) restées en anglais)"
                ),
                "measures": [],
                "notes": [],
                "files": doc["written"],
                "state": "installée",
                "by": "forever update",
                "undo": f"forever update undo {doc['write_id']}",
            },
        )
    return doc
