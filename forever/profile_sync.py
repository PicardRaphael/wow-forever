"""AMI1 : profil rempli tout seul depuis ForeverLogger, sur chaque PC, sans saisie (demande du 2026-11-08 : « tu dois
le retenir, à toi de le faire »). Lecture locale des SavedVariables ; aucune valeur de jeu ici.

Pour chaque personnage relevé : nom `Nom-Royaume` (dossier du personnage dans `WTF/Account/<compte>/…`), classe,
race, faction lue dans `races.json`, dernier niveau relevé et talents de ce relevé (nœuds du client traduits en clés ;
pour le Mage, clés du moteur du Mage, celles que le profil vérifie). Un même nom relevé plusieurs fois (personnages
supprimés ou d'un autre royaume) : le relevé le plus récent l'emporte."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from forever.config import Deps

LOGGER_GLOB = "WTF/Account/*/SavedVariables/ForeverLogger.lua"
RACE_FILES = {"Scourge": "Undead"}
# sortie de WoW Forever (dit par l'utilisateur le 2026-11-08 : « le jeu est dispo depuis le 5 novembre ») : un relevé
# antérieur vient de la bêta et n'entre jamais dans le profil
RELEASE_DAY = "2026-11-05"  # nom de fichier de race du client -> nom de races.json, quand ils diffèrent


def _walk(doc: Any) -> Iterable[dict[str, Any]]:
    if isinstance(doc, dict):
        yield doc
        for value in doc.values():
            yield from _walk(value)
    elif isinstance(doc, list):
        for value in doc:
            yield from _walk(value)


def _profile_name(wow: Path, name: str) -> str:
    """`Nom-Royaume` d'après le dossier du personnage dans `WTF/Account/<compte>/<royaume>/` ; le nom seul sinon."""
    for folder in sorted(wow.glob("WTF/Account/*/*/*")):
        if not folder.is_dir() or folder.parent.name == "SavedVariables":
            continue
        if folder.name.startswith(f"{name}-"):
            return folder.name
        if folder.name == name:
            return f"{name}-{folder.parent.name}"
    return name


def sync_from_logger(deps: Deps, *, set_char: Callable[..., Any] | None = None) -> list[dict[str, Any]]:
    """Personnages de ForeverLogger écrits dans le profil (voir le module) ; rend la liste écrite."""
    from forever.pipeline.addon_sv import read_logger_db
    from forever.profile import set_character
    from forever.store import load_version

    if deps.wow_dir is None:
        return []
    files = sorted(deps.wow_dir.glob(LOGGER_GLOB))
    if not files:
        return []
    vd = load_version(deps)
    races = {
        str(r["name"]).replace(" ", ""): r for r in _walk(vd.read_json("races.json")) if "faction" in r and "name" in r
    }
    classes = vd.read_json("classes.json")["classes"]
    mage_keys = {
        str(t["name"]): str(t["key"]) for t in _walk(vd.read_json("talents.json")) if "key" in t and "name" in t
    }
    latest: dict[str, tuple[int, dict[str, Any]]] = {}
    for path in files:
        for character in read_logger_db(path).characters.values():
            snaps = [s for s in character.snapshots if s.level is not None and s.localtime is not None
                     and s.localtime.strftime("%Y-%m-%d") >= RELEASE_DAY]  # fmt: skip
            if not snaps or not character.class_ or not character.name:
                continue
            snap = max(snaps, key=lambda s: s.time or 0)
            cls = str(character.class_).capitalize()
            if cls not in classes:
                continue
            nodes = {t["node_id"]: t for tree in classes[cls]["trees"] for t in tree["talents"]}
            talents: dict[str, int] = {}
            for node, rank in (snap.talents or {}).items():
                t = nodes.get(node)
                if t is None or not rank:
                    continue
                key = mage_keys.get(str(t["name"]), str(t["key"])) if cls == "Mage" else str(t["key"])
                talents[key] = int(rank)
            race_row = races.get(RACE_FILES.get(str(character.race), str(character.race)))
            name = _profile_name(deps.wow_dir, str(character.name))
            fields = {"cls": cls, "race": race_row["name"] if race_row else character.race,
                      "faction": race_row["faction"] if race_row else None, "level": int(snap.level or 0),
                      "talents": talents}  # fmt: skip
            when = int(snap.time or 0)
            if name not in latest or when >= latest[name][0]:
                latest[name] = (when, fields)
    from forever.errors import ForeverError

    write = set_char or set_character
    done = []
    for name, (_, fields) in sorted(latest.items()):
        try:
            write(deps, name, **{k: v for k, v in fields.items() if v is not None})
        except ForeverError as err:  # relevé ancien (arbre de talents changé depuis) : personnage écarté et nommé
            done.append({"name": name, "class": fields["cls"], "level": fields["level"], "skipped": err.message})
            continue
        done.append({"name": name, "class": fields["cls"], "level": fields["level"]})
    return done
