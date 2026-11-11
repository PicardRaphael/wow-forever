"""Noms officiels français des guides RestedXP (FR1), lus hors réseau, chacun avec sa source.

Ordre de priorité (plan FR1, section 4) : glossaire relevé dans les guides que RestedXP a déjà traduits
(`restedxp`), tables frFR du client téléchargées par la veille (`client` : SpellName, UiMap, AreaTable, ItemSparse,
ChrRaces, CreatureFamily), base de l'addon Questie installé (`questie`, communautaire, certitude `suppose`). Un nom
anglais qui mène à plusieurs noms français différents n'est jamais choisi ; un nom sans source reste en anglais et
figure au rapport. Aucun nom n'est traduit librement."""

from __future__ import annotations

import csv
import re
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
    ("AreaTable", "AreaName_lang", "zone"),
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


def unique_map(pairs: Iterable[tuple[Key, str]]) -> dict[Key, str]:
    """Nom anglais -> nom français, sans les noms anglais qui mènent à plusieurs noms français."""
    seen: dict[Key, set[str]] = defaultdict(set)
    for en, fr in pairs:
        if fr:
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
            if found:
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
