"""Profils EllesmereUI par personnage et par rôle (EX1, bloc F, décision 267) : chaîne `!EUI_` (enveloppe version 3,
`type="full"`, `client="forever"`) construite sur un profil de base du joueur, lu en local dans la sauvegarde
`EllesmereUI.lua` (jamais écrite) ou collé (`!EUI_`). forever-core n'en remplit que les sorts du gestionnaire de
recharges (`cdmSpells`, clé de spécialisation du personnage) et les rappels de buffs (`customIDs`), tirés des sorts de
la classe appris au niveau ; tout le reste du profil de base est recopié tel quel (choix du joueur).

Format relevé dans EllesmereUI 9.5.4 (propriétaire, jamais recopié) : sérialiseur maison (`s<octets>:<texte>`,
`n<nombre>;`, `T`, `F`, `N`, table `{` partie tableau puis paires `K<clé><valeur>` `}`), puis `CompressDeflate` et
`EncodeForPrint` de LibDeflate (codec commun d'EX1). Ordre des clés fixé ici (trié) : sortie déterministe."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from forever.config import Deps
from forever.engine.model import GameData
from forever.errors import InvalidArgumentError
from forever.exports.codec import ExportFormatError, decode_for_print, deflate, encode_for_print, inflate

PREFIX = "!EUI_"
PAYLOAD_VERSION = 3
SAVED_VARIABLES = "EllesmereUI.lua"
ELLESMERE_VERSION = "9.5.4"
ROLE_LABELS = {"dps": "DPS", "heal": "Soins", "tank": "Tank"}
CDM_BARS = ("cooldowns", "utility")
BUFF_ADDON = "EllesmereUIAuraBuffReminders"
DROPPED_SPEC_KEYS = ("_barFilterModelV6", "_importGhostMode")  # comme l'export d'EllesmereUI
GHOST_BAR = "__ghost_cd"
MAX_BYTES = 4 * 1024 * 1024  # borne de lecture d'une chaîne collée (profil complet)
IMPORT_STEPS = "en jeu : /eui, Profiles, Import, coller le code et nommer le profil « {name} », puis /reload"


@dataclass(frozen=True)
class BaseProfile:
    """Profil de base du joueur : nom, données du profil (`profileData`), sorts du gestionnaire de recharges par clé
    de spécialisation, clé du personnage si EllesmereUI l'a gardée (`lastSpecByChar`), source, méta d'export."""

    name: str
    data: Mapping[str, Any]
    cdm: Mapping[str, Any]
    spec_key: str | None
    source: str
    meta: Mapping[str, Any] = field(default_factory=dict)


# --- sérialiseur ----------------------------------------------------------------------------------------------------


def _number(value: float) -> bytes:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"nombre non fini refusé : {value}")
        if value.is_integer() and abs(value) < 2**53:
            return str(int(value)).encode()
        return repr(value).encode()
    return str(value).encode()


def _sort_key(key: Any) -> tuple[int, Any]:
    if isinstance(key, bool):
        return (2, key)
    if isinstance(key, int | float):
        return (0, key)
    return (1, key)


def _write(value: Any, out: bytearray) -> None:
    if value is None:
        out += b"N"
    elif isinstance(value, bool):
        out += b"T" if value else b"F"
    elif isinstance(value, int | float):
        out += b"n" + _number(value) + b";"
    elif isinstance(value, str):
        raw = value.encode("utf-8")
        out += b"s" + str(len(raw)).encode() + b":" + raw
    elif isinstance(value, list | tuple):
        out += b"{"
        for item in value:
            _write(item, out)
        out += b"}"
    elif isinstance(value, Mapping):
        n = 0
        while (n + 1) in value and not any(isinstance(k, bool) for k in value if k == n + 1):
            n += 1
        out += b"{"
        for i in range(1, n + 1):
            _write(value[i], out)
        for key in sorted((k for k in value if not (isinstance(k, int) and 1 <= k <= n)), key=_sort_key):
            if not isinstance(key, str | int | float) or isinstance(key, bool):
                raise TypeError(f"clé non sérialisable : {type(key).__name__}")
            out += b"K"
            _write(key, out)
            _write(value[key], out)
        out += b"}"
    else:
        raise TypeError(f"type non sérialisable pour EllesmereUI : {type(value).__name__}")


def ellesmere_serialize(value: Any) -> bytes:
    """Valeur Python → texte du sérialiseur d'EllesmereUI (octets : la longueur d'une chaîne compte des octets)."""
    out = bytearray()
    _write(value, out)
    return bytes(out)


def _read(data: bytes, pos: int) -> tuple[Any, int]:
    if pos >= len(data):
        raise ExportFormatError("profil tronqué")
    tag = data[pos : pos + 1]
    if tag == b"s":
        colon = data.find(b":", pos + 1)
        if colon < 0 or not data[pos + 1 : colon].isdigit():
            raise ExportFormatError("chaîne illisible dans le profil")
        size = int(data[pos + 1 : colon])
        raw = data[colon + 1 : colon + 1 + size]
        if len(raw) != size:
            raise ExportFormatError("chaîne tronquée dans le profil")
        return raw.decode("utf-8", errors="replace"), colon + 1 + size
    if tag == b"n":
        semi = data.find(b";", pos + 1)
        if semi < 0:
            raise ExportFormatError("nombre illisible dans le profil")
        text = data[pos + 1 : semi].decode("ascii", errors="replace")
        try:
            number = float(text)
        except ValueError:
            raise ExportFormatError(f"nombre illisible dans le profil : {text}") from None
        return (int(number) if number.is_integer() and abs(number) < 2**53 else number), semi + 1
    if tag in (b"T", b"F"):
        return tag == b"T", pos + 1
    if tag == b"N":
        return None, pos + 1
    if tag == b"{":
        array: list[Any] = []
        pairs: dict[Any, Any] = {}
        p = pos + 1
        while True:
            if p >= len(data):
                raise ExportFormatError("table non fermée dans le profil")
            c = data[p : p + 1]
            if c == b"}":
                p += 1
                break
            if c == b"K":
                key, p = _read(data, p + 1)
                val, p = _read(data, p)
                if key is not None:
                    pairs[key] = val
            else:
                val, p = _read(data, p)
                array.append(val)
        if not pairs:
            return array, p
        return {**dict(enumerate(array, 1)), **pairs}, p
    raise ExportFormatError(f"marque inconnue dans le profil : {tag!r}")


def ellesmere_deserialize(data: bytes) -> Any:
    """Texte du sérialiseur d'EllesmereUI → valeur Python (table sans clé `K` : `list`, sinon `dict`)."""
    value, _ = _read(data, 0)
    return value


def read_ellesmere(text: str) -> dict[str, Any]:
    """Enveloppe d'une chaîne `!EUI_` ; version autre que 3 refusée comme le fait EllesmereUI."""
    body = text.strip()
    if not body.startswith(PREFIX):
        raise ExportFormatError("chaîne qui ne commence pas par !EUI_")
    payload = ellesmere_deserialize(inflate(decode_for_print(body[len(PREFIX) :]), MAX_BYTES))
    if not isinstance(payload, dict):
        raise ExportFormatError("profil EllesmereUI illisible")
    if payload.get("version") != PAYLOAD_VERSION:
        raise ExportFormatError(f"profil EllesmereUI de version {payload.get('version')} (attendu {PAYLOAD_VERSION})")
    return payload


# --- profil de base -------------------------------------------------------------------------------------------------


def _saved_variables(wow_dir: Path) -> list[Path]:
    root = wow_dir / "WTF" / "Account"
    return sorted(root.glob(f"*/SavedVariables/{SAVED_VARIABLES}")) if root.is_dir() else []


def read_base_profile(wow_dir: Path, character_key: str, name: str | None = None) -> BaseProfile:
    """Profil de base lu dans la sauvegarde `EllesmereUI.lua` (lecture seule) : profil nommé, sinon le profil actif ;
    sauvegarde du compte qui connaît le personnage d'abord. `InvalidArgumentError` sans sauvegarde ni profil."""
    from forever.pipeline.lua_table import parse_lua_assignments

    candidates = []
    for path in _saved_variables(wow_dir):
        db = parse_lua_assignments(path.read_text(encoding="utf-8", errors="replace")).get("EllesmereUIDB")
        if isinstance(db, dict) and isinstance(db.get("profiles"), dict):
            known = isinstance(db.get("lastSpecByChar"), dict) and character_key in db["lastSpecByChar"]
            candidates.append((not known, str(path), db))
    if not candidates:
        raise InvalidArgumentError(
            "Aucun profil de base EllesmereUI (sauvegarde EllesmereUI.lua introuvable).",
            "lancer le jeu une fois avec EllesmereUI, ou coller une chaîne !EUI_ (--paste)",
        )
    _, _, db = min(candidates, key=lambda c: (c[0], c[1]))
    chosen = name or str(db.get("activeProfile") or "")
    profiles = db["profiles"]
    if chosen not in profiles:
        raise InvalidArgumentError(
            f"Profil de base EllesmereUI « {chosen} » absent.", "profils : " + ", ".join(sorted(map(str, profiles)))
        )
    buckets = ((db.get("spellAssignments") or {}).get("profiles") or {}) if isinstance(db, dict) else {}
    bucket = buckets.get(chosen) if isinstance(buckets, dict) else None
    cdm = (bucket or {}).get("specProfiles") or {}
    last = (db.get("lastSpecByChar") or {}).get(character_key)
    meta = {"euiScale": db["ppUIScale"]} if isinstance(db.get("ppUIScale"), int | float) else {}
    return BaseProfile(
        name=chosen,
        data=profiles[chosen],
        cdm=cdm if isinstance(cdm, dict) else {},
        spec_key=str(last) if last is not None else None,
        source="sauvegarde",
        meta=meta,
    )


def base_from_string(text: str, character_key: str | None = None) -> BaseProfile:
    """Profil de base tiré d'une chaîne `!EUI_` collée : ses données, ses sorts du gestionnaire de recharges."""
    try:
        payload = read_ellesmere(text)
    except ExportFormatError as err:
        raise InvalidArgumentError(f"Chaîne EllesmereUI illisible : {err}.", "coller la chaîne entière") from err
    data = payload.get("data")
    if not isinstance(data, dict):
        raise InvalidArgumentError("Chaîne EllesmereUI sans profil.", "exporter le profil complet dans EllesmereUI")
    cdm = data.get("cdmSpells")
    meta = payload.get("meta")
    return BaseProfile(
        name=str(data.get("name") or "chaîne collée"),
        data={k: v for k, v in data.items() if k != "cdmSpells"},
        cdm=cdm if isinstance(cdm, dict) else {},
        spec_key=None,
        source="chaîne collée",
        meta=meta if isinstance(meta, dict) else {},
    )


# --- sorts d'un rôle ------------------------------------------------------------------------------------------------


@cache
def role_catalogue() -> dict[str, dict[str, dict[str, list[str]]]]:
    """Catalogue `roles.yaml` : classe → rôle → `cooldowns`, `utility`, `buffs` (clés de sorts)."""
    text = resources.files("forever.exports").joinpath("roles.yaml").read_text(encoding="utf-8")
    data: dict[str, dict[str, dict[str, list[str]]]] = yaml.safe_load(text)
    return data


def _learned_ranks(spell: Mapping[str, Any], level: int, taken: set[str]) -> list[Mapping[str, Any]]:
    talent = spell.get("talent")
    if talent is not None:
        key = talent.get("key") if isinstance(talent, Mapping) else talent
        if key not in taken:
            return []
        known = [r for r in spell.get("ranks") or [] if not r.get("level") or r["level"] <= level]
        return known
    return [r for r in spell.get("ranks") or [] if r.get("level") and r["level"] <= level]


def role_spells(
    gd: GameData, class_name: str, role: str, level: int, talents: Mapping[str, int] | None = None
) -> dict[str, list[int]]:
    """Sorts du rôle appris au niveau, par barre : `cooldowns` et `utility` (seulement un rang dont la recharge
    dépasse le temps de recharge global), `buffs` (rappels) ; chaque rang appris, dans l'ordre du catalogue."""
    from forever.profile import normalize_class

    cls = normalize_class(class_name)
    knowledge = gd.classes.get(cls)
    groups = role_catalogue().get(cls, {}).get(role)
    if knowledge is None or groups is None:
        return {"cooldowns": [], "utility": [], "buffs": []}
    taken = {k for k, r in (talents or {}).items() if r > 0}
    out: dict[str, list[int]] = {}
    for bar in ("cooldowns", "utility", "buffs"):
        ids: list[int] = []
        for key in groups.get(bar) or []:
            spell = knowledge.spells.get(key)
            if spell is None:
                continue
            for rank in _learned_ranks(spell, level, taken):
                if bar != "buffs" and not (rank.get("cooldown_s") and rank["cooldown_s"] > (rank.get("gcd_s") or 0)):
                    continue
                if int(rank["spell_id"]) not in ids:
                    ids.append(int(rank["spell_id"]))
        out[bar] = ids
    return out


# --- profil rendu ---------------------------------------------------------------------------------------------------


def ellesmere_profile(
    base: BaseProfile, *, spec_key: str, bars: Mapping[str, Sequence[int]], buff_ids: Sequence[int]
) -> dict[str, Any]:
    """Enveloppe `{version=3, type="full", data, meta, client="forever"}` : données du profil de base recopiées, sauf
    `cdmSpells` (seulement la clé du personnage, barres `bars` remplacées, barre fantôme retirée) et les rappels de
    buffs (`customIDs`)."""
    data = copy.deepcopy(dict(base.data))
    spec = copy.deepcopy(dict(base.cdm.get(spec_key) or {}))
    for key in DROPPED_SPEC_KEYS:
        spec.pop(key, None)
    bar_spells = dict(spec.get("barSpells") or {})
    bar_spells.pop(GHOST_BAR, None)
    for bar, ids in bars.items():
        current = dict(bar_spells.get(bar) or {})
        current["assignedSpells"] = list(ids)
        bar_spells[bar] = current
    spec["barSpells"] = bar_spells
    data["cdmSpells"] = {spec_key: spec}
    addons = data.setdefault("addons", {})
    reminders = addons.setdefault(BUFF_ADDON, {})
    forever = reminders.setdefault("forever", {})
    forever["customIDs"] = list(buff_ids)
    return {
        "version": PAYLOAD_VERSION,
        "type": "full",
        "data": data,
        "meta": dict(base.meta),
        "client": "forever",
    }


def _spec_key_from_spells(base: BaseProfile, class_ids: set[int]) -> str | None:
    """Clé de spécialisation dont les barres portent le plus de sorts de la classe (aucune : None)."""
    best: tuple[int, str] | None = None
    for key, spec in base.cdm.items():
        bars = (spec or {}).get("barSpells") if isinstance(spec, Mapping) else None
        seen: set[int] = set()
        for name, bar in (bars or {}).items():
            if name == GHOST_BAR or not isinstance(bar, Mapping):
                continue
            assigned = bar.get("assignedSpells")
            values = assigned.values() if isinstance(assigned, Mapping) else assigned or []
            seen |= {int(v) for v in values if isinstance(v, int | float)}
        score = len(seen & class_ids)
        if score and (best is None or score > best[0]):
            best = (score, str(key))
    return best[1] if best else None


def ellesmere_export(
    deps: Deps,
    character: str,
    realm: str,
    class_name: str,
    level: int,
    role: str,
    *,
    base_name: str | None = None,
    paste: str | None = None,
    spec_key: str | None = None,
    talents: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Code `!EUI_` du profil « <personnage> - <rôle> » : rôle tenu par la classe (`roles.yaml`, table de
    docs/SPEC.md), profil de base lu en local (ou collé), clé de spécialisation du personnage (gardée par EllesmereUI,
    sinon celle dont les barres portent les sorts de la classe, sinon `spec_key`), sorts appris au niveau. Certitude
    `suppose` (choix de catalogue ; import jamais vérifié en jeu, question EUI1)."""
    from forever.gamedata import build_game_data
    from forever.profile import normalize_class
    from forever.provenance import local_provenance
    from forever.store import load_version

    cls = normalize_class(class_name)
    roles = role_catalogue().get(cls) or {}
    if role not in roles:
        held = ", ".join(sorted(roles)) or "aucun"
        raise InvalidArgumentError(f"Rôle « {role} » non tenu par la classe {cls}.", f"rôles de la classe : {held}")
    key = f"{character} - {realm}"
    if paste:
        base = base_from_string(paste, key)
    elif deps.wow_dir is not None:
        base = read_base_profile(deps.wow_dir, key, base_name)
    else:
        raise InvalidArgumentError(
            "Aucun profil de base EllesmereUI (FOREVER_WOW_DIR non réglé).", "régler FOREVER_WOW_DIR ou coller --paste"
        )
    gd = build_game_data(load_version(deps))
    knowledge = gd.classes[cls]
    class_ids = {int(r["spell_id"]) for s in knowledge.spells.values() for r in s.get("ranks") or []}
    chosen = spec_key or base.spec_key or _spec_key_from_spells(base, class_ids)
    if chosen is None:
        raise InvalidArgumentError(
            f"Clé de spécialisation de {character} inconnue dans le profil de base EllesmereUI.",
            "se connecter une fois avec le personnage, ou donner --spec-key",
        )
    spells = role_spells(gd, cls, role, level, talents)
    payload = ellesmere_profile(base, spec_key=chosen, bars={b: spells[b] for b in CDM_BARS}, buff_ids=spells["buffs"])
    code = PREFIX + encode_for_print(deflate(ellesmere_serialize(payload)))
    profile_name = f"{character} - {ROLE_LABELS[role]}"
    notes = [
        f"format !EUI_ relevé dans EllesmereUI {ELLESMERE_VERSION}, jamais importé en jeu (question EUI1)",
        f"profil de base « {base.name} » ({base.source}), recopié sauf cdmSpells et customIDs",
        f"clé de spécialisation {chosen} ({'gardée par EllesmereUI' if chosen == base.spec_key else 'choisie'})",
        "sorts du rôle : catalogue forever/exports/roles.yaml, rangs appris au niveau (classes.json), supposé",
    ]
    return {
        "kind": "ellesmere",
        "character": character,
        "realm": realm,
        "class": cls,
        "level": level,
        "role": role,
        "profile_name": profile_name,
        "base": {"name": base.name, "source": base.source},
        "spec_key": chosen,
        "spells": spells,
        "code": code,
        "import": IMPORT_STEPS.format(name=profile_name),
        "addon": {"name": "EllesmereUI", "version": ELLESMERE_VERSION, "format": PREFIX},
        "certainty": "suppose",
        "provenance": local_provenance(deps, certainty="suppose", assumptions=notes),
    }
