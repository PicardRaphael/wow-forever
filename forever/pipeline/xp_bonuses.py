"""Bonus d'XP décodés du client (`xp_bonuses.json`, T04f, bloc A).

Chaque sort du client qui porte une aura d'XP (codes de `decode_rules.json`, `xp_bonuses.aura_codes`) avec son nom,
ses effets, sa durée, son cumul, sa voie d'accès (objet, perk Legacy, nourriture, aucune) ; la chaîne du sac de
couchage, les nourritures nutritives, les éléments de camp et les conditions de joueur citées par les descriptions.
Toutes les constantes de lecture viennent de `decode_rules.json` ; aucun chiffre de jeu ici. Les valeurs lues sont
`certain` ; le sens d'un code d'aura, déduit des descriptions, reste `probable`."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import CsvMissingError
from forever.pipeline.fetch import DEFAULT_LOCALE
from forever.pipeline.tables import Row, read_table

XP_BONUS_FILE = "xp_bonuses.json"
XP_BONUS_FILES = (XP_BONUS_FILE,)
SCHEMA_VERSION = 1
ACCESS = ("item", "legacy", "food", "camp", "none")
XP_BONUS_SCHEMAS = {"ItemSparse": "XpItemSparse"}  # niveau requis des objets en plus

Tables = Mapping[str, Sequence[Row]]


def xp_bonus_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) de chaque table lue par le décodeur (`xp_bonuses.tables`)."""
    return [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules.get("xp_bonuses", {}).get("tables", [])]


def xp_bonus_gate_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Tables propres aux bonus d'XP (`xp_bonus_tables`, téléchargées à part, facultatives) : présentes, le fichier
    est décodé ; absentes, il est hérité de la base."""
    return [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules.get("xp_bonus_tables", [])]


def load_xp_bonus_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    files = xp_bonus_table_files(rules)
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    return {name: list(read_table(csv_dir / rel, XP_BONUS_SCHEMAS.get(name, name))) for name, rel in files}


class _Client:
    """Index des tables lues (difficulté 0 seulement pour les tables par sort)."""

    def __init__(self, tables: Tables, spec: Mapping[str, Any]) -> None:
        self.spec = spec
        self.names = {int(r["ID"]): str(r["Name_lang"]) for r in tables["SpellName"]}
        self.descriptions = {int(r["ID"]): str(r["Description_lang"]) for r in tables["Spell"]}
        self.effects: dict[int, list[Row]] = defaultdict(list)
        for r in tables["SpellEffect"]:
            if int(r["DifficultyID"]) == 0:
                self.effects[int(r["SpellID"])].append(r)
        self.misc = {int(r["SpellID"]): r for r in tables["SpellMisc"] if int(r["DifficultyID"]) == 0}
        self.durations = {int(r["ID"]): int(r["Duration"]) for r in tables["SpellDuration"]}
        self.stacks = {
            int(r["SpellID"]): int(r["CumulativeAura"])
            for r in tables["SpellAuraOptions"]
            if int(r["DifficultyID"]) == 0
        }
        self.items = {int(r["ID"]): r for r in tables["ItemSparse"]}
        effects_by_id = {int(r["ID"]): r for r in tables["ItemEffect"]}
        self.item_uses: dict[int, list[tuple[int, Row]]] = defaultdict(list)  # sort d'utilisation -> (objet, effet)
        for link in tables["ItemXItemEffect"]:
            effect = effects_by_id.get(int(link["ItemEffectID"]))
            if effect is not None and int(effect["SpellID"]):
                self.item_uses[int(effect["SpellID"])].append((int(link["ItemID"]), effect))
        self.conditions = {int(r["ID"]): r for r in tables["PlayerCondition"]}
        self.tables = tables

    def name(self, spell: int) -> str | None:
        return self.names.get(spell)

    def duration_ms(self, spell: int) -> int | None:
        """Durée lue (`SpellDuration`) ; None : sans durée ou permanente."""
        row = self.misc.get(spell)
        value = self.durations.get(int(row["DurationIndex"])) if row is not None else None
        return None if value is None or value == int(self.spec["permanent_duration"]) else value

    def triggers(self, spell: int) -> list[int]:
        return [int(e["EffectTriggerSpell"]) for e in self.effects.get(spell, []) if int(e["EffectTriggerSpell"])]

    def item(self, item: int) -> tuple[str | None, int | None]:
        row = self.items.get(item)
        if row is None:
            return None, None
        return (str(row["Display_lang"]) or None), int(row["RequiredLevel"])


def _reached_by_items(c: _Client) -> dict[int, list[tuple[int, int]]]:
    """Sorts atteints depuis le sort d'utilisation d'un objet (sorts déclenchés, et lien déclaré du sac de
    couchage) -> [(objet, sort d'utilisation)]."""
    bag = c.spec.get("sleeping_bag") or {}
    declared = {int(bag["use_spell"]): [int(bag["tracking_aura"])]} if bag else {}
    reached: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for use, items in c.item_uses.items():
        seen, todo = set(), [use]
        while todo:
            spell = todo.pop()
            if spell in seen:
                continue
            seen.add(spell)
            todo += [*c.triggers(spell), *declared.get(spell, [])]
        for spell in seen:
            reached[spell] += [(item, use) for item, _ in items]
    return reached


def _legacy(c: _Client, spell: int) -> dict[str, Any] | None:
    """Perk Legacy du sort : définition de trait rattachée à un nœud, rangs lus dans les courbes."""
    tables = c.tables
    nodes = {int(r["ID"]): int(r["TraitTreeID"]) for r in tables["TraitNode"]}
    entry_node = {int(r["TraitNodeEntryID"]): int(r["TraitNodeID"]) for r in tables["TraitNodeXTraitNodeEntry"]}
    for definition in sorted(int(r["ID"]) for r in tables["TraitDefinition"] if int(r["SpellID"]) == spell):
        for entry in tables["TraitNodeEntry"]:
            node = entry_node.get(int(entry["ID"]))
            if int(entry["TraitDefinitionID"]) != definition or node is None or node not in nodes:
                continue
            ranks: dict[str, list[float]] = {}
            for p in tables["TraitDefinitionEffectPoints"]:
                if int(p["TraitDefinitionID"]) != definition:
                    continue
                points = sorted(
                    (float(cp["Pos_0"]), float(cp["Pos_1"]))
                    for cp in tables["CurvePoint"]
                    if int(cp["CurveID"]) == int(p["CurveID"])
                )
                ranks[str(int(p["EffectIndex"]))] = [v for _, v in points]
            return {
                "trait_definition": definition,
                "node": node,
                "tree": nodes[node],
                "max_ranks": int(entry["MaxRanks"]),
                "ranks": dict(sorted(ranks.items())),
            }
    return None


def _food_uses(c: _Client, spell: int) -> list[int]:
    """Sorts d'utilisation d'un objet dont la description cite l'aura `spell` (`$@spelldesc`)."""
    pattern = re.compile(c.spec["spelldesc_pattern"])
    return sorted(use for use in c.item_uses if spell in {int(m) for m in pattern.findall(c.descriptions.get(use, ""))})


def _condition(c: _Client, spell: int) -> int | None:
    found = re.search(c.spec["condition_pattern"], c.descriptions.get(spell, ""))
    return int(found.group(1)) if found else None


def _decode_condition(c: _Client, condition: int) -> dict[str, Any]:
    row = c.conditions.get(condition)
    if row is None:
        return {"missing": True, "fields": {}, "readable_in_client": False}
    nulls = {int(v) for v in c.spec["condition_null_values"]}
    fields = {
        name: {"value": int(row[name]), "meaning": meaning}
        for name, meaning in c.spec["condition_fields"].items()
        if int(row[name]) not in nulls
    }
    server = set(c.spec["condition_server_fields"])
    return {"missing": False, "fields": fields, "readable_in_client": not any(f in server for f in fields)}


def _aura(c: _Client, spell: int, reached: Mapping[int, list[tuple[int, int]]]) -> dict[str, Any]:
    codes = c.spec["aura_codes"]
    apply = int(c.spec["apply_aura_effect"])
    effects = [
        {
            "index": int(e["EffectIndex"]),
            "aura": int(e["EffectAura"]),
            "key": codes[str(int(e["EffectAura"]))]["key"],
            "applies_to": codes[str(int(e["EffectAura"]))]["applies_to"],
            "base_points": float(e["EffectBasePointsF"]),
            "misc_value": int(e["EffectMiscValue_0"]),
        }
        for e in sorted(c.effects.get(spell, []), key=lambda e: int(e["EffectIndex"]))
        if int(e["Effect"]) == apply and str(int(e["EffectAura"])) in codes
    ]
    legacy = _legacy(c, spell)
    items = sorted(set(reached.get(spell, [])))
    food = _food_uses(c, spell)
    bag = c.spec.get("sleeping_bag") or {}
    if legacy is not None:
        access, access_certainty = "legacy", "certain"
    elif items:
        declared = bool(bag) and any(use == int(bag["use_spell"]) for _, use in items)
        access, access_certainty = "item", "probable" if declared else "certain"
    elif food:
        access, access_certainty = "food", "certain"
    else:
        access, access_certainty = "none", "suppose"
    duration = c.duration_ms(spell)
    stacks = c.stacks.get(spell, 0)
    return {
        "spell_id": spell,
        "name": c.name(spell),
        "description": c.descriptions.get(spell, ""),
        "effects": effects,
        "duration_ms": duration,
        "permanent": duration is None,
        "max_stacks": stacks if stacks > 0 else 1,
        "access": access,
        "items": [{"item": item, "name": c.item(item)[0], "use_spell": use} for item, use in items],
        "legacy": legacy,
        "food_spells": food,
        "condition": _condition(c, spell),
        "certainty": {
            "values": "certain",
            "meaning": c.spec["aura_codes_certainty"],
            "access": access_certainty,
        },
    }


def _food(c: _Client, auras: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buff_aura = int(c.spec["food_buff_aura"])
    out = []
    for aura in auras:
        if aura["access"] != "food":
            continue
        for use in aura["food_spells"]:
            buff = next(
                (int(e["EffectTriggerSpell"]) for e in c.effects.get(use, []) if int(e["EffectAura"]) == buff_aura),
                None,
            )
            for item, _ in c.item_uses[use]:
                name, level = c.item(item)
                out.append(
                    {
                        "item": item,
                        "name": name,
                        "required_level": level,
                        "spell": use,
                        "kind": c.name(use),
                        "buff_spell": buff,
                        "buff_name": c.name(buff) if buff else None,
                        "buff_duration_ms": c.duration_ms(buff) if buff else None,
                        "xp_aura": aura["spell_id"],
                    }
                )
    return sorted(out, key=lambda f: (f["required_level"] or 0, f["item"]))


def _sleeping_bag(c: _Client) -> dict[str, Any] | None:
    bag = c.spec.get("sleeping_bag")
    if not bag:
        return None
    item, use, tracking = int(bag["item"]), int(bag["use_spell"]), int(bag["tracking_aura"])
    uses = [effect for i, effect in c.item_uses.get(use, []) if i == item]
    periodic = int(c.spec["periodic_trigger_aura"])
    tick = next(
        (e for e in c.effects.get(tracking, []) if int(e["EffectAura"]) == periodic and int(e["EffectTriggerSpell"])),
        None,
    )
    if not uses or tick is None:
        return None
    aura = int(tick["EffectTriggerSpell"])
    name, level = c.item(item)
    stacks = c.stacks.get(aura, 0)
    return {
        "item": item,
        "name": name,
        "required_level": level,
        "use_spell": use,
        "use_spell_name": c.name(use),
        "bag_duration_ms": c.duration_ms(use),
        "item_cooldown_ms": max(int(uses[0]["CoolDownMSec"]), int(uses[0]["CategoryCoolDownMSec"])),
        "tracking_aura": tracking,
        "stack_period_ms": int(tick["EffectAuraPeriod"]),
        "aura": aura,
        "aura_name": c.name(aura),
        "aura_duration_ms": c.duration_ms(aura),
        "max_stacks": stacks if stacks > 0 else 1,
        "description": c.descriptions.get(use, ""),
        "certainty": {"values": "certain", "chain": "probable"},
        "note": bag.get("note", ""),
    }


def _camp(c: _Client) -> dict[str, Any] | None:
    spec = c.spec.get("camp")
    if not spec:
        return None
    tent = int(spec["tent"])
    effect = next(
        (e for e in c.effects.get(tent, []) if int(e["EffectIndex"]) == int(spec["tent_threshold_effect"])), None
    )
    if effect is None:
        return None
    codes = {int(k) for k in c.spec["aura_codes"]}

    def spell(s: int) -> dict[str, Any]:
        return {"spell": s, "name": c.name(s), "duration_ms": c.duration_ms(s)}

    benefits = int(spec["benefits"])
    return {
        "tent": {
            **spell(tent),
            "threshold_pct_of_level": float(effect["EffectBasePointsF"]),
            "description": c.descriptions.get(tent, ""),
        },
        "shared_cooldown": spell(int(spec["shared_cooldown"])),
        "benefits": {
            **spell(benefits),
            "xp_bonus": any(int(e["EffectAura"]) in codes for e in c.effects.get(benefits, [])),
        },
        "fires": [spell(int(s)) for s in spec["fires"] if c.name(int(s))],
        "certainty": {"values": "certain", "meaning": "probable"},
        "note": spec.get("note", ""),
    }


def decode_xp_bonuses(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Document `xp_bonuses.json` décodé des tables du client."""
    spec = rules["xp_bonuses"]
    c = _Client(tables, spec)
    apply = int(spec["apply_aura_effect"])
    codes = {int(k) for k in spec["aura_codes"]}
    spells = sorted(
        {
            s
            for s, rows in c.effects.items()
            for e in rows
            if int(e["Effect"]) == apply and int(e["EffectAura"]) in codes
        }
    )
    reached = _reached_by_items(c)
    auras = [_aura(c, s, reached) for s in spells]
    conditions = sorted({a["condition"] for a in auras if a["condition"] is not None})
    return {
        "schema_version": SCHEMA_VERSION,
        "build": version,
        "source": f"Client {version} : tables Spell*, Item*, Trait*, CurvePoint et PlayerCondition (wago.tools) "
        "décodées par forever decode",
        "aura_codes": spec["aura_codes"],
        "auras": auras,
        "sleeping_bag": _sleeping_bag(c),
        "food": _food(c, auras),
        "camp": _camp(c),
        "conditions": {str(k): _decode_condition(c, k) for k in conditions},
        "notes": [
            spec.get("aura_codes_note", ""),
            "accès none : aucune source joueur dans le client ; bonus listé, jamais appliqué (décision 262)",
            spec.get("note", ""),
        ],
    }


def xp_bonuses_errors(doc: Any) -> list[str]:
    """Contrôle de forme du document."""
    if not isinstance(doc, dict):
        return [f"{XP_BONUS_FILE} : objet attendu"]
    errors: list[str] = []
    auras = doc.get("auras")
    if not isinstance(auras, list):
        errors.append(f"{XP_BONUS_FILE} : auras : liste attendue")
    else:
        for a in auras:
            if not isinstance(a, dict) or not isinstance(a.get("spell_id"), int):
                errors.append(f"{XP_BONUS_FILE} : aura sans spell_id")
                continue
            if a.get("access") not in ACCESS:
                errors.append(f"{XP_BONUS_FILE} : aura {a['spell_id']} : accès inconnu {a.get('access')!r}")
            if not isinstance(a.get("max_stacks"), int) or a["max_stacks"] < 1:
                errors.append(f"{XP_BONUS_FILE} : aura {a['spell_id']} : cumul entier positif attendu")
            if not isinstance(a.get("effects"), list) or not a["effects"]:
                errors.append(f"{XP_BONUS_FILE} : aura {a['spell_id']} : effets attendus")
    if not isinstance(doc.get("food"), list):
        errors.append(f"{XP_BONUS_FILE} : food : liste attendue")
    if not isinstance(doc.get("conditions"), dict):
        errors.append(f"{XP_BONUS_FILE} : conditions : objet attendu")
    return errors
