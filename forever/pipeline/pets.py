"""Système de familiers du Chasseur décodé du client (`pets.json`, CH0, bloc A).

Familles (CreatureFamily dont la ligne de compétence est une ligne de familier du Chasseur), capacités et rangs
(SkillLineAbility, Spell*), bonus de famille (aura passive de chaque ligne), régime (masque de CreatureFamily et
ItemPetFood), effets de « Hunter Pet Scaling », cartes (UiMap). Toutes les constantes de lecture viennent de
`decode_rules.json` (`pet_tables`, `localized_pet_tables`, `pets`) ; aucun chiffre de jeu ici. Les sens tirés d'une
colonne sans nom ou d'un type d'aura restent `probable` ; un écart interne au client est listé dans
`observations`, jamais tranché."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import CsvMissingError
from forever.pipeline.fetch import DEFAULT_LOCALE
from forever.pipeline.tables import Row, column_value, read_table
from forever.pipeline.tooltip import normalize, tooltip_values

PETS_FILE = "pets.json"
PETS_FILES = (PETS_FILE,)
SCHEMA_VERSION = 1
KINDS = ("family", "trained", "general", "attack_speed")

Tables = Mapping[str, Sequence[Row]]

_ROMAN = {"I": 1, "V": 5, "X": 10}


def pet_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(clé de table, chemin relatif) de chaque CSV des familiers (`pet_tables`, `localized_pet_tables`)."""
    files = [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules.get("pet_tables", [])]
    for locale, names in rules.get("localized_pet_tables", {}).items():
        files += [(f"{locale}/{name}", f"{locale}/{name}.csv") for name in names]
    return files


def own_pet_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Tables propres aux familiers (absentes des tables du Mage et des 9 classes) : toutes présentes, les
    familiers sont décodés ; toutes absentes, `pets.json` est noté absent ; une partie est une erreur."""
    shared = {*rules.get("tables", []), *rules.get("class_tables", [])}
    return [(key, rel) for key, rel in pet_table_files(rules) if key.rsplit("/", 1)[-1] not in shared]


def load_pet_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    """Tables des familiers lues dans `csv_dir/<locale>/<Table>.csv` (CsvMissingError si un fichier manque)."""
    files = pet_table_files(rules)
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    schema = {"SkillLineAbility": "PetSkillLineAbility"}  # chaîne des rangs et colonne du coût en plus
    out: dict[str, list[Row]] = {}
    for key, rel in files:
        table = key.rsplit("/", 1)[-1]
        out[key] = list(read_table(csv_dir / rel, schema.get(table, table)))
    return out


def family_key(name: str) -> str:
    """Clé d'une famille ou d'une capacité : nom anglais en minuscules, mots joints par des tirets."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _roman(text: str) -> int:
    total = 0
    for i, ch in enumerate(text):
        value = _ROMAN[ch]
        total += -value if i + 1 < len(text) and _ROMAN[text[i + 1]] > value else value
    return total


def _effects(rows: Sequence[Row]) -> list[dict[str, Any]]:
    return [
        {
            "aura": int(e["EffectAura"]),
            "misc": int(e["EffectMiscValue_0"]),
            "base_points": float(e["EffectBasePointsF"]),
        }
        for e in sorted(rows, key=lambda e: int(e["EffectIndex"]))
    ]


class _PetClient:
    """Index des tables des familiers."""

    def __init__(self, tables: Tables, rules: Mapping[str, Any]) -> None:
        from forever.pipeline.decode import _Client  # import tardif : decode importe ce module

        self.rules = rules
        self.pets = rules["pets"]
        self.client = _Client(tables, rules)
        self.names = self.client.names
        self.names_fr = self.client.names_fr
        self.subtext = {int(r["ID"]): str(r["NameSubtext_lang"]) for r in tables["Spell"]}
        self.descriptions = {int(r["ID"]): str(r["Description_lang"]) for r in tables["Spell"]}
        self.lines = {int(r["ID"]): r for r in tables["SkillLine"]}
        self.effect_rows: dict[int, list[Row]] = defaultdict(list)
        for r in tables["SpellEffect"]:
            if r["DifficultyID"] == 0:
                self.effect_rows[int(r["SpellID"])].append(r)
        self.abilities_of: dict[int, list[Row]] = defaultdict(list)
        for r in tables["SkillLineAbility"]:
            self.abilities_of[int(r["SkillLine"])].append(r)
        self.levels = {int(r["SpellID"]): r for r in tables["SpellLevels"] if r["DifficultyID"] == 0}

    def line_named(self, name: str) -> list[int]:
        return sorted(i for i, r in self.lines.items() if r["DisplayName_lang"] == name)

    def hunter_lines(self) -> list[int]:
        """Lignes « Pet - » de la catégorie des familiers qui portent l'aura de mise à l'échelle du Chasseur."""
        p = self.pets
        return sorted(
            i
            for i, r in self.lines.items()
            if int(r["CategoryID"]) == int(p["skill_line_category"])
            and str(r["DisplayName_lang"]).startswith(p["skill_line_prefix"])
            and any(self.names.get(int(a["Spell"])) == p["hunter_marker"] for a in self.abilities_of[i])
        )

    def learnable(self, line: int) -> list[Row]:
        methods = {int(m) for m in self.pets["acquire_methods"]}
        return [a for a in self.abilities_of[line] if int(a["AcquireMethod"]) in methods]

    def rank_of(self, spell: int) -> tuple[str, int] | None:
        """(clé de la capacité, rang) : sous-titre « Rank N », ou chiffre romain des passifs de vitesse."""
        name = self.names.get(spell, "")
        for key, pattern in self.pets["attack_speed"].items():
            m = re.match(pattern, name)
            if m:
                return key, _roman(m[1])
        m = re.match(self.rules["spell_ranks"]["rank_subtext"], self.subtext.get(spell, ""))
        if m and name:
            return family_key(name), int(m[1])
        return None

    def focus_cost(self, spell: int) -> int | None:
        for p in self.client.power.get(spell, []):
            if int(p["PowerType"]) == int(self.pets["focus_power_type"]) and int(p["ManaCost"]) > 0:
                return int(p["ManaCost"])
        return None

    def cooldown_s(self, spell: int) -> float | int | None:
        cd = self.client.cooldowns.get(spell)
        value = max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])) / 1000 if cd else 0
        return normalize(value) if value > 0 else None

    def level(self, spell: int) -> int | None:
        row = self.levels.get(spell)
        return int(row[self.pets["rank_level_field"]]) if row is not None else None

    def tooltip(self, spell: int) -> tuple[list[int | float] | None, str | None]:
        template = self.descriptions.get(spell, "")
        if not template:
            return None, None
        try:
            return tooltip_values(template, self.client.resolver(spell, "base", {})), None
        except (ValueError, KeyError, ZeroDivisionError) as exc:
            return None, str(exc)


def decode_pets(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `pets.json` : familles du Chasseur, capacités et rangs, mise à l'échelle, régimes, cartes."""
    c = _PetClient(tables, rules)
    p = rules["pets"]
    cost_col = p["training_cost_column"]  # un nom de colonne, ou une liste de noms (le nouveau d'abord)
    learn = int(rules["pvp_classification"]["learn_spell_effect"])
    observations: list[str] = []

    hunter = c.hunter_lines()
    generic = set(c.line_named(p["generic_line"]))
    trained = set(c.line_named(p["trained_line"]))
    families_rows = [r for r in tables["CreatureFamily"] if int(r["SkillLine_0"]) in hunter]
    targeted = {int(r["SkillLine_0"]) for r in tables["CreatureFamily"]}
    family_lines = {int(r["SkillLine_0"]): family_key(str(r["Name_lang"])) for r in families_rows}

    # Sorts d'enseignement de Beast Training : sort du familier -> sort qui l'enseigne
    teach: dict[int, int] = {}
    for line in sorted(trained):
        for a in c.learnable(line):
            spell = int(a["Spell"])
            for e in c.effect_rows.get(spell, []):
                if int(e["Effect"]) == learn and int(e["EffectTriggerSpell"]):
                    teach.setdefault(int(e["EffectTriggerSpell"]), spell)

    # Capacités : par clé, rang -> sort ; lignes et coûts bruts par (ligne, sort)
    rank_spell: dict[str, dict[int, int]] = defaultdict(dict)
    ability_lines: dict[str, set[int]] = defaultdict(set)
    line_costs: dict[int, dict[str, dict[int, int]]] = defaultdict(lambda: defaultdict(dict))
    unranked: dict[int, set[int]] = defaultdict(set)
    no_level: dict[int, set[int]] = defaultdict(set)
    for line in sorted({*hunter, *generic}):
        for a in c.learnable(line):
            spell = int(a["Spell"])
            name = c.names.get(spell, "")
            if name in (p["hunter_marker"], p["family_passive"]):
                continue
            found = c.rank_of(spell)
            if found is None:
                unranked[spell].add(line)
                continue
            if c.level(spell) is None:
                no_level[spell].add(line)
                continue
            key, rank = found
            previous = rank_spell[key].get(rank)
            if previous is not None and previous != spell:
                observations.append(f"{key} rang {rank} : deux sorts ({previous}, {spell}) ; le premier est gardé")
                continue
            rank_spell[key][rank] = spell
            ability_lines[key].add(line)
            line_costs[line][key][rank] = int(column_value(a, cost_col))
            sup = int(a["SupercedesSpell"])
            if sup and c.rank_of(sup) != (key, rank - 1):
                observations.append(
                    f"{key} rang {rank} (ligne {line}) : SupercedesSpell {sup} n'est pas le rang précédent"
                )

    abilities: dict[str, Any] = {}
    for key in sorted(rank_spell):
        lines = sorted(ability_lines[key])
        fams = sorted({family_lines[line] for line in lines if line in family_lines})
        if key in p["attack_speed"]:
            kind = "attack_speed"
        elif fams:
            kind = "family"
        else:
            kind = "general"
        ranks = []
        for rank in sorted(rank_spell[key]):
            spell = rank_spell[key][rank]
            values, error = c.tooltip(spell)
            costs = {line_costs[line][key][rank] for line in lines if rank in line_costs[line][key]}
            entry: dict[str, Any] = {
                "rank": rank,
                "spell_id": spell,
                "level": c.level(spell),
                "training_cost": next(iter(costs)) if len(costs) == 1 else None,
                "focus_cost": c.focus_cost(spell),
                "cooldown_s": c.cooldown_s(spell),
                "description": c.descriptions.get(spell, ""),
                "tooltip_values": values,
                "teach_spell_id": teach.get(spell),
            }
            if error is not None:
                entry["tooltip_error"] = error
            if kind == "attack_speed":
                entry["effects"] = _effects(c.effect_rows.get(spell, []))
            ranks.append(entry)
        first = rank_spell[key][min(rank_spell[key])]
        display = re.sub(r"\s+[IVX]+$", "", c.names.get(first, key)) if kind == "attack_speed" else c.names[first]
        display_fr = c.names_fr.get(first, "")
        if kind == "attack_speed":
            display_fr = re.sub(r"\s+[IVX]+$", "", display_fr)
        abilities[key] = {
            "name": {"en": display, "fr": display_fr},
            "kind": kind,
            "skill_lines": lines,
            "families": fams,
            "ranks": ranks,
            "certainty": {
                "rank": "certain",
                "level": "certain",
                "training_cost": p["certainty"]["training_cost"],
                "focus_cost": "certain",
                "cooldown_s": "certain",
            },
        }

    foods = {int(r["ID"]): str(r["Name_lang"]) for r in tables.get("ItemPetFood", [])}
    foods_fr = {int(r["ID"]): str(r["Name_lang"]) for r in tables.get("frFR/ItemPetFood", [])}
    family_fr = {int(r["ID"]): str(r["Name_lang"]) for r in tables.get("frFR/CreatureFamily", [])}
    bonus_spec = p["family_bonus"]
    bonus_auras = {int(v["aura"]) for v in bonus_spec.values()}

    families: dict[str, Any] = {}
    for r in sorted(families_rows, key=lambda r: family_key(str(r["Name_lang"]))):
        key = family_key(str(r["Name_lang"]))
        line = int(r["SkillLine_0"])
        line_name = str(c.lines[line]["DisplayName_lang"])
        passives = [
            int(a["Spell"])
            for a in c.abilities_of[line]
            if c.names.get(int(a["Spell"])) == p["family_passive"]
            and {int(e["EffectAura"]) for e in c.effect_rows.get(int(a["Spell"]), [])} >= bonus_auras
        ]
        passive = min(passives) if passives else None
        bonus: dict[str, float | None] = {}
        for field, spec in bonus_spec.items():
            matches = [
                e
                for e in c.effect_rows.get(passive or 0, [])
                if int(e["EffectAura"]) == int(spec["aura"])
                and ("misc_value" not in spec or int(e["EffectMiscValue_0"]) == int(spec["misc_value"]))
            ]
            bonus[field] = float(matches[0]["EffectBasePointsF"]) if matches else None
        if len(passives) != 1:
            observations.append(f"{key} : {len(passives)} passif(s) de famille dans la ligne {line}")
        mask = int(r["PetFoodMask"])
        diet = [{"id": i, "en": foods[i], "fr": foods_fr.get(i, "")} for i in sorted(foods) if mask & (1 << (i - 1))]
        fam_abilities = sorted(k for k, lines in ability_lines.items() if line in lines)
        expected_name = f"{p['skill_line_prefix']}{r['Name_lang']}"
        if line_name != expected_name:
            observations.append(
                f"{key} : la ligne de compétence {line} s'appelle « {line_name} », CreatureFamily écrit "
                f"« {r['Name_lang']} » (écart interne au client)"
            )
        families[key] = {
            "family_id": int(r["ID"]),
            "name": {"en": str(r["Name_lang"]), "fr": family_fr.get(int(r["ID"]), "")},
            "skill_lines": [int(r["SkillLine_0"]), int(r["SkillLine_1"])],
            "skill_line_name": line_name,
            "passive_spell": passive,
            "bonus": bonus,
            "food_mask": mask,
            "diet": diet if foods else None,
            "pet_talent_type": int(r["PetTalentType"]),
            "abilities": fam_abilities,
            "training_costs": {k: [line_costs[line][k][n] for n in sorted(line_costs[line][k])] for k in fam_abilities},
            "certainty": {
                "name": "certain",
                "abilities": "certain",
                "bonus": p["certainty"]["bonus"],
                "diet": p["certainty"]["diet"],
                "training_costs": p["certainty"]["training_cost"],
            },
        }

    orphans = []
    for line in hunter:
        if line in targeted:
            continue
        keys = sorted(k for k, lines in ability_lines.items() if line in lines)
        orphans.append({"skill_line": line, "name": str(c.lines[line]["DisplayName_lang"]), "abilities": keys})
        observations.append(
            f"ligne {line} « {c.lines[line]['DisplayName_lang']} » : aucune famille de CreatureFamily ne la vise "
            "(ligne orpheline, rendue à part)"
        )
    for line in sorted(set(hunter) - set(family_lines) - {o["skill_line"] for o in orphans}):
        observations.append(f"ligne {line} visée par une famille sans ligne de familier du Chasseur")
    for spell, where in sorted(no_level.items()):
        observations.append(
            f"sort {spell} « {c.names.get(spell, '?')} » sans ligne SpellLevels (lignes {sorted(where)}) : non rendu"
        )
    for key, ability in abilities.items():
        if ability["ranks"][0]["rank"] != 1:
            observations.append(f"{key} : premier rang du client {ability['ranks'][0]['rank']} (aucun rang 1)")
    for spell, where in sorted(unranked.items()):
        observations.append(
            f"sort {spell} « {c.names.get(spell, '?')} » sans rang dans les lignes {sorted(where)} : non rendu"
        )

    marker = min((s for s, n in c.names.items() if n == p["hunter_marker"]), default=None)
    pet_scaling = {
        "spell_id": marker,
        "effects": _effects(c.effect_rows.get(marker or 0, [])),
        "certainty": p["certainty"]["pet_scaling"],
    }

    maps: dict[str, Any] = {}
    ui = {int(r["ID"]): r for r in tables.get("UiMap", [])}
    ui_fr = {int(r["ID"]): str(r["Name_lang"]) for r in tables.get("frFR/UiMap", [])}
    continent_type = int(p["map_types"]["continent"])
    for map_id in sorted(ui):
        row = ui[map_id]
        continent, seen, current = None, set(), int(row["ParentUiMapID"])
        while current in ui and current not in seen:
            seen.add(current)
            if int(ui[current]["Type"]) == continent_type:
                continent = current
                break
            current = int(ui[current]["ParentUiMapID"])
        maps[str(map_id)] = {
            "name": {"en": str(row["Name_lang"]), "fr": ui_fr.get(map_id, "")},
            "parent": int(row["ParentUiMapID"]),
            "type": int(row["Type"]),
            "continent": continent,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "build": version,
        "source": (
            f"Client {version} : SkillLine, SkillLineAbility, Spell*, CreatureFamily, ItemPetFood et UiMap "
            "(wago.tools) décodées par forever decode"
        ),
        "families": families,
        "abilities": abilities,
        "aliases": dict(sorted(p.get("family_aliases", {}).items())),
        "orphan_skill_lines": orphans,
        "pet_scaling": pet_scaling,
        "diets": {str(i): {"en": foods[i], "fr": foods_fr.get(i, "")} for i in sorted(foods)},
        "maps": maps,
        "hunter_spells": {"file": "classes.json", "class": "Hunter", "names": list(p["hunter_spells"])},
        "observations": observations,
        "notes": list(p.get("notes", [])),
    }


def pets_errors(doc: Any) -> list[str]:
    """Contrôle de forme de `pets.json` : chaque famille a au moins une capacité connue, chaque rang un niveau,
    rangs consécutifs sans trou ni doublon. Un premier rang au-dessus de 1 (« Slower Attack II », « Lava Breath »
    rang 2) est permis : c'est le client, listé dans `observations` par le décodeur."""
    if not isinstance(doc, dict) or not isinstance(doc.get("families"), dict):
        return [f"{PETS_FILE} : objet avec families attendu"]
    abilities = doc.get("abilities")
    if not isinstance(abilities, dict):
        return [f"{PETS_FILE} : abilities attendu"]
    errors: list[str] = []
    for key, fam in sorted(doc["families"].items()):
        listed = fam.get("abilities") if isinstance(fam, dict) else None
        if not isinstance(listed, list) or not listed:
            errors.append(f"{PETS_FILE} : famille {key} sans aucune capacité")
            continue
        unknown = [a for a in listed if a not in abilities]
        if unknown:
            errors.append(f"{PETS_FILE} : famille {key}, capacité(s) inconnue(s) : {', '.join(map(str, unknown))}")
    for key, ability in sorted(abilities.items()):
        ranks = ability.get("ranks") if isinstance(ability, dict) else None
        if not isinstance(ranks, list) or not ranks:
            errors.append(f"{PETS_FILE} : capacité {key} sans rang")
            continue
        numbers = [r.get("rank") for r in ranks]
        ints = sorted(n for n in numbers if isinstance(n, int))
        first = ints[0] if ints else 1
        if len(ints) != len(numbers) or ints != list(range(first, first + len(ints))):
            errors.append(f"{PETS_FILE} : capacité {key}, rangs {numbers} : trou ou doublon")
        for r in ranks:
            if not isinstance(r.get("level"), int):
                errors.append(f"{PETS_FILE} : capacité {key}, rang {r.get('rank')} sans niveau")
    return errors
