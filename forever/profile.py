"""Profil joueur hors du dépôt (T06b, décision D5 ; schéma 2 en PV1, décision 125) : plusieurs personnages, un actif.

Fichier : `Deps.profile_path`, sinon `FOREVER_PROFILE`, sinon `~/.forever/profile.json` ; jamais sous le dépôt (les
données personnelles ne se committent pas, décision 99). Lu explicitement par l'agent (`forever_player_profile`) :
les outils de calcul ne le lisent jamais d'eux-mêmes. Schéma 2 :
`{schema_version, active, characters: {<nom>: {<champ>: {value, source, at, client_build, certainty}, guid, realm,
planned, validated, game_version, updated_at, conflicts}}, realms: {<royaume>: {prices: <champ>}}}`. Champs
sourcés : `WRAPPED`. Chaque champ garde sa source, sa date UTC et la version du client en vigueur ; la fusion suit
`merge_field` (la plus récente l'emporte, à date égale la source la plus directe, `SOURCE_RANK`) et garde les
désaccords dans `conflicts`, jamais effacés. Un profil de schéma 1 est migré à la lecture (source `joueur`, date
`updated_at`) et réécrit seulement par une commande qui écrit. `read_profile` rend les valeurs à plat, plus `fields`
et `conflicts`. Neuf classes (noms anglais du client, noms français acceptés). Mage : race (races.json), niveau et
talents (check_build) validés ; autres classes : gardées telles quelles, `validated: false`. Faction donnée par le
joueur, jamais déduite ni importée. `planned` : personnage prévu, pas encore créé ; absent : `false`."""

from __future__ import annotations

import copy
import difflib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

from forever.config import Deps
from forever.engine.talents import check_build, check_class_build
from forever.errors import DataSchemaError, InvalidArgumentError
from forever.gamedata import RACES_FILE, RACIALS_FILE, SEED_RACIALS_FILE, build_game_data, mage_races
from forever.provenance import Provenance, local_provenance
from forever.store import current_identity, load_version
from forever.timefmt import format_utc

SCHEMA_VERSION = 2
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
# Champs sourcés (schéma 2), dans l'ordre d'affichage ; valeur par défaut d'un champ absent.
WRAPPED: dict[str, Any] = {
    "class": None,
    "race": None,
    "faction": None,
    "level": None,
    "talents": {},
    "professions": {},
    "talent_nodes": {},
    "quests_completed": {},
}
_SCHEMA_1_FIELDS = ("class", *FIELDS)
_META = ("source", "at", "client_build", "certainty")

# Ordre des sources à date égale, de la plus directe à la moins directe (PV1, D2 ; décision 125) : rang croissant.
SOURCE_RANK = {"joueur": 0, "ForeverLogger": 1, "Questie": 2, "Auctionator": 2, "journal": 3, "api": 4}


class ProfileView(TypedDict):
    path: str
    active: str | None
    character: dict[str, Any] | None
    characters: list[str]
    stale: bool | None
    missing: list[str]
    provenance: Provenance


def make_field(
    value: Any, source: str, at: str | None, client_build: str | None = None, certainty: str = "certain"
) -> dict[str, Any]:
    """Champ du profil (schéma 2) : valeur, source, date UTC, version du client en vigueur, certitude."""
    return {"value": value, "source": source, "at": at, "client_build": client_build, "certainty": certainty}


def _empty_value(value: Any) -> bool:
    return value is None or value in ("", {})


def _rank(f: Mapping[str, Any]) -> int:
    return SOURCE_RANK.get(str(f.get("source")), len(SOURCE_RANK))


def merge_field(
    current: Mapping[str, Any] | None, new: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """(champ gardé, désaccord ou None) : la valeur la plus récente l'emporte, à date égale la source la plus
    directe (`SOURCE_RANK`) ; un désaccord est rendu, jamais effacé. Même valeur : la source la plus directe est
    gardée (puis la plus récente). Une source qui se met à jour elle-même (valeur plus récente de la même source)
    n'est pas un désaccord. Une valeur vide ne remplace jamais une valeur connue."""
    if current is None or _empty_value(current.get("value")):
        return dict(new), None
    if _empty_value(new.get("value")):
        return dict(current), None
    if current["value"] == new["value"]:
        best = min((current, new), key=lambda f: (_rank(f), _neg(f.get("at"))))
        return dict(best), None
    newer = (new.get("at") or "") > (current.get("at") or "")
    same_time = (new.get("at") or "") == (current.get("at") or "")
    if new.get("source") == current.get("source"):  # la source se met à jour : dernière lecture gardée
        return (dict(new), None) if newer or same_time else (dict(current), None)
    wins = newer or (same_time and _rank(new) < _rank(current))
    winner, loser = (new, current) if wins else (current, new)
    return dict(winner), {"kept": dict(winner), "other": dict(loser)}


def _neg(at: str | None) -> tuple[int, ...]:
    """Clé de tri qui place la date la plus récente en premier."""
    return tuple(-ord(ch) for ch in (at or ""))


def character_values(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Personnage du profil à plat (valeurs seules), plus `fields` (source, date, version du client, certitude par
    champ) et `conflicts`."""
    out: dict[str, Any] = {}
    fields: dict[str, Any] = {}
    for key, default in WRAPPED.items():
        f = raw.get(key)
        if isinstance(f, dict) and "source" in f:
            out[key] = copy.deepcopy(f.get("value"))
            fields[key] = {m: f.get(m) for m in _META}
        else:
            out[key] = copy.deepcopy(default)
    out["guid"] = raw.get("guid")
    out["realm"] = raw.get("realm")
    out["planned"] = bool(raw.get("planned", False))
    out["game_version"] = raw.get("game_version")
    out["updated_at"] = raw.get("updated_at")
    out["validated"] = bool(raw.get("validated", False))
    out["fields"] = fields
    out["conflicts"] = copy.deepcopy(raw.get("conflicts") or [])
    return out


def profile_path(environ: Mapping[str, str] = os.environ) -> Path:
    """FOREVER_PROFILE, sinon EVAL_FOREVER_PROFILE (évaluation du plugin : `claude plugin eval` ne transmet que les
    variables `EVAL_*`), sinon ~/.forever/profile.json."""
    configured = environ.get("FOREVER_PROFILE") or environ.get("EVAL_FOREVER_PROFILE")
    return Path(configured) if configured else Path.home() / ".forever" / "profile.json"


def resolve_path(deps: Deps) -> Path:
    """Chemin du profil pour ces dépendances."""
    return deps.profile_path if deps.profile_path is not None else profile_path()


def _empty() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "active": None, "characters": {}, "realms": {}}


def _migrate_character(c: Mapping[str, Any]) -> dict[str, Any]:
    at = c.get("updated_at")
    out: dict[str, Any] = {
        key: make_field(copy.deepcopy(c.get(key, WRAPPED[key])), "joueur", at) for key in _SCHEMA_1_FIELDS
    }
    for key in ("planned", "validated", "game_version", "updated_at"):
        if key in c:
            out[key] = c[key]
    return out


def _schema_error(path: Path) -> DataSchemaError:
    return DataSchemaError(
        f"Profil joueur {path} : schéma 1 ou {SCHEMA_VERSION} attendu.", "corriger ou supprimer le fichier"
    )


def load_profile(path: Path) -> dict[str, Any]:
    """Profil lu sur disque, en schéma 2 (vide s'il est absent ; un schéma 1 est migré en mémoire, sans écrire) ;
    DataSchemaError s'il est illisible ou d'un autre schéma."""
    if not path.is_file():
        return _empty()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"Profil joueur illisible : {path} ({exc}).", "corriger ou supprimer le fichier") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("characters"), dict):
        raise _schema_error(path)
    if doc.get("schema_version") == 1:
        chars = {name: _migrate_character(c) for name, c in doc["characters"].items() if isinstance(c, dict)}
        return {"schema_version": SCHEMA_VERSION, "active": doc.get("active"), "characters": chars, "realms": {}}
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise _schema_error(path)
    doc.setdefault("realms", {})
    return doc


def save_profile(path: Path, doc: Mapping[str, Any]) -> None:
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


def normalize_class(value: str) -> str:
    """Nom anglais du client d'une classe (nom anglais ou français, jeton du client comme `MAGE`)."""
    key = value.strip().lower()
    if key not in CLASS_NAMES:
        raise InvalidArgumentError(
            f"Classe inconnue « {value} ».",
            "choisir Guerrier, Paladin, Chasseur, Voleur, Prêtre, Chaman, Mage, Démoniste ou Druide",
        )
    return CLASS_NAMES[key]


def _mage_errors(deps: Deps, c: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Erreurs (message, action) de race, de talents et de niveau d'un Mage contre les données courantes."""
    data = load_version(deps)
    races = mage_races(data)
    accepted = set(races)
    if (
        data.path / RACES_FILE
    ).is_file():  # jeton du client (ForeverLogger) et noms de l'ancien relevé (profils d'avant PV1)
        accepted |= {r["client_file"] for r in data.read_json(RACES_FILE)["races"].values() if "Mage" in r["classes"]}
        if (data.path / SEED_RACIALS_FILE).is_file():
            accepted |= set(data.read_json(SEED_RACIALS_FILE)["races"])
    source = RACES_FILE if (data.path / RACES_FILE).is_file() else RACIALS_FILE
    race = c.get("race")
    if race is not None and race not in accepted:
        close = difflib.get_close_matches(race, races, n=3, cutoff=0.5)
        hint = f"proches : {', '.join(close)}" if close else f"choisir parmi {', '.join(races)}"
        return [(f"Race inconnue « {race} » pour un Mage.", f"{hint} ({source})")]
    gd = build_game_data(data)
    unknown = [k for k in c.get("talents") or {} if k not in gd.talents]
    if unknown:
        return [
            (f"Talent(s) inconnu(s) : {', '.join(unknown)}.", "donner les clés de talents.json (ex. improvedFrostbolt)")
        ]
    level = c.get("level")
    if level is not None:
        errors = check_build(gd, c.get("talents") or {}, level)
        if errors:
            return [(f"Talents illégaux au niveau {level} : {' ; '.join(errors)}.", "corriger les rangs ou le niveau")]
    return []


def validation_errors(deps: Deps, c: Mapping[str, Any]) -> list[str]:
    """Erreurs de race, de niveau et de talents d'un personnage contre les données courantes (liste vide : légal).
    Mage : contrôle du moteur du Mage ; autres classes (PV1) : race permise (`races.json`, nom ou jeton du client),
    légalité du build sur `classes.json` (`check_class_build`)."""
    cls = c.get("class")
    if cls == "Mage":
        return [message for message, _ in _mage_errors(deps, c)]
    data = load_version(deps)
    gd = build_game_data(data)
    if not isinstance(cls, str) or cls not in gd.classes:
        return [f"classe {cls} absente des données (classes.json)"]
    errors = []
    race = c.get("race")
    if race is not None and (data.path / RACES_FILE).is_file():
        races = data.read_json(RACES_FILE)["races"]
        allowed = {n for n, r in races.items() if cls in r["classes"]}
        allowed |= {r["client_file"] for n, r in races.items() if cls in r["classes"]}
        if race not in allowed:
            errors.append(f"race {race} non permise pour {cls} (races.json)")
    talents = c.get("talents") or {}
    level = c.get("level")
    if talents and level is None:
        errors.append("niveau inconnu : légalité des talents non contrôlée")
    elif level is not None:
        errors += check_class_build(gd.classes[cls], gd.constants.talents, talents, level)
    return errors


def is_valid(deps: Deps, c: Mapping[str, Any]) -> bool:
    """Personnage contrôlé et légal (9 classes), sans lever d'erreur."""
    return c.get("class") is not None and not validation_errors(deps, c)


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
    """Crée ou met à jour un personnage (champs donnés seulement, source `joueur`) ; le premier créé devient actif.
    Rend le profil. `planned` vrai : personnage prévu (pas encore créé) ; faux : créé en jeu."""
    if not name.strip():
        raise InvalidArgumentError("Nom de personnage vide.", "donner un nom")
    path = resolve_path(deps)
    doc = load_profile(path)
    chars: dict[str, Any] = doc["characters"]
    raw = dict(chars.get(name, {}))
    if not raw and cls is None:
        raise InvalidArgumentError(f"Personnage « {name} » absent du profil.", "donner --class pour le créer")
    flat = character_values(raw)
    given: dict[str, Any] = {}
    if cls is not None:
        given["class"] = normalize_class(cls)
    for key, value in (("race", race), ("faction", faction), ("level", level)):
        if value is not None:
            given[key] = value
    if talents is not None:
        given["talents"] = {k: int(v) for k, v in talents.items() if int(v) > 0}
    if professions is not None:
        merged = dict(flat["professions"] or {})
        for skill, value in professions.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidArgumentError(f"Compétence de métier invalide : {skill} = {value}.", "donner un entier")
            merged[skill] = value
        given["professions"] = merged
    flat.update(given)
    if planned is not None:
        raw["planned"] = planned
    raw["planned"] = bool(raw.get("planned", False))
    if flat["level"] is not None:
        _check_level(deps, flat["level"])
    if flat["class"] == "Mage":
        errors = _mage_errors(deps, flat)
        if errors:
            raise InvalidArgumentError(*errors[0])
    at = format_utc(deps.now())
    conflicts = list(raw.get("conflicts") or [])
    for key, value in given.items():
        kept, conflict = merge_field(raw.get(key), make_field(value, "joueur", at))
        raw[key] = kept
        if conflict is not None and (record := {"field": key, **conflict}) not in conflicts:
            conflicts.append(record)
    if conflicts:
        raw["conflicts"] = conflicts
    raw["validated"] = is_valid(deps, flat)
    raw["game_version"] = current_identity(deps.data_dir).game_version
    raw["updated_at"] = at
    chars[name] = raw
    if doc.get("active") is None:
        doc["active"] = name
    save_profile(path, doc)
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
    path = resolve_path(deps)
    doc = load_profile(path)
    _known(doc, name)
    doc["active"] = name
    save_profile(path, doc)
    return doc


def remove(deps: Deps, name: str) -> dict[str, Any]:
    """Retire un personnage ; l'actif passe au premier restant (ou à aucun)."""
    path = resolve_path(deps)
    doc = load_profile(path)
    _known(doc, name)
    del doc["characters"][name]
    if doc.get("active") == name:
        doc["active"] = next(iter(doc["characters"]), None)
    save_profile(path, doc)
    return doc


def read_profile(deps: Deps, name: str | None = None) -> ProfileView:
    """Personnage actif (ou `name`) à plat, avec `fields` et `conflicts` ; liste des noms, `stale` (profil saisi sur
    une autre version des données), `missing` (champs du joueur vides), provenance. Lecture seule, sans réseau."""
    path = resolve_path(deps)
    doc = load_profile(path)
    chosen = name if name is not None else doc.get("active")
    if name is not None:
        _known(doc, name)
    raw = doc["characters"].get(chosen) if chosen is not None else None
    version = current_identity(deps.data_dir).game_version
    flat = character_values(raw) if raw is not None else None
    planned = bool(flat["planned"]) if flat is not None else False
    character = {"name": chosen, **flat} if flat is not None else None
    expected = [k for k in FIELDS if not (planned and k in PLANNED_UNUSED)]
    missing = [k for k in expected if flat is not None and _empty_value(flat.get(k))]
    notes = [f"profil joueur : {path} (données personnelles, hors du dépôt)"]
    if flat is None:
        notes.append("aucun personnage dans le profil : demander les données au joueur (forever profile set)")
    elif flat["game_version"] != version:
        notes.append(f"profil saisi sur {flat['game_version']}, données {version} : à revérifier")
    return {
        "path": str(path),
        "active": doc.get("active"),
        "character": character,
        "characters": list(doc["characters"]),
        "stale": flat["game_version"] != version if flat is not None else None,
        "missing": missing,
        "provenance": local_provenance(deps, certainty="certain", assumptions=notes),
    }
