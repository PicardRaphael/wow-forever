"""Addons d'équipement lus en local (CJ1, bloc 4, décisions 272 et 276) : ce que les addons calculent déjà, jamais
recopié dans le dépôt (décision 133), certitude au mieux `suppose`.

- Forever Guide (`ForeverGuide/GearData.lua`, `ns.GEAR_DATA`) : une ligne par objet, « id emplacement sous-classe
  niveau_requis rareté flags masque_de_classes stats » (stats `clé=valeur` séparées par des virgules ; pour toucher et
  critique, 1 point = 1 %).
- Naowh Forever (`NaowhForever_BiS/BiS/Data/BiS.lua`, `ns.BiSData`) : listes BiS classées par spécialisation et
  emplacement, et `sources` (lieu de butin de chaque objet).
- Forever Companion (`ForeverCompanion/Data/Bis.lua`, `B["Classe"]["Spé"]["BETA"]`, et `Data/Weights.lua`,
  `ForeverCompanionData.weights`) : listes BiS par emplacement nommé, échelles de statistiques par classe.
- GearQuest Forever (`GearQuestForever_<CLASSE>/*.lua`, `GQ.Data.<classe>Picks`) : choix de leveling par plage de
  niveaux (objet, emplacement, niveaux, rang, spécialisation, camp, score).

Un addon absent rend une lecture vide. Aucun chiffre de jeu ici."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from forever.pipeline.lua_table import parse_lua_value_at

GUIDE_GEAR = ("ForeverGuide", "GearData.lua")
NAOWH_BIS = ("NaowhForever_BiS", "BiS", "Data", "BiS.lua")
COMPANION_BIS = ("ForeverCompanion", "Data", "Bis.lua")
COMPANION_WEIGHTS = ("ForeverCompanion", "Data", "Weights.lua")
NAOWH_WEIGHTS = ("NaowhForever_BiS", "StatWeights", "Data", "Defaults.lua")
_NAOWH_TEMPLATE = re.compile(r"^local\s+([A-Z_]+)\s*=\s*(?=\{)", re.MULTILINE)
_NAOWH_SPEC = re.compile(r'Spec\(\s*"([A-Z]+)"\s*,\s*"([a-z-]+)"\s*,\s*"([^"]*)"\s*,\s*([A-Z_]+)\s*,\s*(?=\{)')
_NAOWH_DATE = re.compile(r'StatWeightDefaultsUpdated\s*=\s*"(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})"')
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
GEARQUEST_PREFIX = "GearQuestForever_"
_GEAR_LINE = re.compile(r"^(\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)(?: (\S*))?$")
_COMPANION_SPEC = re.compile(r'^B\["([^"]+)"\]\["([^"]+)"\]\s*=\s*', re.MULTILINE)


@dataclass(frozen=True)
class GearItem:
    id: int
    inv_type: int  # emplacement de Forever Guide (INVTYPE)
    subclass: int
    req_level: int
    quality: int
    classes: int  # masque de classes (0 : toutes)
    stats: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class BisList:
    class_token: str
    key: str
    name: str
    updated: str
    slots: dict[int, tuple[int, ...]]  # emplacement d'inventaire -> objets classés


@dataclass(frozen=True)
class Scale:
    label: str
    tab: int
    weights: dict[str, float]


class GearPick(NamedTuple):
    item: int
    slot: str
    min_level: int
    max_level: int
    rank: int
    spec: str
    faction: str
    score: float


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def _value_after(text: str, marker: str) -> Any:
    i = text.find(marker)
    if i < 0:
        return None
    return parse_lua_value_at(text, i + len(marker))[0]


def _ints(values: Any) -> tuple[int, ...]:
    items = values.values() if isinstance(values, dict) else values or ()
    return tuple(int(v) for v in items if isinstance(v, int))


_LUA_FLAGS = re.compile(r"\[(\d+)\]=true")
_LUA_STRINGS = re.compile(r'\[(\d+)\]="([^"]*)"')


def _lua_table(text: str, head: str) -> str:
    """Corps `{...}` de la table qui suit `head` (`local gear=`), sans accolade imbriquée ; vide si absente."""
    start = text.find(head)
    if start < 0:
        return ""
    end = text.find("}", start)
    return text[start + len(head) : end] if end > 0 else ""


def _apply_item_builds(addons: Path, lines: list[str]) -> list[str]:
    """Deltas `ItemBuild<build>.lua` de Forever Guide, dans l'ordre de son `.toc`, appliqués aux lignes de
    `GearData.lua` comme le fait l'addon au chargement (relevé de 1.60.1.70425) : emplacement, sous-classe, niveau,
    rareté remplacés ; classes si non nulles ; statistiques seulement pour un objet de `BETA_STAT_CHANGED` ; objet de
    `removed` retiré ; objet nouveau ajouté (flags 0)."""
    folder = addons / GUIDE_GEAR[0]
    toc = _read(folder / f"{GUIDE_GEAR[0]}.toc") or ""
    names = [ln.strip() for ln in toc.splitlines() if re.fullmatch(r"ItemBuild\d+\.lua", ln.strip())]
    for name in names:
        text = _read(folder / name)
        if not text or "local gear=" not in text:
            continue
        gear = {int(k): v.split() for k, v in _LUA_STRINGS.findall(_lua_table(text, "local gear="))}
        removed = {int(k) for k in _LUA_FLAGS.findall(_lua_table(text, "local removed="))}
        changed = {int(k) for k in _LUA_FLAGS.findall(_lua_table(text, "ns.BETA_STAT_CHANGED="))}
        seen: set[int] = set()
        out: list[str] = []
        for line in lines:
            a = line.split()
            if not a or not a[0].isdigit():
                out.append(line)
                continue
            item = int(a[0])
            if item in removed:
                continue
            b = gear.get(item)
            if b is not None and len(a) >= 7:
                seen.add(item)
                a[1:5] = b[0:4]
                if len(b) > 4 and b[4] != "0":
                    a[6] = b[4]
                if item in changed:
                    a = [*a[:7], b[5] if len(b) > 5 else ""]
                line = " ".join(a).rstrip()
            out.append(line)
        for item, b in gear.items():
            if item not in seen and item not in removed:
                out.append(" ".join([str(item), *b[0:4], "0", b[4] if len(b) > 4 else "0", *(b[5:6])]).rstrip())
        lines = out
    return lines


def read_guide_gear(addons: Path) -> dict[int, GearItem]:
    """Statistiques des objets de Forever Guide, par identifiant, deltas `ItemBuild<build>.lua` appliqués comme
    l'addon (sinon les statistiques d'un build ancien : 291 objets changés et 20 retirés au build 70425)."""
    text = _read(addons.joinpath(*GUIDE_GEAR))
    if text is None:
        return {}
    out: dict[int, GearItem] = {}
    for line in _apply_item_builds(addons, text.splitlines()):
        m = _GEAR_LINE.match(line.strip())
        if not m:
            continue
        stats: dict[str, float] = {}
        for part in (m.group(8) or "").split(","):
            key, sep, raw = part.partition("=")
            if sep and key:
                try:
                    stats[key] = float(raw)
                except ValueError:
                    continue
        item_id, inv, sub, req, quality, _flags, classes = (int(m.group(i)) for i in range(1, 8))
        out[item_id] = GearItem(item_id, inv, sub, req, quality, classes, stats)
    return out


def read_naowh_bis(addons: Path) -> tuple[dict[str, BisList], dict[int, str]]:
    """Listes BiS de Naowh Forever par clé de spécialisation (`fire-mage`…) et lieux de butin par objet."""
    text = _read(addons.joinpath(*NAOWH_BIS))
    data = _value_after(text, "ns.BiSData = ") if text else None
    if not isinstance(data, dict):
        return {}, {}
    specs = data.get("specs") or {}
    lists: dict[str, BisList] = {}
    for spec in specs.values() if isinstance(specs, dict) else specs:
        if not isinstance(spec, dict) or not isinstance(spec.get("key"), str):
            continue
        slots = spec.get("slots") or {}
        lists[spec["key"]] = BisList(
            class_token=str(spec.get("class") or ""),
            key=spec["key"],
            name=str(spec.get("name") or spec["key"]),
            updated=str(spec.get("updated") or ""),
            slots={int(k): _ints(v) for k, v in slots.items() if isinstance(k, int)},
        )
    raw_sources = data.get("sources") or {}
    sources = {int(k): str(v) for k, v in raw_sources.items() if isinstance(k, int) and isinstance(v, str)}
    return lists, sources


def read_companion_bis(addons: Path) -> dict[tuple[str, str], dict[str, tuple[int, ...]]]:
    """Listes BiS de Forever Companion : (classe, spécialisation) -> emplacement nommé -> objets classés."""
    text = _read(addons.joinpath(*COMPANION_BIS))
    if text is None:
        return {}
    out: dict[tuple[str, str], dict[str, tuple[int, ...]]] = {}
    for m in _COMPANION_SPEC.finditer(text):
        value = parse_lua_value_at(text, m.end())[0]
        phase = value.get("BETA") if isinstance(value, dict) else None
        rows = phase.values() if isinstance(phase, dict) else phase or ()
        slots: dict[str, tuple[int, ...]] = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("s"), str):
                continue
            entries = row.get("i") or {}
            ids = [
                e.get(1) if isinstance(e, dict) else (e[0] if isinstance(e, list) and e else None)
                for e in (entries.values() if isinstance(entries, dict) else entries)
            ]
            slots[row["s"]] = tuple(int(i) for i in ids if isinstance(i, int))
        out[(m.group(1), m.group(2))] = slots
    return out


def read_companion_scales(addons: Path) -> dict[str, list[Scale]]:
    """Échelles de statistiques de Forever Companion par jeton de classe (`MAGE`…)."""
    text = _read(addons.joinpath(*COMPANION_WEIGHTS))
    data = _value_after(text, "ForeverCompanionData.weights = ") if text else None
    if not isinstance(data, dict):
        return {}
    out: dict[str, list[Scale]] = {}
    for token, scales in data.items():
        rows = scales.values() if isinstance(scales, dict) else scales or ()
        for s in rows:
            if isinstance(s, dict) and isinstance(s.get("w"), dict):
                weights = {str(k): float(v) for k, v in s["w"].items() if isinstance(v, int | float)}
                out.setdefault(str(token), []).append(Scale(str(s.get("label") or ""), int(s.get("tab") or 0), weights))
    return out


class NaowhSpecWeights(NamedTuple):
    class_token: str
    name: str
    weights: dict[str, float]  # clés de Naowh (`spell`, `heal`, `shit`…), gabarit de rôle fusionné


class NaowhWeights(NamedTuple):
    updated: str | None  # date ISO de `StatWeightDefaultsUpdated`
    specs: dict[str, NaowhSpecWeights]  # clé de spécialisation (`balance-druid`) -> poids


def read_naowh_weights(addons: Path) -> NaowhWeights | None:
    """Poids par défaut de Naowh Forever (`StatWeights/Data/Defaults.lua`, niveau 60, écrits à la main) : gabarits de
    rôle (`local CASTER = {…}`) puis appels `Spec(classe, clé, nom, gabarit, {propres})`, fusionnés comme l'addon (le
    poids propre l'emporte) ; lus sans exécuter de Lua. None sans l'addon."""
    text = _read(addons.joinpath(*NAOWH_WEIGHTS))
    if not text:
        return None
    templates: dict[str, dict[str, float]] = {}
    for m in _NAOWH_TEMPLATE.finditer(text):
        templates[m.group(1)] = _numbers(parse_lua_value_at(text, m.end())[0])
    specs: dict[str, NaowhSpecWeights] = {}
    for m in _NAOWH_SPEC.finditer(text):
        own = _numbers(parse_lua_value_at(text, m.end())[0])
        specs[m.group(2)] = NaowhSpecWeights(m.group(1), m.group(3), {**templates.get(m.group(4), {}), **own})
    d = _NAOWH_DATE.search(text)
    updated = None
    if d and d.group(2) in _MONTHS:
        updated = f"{d.group(3)}-{_MONTHS.index(d.group(2)) + 1:02d}-{int(d.group(1)):02d}"
    return NaowhWeights(updated, specs)


def _numbers(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {str(k): float(v) for k, v in value.items() if isinstance(v, int | float) and not isinstance(v, bool)}


def read_gearquest_picks(addons: Path, class_token: str) -> list[GearPick]:
    """Choix de leveling de GearQuest Forever pour une classe (`GQ.Data.<classe>Picks`), dans l'ordre du fichier."""
    folder = addons / f"{GEARQUEST_PREFIX}{class_token.upper()}"
    marker = f"GQ.Data.{class_token.lower()}Picks = "
    out: list[GearPick] = []
    for path in sorted(folder.glob("*.lua")) if folder.is_dir() else []:
        text = _read(path) or ""
        if marker not in text:
            continue
        rows = _value_after(text, marker)
        for row in rows.values() if isinstance(rows, dict) else rows or ():
            values: list[Any] = [row.get(i) for i in range(1, 9)] if isinstance(row, dict) else list(row)[:8]
            if len(values) == 8 and isinstance(values[0], int) and all(v is not None for v in values):
                item, slot, low, high, rank, spec, faction, score = values
                out.append(GearPick(item, str(slot), int(low), int(high), int(rank), str(spec), str(faction),
                                    float(score)))  # fmt: skip
    return out


def read_gearquest_facts(addons: Path, class_token: str) -> dict[int, dict[str, Any]]:
    """Fiches d'objets de GearQuest Forever (`GQ.Data.<classe>ItemFacts`) : nom, zone, sorte de source, consigne."""
    folder = addons / f"{GEARQUEST_PREFIX}{class_token.upper()}"
    marker = f"GQ.Data.{class_token.lower()}ItemFacts = "
    out: dict[int, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.lua")) if folder.is_dir() else []:
        text = _read(path) or ""
        if marker not in text:
            continue
        facts = _value_after(text, marker)
        for item, row in (facts or {}).items() if isinstance(facts, dict) else ():
            if isinstance(item, int) and isinstance(row, dict):
                out[item] = row
    return out
