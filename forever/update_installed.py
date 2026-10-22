"""Historique des installations de la veille (décision 295) : chaque écriture fusionnée dans `main` par
`forever update` laisse une fiche `<cache>/update/installed/<id>.json` (version, révision, commit, ce qui a changé
en mots de joueur, état). La fiche nourrit la carte « Mis à jour » du pont et `forever update status`, et porte la
commande « Annuler » (`forever update undo <id>`). Une fiche annulée empêche la veille de réinstaller le même
contenu ; un contenu nouveau s'installe normalement.

Ce module ne fait ni git ni réseau : il lit et écrit des fiches, et traduit un rejeu en phrases."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import InvalidArgumentError

INSTALLED_STATES = ("installée", "annulée")
# Contextes des cas rejoués (`forever/replay.py`, « leveling-20 ») en mots de joueur.
CONTEXT_FR = {
    "leveling": "leveling",
    "dungeon": "donjon",
    "raid": "raid",
    "pvp-bg": "PvP en champ de bataille",
    "pvp-world": "PvP sauvage",
    "sim-leveling": "simulation du leveling",
}
CHOICE_FR = {"rotation": "rotation", "armor": "armure", "aoe_filler": "sort de zone"}
CHANGES_SHOWN = 8  # phrases gardées par fiche ; le reste est compté


def installed_dir(cache_dir: Path) -> Path:
    return cache_dir / "update" / "installed"


def _path(cache_dir: Path, record_id: str) -> Path:
    if not record_id or any(c in record_id for c in "/\\") or record_id.startswith("."):
        raise InvalidArgumentError(f"Identifiant d'installation invalide : {record_id!r}.", "`forever update status`")
    return installed_dir(cache_dir) / f"{record_id}.json"


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(path: Path, doc: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def save_installed(cache_dir: Path, record: Mapping[str, Any]) -> Path:
    """Écrit (ou remplace) la fiche d'une installation ; l'historique n'est jamais élagué."""
    path = _path(cache_dir, str(record["id"]))
    _write(path, record)
    return path


def load_installed(cache_dir: Path, record_id: str) -> dict[str, Any]:
    doc = _read(_path(cache_dir, record_id))
    if not isinstance(doc, dict):
        raise InvalidArgumentError(
            f"Aucune installation {record_id} dans l'historique de la veille.",
            "`forever update status` liste les installations et leur identifiant",
        )
    return doc


def update_installed(cache_dir: Path, record_id: str, **fields: Any) -> dict[str, Any]:
    doc = {**load_installed(cache_dir, record_id), **fields}
    save_installed(cache_dir, doc)
    return doc


def list_installed(cache_dir: Path) -> list[dict[str, Any]]:
    """Fiches de l'historique, de la plus récente à la plus ancienne."""
    folder = installed_dir(cache_dir)
    docs = [d for p in sorted(folder.glob("*.json")) if isinstance(d := _read(p), dict)] if folder.is_dir() else []
    return sorted(docs, key=lambda d: (str(d.get("installed_at") or ""), str(d.get("id"))), reverse=True)


def undone(cache_dir: Path, record_id: str) -> dict[str, Any] | None:
    """Fiche annulée de ce contenu (même identifiant), sinon None : la veille ne le réinstalle pas."""
    doc = _read(_path(cache_dir, record_id)) if record_id else None
    return doc if isinstance(doc, dict) and doc.get("state") == "annulée" else None


def notices(cache_dir: Path) -> list[dict[str, Any]]:
    """Installations à signaler (carte « Mis à jour ») : ni masquées ni annulées, plus récentes d'abord."""
    return [d for d in list_installed(cache_dir) if d.get("state") == "installée" and not d.get("dismissed")]


def _case_label(engine: str, case: str) -> str:
    context, _, level = case.rpartition("-")
    what = CONTEXT_FR.get(context, context or case)
    who = "Mage" if engine.startswith("mage") else engine
    return f"build {who} {what} niveau {level}" if level.isdigit() else f"build {who} {case}"


def _talent_lines(before: Mapping[str, Any], after: Mapping[str, Any], names: Mapping[str, str]) -> list[str]:
    out = []
    for key in sorted(set(before) | set(after), key=lambda k: names.get(k, k)):
        a, b = before.get(key, 0) or 0, after.get(key, 0) or 0
        if a != b:
            out.append(f"{names.get(key, key)} passe de {a} à {b}")
    return out


def _choice_lines(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    out = []
    for situation in sorted(set(before) | set(after)):
        old, new = before.get(situation) or {}, after.get(situation) or {}
        for field in sorted(set(old) | set(new)):
            if old.get(field) != new.get(field) and field in CHOICE_FR:
                where = situation.rpartition("_")[2] if "_" in situation else situation
                out.append(f"{CHOICE_FR[field]} ({where}) : {old.get(field)} → {new.get(field)}")
    return out


def advice_changes(replayed: Mapping[str, Any], names: Mapping[str, str]) -> list[str]:
    """Conseils changés par une installation, en mots de joueur : « build Mage donjon niveau 20 : Frost Warding passe
    de 0 à 2 ». `replayed` : rejeu ciblé (`{moteur: {cas: {"avant": conseil, "après": conseil}}}`) ; `names` : clé
    du talent → nom en jeu. Un cas non rejoué ou inchangé ne donne rien."""
    lines: list[str] = []
    for engine in sorted(replayed):
        cases = replayed[engine]
        if not isinstance(cases, Mapping):
            continue
        for case in sorted(cases):
            sides = cases[case]
            if not isinstance(sides, Mapping):
                continue
            before, after = sides.get("avant"), sides.get("après")
            if not isinstance(before, Mapping) or not isinstance(after, Mapping) or before == after:
                continue
            if before.get("rejoué") is False or after.get("rejoué") is False:
                continue
            parts = _talent_lines(before.get("talents") or {}, after.get("talents") or {}, names)
            parts += _choice_lines(before.get("choices") or {}, after.get("choices") or {})
            if parts:
                lines.append(f"{_case_label(engine, case)} : {', '.join(parts)}")
    return lines


def notice_lines(record: Mapping[str, Any]) -> list[str]:
    """Ce qu'une installation a changé, pour la carte et `forever update status` : conseils changés (rejeu), sinon
    résumé des valeurs ; puis les notes de la règle (valeur faite à la main remplacée…)."""
    changes: Sequence[str] = record.get("changes") or []
    lines = list(changes[:CHANGES_SHOWN])
    if len(changes) > CHANGES_SHOWN:
        lines.append(f"et {len(changes) - CHANGES_SHOWN} autre(s) conseil(s) changé(s)")
    replay = record.get("replay")
    if not changes:
        if replay == "en cours":
            lines.append("conseils en cours de comparaison")
        elif replay == "aucun changement":
            lines.append("aucun conseil de build ne change")
        summary = str(record.get("summary") or "")
        if summary:
            lines.append(summary)
    lines += [str(n) for n in record.get("notes") or []]
    return lines


def title(record: Mapping[str, Any]) -> str:
    what = "mesure des journaux" if record.get("kind") == "measures" else "données"
    return f"{what} {record.get('version')} r{record.get('revision')}"
