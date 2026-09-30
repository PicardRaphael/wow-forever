"""Profil joueur minimal, hors du dépôt (T06b, décision D5) : plusieurs personnages, un actif.

Fichier : `Deps.profile_path`, sinon `FOREVER_PROFILE`, sinon `~/.forever/profile.json` ; jamais sous le dépôt (les
données personnelles ne se committent pas, décision 99). Lu explicitement par l'agent (`forever_player_profile`) :
les outils de calcul ne le lisent jamais d'eux-mêmes. Schéma 1 :
`{schema_version, active, characters: {<nom>: {class, race, faction, level, talents, professions, planned,
game_version, updated_at, validated}}}`. Neuf classes (noms anglais du client, noms français acceptés). Mage : race
(racials.json), niveau et talents (check_build) validés ; autres classes (tranches de classe PA1 à DR1) : gardées
telles quelles, `validated: false`. Faction donnée par le joueur, jamais déduite. `planned` : personnage prévu, pas
encore créé (classe, race, faction, métiers envisagés ; ni niveau ni talents attendus) ; absent : `false`."""

from __future__ import annotations

import difflib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

from forever.config import Deps
from forever.engine.talents import check_build
from forever.errors import DataSchemaError, InvalidArgumentError
from forever.gamedata import RACIALS_FILE, build_game_data
from forever.provenance import Provenance, local_provenance
from forever.store import current_identity, load_version
from forever.timefmt import format_utc

SCHEMA_VERSION = 1
REPO_ROOT = Path(__file__).resolve().parent.parent
CLASSES = ("Warrior", "Paladin", "Hunter", "Rogue", "Priest", "Shaman", "Mage", "Warlock", "Druid")
CLASS_NAMES = {
    **{c.lower(): c for c in CLASSES},
    "guerrier": "Warrior",
    "chasseur": "Hunter",
    "voleur": "Rogue",
    "prêtre": "Priest",
    "pretre": "Priest",
    "chaman": "Shaman",
    "démoniste": "Warlock",
    "demoniste": "Warlock",
    "druide": "Druid",
}
FIELDS = ("race", "faction", "level", "talents", "professions")  # champs du joueur, dans l'ordre de `missing`
PLANNED_UNUSED = ("level", "talents")  # champs qu'un personnage prévu n'a pas encore


# Ordre des sources à date égale, de la plus directe à la moins directe (PV1, D2 ; décision 125) : rang croissant.
SOURCE_RANK = {"joueur": 0, "ForeverLogger": 1, "Questie": 2, "Auctionator": 2, "journal": 3, "api": 4}


def make_field(
    value: Any, source: str, at: str | None, client_build: str | None = None, certainty: str = "certain"
) -> dict[str, Any]:
    """Champ du profil (schéma 2) : valeur, source, date UTC, version du client en vigueur, certitude."""
    raise NotImplementedError


def merge_field(current: Mapping[str, Any] | None, new: Mapping[str, Any]) -> tuple[dict[str, Any], dict | None]:
    """(champ gardé, désaccord ou None) : la valeur la plus récente l'emporte, à date égale la source la plus
    directe (`SOURCE_RANK`) ; un désaccord est rendu, jamais effacé."""
    raise NotImplementedError


def character_values(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Personnage du profil à plat (valeurs seules), plus `fields` (source, date, version du client, certitude par
    champ) et `conflicts`."""
    raise NotImplementedError


class ProfileView(TypedDict):
    path: str
    active: str | None
    character: dict[str, Any] | None
    characters: list[str]
    stale: bool | None
    missing: list[str]
    provenance: Provenance


def profile_path(environ: Mapping[str, str] = os.environ) -> Path:
    """FOREVER_PROFILE, sinon EVAL_FOREVER_PROFILE (évaluation du plugin : `claude plugin eval` ne transmet que les
    variables `EVAL_*`), sinon ~/.forever/profile.json."""
    configured = environ.get("FOREVER_PROFILE") or environ.get("EVAL_FOREVER_PROFILE")
    return Path(configured) if configured else Path.home() / ".forever" / "profile.json"


def _path(deps: Deps) -> Path:
    return deps.profile_path if deps.profile_path is not None else profile_path()


def _empty() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "active": None, "characters": {}}


def load_profile(path: Path) -> dict[str, Any]:
    """Profil lu sur disque (vide s'il est absent) ; DataSchemaError s'il est illisible ou d'un autre schéma."""
    if not path.is_file():
        return _empty()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"Profil joueur illisible : {path} ({exc}).", "corriger ou supprimer le fichier") from exc
    if (
        not isinstance(doc, dict)
        or doc.get("schema_version") != SCHEMA_VERSION
        or not isinstance(doc.get("characters"), dict)
    ):
        raise DataSchemaError(
            f"Profil joueur {path} : schéma {SCHEMA_VERSION} attendu.", "corriger ou supprimer le fichier"
        )
    return doc


def _save(path: Path, doc: Mapping[str, Any]) -> None:
    """Écriture atomique (fichier temporaire puis remplacement), UTF-8, fins de ligne LF ; refus sous le dépôt."""
    if path.resolve().is_relative_to(REPO_ROOT):
        raise InvalidArgumentError(
            f"Le profil joueur ne s'écrit jamais dans le dépôt ({path}).",
            "choisir FOREVER_PROFILE hors du dépôt (défaut : ~/.forever/profile.json)",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def _class(value: str) -> str:
    key = value.strip().lower()
    if key not in CLASS_NAMES:
        raise InvalidArgumentError(
            f"Classe inconnue « {value} ».",
            "choisir Guerrier, Paladin, Chasseur, Voleur, Prêtre, Chaman, Mage, Démoniste ou Druide",
        )
    return CLASS_NAMES[key]


def _check_mage(deps: Deps, c: Mapping[str, Any]) -> None:
    """Race, niveau et talents d'un Mage contre les données de la version courante."""
    data = load_version(deps)
    races = sorted(data.read_json(RACIALS_FILE)["races"])
    race = c.get("race")
    if race is not None and race not in races:
        close = difflib.get_close_matches(race, races, n=3, cutoff=0.5)
        hint = f"proches : {', '.join(close)}" if close else f"choisir parmi {', '.join(races)}"
        raise InvalidArgumentError(f"Race inconnue « {race} » pour un Mage.", f"{hint} (racials.json)")
    gd = build_game_data(data)
    unknown = [k for k in c.get("talents") or {} if k not in gd.talents]
    if unknown:
        raise InvalidArgumentError(
            f"Talent(s) inconnu(s) : {', '.join(unknown)}.",
            "donner les clés de talents.json (ex. improvedFrostbolt)",
        )
    level = c.get("level")
    if level is not None:
        errors = check_build(gd, c.get("talents") or {}, level)
        if errors:
            raise InvalidArgumentError(
                f"Talents illégaux au niveau {level} : {' ; '.join(errors)}.", "corriger les rangs ou le niveau"
            )


def _check_level(deps: Deps, level: int) -> None:
    cap = build_game_data(load_version(deps)).level_cap
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= cap:
        raise InvalidArgumentError(f"Niveau {level} hors de 1-{cap}.", f"donner un niveau entier de 1 à {cap}")


def set_character(
    deps: Deps,
    name: str,
    *,
    cls: str | None = None,
    race: str | None = None,
    faction: str | None = None,
    level: int | None = None,
    talents: Mapping[str, int] | None = None,
    professions: Mapping[str, int] | None = None,
    planned: bool | None = None,
) -> dict[str, Any]:
    """Crée ou met à jour un personnage (champs donnés seulement) ; le premier créé devient actif. Rend le profil.
    `planned` vrai : personnage prévu (pas encore créé) ; faux : créé en jeu."""
    if not name.strip():
        raise InvalidArgumentError("Nom de personnage vide.", "donner un nom")
    path = _path(deps)
    doc = load_profile(path)
    chars: dict[str, Any] = doc["characters"]
    current = dict(chars.get(name, {}))
    if not current and cls is None:
        raise InvalidArgumentError(f"Personnage « {name} » absent du profil.", "donner --class pour le créer")
    if cls is not None:
        current["class"] = _class(cls)
    for key, value in (("race", race), ("faction", faction), ("level", level)):
        if value is not None:
            current[key] = value
    if talents is not None:
        current["talents"] = {k: int(v) for k, v in talents.items() if int(v) > 0}
    if professions is not None:
        merged = dict(current.get("professions") or {})
        for skill, value in professions.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidArgumentError(f"Compétence de métier invalide : {skill} = {value}.", "donner un entier")
            merged[skill] = value
        current["professions"] = merged
    for key in FIELDS:
        current.setdefault(key, {} if key in ("talents", "professions") else None)
    if planned is not None:
        current["planned"] = planned
    current["planned"] = bool(current.get("planned", False))
    if current["level"] is not None:
        _check_level(deps, current["level"])
    validated = current["class"] == "Mage"
    if validated:
        _check_mage(deps, current)
    current["validated"] = validated
    current["game_version"] = current_identity(deps.data_dir).game_version
    current["updated_at"] = format_utc(deps.now())
    chars[name] = {k: current[k] for k in ("class", *FIELDS, "planned", "game_version", "updated_at", "validated")}
    if doc.get("active") is None:
        doc["active"] = name
    _save(path, doc)
    return doc


def _known(doc: Mapping[str, Any], name: str) -> None:
    if name not in doc["characters"]:
        names = list(doc["characters"])
        close = difflib.get_close_matches(name, names, n=3, cutoff=0.5)
        raise InvalidArgumentError(
            f"Personnage « {name} » absent du profil.", f"choisir parmi {', '.join(close or names) or 'aucun'}"
        )


def use(deps: Deps, name: str) -> dict[str, Any]:
    """Rend `name` actif."""
    path = _path(deps)
    doc = load_profile(path)
    _known(doc, name)
    doc["active"] = name
    _save(path, doc)
    return doc


def remove(deps: Deps, name: str) -> dict[str, Any]:
    """Retire un personnage ; l'actif passe au premier restant (ou à aucun)."""
    path = _path(deps)
    doc = load_profile(path)
    _known(doc, name)
    del doc["characters"][name]
    if doc.get("active") == name:
        doc["active"] = next(iter(doc["characters"]), None)
    _save(path, doc)
    return doc


def read_profile(deps: Deps, name: str | None = None) -> ProfileView:
    """Personnage actif (ou `name`), liste des noms, `stale` (profil saisi sur une autre version des données),
    `missing` (champs du joueur vides), provenance. Lecture seule, sans réseau."""
    path = _path(deps)
    doc = load_profile(path)
    chosen = name if name is not None else doc.get("active")
    if name is not None:
        _known(doc, name)
    raw = doc["characters"].get(chosen) if chosen is not None else None
    version = current_identity(deps.data_dir).game_version
    planned = bool(raw.get("planned", False)) if raw is not None else False
    character = {"name": chosen, **raw, "planned": planned} if raw is not None else None
    expected = [k for k in FIELDS if not (planned and k in PLANNED_UNUSED)]
    missing = [k for k in expected if raw is not None and raw.get(k) in (None, "", {})]
    notes = [f"profil joueur : {path} (données personnelles, hors du dépôt)"]
    if raw is None:
        notes.append("aucun personnage dans le profil : demander les données au joueur (forever profile set)")
    elif raw.get("game_version") != version:
        notes.append(f"profil saisi sur {raw.get('game_version')}, données {version} : à revérifier")
    return {
        "path": str(path),
        "active": doc.get("active"),
        "character": character,
        "characters": list(doc["characters"]),
        "stale": raw.get("game_version") != version if raw is not None else None,
        "missing": missing,
        "provenance": local_provenance(deps, certainty="certain", assumptions=notes),
    }
