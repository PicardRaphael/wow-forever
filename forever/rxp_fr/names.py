"""Noms officiels français des guides RestedXP (FR1), lus hors réseau, chacun avec sa source.

Ordre de priorité (plan FR1, section 4) : glossaire relevé dans les guides que RestedXP a déjà traduits
(`restedxp`), tables frFR du client téléchargées par la veille (`client` : SpellName, UiMap, AreaTable, ItemSparse,
ChrRaces, CreatureFamily), base de l'addon Questie installé (`questie`, communautaire, certitude `suppose`). Un nom
anglais qui mène à plusieurs noms français différents n'est jamais choisi ; un nom sans source reste en anglais et
figure au rapport. Aucun nom n'est traduit librement."""

from __future__ import annotations

import base64
import csv
import json
import os
import re
import zlib
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

Key = str | int
Layer = Mapping[str, Mapping[Key, str]]

# Tables du client lues (locale par défaut et frFR) : (table, colonne du nom, sorte de nom). Format de wago.tools.
CLIENT_TABLES: tuple[tuple[str, str, str], ...] = (
    ("SpellName", "Name_lang", "spell"),
    ("UiMap", "Name_lang", "zone"),
    ("AreaTable", "AreaName_lang", "area"),  # après UiMap : AreaTable a des doublons de développement
    ("ItemSparse", "Display_lang", "item"),
    ("ChrRaces", "Name_lang", "race"),
    ("CreatureFamily", "Name_lang", "family"),
)
# Tables frFR téléchargées par la veille pour FR1 (question Q3), en plus de celles des règles de décodage.
FRENCH_NAME_TABLES = {"frFR": ["SpellName", "UiMap", "AreaTable", "ItemSparse", "ChrRaces", "CreatureFamily"]}
RXP_GUIDES = ("Interface", "AddOns", "RXPGuides", "Guides", "Forever")


def french_name_tables(wow_dir: Path | None) -> dict[str, list[str]]:
    """Tables frFR à télécharger pour FR1 : seulement si les guides RestedXP de Forever sont installés."""
    if wow_dir is None or not wow_dir.joinpath(*RXP_GUIDES).is_dir():
        return {}
    return {locale: list(tables) for locale, tables in FRENCH_NAME_TABLES.items()}


# Fichiers de l'addon Questie (base Classic chargée sur Forever, noms anglais ; traductions frFR).
QUESTIE_DB = {
    "npc": "Database/Classic/classicNpcDB.lua",
    "item": "Database/Classic/classicItemDB.lua",
    "object": "Database/Classic/classicObjectDB.lua",
    "quest": "Database/Classic/classicQuestDB.lua",
}
QUESTIE_FR = {
    "npc": "Localization/lookups/Classic/lookupNpcs/frFR.lua",
    "item": "Localization/lookups/Classic/lookupItems/frFR.lua",
    "object": "Localization/lookups/Classic/lookupObjects/frFR.lua",
    "quest": "Localization/lookups/Classic/lookupQuests/frFR.lua",
}
_ENTRY = re.compile(r"""^\[(\d+)\]\s*=\s*\{?\s*(['"])((?:\\.|(?!\2).)*)\2""", re.MULTILINE)
_ESCAPE = re.compile(r"\\(.)")


@dataclass(frozen=True)
class Name:
    fr: str
    source: str


def usable(name: str) -> bool:
    """Nom utilisable dans un guide : ni crochet (noms de développement du client, « [UNUSED] … », qui donneraient
    `[[` refusé par le Lua 5.1 du jeu dans une chaîne longue), ni code `|`, ni saut de ligne."""
    return bool(name) and not any(c in name for c in "[]|\r\n")


def unique_map(pairs: Iterable[tuple[Key, str]]) -> dict[Key, str]:
    """Nom anglais -> nom français, sans les noms anglais qui mènent à plusieurs noms français."""
    seen: dict[Key, set[str]] = defaultdict(set)
    for en, fr in pairs:
        if usable(fr):
            seen[en].add(fr)
    return {en: next(iter(frs)) for en, frs in seen.items() if len(frs) == 1}


class NameTable:
    """Couches de noms par ordre de priorité ; garde les noms manquants et les sources utilisées (rapport)."""

    def __init__(self, layers: Sequence[tuple[str, Layer]]) -> None:
        self.layers = list(layers)
        self.missing: Counter[tuple[str, Key]] = Counter()
        self.used: Counter[str] = Counter()

    def find(self, kind: str, key: Key) -> Name | None:
        for source, layer in self.layers:
            found = layer.get(kind, {}).get(key)
            if found and usable(found):
                return Name(found, source)
        return None

    def lookup(self, kind: str, key: Key, *, more: Sequence[str] = ()) -> Name | None:
        """Nom français de `key` dans la sorte `kind` (puis dans `more`), ou None (noté manquant)."""
        for k in (kind, *more):
            found = self.find(k, key)
            if found is not None:
                self.used[found.source] += 1
                return found
        self.missing[(kind, key)] += 1
        return None


def _read_csv(path: Path, column: str) -> list[tuple[int, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "ID" not in reader.fieldnames or column not in reader.fieldnames:
            return []
        return [(int(row["ID"]), row[column]) for row in reader if row["ID"].isdigit() and row[column]]


def client_layer(csv_dir: Path, *, locale: str = "frFR", default: str = "enUS") -> dict[str, dict[Key, str]]:
    """Noms du client par sorte (anglais -> français, et identifiant -> français pour les sorts) depuis
    `<csv_dir>/<locale>/<Table>.csv` ; une table absente est sautée."""
    pairs: dict[str, list[tuple[Key, str]]] = defaultdict(list)
    by_id: dict[str, dict[Key, str]] = defaultdict(dict)
    for table, column, kind in CLIENT_TABLES:
        english = dict(_read_csv(csv_dir / default / f"{table}.csv", column))
        french = dict(_read_csv(csv_dir / locale / f"{table}.csv", column))
        for ident, fr in french.items():
            by_id[f"{kind}_id"][ident] = fr
            if ident in english:
                pairs[kind].append((english[ident], fr))
    layer: dict[str, dict[Key, str]] = {kind: unique_map(items) for kind, items in pairs.items()}
    layer.update(by_id)
    return layer


def _entries(path: Path) -> dict[int, str]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {int(m[1]): _ESCAPE.sub(r"\1", m[3]) for m in _ENTRY.finditer(text)}


def questie_layer(addon_dir: Path) -> dict[str, dict[Key, str]]:
    """Noms de Questie : anglais (base Classic) -> français (lookups frFR) par identifiant commun, et identifiant ->
    français ; les quêtes sont rangées par identifiant (`quest`) et par titre anglais (`quest_title`)."""
    layer: dict[str, dict[Key, str]] = {}
    for kind, rel in QUESTIE_DB.items():
        english = _entries(addon_dir / rel)
        french = _entries(addon_dir / QUESTIE_FR[kind])
        named = unique_map((english[i], fr) for i, fr in french.items() if i in english)
        ids: dict[Key, str] = {i: fr for i, fr in french.items()}
        if kind == "quest":
            layer["quest"] = ids
            layer["quest_title"] = named
        else:
            layer[kind] = {**named, **ids}
    return layer


# --- QuestieDB (Questie 12.11.1 et suivants) ---------------------------------------------------------------------

QUESTIEDB_TYPES = {"npc": "Npc", "item": "Item", "object": "Object", "quest": "Quest"}
_TOC_LINE = re.compile(r"^## ([^:\s]+):\s?(.*)$")
_CHUNKS = re.compile(r"^~(\d+)~$")
_NAME_KEY = re.compile(r"\[\s*['\"]name['\"]\s*\]\s*=\s*(\d+)")


def _inflate(raw: bytes) -> bytes:
    for wbits in (15, -15, 31):  # zlib, deflate brut, gzip
        try:
            return zlib.decompress(raw, wbits)
        except zlib.error:
            continue
    raise ValueError("bloc compressé illisible")


def _text(value: object) -> str | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value if isinstance(value, str) and value else None


def questiedb_layer(addon_dir: Path, *, locale: str = "frFR") -> dict[str, dict[Key, str]]:
    """Noms de l'addon QuestieDB : base « cuite » dans les métadonnées du `.toc` (`## X-<Type>-IDS` : identifiants
    triés ; `## X-<Type>-<id>-S` : ligne anglaise ; `## X-l10n-<locale>-<Type>` : colonnes traduites alignées sur
    les identifiants ; valeur `~N~` : morceaux `-1`…`-N`), base64, zlib, CBOR. Format relevé dans `src/read/baked.lua`
    et `src/l10n/overlay.lua` de l'addon (lecture seule). Addon absent ou illisible : aucun nom."""
    from forever.pipeline.cbor import CborError, decode

    tocs = sorted(addon_dir.glob("QuestieDB*.toc"), key=lambda p: ("Forever" not in p.name, p.name))
    if not tocs:
        return {}
    meta: dict[str, str] = {}
    for line in tocs[0].read_text(encoding="utf-8", errors="replace").splitlines():
        m = _TOC_LINE.match(line)
        if m:
            meta[m[1]] = m[2]

    def stored(key: str) -> str | None:
        value = meta.get(key)
        chunks = _CHUNKS.match(value) if value else None
        if chunks:
            return "".join(meta.get(f"{key}-{i}", "") for i in range(1, int(chunks[1]) + 1))
        return value

    layer: dict[str, dict[Key, str]] = {}
    for kind, entity in QUESTIEDB_TYPES.items():
        meta_file = addon_dir / "src" / "meta" / f"{kind}Meta.lua"
        found = (
            _NAME_KEY.search(meta_file.read_text(encoding="utf-8", errors="replace")) if meta_file.is_file() else None
        )
        name_field = int(found[1]) if found else 1
        try:
            ids_raw, block_raw = stored(f"X-{entity}-IDS"), stored(f"X-l10n-{locale}-{entity}")
            if not ids_raw or not block_raw:
                continue
            ids = decode(_inflate(base64.b64decode(ids_raw)))
            block = decode(_inflate(base64.b64decode(block_raw)))
        except (ValueError, CborError):
            continue
        if not isinstance(ids, list) or not isinstance(block, list) or not block or not isinstance(block[0], list):
            continue
        by_id: dict[Key, str] = {}
        pairs: list[tuple[Key, str]] = []
        for ident, french in zip(ids, block[0], strict=False):
            fr = _text(french)
            if not isinstance(ident, int) or fr is None:
                continue
            by_id[ident] = fr
            row_raw = stored(f"X-{entity}-{ident}-S")
            try:
                row = decode(base64.b64decode(row_raw)) if row_raw else None
            except (ValueError, CborError):
                row = None
            english = _text(row.get(name_field)) if isinstance(row, dict) else None
            if english:
                pairs.append((english, fr))
        if kind == "quest":
            layer["quest"] = by_id
            layer["quest_title"] = unique_map(pairs)
        else:
            layer[kind] = {**unique_map(pairs), **by_id}
    return {k: v for k, v in layer.items() if v}


# --- copie des noms de Questie (hors dépôt) ---------------------------------------------------------------------


def _save_layer(path: Path, layer: Mapping[str, Mapping[Key, str]]) -> None:
    doc = {
        "schema_version": 1,
        "note": "Dernière lecture des noms de Questie ou QuestieDB (FR1, hors dépôt).",
        "kinds": {
            kind: {
                "ids": {str(k): v for k, v in names.items() if isinstance(k, int)},
                "names": {k: v for k, v in names.items() if isinstance(k, str)},
            }
            for kind, names in layer.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(json.dumps(doc, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    os.replace(tmp, path)


def _load_layer(path: Path) -> dict[str, dict[Key, str]]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    layer: dict[str, dict[Key, str]] = {}
    for kind, value in (doc.get("kinds") or {}).items() if isinstance(doc, dict) else []:
        names: dict[Key, str] = {int(k): v for k, v in (value.get("ids") or {}).items() if k.isdigit()}
        names.update(value.get("names") or {})
        layer[kind] = names
    return layer


def questie_names(questie_dir: Path, cache: Path) -> dict[str, dict[Key, str]]:
    """Noms de Questie : ancienne base de l'addon Questie, sinon addon QuestieDB voisin (Questie 12.11.1 et
    suivants), sinon la dernière lecture gardée dans `cache` (une réorganisation de Questie ne fait plus revenir
    l'anglais). Une lecture réussie remplace la copie."""
    layer = questie_layer(questie_dir)
    if not any(layer.values()):
        layer = questiedb_layer(questie_dir.parent / "QuestieDB")
    if any(layer.values()):
        _save_layer(cache, layer)
        return layer
    return _load_layer(cache)
