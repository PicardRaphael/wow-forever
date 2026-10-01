"""Lecteur local de l'addon Forever Bestiary et de sa sauvegarde `ForeverBestiaryDB` (CH0, bloc B).

Lecture sur disque seulement, jamais par le réseau ; rien n'est copié dans le dépôt (décision 133 : addon sans
licence, seuls des agrégats). Anonymisation à la lecture : empreintes de joueurs (`rp`), noms de tiers (`peers`,
`feed[].who`), GUID (`petGuids`), clés `self*`, `likes` et `votes` ne sont jamais rendus ; chaque table est relue
par liste blanche (un champ ajouté par une version future de l'addon n'est pas rendu).

Sens des marques de l'addon (lus dans son code, `UI/Beasts.lua` et `Core/Index.lua` de la version 0.5.0) :
- troisième élément d'un rang enseigné (`t`) : `p` affiché « beta », `b` affiché « ? », autre valeur sans marque ;
- confirmation d'une bête (`cf`) : textes de l'addon traduits ci-dessous."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forever.addons import _version, fingerprint_folder
from forever.errors import DataSchemaError, PathNotFoundError
from forever.pipeline.lua_table import parse_lua_assignments, parse_lua_value_at

ADDON_NAME = "ForeverBestiary"
SAVED_VARIABLE = "ForeverBestiaryDB"
DATA_FILE = Path("Data/Data.lua")
COMMUNITY_FILE = Path("Data/Community.lua")

# Marque d'un rang enseigné : (étiquette affichée par l'addon, sens, certitude du sens).
TAUGHT_MARKS: Mapping[str, tuple[str, str, str]] = {
    "p": ("beta", "rang relevé par des joueurs de la bêta (étiquette « beta » de l'addon)", "probable"),
    "b": ("?", "rang non confirmé (l'addon affiche « ? » sans l'expliquer)", "suppose"),
    "c": ("", "rang de Classic, sans marque dans l'addon", "probable"),
}
UNKNOWN_MARK = ("", "marque inconnue de l'addon", "suppose")
# Confirmation d'une bête (`cf`) : textes de `Core/Index.lua` traduits.
CONFIRMATIONS: Mapping[str, str] = {
    "classic": "pas encore confirmée dans Forever (bête de Classic)",
    "beta": "signalée par des joueurs de la bêta",
    "datos": "vue seulement dans les données du jeu",
    "community": "découverte de la communauté : apprivoisable dans Forever, absente de la base de l'addon",
}

_ASSIGN = re.compile(r"^(ns\.[A-Za-z_.]+)\s*=", re.MULTILINE)


def _assignments(path: Path) -> dict[str, Any]:
    """Littéraux affectés aux champs `ns.…` d'un fichier de l'addon (le code autour n'est pas lu)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DataSchemaError(f"Forever Bestiary : {path} illisible ({exc}).") from exc
    out: dict[str, Any] = {}
    for m in _ASSIGN.finditer(text):
        try:
            out[m[1]], _ = parse_lua_value_at(text, m.end())
        except ValueError as exc:
            raise DataSchemaError(f"Forever Bestiary : {path.name}, {m[1]} illisible ({exc}).") from exc
    return out


def _obj(value: Any) -> dict[Any, Any]:
    return value if isinstance(value, dict) else {}


def _seq(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value[k] for k in sorted(k for k in value if isinstance(k, int))]
    return []


def _family(raw: Mapping[str, Any]) -> dict[str, Any]:
    fastest = _obj(raw.get("fastest"))
    entry: dict[str, Any] = {
        "name": {"en": raw.get("en"), "es": raw.get("es")},
        "bonus": {"damage_pct": raw.get("dmg"), "armor_pct": raw.get("armor"), "health_pct": raw.get("hp")},
        "diet": [str(d) for d in _seq(raw.get("diet"))],
        "abilities": [str(_obj(a).get("n")) for a in _seq(raw.get("abil"))],
    }
    learned = {str(_obj(a).get("n")): _obj(a)["from"] for a in _seq(raw.get("abil")) if "from" in _obj(a)}
    if learned:
        entry["abilities_from_rank"] = learned
    if fastest:
        entry["fastest"] = {"speed_s": fastest.get("s"), "beast": fastest.get("n"), "level": fastest.get("l")}
    if raw.get("renamed"):
        entry["renamed_from"] = raw["renamed"]
    return entry


def _ability(raw: Mapping[str, Any]) -> dict[str, Any]:
    ranks = []
    for r in _seq(raw.get("ranks")):
        r = _obj(r)
        rank: dict[str, Any] = {"rank": r.get("r"), "level": r.get("l"), "text_en": r.get("en")}
        if "spd" in r:
            rank["speed_s"] = r["spd"]
        if "pct" in r:
            rank["attack_speed_pct"] = r["pct"]
        ranks.append(rank)
    return {
        "kind": raw.get("kind"),
        "focus": raw.get("focus"),
        "cooldown_s": raw.get("cd"),
        "new": bool(raw.get("new")),
        "families": [str(f) for f in _seq(raw.get("fams"))],
        "ranks": ranks,
        "taught": {str(k): v for k, v in _obj(raw.get("taught")).items()},
    }


def _taught(item: Any) -> dict[str, Any]:
    t = _seq(item)
    code = str(t[2]) if len(t) > 2 and t[2] is not None else ""
    label, meaning, certainty = TAUGHT_MARKS.get(code, UNKNOWN_MARK)
    return {
        "ability": t[0] if t else None,
        "rank": t[1] if len(t) > 1 else None,
        "mark": code,
        "label": label,
        "meaning": meaning,
        "certainty": certainty,
    }


def _beast(raw: Mapping[str, Any]) -> dict[str, Any]:
    code = str(raw.get("cf") or "classic")
    coords = {
        str(zone): [[p for p in _seq(point)] for point in _seq(points)] for zone, points in _obj(raw.get("c")).items()
    }
    return {
        "id": raw.get("id"),
        "name": {"en": raw.get("en"), "es": raw.get("es")},
        "family": raw.get("f"),
        "level": [raw.get("l1"), raw.get("l2")],
        "rank": raw.get("r"),
        "speed_s": raw.get("s"),
        "zones": [str(_obj(z).get("z")) for z in _seq(raw.get("z"))],
        "coords": coords,
        "taught": [_taught(t) for t in _seq(raw.get("t"))],
        "confirmation": {"code": code, "meaning": CONFIRMATIONS.get(code, "code de confirmation inconnu")},
        "other_names": [str(n) for n in _seq(raw.get("colEN"))],
        "sources": raw.get("src"),
    }


def _positions(raw: Any) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for map_id, points in _obj(raw).items():
        rows = []
        for p in _seq(points):
            p = _seq(p)
            row: dict[str, Any] = {
                "x": p[0] if p else None,
                "y": p[1] if len(p) > 1 else None,
                "t": p[2] if len(p) > 2 else None,
                "n": p[3] if len(p) > 3 else None,
            }
            if len(p) > 4:
                row["me"] = bool(p[4])
            rows.append(row)
        out[str(map_id)] = rows
    return out


def _names(raw: Any) -> dict[str, str]:
    return {str(k): str(v) for k, v in _obj(raw).items() if isinstance(v, str)}


def _observation(raw: Mapping[str, Any], reporters: int | None) -> dict[str, Any]:
    """Observation d'un PNJ (carte ou sauvegarde) par liste blanche : jamais `rp` ni autre champ inconnu."""
    entry: dict[str, Any] = {
        "level": [raw.get("l1"), raw.get("l2")],
        "classification": raw.get("c"),
        "speed_s": raw.get("sp"),
        "speed_samples": raw.get("spn"),
        "first_seen": raw.get("ft"),
        "last_seen": raw.get("lt"),
        "names": _names(raw.get("n")),
        "positions": _positions(raw.get("p")),
        "reporters": reporters,
    }
    if raw.get("f"):
        entry["family"] = raw["f"]
    return entry


def read_bestiary(addon_dir: Path) -> dict[str, Any]:
    """Base de l'addon : version, empreinte, date et build de la base, familles, capacités, bêtes, carte
    communautaire (PathNotFoundError si l'addon manque)."""
    data_path = addon_dir / DATA_FILE
    if not data_path.is_file():
        raise PathNotFoundError(
            "Addon Forever Bestiary",
            str(addon_dir),
            "installer l'addon (Interface/AddOns/ForeverBestiary) ou donner son dossier",
        )
    data = _assignments(data_path)
    base = _obj(data.get("ns.Data"))
    community_raw: dict[Any, Any] = {}
    if (addon_dir / COMMUNITY_FILE).is_file():
        community_raw = _obj(_assignments(addon_dir / COMMUNITY_FILE).get("ns.Data.community"))
    families_raw = _obj(base.get("families"))
    order = [str(k) for k in _seq(base.get("familyOrder"))] or sorted(str(k) for k in families_raw)
    order += sorted(str(k) for k in families_raw if str(k) not in order)
    community = {
        "date": community_raw.get("date"),
        "players": community_raw.get("players"),
        "beasts": {
            str(npc): _observation(_obj(o), len(_seq(_obj(o).get("rp"))))
            for npc, o in sorted(_obj(community_raw.get("obs")).items(), key=lambda kv: str(kv[0]))
        },
    }
    return {
        "info": {
            "name": ADDON_NAME,
            "folder": str(addon_dir),
            "version": _version(addon_dir),
            "fingerprint": fingerprint_folder(addon_dir),
            "date": base.get("date"),
            "client_build": base.get("clientBuild"),
            "community_date": community["date"],
            "community_players": community["players"],
        },
        "families": {key: _family(_obj(families_raw.get(key))) for key in order if key in families_raw},
        "abilities": {str(k): _ability(_obj(v)) for k, v in _obj(base.get("abilities")).items()},
        "zones_es": {str(k): str(v) for k, v in _obj(base.get("zonesES")).items()},
        "beasts": [_beast(_obj(b)) for b in _seq(data.get("ns.Data.beasts"))],
        "community": community,
    }


def read_bestiary_saved(path: Path) -> dict[str, Any]:
    """Sauvegarde `ForeverBestiaryDB` : mes observations et mes familiers, sans aucune donnée de tiers."""
    if not path.is_file():
        raise PathNotFoundError(
            "Sauvegarde de Forever Bestiary",
            str(path),
            "donner WTF/Account/<COMPTE>/SavedVariables/ForeverBestiary.lua",
        )
    try:
        raw = parse_lua_assignments(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise DataSchemaError(f"Forever Bestiary : sauvegarde {path} illisible ({exc}).") from exc
    db = _obj(raw.get(SAVED_VARIABLE))
    observations = {}
    for npc, o in sorted(_obj(db.get("obs")).items(), key=lambda kv: str(kv[0])):
        o = _obj(o)
        entry = _observation(o, o.get("nrp") if isinstance(o.get("nrp"), int) else len(_seq(o.get("rp"))))
        entry["mine"] = bool(o.get("me"))
        observations[str(npc)] = entry
    feed = [
        {k: _obj(f).get(k) for k in ("id", "map", "x", "y", "t", "k") if k in _obj(f)} for f in _seq(db.get("feed"))
    ]
    pets = {}
    for character, entry in _obj(db.get("pets")).items():
        entry = _obj(entry)
        pets[str(character)] = {
            "updated": entry.get("t"),
            "active": [
                {
                    "name": _obj(a).get("name"),
                    "family": _obj(a).get("fam"),
                    "level": _obj(a).get("lvl"),
                    "loyalty": _obj(a).get("loyalty"),
                    "npc": _obj(a).get("id"),
                    "slot": _obj(a).get("slot"),
                }
                for a in _seq(entry.get("active"))
            ],
        }
    history = {
        str(npc): {"how": _obj(h).get("how"), "t": _obj(h).get("t"), "character": _obj(h).get("c")}
        for npc, h in sorted(_obj(db.get("history")).items(), key=lambda kv: str(kv[0]))
    }
    return {
        "schema": db.get("schema"),
        "bundle": db.get("bundle"),
        "observations": observations,
        "feed": feed,
        "pets": pets,
        "history": history,
        "zone_ids": {str(k): v for k, v in _obj(db.get("zoneIds")).items()},
    }
