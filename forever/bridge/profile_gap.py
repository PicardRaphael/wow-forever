"""Écart entre le jeu et le profil joueur (P06b, bloc C, décisions 122 et 235). À chaque message, le pont compare le
contexte relié (`context.Resolved`) au personnage du profil de même nom et royaume (à défaut, de même nom) : classe,
race, faction, niveau, talents et équipement. Un écart ajoute une ligne fixe au message (« le jeu l'emporte pour
cette réponse ») et une carte « Mettre à jour le profil » ; rien n'est écrit sans le clic du joueur, et alors par le
pont seulement (`profile.apply_game_fields`, source `jeu`). « Ignorer » garde l'empreinte de l'écart : il n'est plus
proposé tant qu'il ne change pas. Propositions et empreintes ignorées : `<cache>/bridge/profile_gaps.json`."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from forever.timefmt import format_utc

FIELDS = ("class", "race", "faction", "level", "talents", "gear", "professions")
LABELS = {
    "sheet": "fiche",
    "class": "classe",
    "race": "race",
    "faction": "faction",
    "level": "niveau",
    "talents": "talents",
    "gear": "équipement",
    "professions": "métiers",
}
DISMISSED_KEPT = 200
GAP_NOTE = "Le jeu l'emporte pour cette réponse."
MENTION = "Écart avec ton profil : voir À valider"


@dataclass(frozen=True)
class Gap:
    field: str
    profile: Any
    game: Any


def _piece(piece: Any) -> dict[str, Any]:
    item = piece.item
    return {"item": item.item, "enchant": item.enchant, "gems": list(item.gems), "suffix": item.suffix,
            "unique": item.unique, "name": piece.name}  # fmt: skip


def game_fields(resolved: Any) -> dict[str, Any]:
    """Valeurs du jeu au format du profil (schéma 3) ; une valeur inconnue vaut None (jamais comparée)."""
    faction = resolved.faction.capitalize() if resolved.faction else None
    return {
        "class": resolved.class_name,
        "race": resolved.race,
        "faction": faction,
        "level": resolved.level,
        "talents": dict(resolved.current),
        "gear": {str(p.slot): _piece(p) for p in resolved.pieces},
        "professions": dict(resolved.professions) if resolved.professions is not None else None,
    }


def _comparable_gear(gear: Any) -> dict[str, tuple[Any, ...]]:
    out = {}
    for slot, piece in (gear or {}).items():
        if isinstance(piece, Mapping):
            out[str(slot)] = (piece.get("item"), piece.get("enchant") or 0, piece.get("suffix") or 0)
    return out


def _same(field: str, profile: Any, game: Any) -> bool:
    if field == "faction":
        return str(profile or "").lower() == str(game or "").lower()
    if field == "gear":
        return _comparable_gear(profile) == _comparable_gear(game)
    if field in ("talents", "professions"):
        return dict(profile or {}) == dict(game or {})
    return bool(profile == game)


def profile_gaps(resolved: Any, profile: Mapping[str, Any] | None) -> list[Gap]:
    """Écarts entre le jeu et le personnage du profil (valeurs à plat), dans l'ordre de FIELDS ; sans personnage, toute
    valeur connue du jeu est un écart. Une valeur que le jeu n'a pas envoyée n'est jamais un écart."""
    game = game_fields(resolved)
    gaps = []
    for field in FIELDS:
        value = game[field]
        if value is None or (field == "gear" and not value and resolved.pieces == []):
            continue
        known = None if profile is None else profile.get(field)
        if profile is None or not _same(field, known, value):
            gaps.append(Gap(field, known, value))
    return gaps


def gap_fingerprint(gaps: Sequence[Gap]) -> str:
    """Empreinte de l'écart (champs et valeurs du jeu), indépendante de l'ordre ; 16 caractères hexadécimaux."""
    doc = sorted((g.field, json.dumps(g.game, sort_keys=True, ensure_ascii=False, default=str)) for g in gaps)
    return hashlib.sha256(json.dumps(doc, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def _text(field: str, value: Any) -> str:
    if value in (None, "", {}):
        return "aucun" if field in ("talents", "gear", "professions") else ("aucune" if field == "sheet" else "?")
    if field == "sheet":
        return f"{len(value)} rubrique(s)"
    if field == "talents":
        return f"{len(value)} talent(s)"
    if field == "gear":
        return f"{len(value)} pièce(s)"
    if field == "professions":
        return ", ".join(f"{k} {v}" for k, v in sorted(value.items()))
    return str(value)


def gap_line(gap: Gap) -> str:
    """« niveau : 18 au profil, 19 en jeu »."""
    if gap.field == "gear" and gap.profile:
        before, after = _comparable_gear(gap.profile), _comparable_gear(gap.game)
        slots = sorted({s for s in before.keys() | after.keys() if before.get(s) != after.get(s)}, key=int)
        return f"équipement : {len(slots)} emplacement(s) différent(s) ({', '.join(slots)})"
    return f"{LABELS[gap.field]} : {_text(gap.field, gap.profile)} au profil, {_text(gap.field, gap.game)} en jeu"


def gaps_text(gaps: Sequence[Gap]) -> str:
    return "; ".join(gap_line(g) for g in gaps)


def gap_card(name: str, realm: str | None, gaps: Sequence[Gap], *, create: bool) -> dict[str, Any]:
    """Carte « À valider » : Mettre à jour le profil (second clic de confirmation) ou Ignorer."""
    card_id = "profile-" + gap_fingerprint(gaps)
    title = f"Créer le personnage {name} au profil" if create else f"Écart avec ton profil : {name}"
    lines = [gap_line(g) for g in gaps]
    if realm:
        lines.append(f"royaume : {realm}")
    return {
        "id": card_id,
        "kind": "profile",
        "title": title,
        "lines": lines,
        "buttons": [
            {"key": "apply", "label": "Mettre à jour le profil", "action": f"profile_apply:{card_id}", "confirm": True},
            {"key": "dismiss", "label": "Ignorer", "action": f"profile_dismiss:{card_id}"},
        ],
    }


def find_character(doc: Mapping[str, Any], name: str, realm: str | None) -> tuple[str, dict[str, Any] | None]:
    """(clé du personnage dans le profil, personnage brut ou None) : même nom et même royaume, ou même nom sans
    royaume connu ; un personnage de même nom d'un autre royaume prend la clé « Nom (Royaume) »."""
    chars = doc.get("characters") or {}
    raw = chars.get(name)
    if isinstance(raw, dict) and (not realm or not raw.get("realm") or raw.get("realm") == realm):
        return name, raw
    if raw is None:
        return name, None
    key = f"{name} ({realm})"
    other = chars.get(key)
    return key, other if isinstance(other, dict) else None


class ProfileWatch:
    """Écarts au fil des messages, propositions publiées en cartes, Mettre à jour le profil et Ignorer."""

    def __init__(
        self,
        *,
        data: Any,
        deps: Any,
        store: Path,
        now: Callable[[], datetime],
    ) -> None:
        self.data = data
        self.deps = deps
        self.store = store
        self.now = now

    # --- état ---------------------------------------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        try:
            doc = json.loads(self.store.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = {}
        if not isinstance(doc, dict):
            doc = {}
        doc.setdefault("proposals", {})
        doc.setdefault("dismissed", [])
        return doc

    def _save(self, doc: Mapping[str, Any]) -> None:
        self.store.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.store.with_name(self.store.name + ".tmp")
        tmp.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
        os.replace(tmp, self.store)

    # --- au fil des messages ------------------------------------------------------------------------------------

    def check(self, context: Mapping[str, str]) -> tuple[list[Gap], bool]:
        """(écarts, carte proposée) pour le contexte d'un message ; enregistre la proposition (une par personnage,
        remplacée quand l'écart change), sauf si cet écart a été ignoré."""
        from forever.bridge.context import resolve
        from forever.profile import character_values, load_profile, resolve_path

        name = context.get("name")
        if not name or not context.get("class"):
            return [], False
        realm = context.get("realm") or None
        resolved = resolve(self.data, context)
        key, raw = find_character(load_profile(resolve_path(self.deps)), name, realm)
        gaps = profile_gaps(resolved, character_values(raw) if raw is not None else None)
        return gaps, self._propose(context, key, raw, gaps, {})

    def check_simc(self, context: Mapping[str, str], export: Any) -> tuple[list[Gap], list[str], bool]:
        """(écarts, avertissements, carte proposée) pour un export SimulationCraft collé et le contexte du même
        message : fiche de l'export (source `simulationcraft`), le reste du contexte (source `jeu`)."""
        from forever.bridge.context import resolve
        from forever.profile import character_values, load_profile, resolve_path
        from forever.simc import simc_gaps

        name = context.get("name") or export.name
        if not name:
            return [], ["nom du personnage inconnu : profil non comparé"], False
        realm = context.get("realm") or None
        key, raw = find_character(load_profile(resolve_path(self.deps)), name, realm)
        flat = character_values(raw) if raw is not None else None
        gaps = profile_gaps(resolve(self.data, context), flat) if context.get("class") else []
        resolved = resolve(self.data, context)
        sheet_gaps, warnings = simc_gaps(export, flat, resolved.pieces)
        gaps += sheet_gaps
        merged = {**context, "name": name}
        return gaps, warnings, self._propose(merged, key, raw, gaps, {"sheet": "simulationcraft"})

    def _propose(
        self, context: Mapping[str, str], key: str, raw: Any, gaps: Sequence[Gap], sources: Mapping[str, str]
    ) -> bool:
        name = str(context.get("name"))
        realm = context.get("realm") or None
        doc = self._load()
        doc["proposals"] = {i: p for i, p in doc["proposals"].items() if p.get("key") != key}
        if not gaps:
            self._save(doc)
            return False
        fingerprint = gap_fingerprint(gaps)
        if fingerprint in doc["dismissed"]:
            self._save(doc)
            return False
        card = gap_card(name, realm, gaps, create=raw is None)
        doc["proposals"][card["id"]] = {
            "key": key,
            "name": name,
            "realm": realm,
            "fingerprint": fingerprint,
            "fields": {g.field: g.game for g in gaps},
            "sources": {g.field: sources.get(g.field, "jeu") for g in gaps},
            "client_build": context.get("client"),
            "card": card,
        }
        self._save(doc)
        return True

    def cards(self) -> list[dict[str, Any]]:
        return [p["card"] for p in self._load()["proposals"].values() if isinstance(p.get("card"), dict)]

    def known(self, card_id: str) -> bool:
        return card_id in self._load()["proposals"]

    # --- clics --------------------------------------------------------------------------------------------------

    def apply(self, card_id: str) -> tuple[str, str]:
        from forever.profile import apply_game_fields, resolve_path

        doc = self._load()
        proposal = doc["proposals"].get(card_id)  # identifiant apparié exactement à une proposition du pont
        if proposal is None:
            return "refusée", "Action refusée : proposition de profil inconnue ou déjà traitée."
        sources = proposal.get("sources") or {}
        by_source: dict[str, dict[str, Any]] = {}
        for name, value in proposal["fields"].items():
            by_source.setdefault(str(sources.get(name, "jeu")), {})[name] = value
        at = format_utc(self.now())
        for source in sorted(by_source, key=lambda s: s != "jeu"):  # jeu d'abord : il crée le personnage
            apply_game_fields(
                resolve_path(self.deps), str(proposal["key"]), proposal.get("realm"), by_source[source],
                source=source, at=at, client_build=proposal.get("client_build"), deps=self.deps,
            )  # fmt: skip
        del doc["proposals"][card_id]
        self._save(doc)
        fields = ", ".join(LABELS.get(f, f) for f in proposal["fields"])
        used = ", ".join(sorted(by_source))
        return "profil mis à jour", f"Profil mis à jour pour {proposal['key']} ({fields} ; source {used})."

    def dismiss(self, card_id: str) -> tuple[str, str]:
        doc = self._load()
        proposal = doc["proposals"].pop(card_id, None)
        if proposal is None:
            return "refusée", "Action refusée : proposition de profil inconnue ou déjà traitée."
        doc["dismissed"] = [*doc["dismissed"], proposal["fingerprint"]][-DISMISSED_KEPT:]
        self._save(doc)
        return "écart ignoré", "Écart ignoré : il ne sera plus proposé tant qu'il ne change pas."
