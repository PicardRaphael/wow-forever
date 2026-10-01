"""Décodage des tables du client en données au format du dépôt (`talents.json`, `spells.json`).

Toutes les constantes de lecture (lignes de compétence, géométrie de l'arbre, identifiants d'effet, niveaux
d'évaluation) viennent de `decode_rules.json` ; ce module n'en contient aucune. Le résultat est une version
candidate écrite hors de `forever/data/` : T03 n'installe jamais une version."""

from __future__ import annotations

import copy
import json
import re
import shutil
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from forever.config import Deps
from forever.errors import CandidateExistsError, CsvMissingError, DataSchemaError, InvalidArgumentError
from forever.manifest import SOURCES_NAME, VERSION_DIR_RE, version_dirs, write_manifest
from forever.pipeline.character_scaling import (
    CHARACTER_FILE,
    CHARACTER_FILES,
    character_table_files,
    decode_character_scaling,
    gametables_dir,
    load_character_tables,
    load_gametables,
)
from forever.pipeline.fetch import DEFAULT_LOCALE, wago_dir
from forever.pipeline.tables import Row, read_table
from forever.pipeline.tooltip import half_up, normalize, tooltip_values
from forever.timefmt import format_utc

RULES_NAME = "decode_rules.json"
CLASS_FILES = ("classes.json", "races.json", "pvp_items.json")  # PV1 : 9 classes, races, bijoux PvP
DECODED_FILES = ("talents.json", "spells.json", "spell_scaling.json", *CLASS_FILES)
INHERITED_FILES = (
    "_seed_racials.json",  # PV1, D5 : copie figée du relevé communautaire (mode seed), racials.json retiré
    "pvp_rules.json",  # PV1 : règles du serveur des rendements décroissants (suppose)
    "leveling.json",
    "mechanics.json",
    "respec.json",
    "overrides.json",
    "meta.json",
    "monsters.json",
    "origins.json",  # T08b, bloc H : origine déclarée de chaque valeur, complétée à chaque nouvelle version
    RULES_NAME,
)

Tables = Mapping[str, Sequence[Row]]
"""Table -> lignes typées ; « SpellName » pour la locale par défaut, « frFR/SpellName » pour une autre locale."""

_CITED_SPELL = re.compile(r"\$(\d+)[A-Za-z]")


class Candidate(NamedTuple):
    root: Path  # dossier de données : manifest.json + <version>/
    version: str
    talents: int
    spells: int
    spell_ranks: int
    observations: list[str]


# --- Règles et tables ----------------------------------------------------------------------------


def load_rules(data_dir: Path) -> tuple[str, dict[str, Any]]:
    """(version, règles) : `decode_rules.json` de la version locale la plus récente qui en a un."""
    for version in reversed(version_dirs(data_dir)):
        path = data_dir / version / RULES_NAME
        if path.is_file():
            try:
                rules = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise DataSchemaError(f"{path} illisible ({exc}).") from exc
            if not isinstance(rules, dict):
                raise DataSchemaError(f"{path} : objet JSON attendu.")
            return version, rules
    raise DataSchemaError(f"Aucune version locale n'a de {RULES_NAME} dans {data_dir}.")


def table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(clé de table, chemin relatif) de chaque CSV attendu par les règles."""
    files = [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules["tables"]]
    for locale, names in rules.get("localized_tables", {}).items():
        files += [(f"{locale}/{name}", f"{locale}/{name}.csv") for name in names]
    return files


def load_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    """Tables des règles lues dans `csv_dir/<locale>/<Table>.csv` (DataSchemaError si une colonne manque,
    CsvMissingError si un fichier manque)."""
    files = table_files(rules)
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    return {key: list(read_table(csv_dir / rel, key.rsplit("/", 1)[-1])) for key, rel in files}


def fetch_list(rules: Mapping[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    """(tables enUS, tables par autre locale) à télécharger : celles du Mage (`tables`, `localized_tables`) puis
    celles des 9 classes (`class_tables`, `localized_class_tables`, PV1), sans doublon, dans l'ordre des règles."""
    tables = list(dict.fromkeys([*rules["tables"], *rules.get("class_tables", [])]))
    localized: dict[str, list[str]] = {}
    for source in (rules.get("localized_tables", {}), rules.get("localized_class_tables", {})):
        for locale, names in source.items():
            localized[locale] = list(dict.fromkeys([*localized.get(locale, []), *names]))
    return tables, localized


def class_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(clé de table, chemin relatif) de chaque CSV des 9 classes (`class_tables`, `localized_class_tables`)."""
    files = [(name, f"{DEFAULT_LOCALE}/{name}.csv") for name in rules.get("class_tables", [])]
    for locale, names in rules.get("localized_class_tables", {}).items():
        files += [(f"{locale}/{name}", f"{locale}/{name}.csv") for name in names]
    return files


def load_class_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    """Tables du Mage et des 9 classes lues dans `csv_dir/<locale>/<Table>.csv` (CsvMissingError si un fichier
    manque, DataSchemaError si une colonne manque)."""
    files = [*table_files(rules), *class_table_files(rules)]
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    return {key: list(read_table(csv_dir / rel, key.rsplit("/", 1)[-1])) for key, rel in files}


class _Client:
    """Index des tables du client et évaluation des points d'effet."""

    def __init__(self, tables: Tables, rules: Mapping[str, Any]) -> None:
        self.rules = rules
        self.names = {int(r["ID"]): str(r["Name_lang"]) for r in tables["SpellName"]}
        self.names_fr: dict[int, str] = {}
        for locale, names in rules.get("localized_tables", {}).items():
            if "SpellName" in names and locale == "frFR":
                self.names_fr = {int(r["ID"]): str(r["Name_lang"]) for r in tables[f"{locale}/SpellName"]}
        self.spell = {int(r["ID"]): r for r in tables["Spell"]}
        self.effects: dict[int, dict[int, Row]] = defaultdict(dict)
        for r in tables["SpellEffect"]:
            if r["DifficultyID"] == 0:
                self.effects[int(r["SpellID"])][int(r["EffectIndex"])] = r
        self.levels = self._by_spell(tables["SpellLevels"])
        self.misc = self._by_spell(tables["SpellMisc"])
        self.cooldowns = self._by_spell(tables["SpellCooldowns"])
        self.auras = self._by_spell(tables["SpellAuraOptions"])
        self.power: dict[int, list[Row]] = defaultdict(list)
        for r in tables["SpellPower"]:
            self.power[int(r["SpellID"])].append(r)
        self.cast = {int(r["ID"]): int(r["Base"]) for r in tables["SpellCastTimes"]}
        self.duration = {int(r["ID"]): int(r["Duration"]) for r in tables["SpellDuration"]}
        self.curves: dict[int, dict[float, float]] = defaultdict(dict)
        for r in tables["CurvePoint"]:
            self.curves[int(r["CurveID"])][float(r["Pos_0"])] = float(r["Pos_1"])

    @staticmethod
    def _by_spell(rows: Sequence[Row]) -> dict[int, Row]:
        return {int(r["SpellID"]): r for r in rows if r["DifficultyID"] == 0}

    def effect(self, spell: int, index: int) -> Row:
        try:
            return self.effects[spell][index]
        except KeyError:
            raise ValueError(f"effet {index + 1} absent du sort {spell}") from None

    def duration_ms(self, spell: int) -> int | None:
        misc = self.misc.get(spell)
        if misc is None or int(misc["DurationIndex"]) == 0:
            return None
        return self.duration[int(misc["DurationIndex"])]

    def level_for(self, spell: int, mode: str) -> tuple[int, int]:
        """(niveau de base, niveau d'évaluation) selon `levels.talent_tooltip` / `levels.spell_rank`."""
        row = self.levels.get(spell)
        if row is None:
            return 0, 0
        base, cap = int(row["BaseLevel"]), int(self.rules["levels"]["level_cap"])
        if mode == "base":
            return base, base
        if mode == "max_capped":
            top = int(row["MaxLevel"]) or cap
            return base, max(base, min(top, cap))
        raise DataSchemaError(f"{RULES_NAME} : niveau d'évaluation inconnu « {mode} ».")

    def points(self, spell: int, index: int, mode: str, override: float | None = None) -> tuple[float, float]:
        """(points de l'effet au niveau d'évaluation, variance)."""
        e = self.effect(spell, index)
        base, level = self.level_for(spell, mode)
        value = float(e["EffectBasePointsF"]) if override is None else override
        value += float(e["EffectRealPointsPerLevel"]) * (level - base)
        return value, float(e["Variance"])

    def damage(self, spell: int, index: int, mode: str, override: float | None = None) -> tuple[int, int]:
        """(minimum, maximum) arrondis au demi supérieur."""
        value, variance = self.points(spell, index, mode, override)
        return int(half_up(value * (1 - variance / 2))), int(half_up(value * (1 + variance / 2)))

    def display_duration(self, ms: int) -> int | float:
        if ms < 0:
            raise ValueError("durée illimitée dans une infobulle")
        units = sorted(self.rules["tooltip"]["duration_units"], key=lambda u: -int(u["ms"]))
        for unit in units:
            if ms >= int(unit["ms"]):
                return normalize(ms / int(unit["ms"]))
        return normalize(ms / int(units[-1]["ms"]))

    def resolver(self, main: int, mode: str, overrides: Mapping[int, float]) -> Any:
        """Résolveur de `tooltip_values` pour l'infobulle du sort `main` (points de rang `overrides`)."""

        def resolve(cited: int | None, letter: str, index: int) -> list[float]:
            spell = main if cited is None else cited
            override = overrides.get(index) if spell == main else None
            if letter in ("s", "m", "M"):
                value, variance = self.points(spell, index, mode, override)
                if not variance:
                    return [value]
                low, high = self.damage(spell, index, mode, override)
                return {"s": [float(low), float(high)], "m": [float(low)], "M": [float(high)]}[letter]
            if letter == "o":
                value, _ = self.points(spell, index, mode, override)
                period = int(self.effect(spell, index)["EffectAuraPeriod"])
                duration = self.duration_ms(spell)
                if not period or duration is None:
                    raise ValueError(f"$o{index + 1} sans période ni durée (sort {spell})")
                return [half_up(value) * duration / period]
            if letter == "t":
                return [int(self.effect(spell, index)["EffectAuraPeriod"]) / 1000]
            if letter == "d":
                duration = self.duration_ms(spell)
                if duration is None:
                    raise ValueError(f"$d sans durée (sort {spell})")
                return [self.display_duration(duration)]
            if letter in ("u", "n"):
                aura = self.auras.get(spell)
                if aura is None:
                    raise ValueError(f"${letter} sans SpellAuraOptions (sort {spell})")
                return [int(aura["CumulativeAura" if letter == "u" else "ProcCharges"])]
            raise ValueError(f"variable ${letter} non prise en charge")

        return resolve


# --- Talents -------------------------------------------------------------------------------------


def talent_key(name: str) -> str:
    """Clé d'un talent : nom anglais en camelCase, apostrophes retirées (« Winter's Chill » -> wintersChill)."""
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name.replace("'", "")) if w]
    if not words:
        raise DataSchemaError(f"Nom de talent sans lettre : « {name} ».")
    return words[0].lower() + "".join(w[0].upper() + w[1:] for w in words[1:])


def _grid(value: int, origin: int, step: int, divisor: int) -> int:
    """Position (à partir de 1) sur la grille ; une valeur hors grille est divisée par `divisor` (zéro en trop)."""
    for v in (value, value / divisor if divisor and value % divisor == 0 else None):
        if v is not None and (v - origin) % step == 0 and v >= origin:
            return int((v - origin) // step) + 1
    raise DataSchemaError(f"Position {value} hors de la grille (origine {origin}, pas {step}).")


def _tree_of(x: int, tabs: Mapping[str, int], step: int, divisor: int) -> tuple[str, int]:
    """(arbre, colonne) d'une abscisse ; une abscisse hors grille est divisée par `divisor`."""
    ordered = sorted(tabs.items(), key=lambda kv: kv[1])
    for v in (x, x // divisor if divisor and x % divisor == 0 else None):
        if v is None:
            continue
        inside = [t for t in ordered if t[1] <= v]
        if inside and (v - inside[-1][1]) % step == 0:
            name, origin = inside[-1]
            return name, _grid(v, origin, step, 0)
    raise DataSchemaError(f"Abscisse {x} hors des onglets de l'arbre ({dict(tabs)}).")


def _select(key: str, values: list[list[int | float]], indices: Sequence[int] | None) -> list[list[int | float]]:
    """Variables retenues dans `ranks` (`rank_variables` de decode_rules.json) ; toutes si le talent n'y figure pas."""
    if indices is None:
        return [list(v) for v in values]
    out = []
    for rank, row in enumerate(values, start=1):
        if any(i >= len(row) for i in indices):
            raise DataSchemaError(
                f"{RULES_NAME} : rank_variables de {key} {list(indices)} hors de l'infobulle du rang {rank} ({row})."
            )
        out.append([row[i] for i in indices])
    return out


def decode_talents(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `talents.json` décodé : arbres, puis talents par palier et colonne."""
    client = _Client(tables, rules)
    geo = rules["talent_geometry"]
    lines = set(rules["skill_lines"].values())
    trees = {int(r["TraitTreeID"]) for r in tables["SkillLineXTraitTree"] if int(r["SkillLineID"]) in lines}
    if len(trees) != 1:
        raise DataSchemaError(f"Arbre de talents introuvable ou ambigu pour les lignes {sorted(lines)} : {trees}.")
    tree_id = trees.pop()
    links: dict[int, list[Row]] = defaultdict(list)
    for r in tables["TraitNodeXTraitNodeEntry"]:
        links[int(r["TraitNodeID"])].append(r)
    entries = {int(r["ID"]): r for r in tables["TraitNodeEntry"]}
    definitions = {int(r["ID"]): r for r in tables["TraitDefinition"]}
    points: dict[int, list[Row]] = defaultdict(list)
    for r in tables["TraitDefinitionEffectPoints"]:
        points[int(r["TraitDefinitionID"])].append(r)

    by_spell: dict[int, tuple[Row, Row, Row]] = {}
    for node in sorted((n for n in tables["TraitNode"] if int(n["TraitTreeID"]) == tree_id), key=lambda n: n["ID"]):
        node_links = links.get(int(node["ID"]), [])
        if len(node_links) != 1:
            raise DataSchemaError(f"Nœud {node['ID']} : {len(node_links)} entrée(s), une seule prise en charge.")
        entry = entries[int(node_links[0]["TraitNodeEntryID"])]
        definition = definitions[int(entry["TraitDefinitionID"])]
        if rules["shared_spell"] != "latest_node":
            raise DataSchemaError(f"{RULES_NAME} : règle shared_spell inconnue « {rules['shared_spell']} ».")
        by_spell[int(definition["SpellID"])] = (node, entry, definition)  # nœuds triés : le plus récent gagne

    talents: dict[int, dict[str, Any]] = {}
    for spell, (node, entry, definition) in by_spell.items():
        tree, col = _tree_of(int(node["PosX"]), geo["tabs"], geo["col_step"], geo["extra_zero_divisor"])
        tier = _grid(int(node["PosY"]), geo["row_base"], geo["row_step"], geo["extra_zero_divisor"])
        name = str(definition["OverrideName_lang"]) or client.names.get(spell, "")
        desc = str(definition["OverrideDescription_lang"]) or str(
            client.spell.get(spell, {}).get("Description_lang", "")
        )
        key = talent_key(name)
        max_rank = int(entry["MaxRanks"])
        values: list[list[int | float]] = []
        for rank in range(1, max_rank + 1):
            overrides: dict[int, float] = {}
            for p in points.get(int(definition["ID"]), []):
                if str(p["OperationType"]) not in rules["curve_operations"]:
                    raise DataSchemaError(f"{key} : OperationType {p['OperationType']} non pris en charge.")
                curve = client.curves.get(int(p["CurveID"]), {})
                if float(rank) not in curve:
                    raise DataSchemaError(f"{key} : courbe {p['CurveID']} sans valeur au rang {rank}.")
                overrides[int(p["EffectIndex"])] = curve[float(rank)]
            try:
                values.append(
                    tooltip_values(desc, client.resolver(spell, rules["levels"]["talent_tooltip"], overrides))
                )
            except ValueError as exc:
                raise DataSchemaError(f"Infobulle du talent {key} (sort {spell}, rang {rank}) : {exc}.") from exc
        ranks = _select(key, values, rules.get("rank_variables", {}).get(key))
        talents[int(node["ID"])] = {
            "key": key,
            "name": name,
            "name_fr": client.names_fr.get(spell, ""),
            "tree": tree,
            "tier": tier,
            "col": col,
            "max": max_rank,
            "ranks": ranks,
            "tooltip_values": values,
            "desc": desc,
            "spellIds": [spell],
            "prereq": None,
            "certainty": f"FC-{version}",
        }
    for edge in tables["TraitEdge"]:
        left, right = int(edge["LeftTraitNodeID"]), int(edge["RightTraitNodeID"])
        if left in talents and right in talents:
            if talents[right]["prereq"] is not None:
                raise DataSchemaError(f"{talents[right]['key']} : plusieurs prérequis, un seul pris en charge.")
            talents[right]["prereq"] = {"tier": talents[left]["tier"], "col": talents[left]["col"]}
    order = list(geo["tabs"])
    trees_out = []
    for name in order:
        members = sorted((t for t in talents.values() if t["tree"] == name), key=lambda t: (t["tier"], t["col"]))
        trees_out.append({"name": name, "talents": members})
    return {
        "build": version,
        "class": rules["class"],
        "source": f"Client {version} : tables Trait* et Spell* (wago.tools) décodées par forever decode",
        "trees": trees_out,
        "notes": [
            (
                "Rangs : variables de l'infobulle du sort du nœud, dans leur ordre d'apparition, évaluées au niveau "
                "de base du sort (decode_rules.json, levels.talent_tooltip)."
            ),
            "tooltip_values : toutes les variables de l'infobulle ; ranks : celles retenues par rank_variables.",
            "desc : gabarit d'infobulle du client ; spellIds : sort unique du nœud (le client n'a pas un sort par rang).",
        ],
    }


def _place(value: int, origins: Sequence[int], step: int, divisor: int) -> tuple[int, int] | None:
    """(indice de l'origine, position à partir de 1) d'une coordonnée sur la grille, directement ou après la règle
    du zéro en trop ; None si elle tombe hors de la grille (jamais arrondie)."""
    ordered = sorted(range(len(origins)), key=lambda i: origins[i])
    for v in (value, value // divisor if divisor and value % divisor == 0 else None):
        if v is None:
            continue
        inside = [i for i in ordered if origins[i] <= v]
        if inside and (v - origins[inside[-1]]) % step == 0:
            return inside[-1], (v - origins[inside[-1]]) // step + 1
    return None


def _region(x: int, origins: Sequence[int], divisor: int) -> int | None:
    """Onglet dont la zone contient une abscisse hors grille (zone : de son origine à celle de l'onglet suivant)."""
    ordered = sorted(origins)
    width = ordered[1] - ordered[0] if len(ordered) > 1 else 0
    for v in (x, x // divisor if divisor and x % divisor == 0 else None):
        if v is not None and ordered[0] <= v < ordered[-1] + width:
            return list(origins).index(max(o for o in ordered if o <= v))
    return None


def _class_talents(tables: Tables, rules: Mapping[str, Any], client: _Client, cls: str, version: str) -> dict[str, Any]:
    spec = rules["classes"][cls]
    geo = rules["talent_geometry"]
    origins, div = [int(o) for o in geo["tab_origins"]], int(geo["extra_zero_divisor"])
    lines = [int(i) for i in spec["skill_lines"]]
    skill_names = {int(r["ID"]): str(r["DisplayName_lang"]) for r in tables["SkillLine"]}
    trees = {int(r["TraitTreeID"]) for r in tables["SkillLineXTraitTree"] if int(r["SkillLineID"]) in lines}
    if len(trees) != 1:
        raise DataSchemaError(f"{cls} : arbre de traits introuvable ou ambigu pour les lignes {lines} : {trees}.")
    tree_id = trees.pop()
    links: dict[int, list[Row]] = defaultdict(list)
    for r in tables["TraitNodeXTraitNodeEntry"]:
        links[int(r["TraitNodeID"])].append(r)
    entries = {int(r["ID"]): r for r in tables["TraitNodeEntry"]}
    definitions = {int(r["ID"]): r for r in tables["TraitDefinition"]}
    by_spell: dict[int, tuple[Row, Row, Row]] = {}
    dropped: list[dict[str, Any]] = []
    for node in sorted((n for n in tables["TraitNode"] if int(n["TraitTreeID"]) == tree_id), key=lambda n: n["ID"]):
        node_links = links.get(int(node["ID"]), [])
        if len(node_links) != 1:
            raise DataSchemaError(f"{cls}, nœud {node['ID']} : {len(node_links)} entrée(s), une seule prise en charge.")
        entry = entries[int(node_links[0]["TraitNodeEntryID"])]
        definition = definitions[int(entry["TraitDefinitionID"])]
        spell = int(definition["SpellID"])
        if spell in by_spell:  # nœuds triés : le plus récent l'emporte (shared_spell « latest_node »)
            old = int(by_spell[spell][0]["ID"])
            reason = f"même sort ({spell}) qu'un nœud plus récent : {rules['shared_spell']}"
            dropped.append({"node_id": old, "kept_node": int(node["ID"]), "reason": reason})
        by_spell[spell] = (node, entry, definition)

    talents: dict[int, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    for spell, (node, entry, definition) in by_spell.items():
        x, y = int(node["PosX"]), int(node["PosY"])
        at_x = _place(x, origins, int(geo["col_step"]), div)
        at_y = _place(y, [int(geo["row_base"])], int(geo["row_step"]), div)
        reasons = []
        if at_x is None:
            reasons.append(f"abscisse {x} hors de la grille des onglets {origins} (pas {geo['col_step']})")
        if at_y is None:
            reasons.append(
                f"ordonnée {y} hors de la grille des paliers (base {geo['row_base']}, pas {geo['row_step']})"
            )
        tab = at_x[0] if at_x is not None else _region(x, origins, div)
        if tab is None:
            raise DataSchemaError(f"{cls}, nœud {node['ID']} : abscisse {x} hors de tous les onglets {origins}.")
        name = str(definition["OverrideName_lang"]) or client.names.get(spell, "")
        desc = str(definition["OverrideDescription_lang"]) or str(
            client.spell.get(spell, {}).get("Description_lang", "")
        )
        key = talent_key(name)
        talent: dict[str, Any] = {
            "key": key,
            "name": name,
            "name_fr": client.names_fr.get(spell, ""),
            "node_id": int(node["ID"]),
            "tree": skill_names.get(lines[tab], str(lines[tab])),
            "tier": at_y[1] if at_y is not None else None,
            "col": at_x[1] if at_x is not None else None,
            "max": int(entry["MaxRanks"]),
            "desc": desc,
            "spell_id": spell,
            "prereq": None,
            "prereqs": [],
            "certainty": f"FC-{version}",
        }
        if reasons:
            talent["unresolved"] = reasons
            unresolved.append(
                {"node_id": int(node["ID"]), "key": key, "pos_x": x, "pos_y": y, "reason": " ; ".join(reasons)}
            )
        talents[int(node["ID"])] = talent

    observed_nodes = []
    for key, pos in (rules.get("observed_positions", {}).get(cls) or {}).items():
        found = [t for t in talents.values() if t["key"] == key]
        if not found:
            raise DataSchemaError(f"{cls} : position relevée pour un talent inconnu « {key} ».")
        t = found[0]
        for field in ("tier", "col"):
            if t[field] is not None and t[field] != pos[field]:
                raise DataSchemaError(
                    f"{cls}, {key} : {field} décodé du client ({t[field]}) différent du relevé en jeu ({pos[field]})."
                )
        t["tier"], t["col"] = pos["tier"], pos["col"]
        t.pop("unresolved", None)
        t["position"] = {"source": pos["source"], "certainty": pos["certainty"]}
        unresolved = [u for u in unresolved if u["node_id"] != t["node_id"]]
        observed_nodes.append({"node_id": t["node_id"], "key": key, "tier": t["tier"], "col": t["col"]})

    kinds = rules.get("trait_edge_types", {})
    visual = {int(v) for v in kinds.get("visual", [])}
    kind_of = {int(v): name for name in ("sufficient", "required") for v in kinds.get(name, [])}
    for edge in tables["TraitEdge"]:
        left, right = int(edge["LeftTraitNodeID"]), int(edge["RightTraitNodeID"])
        edge_type = int(edge["Type"])
        if left in talents and right in talents and edge_type not in visual:
            source = talents[left]
            talents[right]["prereqs"].append(
                {
                    "node_id": left,
                    "tier": source["tier"],
                    "col": source["col"],
                    "kind": kind_of.get(edge_type, f"type {edge_type}"),
                }
            )
    for t in talents.values():
        if len(t["prereqs"]) == 1:
            first = t["prereqs"][0]
            t["prereq"] = {"node_id": first["node_id"], "tier": first["tier"], "col": first["col"]}

    community = rules.get("community_positions", {}).get(cls, {})
    for t in talents.values():
        found = community.get(t["key"])
        if isinstance(found, dict) and t["tier"] is None:
            t["tier_community"] = {"tier": found["tier"], "sources": list(found["sources"]), "certainty": "probable"}
    keys = [t["key"] for t in talents.values()]
    doubles = sorted({k for k in keys if keys.count(k) > 1})
    if doubles:
        raise DataSchemaError(f"{cls} : clés de talents en double ({', '.join(doubles)}).")
    ability_lines: dict[int, set[int]] = defaultdict(set)
    for r in tables["SkillLineAbility"]:
        ability_lines[int(r["Spell"])].add(int(r["SkillLine"]))
    trees_out, checks = [], []
    for line in lines:
        name = skill_names.get(line, str(line))
        members = sorted(
            (t for t in talents.values() if t["tree"] == name),
            key=lambda t: (t["tier"] is None, t["tier"] or 0, t["col"] is None, t["col"] or 0, t["node_id"]),
        )
        counts: dict[int, int] = defaultdict(int)
        for t in members:
            for owner in ability_lines.get(t["spell_id"], set()) & set(lines):
                counts[owner] += 1
        majority = max(counts, key=lambda k: (counts[k], k == line)) if counts else None
        checks.append({"tree": name, "skill_line": line, "majority": majority, "counts": dict(sorted(counts.items()))})
        trees_out.append({"name": name, "skill_line": line, "talents": members})
    client_class = next((r for r in tables["ChrClasses"] if str(r["Name_lang"]) == cls), None)
    if client_class is None:
        raise DataSchemaError(f"Classe {cls} absente de ChrClasses.")
    return {
        "id": int(client_class["ID"]),
        "file": str(client_class["Filename"]),
        "trait_tree": tree_id,
        "trees": trees_out,
        "unresolved_nodes": sorted(unresolved, key=lambda u: u["node_id"]),
        "dropped_nodes": sorted(dropped, key=lambda d: d["node_id"]),
        "tree_checks": checks,
        "observed_nodes": observed_nodes,
    }


_PVP_KINDS = ("control", "defensive", "cc_break", "interrupt", "dispel", "mobility", "burst")


class _ClassIndex:
    """Index des tables des 9 classes (catégories, ruptures, portées, noms des mécaniques et des dissipations)."""

    def __init__(self, tables: Tables) -> None:
        self.categories = {int(r["SpellID"]): r for r in tables["SpellCategories"] if int(r["DifficultyID"]) == 0}
        self.interrupts = {int(r["SpellID"]): r for r in tables["SpellInterrupts"] if int(r["DifficultyID"]) == 0}
        self.ranges = {int(r["ID"]): r for r in tables["SpellRange"]}
        self.mechanics = {int(r["ID"]): str(r["StateName_lang"]) for r in tables["SpellMechanic"]}
        self.dispels = {int(r["ID"]): str(r["Name_lang"]) for r in tables["SpellDispelType"]}
        self.skill_names = {int(r["ID"]): str(r["DisplayName_lang"]) for r in tables["SkillLine"]}


def _spell_rank(client: _Client, index: _ClassIndex, spell: int, rules: Mapping[str, Any]) -> dict[str, Any]:
    """Champs du client d'un rang de sort (certains)."""
    misc = client.misc.get(spell)
    duration = client.duration_ms(spell)
    duration_ms = duration if duration is not None and duration > 0 else 0
    channel = misc is not None and bool(
        int(misc["Attributes_1"]) & int(rules["spell_ranks"]["channel_attributes_1_mask"])
    )
    cast_ms = (
        duration_ms if channel and duration_ms else client.cast.get(int(misc["CastingTimeIndex"]) if misc else 0, 0)
    )
    cd = client.cooldowns.get(spell)
    recovery = max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])) if cd else 0
    gcd = int(cd["StartRecoveryTime"]) if cd else 0
    pvp_index = int(misc["PvPDurationIndex"]) if misc else 0
    pvp_ms = client.duration.get(pvp_index) if pvp_index else None
    range_row = index.ranges.get(int(misc["RangeIndex"])) if misc and int(misc["RangeIndex"]) else None
    cost = None
    for p in client.power.get(spell, []):
        if int(p["ManaCost"]) > 0 or float(p["PowerCostPct"]) > 0:
            cost = {
                "power_type": int(p["PowerType"]),
                "amount": int(p["ManaCost"]),
                "pct": normalize(float(p["PowerCostPct"])),
            }
            break
    category = index.categories.get(spell)
    level = client.levels.get(spell)
    subtext = str(client.spell.get(spell, {}).get("NameSubtext_lang", ""))
    match = re.match(rules["spell_ranks"]["rank_subtext"], subtext)
    return {
        "spell_id": spell,
        "rank": int(match[1]) if match else None,
        "level": int(level["BaseLevel"]) if level else None,
        "cast_s": normalize(cast_ms / 1000),
        "cooldown_s": normalize(recovery / 1000) if recovery > 0 else None,
        "gcd_s": normalize(gcd / 1000) if gcd > 0 else None,
        "duration_s": normalize(duration_ms / 1000) if duration_ms else None,
        "pvp_duration_s": normalize(pvp_ms / 1000) if pvp_ms is not None and pvp_ms > 0 else None,
        "range_yd": (
            {"min": normalize(float(range_row["RangeMin_0"])), "max": normalize(float(range_row["RangeMax_0"]))}
            if range_row is not None
            else None
        ),
        "school": int(misc["SchoolMask"]) if misc else 0,
        "cost": cost,
        "mechanic": int(category["Mechanic"]) if category else 0,
        "diminish": int(category["DiminishType"]) if category else 0,
        "dispel_type": int(category["DispelType"]) if category else 0,
    }


def _own_roles(client: _Client, index: _ClassIndex, spell: int, rules: Mapping[str, Any]) -> dict[str, Any]:
    """Rôles PvP portés par les effets d'un sort (sans ses déclencheurs), d'après la table `pvp_classification`."""
    spec = rules["pvp_classification"]
    aura_effects = {int(e) for e in spec["aura_effects"]}
    hostile, friendly = {int(t) for t in spec["hostile_targets"]}, {int(t) for t in spec["friendly_targets"]}
    self_targets = {int(t) for t in spec["self_targets"]}
    cc = {int(m) for m in spec["cc_mechanics"]}
    negative_only, positive_only = set(spec.get("negative_only_auras", [])), set(spec.get("positive_only_auras", []))
    roles: dict[str, Any] = defaultdict(list)
    for _, e in sorted(client.effects.get(spell, {}).items()):
        effect, aura, misc = int(e["Effect"]), int(e["EffectAura"]), int(e["EffectMiscValue_0"])
        targets = {int(e["ImplicitTarget_0"]), int(e["ImplicitTarget_1"])} - {0}
        points = float(e["EffectBasePointsF"])
        on_self = bool(targets) and targets <= self_targets
        if effect in aura_effects:
            name = str(aura)
            if name in spec["control_auras"] and targets & hostile:
                roles["control"].append((spec["control_auras"][name], int(e["EffectMechanic"])))
            wrong_sign = aura in negative_only and points >= 0
            if name in spec["defensive_auras"] and targets & friendly and not wrong_sign:
                roles["defensive"].append(spec["defensive_auras"][name])
            if aura == spec["mechanic_immunity_aura"] and targets & friendly and misc in cc:
                roles["cc_break"].append(("immunité", misc))
            if name in spec["mobility_auras"] and on_self:
                roles["mobility"].append(spec["mobility_auras"][name])
            if name in spec["burst_auras"] and on_self and not (aura in positive_only and points <= 0):
                roles["burst"].append(spec["burst_auras"][name])
        if effect == spec["dispel_mechanic_effect"] and misc in cc:
            roles["cc_break"].append(("dissipation", misc))
        if effect == spec["dispel_effect"]:
            if targets & hostile:
                roles["dispel"].append((misc, "ennemi"))
            if targets & friendly:
                roles["dispel"].append((misc, "allié"))
        if effect == spec["interrupt_effect"]:
            roles["interrupt"].append(True)
        if str(effect) in spec["mobility_effects"]:
            roles["mobility"].append(spec["mobility_effects"][str(effect)])
        if str(effect) in spec["summon_effects"]:
            roles["summon"].append(spec["summon_effects"][str(effect)])
    return roles


def _markers(client: _Client, index: _ClassIndex, spell: int, rules: Mapping[str, Any]) -> list[str]:
    """Marqueurs PvP du client portés par un sort (mécanique, catégorie de rendement, mécanique d'effet, invocation)."""
    spec = rules["pvp_classification"]
    neutral = {int(m) for m in spec["neutral_mechanics"]} | {0}
    out = []
    category = index.categories.get(spell)
    if category is not None and int(category["Mechanic"]) not in neutral:
        m = int(category["Mechanic"])
        out.append(f"mécanique {m} ({index.mechanics.get(m, '?')})")
    if category is not None and int(category["DiminishType"]):
        out.append(f"catégorie de rendement décroissant {int(category['DiminishType'])}")
    for _, e in sorted(client.effects.get(spell, {}).items()):
        if int(e["EffectMechanic"]) not in neutral:
            m = int(e["EffectMechanic"])
            out.append(f"mécanique d'effet {m} ({index.mechanics.get(m, '?')})")
        if str(int(e["Effect"])) in spec["summon_effects"]:
            out.append(spec["summon_effects"][str(int(e["Effect"]))])
    return list(dict.fromkeys(out))


def _classify(
    client: _Client, index: _ClassIndex, ranks: list[dict[str, Any]], rules: Mapping[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """(classement PvP du rang le plus haut, suivi de ses déclencheurs directs ; marqueurs non classés)."""
    spec = rules["pvp_classification"]
    top = ranks[-1]
    spell = top["spell_id"]
    own = _own_roles(client, index, spell, rules)
    triggers = sorted(
        {int(e["EffectTriggerSpell"]) for r in ranks for e in client.effects.get(r["spell_id"], {}).values()} - {0}
    )
    pvp: dict[str, Any] = {"kinds": [], "certainty": "probable", "via": []}
    sources: dict[str, tuple[int, dict[str, Any], int | None]] = {}
    for kind in _PVP_KINDS:
        if own.get(kind):
            sources[kind] = (spell, own, None)
    for trigger in triggers:
        theirs = _own_roles(client, index, trigger, rules)
        for kind in _PVP_KINDS:
            if kind not in sources and theirs.get(kind):
                sources[kind] = (trigger, theirs, trigger)
    passive = bool(int((client.misc.get(spell) or {}).get("Attributes_0", 0)) & int(rules["passive_attributes_0_mask"]))
    if "burst" in sources and (passive or (top["cooldown_s"] or 0) < spec["burst_min_cooldown_s"]):
        del sources["burst"]
    for kind in _PVP_KINDS:
        if kind not in sources:
            continue
        origin, roles, via = sources[kind]
        rank = top if via is None else _spell_rank(client, index, origin, rules)
        detail: dict[str, Any]
        if kind == "control":
            types = list(dict.fromkeys(t for t, _ in roles["control"]))
            effect_mechanics = [m for _, m in roles["control"] if m]
            mechanic = rank["mechanic"] or (effect_mechanics[0] if effect_mechanics else 0)
            interrupt = index.interrupts.get(origin)
            flags = int(interrupt["AuraInterruptFlags_0"]) if interrupt else 0
            detail = {
                "types": types,
                "mechanic": mechanic,
                "mechanic_name": index.mechanics.get(mechanic, "") if mechanic else "",
                "diminish": rank["diminish"],
                "breaks_on_damage": bool(flags & int(spec["damage_break_aura_interrupt_mask"])),
                "duration_s": rank["duration_s"],
                "pvp_duration_s": rank["pvp_duration_s"],
                "via": via,
            }
        elif kind == "defensive":
            detail = {"types": list(dict.fromkeys(roles["defensive"])), "duration_s": rank["duration_s"], "via": via}
        elif kind == "cc_break":
            mechanics = sorted({m for _, m in roles["cc_break"]})
            detail = {
                "mechanics": mechanics,
                "mechanic_names": [index.mechanics.get(m, "") for m in mechanics],
                "how": sorted({how for how, _ in roles["cc_break"]}),
                "via": via,
            }
        elif kind == "interrupt":
            detail = {"lockout_s": rank["duration_s"], "via": via}
        elif kind == "dispel":
            types = sorted({t for t, _ in roles["dispel"]})
            detail = {
                "types": types,
                "type_names": [index.dispels.get(t, "") for t in types],
                "targets": sorted({d for _, d in roles["dispel"]}),
                "via": via,
            }
        elif kind == "mobility":
            detail = {"types": list(dict.fromkeys(roles["mobility"])), "via": via}
        else:
            detail = {"types": list(dict.fromkeys(roles["burst"])), "cooldown_s": top["cooldown_s"], "via": via}
        pvp["kinds"].append(kind)
        pvp[kind] = detail
        if via is not None and via not in pvp["via"]:
            pvp["via"].append(via)
    markers: list[str] = []
    for r in ranks:
        markers += _markers(client, index, r["spell_id"], rules)
    return pvp, list(dict.fromkeys(markers))


def _spell_entries(
    tables: Tables,
    rules: Mapping[str, Any],
    client: _Client,
    index: _ClassIndex,
    lines: Sequence[int],
    version: str,
    talent_of: Mapping[int, dict[str, Any]],
    pets: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    methods = {int(m) for m in rules["spell_ranks"]["acquire_methods"]}
    wanted = set(lines)
    rows_of: dict[int, list[Row]] = defaultdict(list)
    for r in tables["SkillLineAbility"]:
        if int(r["SkillLine"]) in wanted and int(r["AcquireMethod"]) in methods:
            rows_of[int(r["Spell"])].append(r)
    by_name: dict[str, list[int]] = defaultdict(list)
    for spell in sorted(rows_of):
        by_name[client.names.get(spell, f"sort {spell}")].append(spell)
    entries: dict[str, Any] = {}
    unresolved: list[dict[str, Any]] = []
    for name, spells in sorted(by_name.items(), key=lambda kv: min(kv[1])):
        ranks = sorted(
            (_spell_rank(client, index, s, rules) for s in spells),
            key=lambda r: (r["rank"] is None, r["rank"] or 0, r["level"] or 0, r["spell_id"]),
        )
        try:
            key = talent_key(name)
        except DataSchemaError:
            key = f"spell{min(spells)}"
        if key in entries:
            key = f"{key}{min(spells)}"
        pvp, markers = _classify(client, index, ranks, rules)
        talent = next((talent_of[s] for s in spells if s in talent_of), None)
        entry: dict[str, Any] = {
            "name": name,
            "name_fr": client.names_fr.get(min(spells), ""),
            "skill_line": int(rows_of[min(spells)][0]["SkillLine"]),
            "talent": talent,
            "ranks": ranks,
            "pvp": pvp,
            "certainty": f"FC-{version}",
        }
        if pets:
            entry["pet_families"] = sorted(
                {index.skill_names.get(int(r["SkillLine"]), "") for s in spells for r in rows_of[s]}
            )
        entries[key] = entry
        if markers and not pvp["kinds"]:
            unresolved.append(
                {"key": key, "spell_id": ranks[-1]["spell_id"], "name": name, "reason": " ; ".join(markers)}
            )
    return entries, unresolved


def _class_spells(
    tables: Tables,
    rules: Mapping[str, Any],
    client: _Client,
    index: _ClassIndex,
    cls: str,
    c: dict[str, Any],
    version: str,
) -> None:
    """Ajoute à la classe `c` ses sorts, ceux de ses familiers et les sorts non résolus."""
    spec = rules["classes"][cls]
    learn = int(rules["pvp_classification"]["learn_spell_effect"])
    talent_of: dict[int, dict[str, Any]] = {}
    for tree in c["trees"]:
        for t in tree["talents"]:
            link = {"node_id": t["node_id"], "key": t["key"]}
            talent_of[t["spell_id"]] = link
            for e in client.effects.get(t["spell_id"], {}).values():
                if int(e["Effect"]) == learn and int(e["EffectTriggerSpell"]):
                    talent_of[int(e["EffectTriggerSpell"])] = link
    c["spells"], unresolved = _spell_entries(
        tables, rules, client, index, [int(i) for i in spec["skill_lines"]], version, talent_of, pets=False
    )
    if spec.get("pet_skill_lines"):
        c["pet_spells"], pet_unresolved = _spell_entries(
            tables, rules, client, index, [int(i) for i in spec["pet_skill_lines"]], version, {}, pets=True
        )
        unresolved += pet_unresolved
    c["unresolved_spells"] = unresolved


def decode_classes(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `classes.json` (PV1) : pour chacune des 9 classes (`classes` des règles), identifiant et jeton du
    client, arbre de traits, trois arbres de talents (nom de la ligne de compétence de l'onglet), talents avec leur
    nœud (`node_id`), palier, colonne, rangs, prérequis (nœud), sort et description du client ; nœuds hors grille
    listés non résolus (`unresolved_nodes`, jamais arrondis), doublons périmés écartés (`dropped_nodes`, règle
    `shared_spell`), contrôle de l'ordre des onglets (`tree_checks`)."""
    client = _Client(tables, rules)
    index = _ClassIndex(tables)
    classes = {cls: _class_talents(tables, rules, client, cls, version) for cls in rules["classes"]}
    for cls, c in classes.items():
        _class_spells(tables, rules, client, index, cls, c, version)
    return {
        "build": version,
        "source": (
            f"Client {version} : tables Trait*, SkillLine*, ChrClasses et Spell* (wago.tools) décodées par forever decode"
        ),
        "classes": classes,
        "notes": [
            "Onglet i : lignes de compétence classes.<Classe>.skill_lines[i] (decode_rules.json), abscisse tab_origins[i].",
            (
                "Position hors grille : zéro en trop corrigé (extra_zero_divisor) ; tout autre écart laissé à null "
                "et listé dans unresolved_nodes, jamais arrondi."
            ),
            (
                "prereqs : arêtes non visuelles du client, sens tiré de TraitEdge.Type (decode_rules.json, "
                "trait_edge_types, probable) ; prereq : le prérequis unique quand il n'y en a qu'un."
            ),
        ],
    }


def _class_mask_names(tables: Tables, rules: Mapping[str, Any], mask: int) -> list[str] | None:
    """Classes d'un masque du client (bit = 1 << (ID de ChrClasses - 1)), par ordre alphabétique ; None : toutes."""
    if mask in (0, -1):
        return None
    ids = {str(r["Name_lang"]): int(r["ID"]) for r in tables["ChrClasses"]}
    return sorted(c for c in rules["classes"] if c in ids and mask & (1 << (ids[c] - 1)))


def _race_mask(row: Row) -> int:
    """Masque de races sur 64 bits (RaceMasks_0 | RaceMasks_1 << 32) ; -1 : toutes."""
    low, high = int(row["RaceMasks_0"]), int(row["RaceMasks_1"])
    return -1 if low == -1 else (low & 0xFFFFFFFF) | (high << 32)


def _spell_effects(client: _Client, spell: int) -> list[dict[str, Any]]:
    return [
        {
            "effect": int(e["Effect"]),
            "aura": int(e["EffectAura"]),
            "base_points": normalize(float(e["EffectBasePointsF"])),
            "misc": int(e["EffectMiscValue_0"]),
            "mechanic": int(e["EffectMechanic"]),
        }
        for _, e in sorted(client.effects.get(spell, {}).items())
    ]


def _cooldown_s(client: _Client, spell: int) -> float | None:
    cd = client.cooldowns.get(spell)
    value = max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])) / 1000 if cd else 0
    return normalize(value) if value > 0 else None


def _duration_s(client: _Client, spell: int) -> float | None:
    ms = client.duration_ms(spell)
    return normalize(ms / 1000) if ms is not None and ms > 0 else None  # -1 : jusqu'à annulation


def decode_races(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `races.json` (PV1, décision 106) : races jouables (présentes dans CharBaseInfo), nom anglais et
    français, jeton du client, faction, classes permises ; raciaux (lignes `racial_skill_lines`) par race avec les
    classes concernées, passif ou non, recharge, durée et effets bruts du client ; `mage_values` : les grandeurs lues
    par le moteur du Mage (`racial_values` des règles)."""
    client = _Client(tables, rules)
    chr_races = {int(r["ID"]): r for r in tables["ChrRaces"]}
    french = {int(r["ID"]): str(r["Name_lang"]) for r in tables.get("frFR/ChrRaces", [])}
    class_ids = {int(r["ID"]): str(r["Name_lang"]) for r in tables["ChrClasses"]}
    order = list(rules["classes"])
    allowed: dict[int, set[str]] = defaultdict(set)
    for r in tables["CharBaseInfo"]:
        allowed[int(r["RaceID"])].add(class_ids[int(r["ClassID"])])
    lines = {int(i) for i in rules["racial_skill_lines"]}
    abilities = [r for r in tables["SkillLineAbility"] if int(r["SkillLine"]) in lines]
    passive_mask = int(rules["passive_attributes_0_mask"])
    values_rules = rules["racial_values"]
    races: dict[str, Any] = {}
    for race_id in sorted(allowed):
        row = chr_races.get(race_id)
        if row is None:
            raise DataSchemaError(f"Race {race_id} de CharBaseInfo absente de ChrRaces.")
        bit = 1 << int(row["PlayableRaceBit"])
        racials = []
        mage_values: dict[str, float] = {}
        for a in abilities:
            mask = _race_mask(a)
            if mask != -1 and not mask & bit:
                continue
            spell = int(a["Spell"])
            misc = client.misc.get(spell)
            classes = _class_mask_names(tables, rules, int(a["ClassMask"]))
            effects = _spell_effects(client, spell)
            name = client.names.get(spell, "")
            racials.append(
                {
                    "spell_id": spell,
                    "name": name,
                    "name_fr": client.names_fr.get(spell, ""),
                    "classes": classes,
                    "passive": bool(misc is not None and int(misc["Attributes_0"]) & passive_mask),
                    "cooldown_s": _cooldown_s(client, spell),
                    "duration_s": _duration_s(client, spell),
                    "effects": effects,
                    "certainty": f"FC-{version}",
                }
            )
            if classes is not None and "Mage" not in classes:
                continue
            for key, rule in values_rules.items():
                if "spell_name" in rule and rule["spell_name"] != name:
                    continue
                for e in effects:
                    if e["aura"] == rule["aura"] and ("misc" not in rule or e["misc"] == rule["misc"]):
                        mage_values[key] = round(mage_values.get(key, 0.0) + e["base_points"] * rule["scale"], 10)
        races[str(row["Name_lang"])] = {
            "id": race_id,
            "client_file": str(row["ClientFileString"]),
            "name": str(row["Name_lang"]),
            "name_fr": french.get(race_id, ""),
            "faction": rules["race_factions"].get(str(row["Alliance"])),
            "classes": sorted(allowed[race_id], key=order.index),
            "racials": racials,
            "mage_values": mage_values,
        }
    return {
        "build": version,
        "source": (
            f"Client {version} : tables ChrRaces, CharBaseInfo, SkillLineAbility et Spell* (wago.tools) décodées par "
            "forever decode"
        ),
        "races": races,
        "notes": [
            "Races jouables : celles de CharBaseInfo (combinaisons de Forever comprises), sans liste de Classic.",
            "Raciaux : lignes racial_skill_lines de decode_rules.json ; classes null : toutes les classes.",
            (
                "mage_values : grandeurs lues par le moteur du Mage (racial_values de decode_rules.json), variantes "
                "de classe qui concernent le Mage seulement ; sword_crit exige une épée (arme hors des tables lues)."
            ),
        ],
    }


def decode_pvp_items(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `pvp_items.json` (PV1) : bijoux (`pvp_trinkets.inventory_type`) dont le sort d'utilisation rompt
    un contrôle (dissipation par mécanique ou immunité de mécanique), avec classes permises, recharge, recharge de
    catégorie et mécaniques rompues ; recharge partagée avec un racial non décidée par le client (registre K4)."""
    spec = rules["pvp_trinkets"]
    client = _Client(tables, rules)
    items = {int(r["ID"]): r for r in tables["Item"]}
    sparse = {int(r["ID"]): r for r in tables["ItemSparse"]}
    item_effects = {int(r["ID"]): r for r in tables["ItemEffect"]}
    mechanics = {int(r["ID"]): str(r["StateName_lang"]) for r in tables["SpellMechanic"]}
    trinkets = []
    for link in sorted(tables["ItemXItemEffect"], key=lambda r: (int(r["ItemID"]), int(r["ID"]))):
        item_id = int(link["ItemID"])
        item, name_row = items.get(item_id), sparse.get(item_id)
        effect = item_effects.get(int(link["ItemEffectID"]))
        if item is None or name_row is None or effect is None:
            continue
        if int(item["InventoryType"]) != spec["inventory_type"] or int(effect["TriggerType"]) != spec["use_trigger"]:
            continue
        spell = int(effect["SpellID"])
        breaks = []
        for e in _spell_effects(client, spell):
            if e["effect"] == spec["dispel_mechanic_effect"]:
                breaks.append({"kind": "dispel", "mechanic": e["misc"], "mechanic_name": mechanics.get(e["misc"], "")})
            elif e["effect"] == spec["apply_aura_effect"] and e["aura"] == spec["mechanic_immunity_aura"]:
                breaks.append(
                    {"kind": "immunity", "mechanic": e["misc"], "mechanic_name": mechanics.get(e["misc"], "")}
                )
        if not breaks:
            continue
        category_ms = int(effect["CategoryCoolDownMSec"])
        trinkets.append(
            {
                "item_id": item_id,
                "name": str(name_row["Display_lang"]),
                "classes": _class_mask_names(tables, rules, int(name_row["AllowableClass"])),
                "spell_id": spell,
                "spell_name": client.names.get(spell, ""),
                "cooldown_s": normalize(int(effect["CoolDownMSec"]) / 1000),
                "category_cooldown_s": normalize(category_ms / 1000) if category_ms > 0 else None,
                "spell_category": int(effect["SpellCategoryID"]),
                "breaks": breaks,
                "certainty": f"FC-{version}",
            }
        )
    return {
        "build": version,
        "source": f"Client {version} : tables Item, ItemSparse, ItemEffect, ItemXItemEffect et Spell* décodées",
        "trinkets": trinkets,
        "shared_cooldown_with_racials": None,
        "notes": [
            (
                "Recharge partagée entre un bijou PvP et un racial (Will of the Forsaken…) : non décidée par le "
                "client (registre K4, absent ; docs/OPEN_QUESTIONS.md)."
            ),
            "Faction d'un Insigne : absente des tables lues (nom seulement).",
        ],
    }


# --- Sorts ---------------------------------------------------------------------------------------


def _rank_row(client: _Client, spell: int, rules: Mapping[str, Any]) -> list[Any]:
    fx, ranks_rules = rules["effects"], rules["spell_ranks"]
    mode = rules["levels"]["spell_rank"]
    level = client.levels.get(spell)
    misc = client.misc.get(spell)
    if level is None or misc is None:
        raise DataSchemaError(f"Sort {spell} : SpellLevels ou SpellMisc absent.")
    channel = bool(int(misc["Attributes_1"]) & int(ranks_rules["channel_attributes_1_mask"]))
    duration = client.duration_ms(spell)
    low: float = 0
    high: float = 0
    effects = [client.effects[spell][i] for i in sorted(client.effects.get(spell, {}))]
    for e in effects:
        if int(e["Effect"]) == fx["school_damage"]:
            a, b = client.damage(spell, int(e["EffectIndex"]), mode)
            low, high = low + a, high + b
    periodic: list[tuple[int, int, float]] = []  # (min par tick, max par tick, ticks)
    description = str(client.spell.get(spell, {}).get("Description_lang", ""))
    for e in effects:
        if int(e["Effect"]) != fx["apply_aura"] or not int(e["EffectAuraPeriod"]):
            continue
        if duration is None:
            raise DataSchemaError(f"Sort {spell} : effet périodique sans durée.")
        ticks = duration / int(e["EffectAuraPeriod"])
        aura = int(e["EffectAura"])
        if aura == fx["aura_periodic_damage"]:
            value = int(half_up(client.points(spell, int(e["EffectIndex"]), mode)[0]))
            periodic.append((value, value, ticks))
            continue
        if aura == fx["aura_periodic_trigger_spell"]:
            linked = [int(e["EffectTriggerSpell"])]
        elif aura == fx["aura_periodic_dummy"]:
            linked = [int(s) for s in _CITED_SPELL.findall(description)]
        else:
            continue
        for other in linked:
            for te in client.effects.get(other, {}).values():
                if int(te["Effect"]) == fx["school_damage"]:
                    a, b = client.damage(other, int(te["EffectIndex"]), mode)
                    periodic.append((a, b, ticks))
    dot_total: float = 0
    for a, b, ticks in periodic:
        if channel:
            low, high = low + a * ticks, high + b * ticks
        else:
            dot_total += a * ticks
    cast = duration / 1000 if channel and duration else client.cast.get(int(misc["CastingTimeIndex"]), 0) / 1000
    mana = None
    for p in client.power.get(spell, []):
        if int(p["PowerType"]) == ranks_rules["mana_power_type"] and int(p["ManaCost"]) > 0:
            mana = int(p["ManaCost"])
    cd = client.cooldowns.get(spell)
    cooldown = max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])) / 1000 if cd else 0
    dot_duration = normalize(duration / 1000) if dot_total and duration else 0
    row = {
        "level": int(level["BaseLevel"]),
        "min": normalize(low),
        "max": normalize(high),
        "dot_total": normalize(dot_total),
        "dot_duration": dot_duration,
        "cast_s": float(cast),
        "mana": mana,
        "cooldown_s": normalize(cooldown),
    }
    return [row[f] for f in rules["rank_format"]]


def _rank_ids(
    tables: Tables, rules: Mapping[str, Any], client: _Client, names: Mapping[str, str]
) -> dict[str, list[int]]:
    """Clé -> identifiants des rangs 1, 2, … des sorts `names` (clé -> nom anglais) : lignes du Mage de
    SkillLineAbility aux méthodes d'acquisition retenues, rang lu dans Spell.NameSubtext (`spell_ranks`)."""
    lines = set(rules["skill_lines"].values())
    methods = set(rules["spell_ranks"]["acquire_methods"])
    rank_re = re.compile(rules["spell_ranks"]["rank_subtext"])
    wanted = {name: key for key, name in names.items()}
    found: dict[str, dict[int, int]] = defaultdict(dict)
    for r in tables["SkillLineAbility"]:
        spell = int(r["Spell"])
        key = wanted.get(client.names.get(spell, ""))
        if key is None or int(r["SkillLine"]) not in lines or int(r["AcquireMethod"]) not in methods:
            continue
        match = rank_re.match(str(client.spell.get(spell, {}).get("NameSubtext_lang", "")))
        if not match:
            raise DataSchemaError(f"Sort {spell} ({names[key]}) : rang illisible dans NameSubtext.")
        rank = int(match[1])
        if found[key].get(rank, spell) != spell:
            raise DataSchemaError(f"{key} : deux sorts pour le rang {rank} ({found[key][rank]}, {spell}).")
        found[key][rank] = spell
    out = {}
    for key, name in names.items():
        ranks = found.get(key, {})
        if not ranks or sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise DataSchemaError(f"{key} ({name}) : rangs incomplets dans le client ({sorted(ranks)}).")
        out[key] = [ranks[r] for r in sorted(ranks)]
    return out


def decode_spells(
    tables: Tables, rules: Mapping[str, Any], inherited: Mapping[str, Any], version: str
) -> dict[str, Any]:
    """Contenu de `spells.json` : rangs décodés (`rank_format`), noms anglais et français, identifiants des rangs ;
    les autres champs (portée, ralentissement, sorts utilitaires…) sont repris de `inherited`."""
    if list(inherited.get("rank_format", [])) != list(rules["rank_format"]):
        raise DataSchemaError(f"rank_format de {RULES_NAME} différent de celui de spells.json hérité.")
    client = _Client(tables, rules)
    found = _rank_ids(tables, rules, client, rules["spells"])
    doc = copy.deepcopy(dict(inherited))
    doc["build"] = version
    doc["inherited_from"] = inherited.get("build")
    doc["source"] = f"Client {version} : tables Spell* et SkillLineAbility (wago.tools) décodées par forever decode"
    for key, name in rules["spells"].items():
        ids = found[key]
        entry = dict(doc["spells"].get(key, {}))
        entry["ranks"] = [_rank_row(client, i, rules) for i in ids]
        entry["name"] = name
        entry["name_fr"] = client.names_fr.get(ids[0], "")
        entry["spell_ids"] = ids
        doc["spells"][key] = entry
    return doc


def _component(
    client: _Client, spell: int, index: int, kind: str, ticks: float, variance: bool, period_ms: int = 0
) -> dict[str, Any]:
    """Effet de dégâts `index` du sort `spell` ; `period_ms` : période de l'aura qui le porte (celle du sort parent
    pour un sort déclenché), 0 pour un coup direct."""
    e = client.effect(spell, index)
    base, top = client.level_for(spell, "max_capped")
    return {
        "spell_id": spell,
        "index": index,
        "kind": kind,
        "ticks": normalize(ticks),
        "base_level": base,
        "max_level": top,
        "base_points": float(e["EffectBasePointsF"]),
        "points_per_level": float(e["EffectRealPointsPerLevel"]),
        "variance": float(e["Variance"]) if variance else 0.0,
        "bonus_coefficient": float(e["EffectBonusCoefficient"]),
        "period_ms": period_ms,
    }


def _components(client: _Client, spell: int, rules: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Effets de dégâts d'un rang, dans l'ordre de `_rank_row` : directs (`direct`), puis périodiques (`dot`, ou
    `channel` pour un sort canalisé), éventuellement portés par un sort déclenché ou cité par l'infobulle."""
    fx = rules["effects"]
    misc = client.misc[spell]
    channel = bool(int(misc["Attributes_1"]) & int(rules["spell_ranks"]["channel_attributes_1_mask"]))
    effects = [client.effects[spell][i] for i in sorted(client.effects.get(spell, {}))]
    out = [
        _component(client, spell, int(e["EffectIndex"]), "direct", 1, True)
        for e in effects
        if int(e["Effect"]) == fx["school_damage"]
    ]
    description = str(client.spell.get(spell, {}).get("Description_lang", ""))
    duration = client.duration_ms(spell)
    kind = "channel" if channel else "dot"
    for e in effects:
        if int(e["Effect"]) != fx["apply_aura"] or not int(e["EffectAuraPeriod"]) or duration is None:
            continue
        period = int(e["EffectAuraPeriod"])
        ticks = duration / period
        aura = int(e["EffectAura"])
        if aura == fx["aura_periodic_damage"]:
            out.append(_component(client, spell, int(e["EffectIndex"]), kind, ticks, False, period))
            continue
        if aura == fx["aura_periodic_trigger_spell"]:
            linked = [int(e["EffectTriggerSpell"])]
        elif aura == fx["aura_periodic_dummy"]:
            linked = [int(s) for s in _CITED_SPELL.findall(description)]
        else:
            continue
        for other in linked:
            for te in client.effects.get(other, {}).values():
                if int(te["Effect"]) == fx["school_damage"]:
                    out.append(_component(client, other, int(te["EffectIndex"]), kind, ticks, True, period))
    return out


def decode_scaling(tables: Tables, rules: Mapping[str, Any], version: str) -> dict[str, Any]:
    """Contenu de `spell_scaling.json` : pour chaque rang des sorts suivis, niveaux (`MaxLevel` 0 résolu au plafond
    de `decode_rules.json`), recharge globale déclenchée (`SpellCooldowns.StartRecoveryTime`, 0 sans ligne) et effets
    de dégâts (points de base, points par niveau, variance, nombre de ticks, coefficient de puissance des sorts,
    période), pour calculer les dégâts au niveau du personnage (moteur : `rank_values_at_level`, `coefficient`)."""
    client = _Client(tables, rules)
    spells = decode_spells(tables, rules, {"rank_format": rules["rank_format"], "spells": {}}, version)["spells"]
    out: dict[str, list[dict[str, Any]]] = {}
    for key, spell in spells.items():
        ranks = []
        for position, spell_id in enumerate(spell["spell_ids"], start=1):
            level = client.levels[spell_id]
            base, top = client.level_for(spell_id, "max_capped")
            ranks.append(
                {
                    "rank": position,
                    "spell_id": spell_id,
                    "base_level": base,
                    "spell_level": int(level["SpellLevel"]),
                    "max_level": top,
                    "start_recovery_ms": int(cd["StartRecoveryTime"]) if (cd := client.cooldowns.get(spell_id)) else 0,
                    "components": _components(client, spell_id, rules),
                }
            )
        out[key] = ranks
    notes = [
        "points au niveau L : base_points + points_per_level × (min(max(L, base_level), max_level) - base_level)",
        "min et max : points × (1 ∓ variance / 2), arrondis au demi supérieur ; channel et dot : × ticks",
        "max_level : MaxLevel du client (0 = plafond de niveau), borné au plafond",
        "start_recovery_ms : StartRecoveryTime de SpellCooldowns (recharge globale déclenchée par le rang)",
        "bonus_coefficient : EffectBonusCoefficient de l'effet de dégâts (par coup, par tic ou par éclair canalisé)",
        (
            "period_ms : EffectAuraPeriod de l'aura qui porte l'effet (celle du sort parent pour un sort déclenché), "
            "0 pour un coup direct"
        ),
    ]
    doc: dict[str, Any] = {
        "schema_version": 2,
        "build": version,
        "source": f"Client {version} : tables SpellEffect, SpellLevels, SpellMisc, SpellCooldowns, SkillLineAbility "
        "(wago.tools) décodées par forever decode",
        "level_cap": int(rules["levels"]["level_cap"]),
        "spells": out,
        "notes": notes,
    }
    if "utility_spells" in rules:
        doc["utility"] = _utility(tables, rules, client)
        notes.append(
            "utility : armures du Mage, niveau d'apprentissage (SpellLevels.BaseLevel) et effets retenus par "
            "decode_rules.json.utility_spells"
        )
    if "target_auras" in rules:
        doc["auras"] = _target_auras(tables, rules, client)
        notes.append(
            "auras : auras posées sur la cible par un talent (decode_rules.json.target_auras) : part par cumul (%), "
            "cumuls maximum, durée, écoles touchées"
        )
    if "talent_cooldowns" in rules:
        doc["talent_cooldowns"] = _talent_cooldowns(tables, rules, client)
        notes.append(
            "talent_cooldowns : recharge des sorts de talent actifs (decode_rules.json.talent_cooldowns), maximum de "
            "RecoveryTime et CategoryRecoveryTime de SpellCooldowns, en millisecondes"
        )
    return doc


def _talent_cooldowns(tables: Tables, rules: Mapping[str, Any], client: _Client) -> dict[str, dict[str, int]]:
    """Recharges des talents actifs (`talent_cooldowns.talents` : noms du client) : sort du talent (TraitDefinition,
    nom du sort à défaut du nom de remplacement), recharge = max(RecoveryTime, CategoryRecoveryTime) en ms."""
    talents: dict[str, int] = {}
    for d in tables["TraitDefinition"]:
        spell = int(d["SpellID"])
        talents.setdefault(str(d["OverrideName_lang"]) or client.names.get(spell, ""), spell)
    out: dict[str, dict[str, int]] = {}
    for name in rules["talent_cooldowns"]["talents"]:
        found = talents.get(name)
        cd = client.cooldowns.get(found) if found is not None else None
        if found is None or cd is None:
            raise DataSchemaError(f"{RULES_NAME} : talent « {name} » sans sort ou sans recharge (talent_cooldowns).")
        out[talent_key(name)] = {
            "spell_id": found,
            "cooldown_ms": max(int(cd["RecoveryTime"]), int(cd["CategoryRecoveryTime"])),
        }
    return out


def _target_auras(tables: Tables, rules: Mapping[str, Any], client: _Client) -> dict[str, dict[str, Any]]:
    """Auras posées sur la cible par un talent (`target_auras`) : sort de l'aura (EffectTriggerSpell du talent),
    part par cumul, cumuls maximum (SpellAuraOptions), durée (SpellDuration), écoles (bits de `school_masks`)."""
    fx = rules["effects"]
    masks = rules["school_masks"]
    talents: dict[str, int] = {}
    for d in tables["TraitDefinition"]:
        spell = int(d["SpellID"])
        talents.setdefault(str(d["OverrideName_lang"]) or client.names.get(spell, ""), spell)
    out: dict[str, dict[str, Any]] = {}
    for key, spec in rules["target_auras"].items():
        source = talents.get(spec["talent"])
        if source is None:
            raise DataSchemaError(f"{RULES_NAME} : talent « {spec['talent']} » absent de TraitDefinition ({key}).")
        triggers = [
            int(e["EffectTriggerSpell"])
            for e in client.effects.get(source, {}).values()
            if int(e["Effect"]) == fx["apply_aura"] and int(e["EffectAura"]) == spec["trigger_aura"]
        ]
        if len(triggers) != 1:
            raise DataSchemaError(f"{key} : {len(triggers)} sort(s) déclenché(s) par {source}, un seul attendu.")
        aura = triggers[0]
        effects = [
            e
            for e in client.effects.get(aura, {}).values()
            if int(e["Effect"]) == fx["apply_aura"] and int(e["EffectAura"]) == spec["aura"]
        ]
        options, duration = client.auras.get(aura), client.duration_ms(aura)
        if len(effects) != 1 or options is None or duration is None:
            raise DataSchemaError(f"{key} (sort {aura}) : effet d'aura {spec['aura']}, cumuls ou durée absents.")
        mask = int(effects[0]["EffectMiscValue_0"])
        out[key] = {
            "spell_id": aura,
            "source_spell_id": source,
            "talent": talent_key(spec["talent"]),
            "pct_per_stack": normalize(float(effects[0][spec["field"]])),
            "max_stacks": int(options["CumulativeAura"]),
            "duration_ms": duration,
            "schools": [school for school, bit in masks.items() if mask & int(bit)],
        }
    return out


def _utility(tables: Tables, rules: Mapping[str, Any], client: _Client) -> dict[str, list[dict[str, Any]]]:
    """Armures (`utility_spells`) : par rang, identifiant, niveau d'apprentissage et effets retenus (aura, valeur
    diverse éventuelle -> champ de SpellEffect)."""
    spec = rules["utility_spells"]
    wanted = spec["effects"]
    out: dict[str, list[dict[str, Any]]] = {}
    for key, ids in _rank_ids(tables, rules, client, spec["spells"]).items():
        ranks = []
        for position, spell_id in enumerate(ids, start=1):
            effects: dict[str, int | float] = {}
            for e in client.effects.get(spell_id, {}).values():
                if int(e["Effect"]) != rules["effects"]["apply_aura"]:
                    continue
                for name, want in wanted.items():
                    if int(e["EffectAura"]) != want["aura"]:
                        continue
                    if "misc_value" in want and int(e["EffectMiscValue_0"]) != want["misc_value"]:
                        continue
                    effects[name] = normalize(float(e[want["field"]]))
            ranks.append(
                {
                    "rank": position,
                    "spell_id": spell_id,
                    "learned_level": int(client.levels[spell_id]["BaseLevel"]),
                    "effects": effects,
                }
            )
        out[key] = ranks
    return out


# --- Version candidate ---------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"{path} illisible ({exc}).") from exc


def _write_json(path: Path, doc: Any) -> None:
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def _observations(talents: Mapping[str, Any], spells: Mapping[str, Any], base: Path) -> list[str]:
    notes: list[str] = []
    reference = {t["key"]: t for tree in _read_json(base / "talents.json")["trees"] for t in tree["talents"]}
    differing = [
        f"{t['key']} {t['spellIds'][0]} contre {reference[t['key']].get('spellIds', [None])[:1]}"
        for tree in talents["trees"]
        for t in tree["talents"]
        if t["key"] in reference and t["spellIds"][:1] != reference[t["key"]].get("spellIds", [])[:1]
    ]
    if differing:
        notes.append(
            f"spellIds : {len(differing)} talent(s) portent un autre sort que la référence ({'; '.join(differing)})"
        )
    ref_spells = _read_json(base / "spells.json")
    fields = list(ref_spells["rank_format"])
    for key, spell in spells["spells"].items():
        old = ref_spells["spells"].get(key, {}).get("ranks", [])
        for i, (a, b) in enumerate(zip(old, spell["ranks"], strict=False), start=1):
            for field, x, y in zip(fields, a, b, strict=True):
                if x is None and y is not None:
                    notes.append(f"{key} rang {i} : {field} {y} relevé dans le client (référence null)")
    return notes


def _is_candidate(path: Path, version: str) -> bool:
    """Dossier produit par `decode` pour cette version : manifeste, un seul dossier de version, `candidate` dans
    son `sources.json`. Seul un tel dossier peut être remplacé avec `force`."""
    if not (path / "manifest.json").is_file() or version_dirs(path) != [version]:
        return False
    try:
        sources = json.loads((path / version / SOURCES_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(sources, dict) and sources.get("candidate") is True


def _class_observations(doc: Mapping[str, Any]) -> list[str]:
    """Nœuds hors grille, doublons écartés et sorts marqués sans classement, par classe (rapport de décodage)."""
    notes: list[str] = []
    for cls, c in doc.get("classes", {}).items():
        if c.get("unresolved_nodes"):
            keys = ", ".join(u["key"] for u in c["unresolved_nodes"])
            notes.append(f"{cls} : {len(c['unresolved_nodes'])} nœud(s) hors grille non résolu(s) ({keys})")
        if c.get("dropped_nodes"):
            notes.append(f"{cls} : {len(c['dropped_nodes'])} nœud(s) en double écarté(s) (même sort, nœud plus récent)")
        if c.get("unresolved_spells"):
            names = ", ".join(u["name"] for u in c["unresolved_spells"])
            notes.append(f"{cls} : {len(c['unresolved_spells'])} sort(s) marqué(s) non classé(s) ({names})")
    return notes


def _inherited_source(base: Path, name: str, rules: Mapping[str, Any]) -> Path | None:
    """Fichier de la version de base dont `name` hérite : lui-même, ou le fichier retiré dont il est la copie figée
    (`retired_files`, première installation de la copie)."""
    if (base / name).is_file():
        return base / name
    for old, spec in rules.get("retired_files", {}).items():
        retired = base / str(old)
        if spec.get("frozen_copy") == name and retired.is_file():
            return retired
    return None


def decode_version(
    deps: Deps, version: str, *, csv_dir: Path | None = None, out: Path | None = None, force: bool = False
) -> Candidate:
    """Écrit une version candidate complète dans `out` (défaut : `<cache>/candidates/<version>/`).

    `csv_dir` : dossier des CSV (défaut : cache de `forever fetch`). Règles et fichiers hérités : version locale la
    plus récente. Refuse d'écraser une candidate existante sans `force`. Aucun accès réseau."""
    if not VERSION_DIR_RE.fullmatch(version):
        raise InvalidArgumentError(
            f"Version mal formée : « {version} ».", "donner une version complète, par exemple 1.60.1.70009"
        )
    base_version, rules = load_rules(deps.data_dir)
    base = deps.data_dir / base_version
    csv_dir = csv_dir or wago_dir(deps.cache_dir, version)
    out = out or deps.cache_dir / "candidates" / version
    if out.resolve().is_relative_to(deps.data_dir.resolve()):
        raise InvalidArgumentError(
            f"Une version candidate ne s'écrit jamais dans {deps.data_dir}.",
            "choisir un dossier --out hors des données",
        )
    missing = [rel for _, rel in table_files(rules) if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(version, missing)
    # Tables des 9 classes : toutes (décodées) ou aucune (fichiers hérités de la base) ; une partie est une erreur.
    class_files = class_table_files(rules)
    class_missing = [rel for _, rel in class_files if not (csv_dir / rel).is_file()]
    if class_missing and len(class_missing) < len(class_files):
        raise CsvMissingError(version, class_missing)
    if out.exists() and any(out.iterdir()) and (not force or not _is_candidate(out, version)):
        raise CandidateExistsError(str(out))
    tables = load_tables(csv_dir, rules)
    talents = decode_talents(tables, rules, version)
    spells = decode_spells(tables, rules, _read_json(base / "spells.json"), version)
    scaling = decode_scaling(tables, rules, version)
    extra_notes: list[str] = []
    decoded_classes: dict[str, Any] = {}
    if class_files and not class_missing:
        more = load_class_tables(csv_dir, rules)
        decoded_classes = {
            "classes.json": decode_classes(more, rules, version),
            "races.json": decode_races(more, rules, version),
            "pvp_items.json": decode_pvp_items(more, rules, version),
        }
        extra_notes += _class_observations(decoded_classes["classes.json"])
    # T08b, bloc A : ratios du personnage (character_tables) : toutes les tables (décodées) ou aucune (héritées).
    char_files = [(n, rel) for n, rel in character_table_files(rules) if n in rules.get("character_tables", [])]
    char_missing = [rel for _, rel in char_files if not (csv_dir / rel).is_file()]
    if char_missing and len(char_missing) < len(char_files):
        raise CsvMissingError(version, char_missing)
    if char_files and not char_missing:
        char_doc = decode_character_scaling(
            load_character_tables(csv_dir, rules), rules, load_gametables(gametables_dir(csv_dir), rules), version
        )
        decoded_classes[CHARACTER_FILE] = char_doc
        extra_notes += [
            f"{CHARACTER_FILE} : {c['value']} / GameTable {c['gametable']} : {c['status']}"
            + (f" ({len(c['gaps'])} écart(s))" if c["gaps"] else "")
            for c in char_doc["crosscheck"]
        ]
    inherited = {}
    optional = (*CLASS_FILES, *CHARACTER_FILES)
    names = [*INHERITED_FILES, *(n for n in optional if n not in decoded_classes)]
    for name in names:
        path = _inherited_source(base, name, rules)
        if path is None:
            if name in CHARACTER_FILES:
                extra_notes.append(f"{name} absent : tables des ratios absentes de {csv_dir.name} et de {base_version}")
                continue
            if name in CLASS_FILES:
                extra_notes.append(
                    f"{name} absent : tables des 9 classes absentes de {csv_dir.name} et de {base_version}"
                )
                continue
            raise DataSchemaError(f"{base / name} introuvable : fichier hérité attendu.")
        doc = _read_json(path)
        if not isinstance(doc, dict):
            raise DataSchemaError(f"{path} : objet JSON attendu pour y noter inherited_from.")
        inherited[name] = {**doc, "inherited_from": base_version}
        if name in CLASS_FILES:
            extra_notes.append(f"{name} hérité de {base_version} : tables des 9 classes absentes de {csv_dir.name}")
    local_sources = _read_json(base / SOURCES_NAME)
    files = local_sources.get("files", {})
    decoded_note = f"tables du client {version} (wago.tools, {csv_dir.name}) décodées par forever decode"
    frozen_of = {spec.get("frozen_copy"): old for old, spec in rules.get("retired_files", {}).items()}

    def inherited_entry(name: str) -> dict[str, Any]:
        entry = files.get(name) or files.get(frozen_of.get(name, ""), {"source": "inconnue", "certainty": "suppose"})
        notes = [*entry.get("notes", [])]
        if name not in files and name in frozen_of:
            notes.append(f"copie figée de {frozen_of[name]} (retired_files de {RULES_NAME})")
        return {**entry, "inherited_from": base_version, "notes": [*notes, f"hérité de {base_version}"]}

    class_notes = {
        "classes.json": "arbres, talents (node_id), sorts et classement PvP des 9 classes (decode_rules.json, classes)",
        "races.json": "races jouables, classes permises et raciaux (decode_rules.json, racial_skill_lines)",
        "pvp_items.json": "bijoux dont le sort d'utilisation rompt un contrôle (decode_rules.json, pvp_trinkets)",
        CHARACTER_FILE: "ratios du personnage par classe et par niveau, XP, repos, constante d'armure, courbes de "
        "régénération (decode_rules.json, character_scaling) ; recoupement par les GameTables dans crosscheck",
    }
    class_certainty_note = {
        CHARACTER_FILE: "PV par Endurance et constante d'armure : sens ou usage par le serveur probable",
    }
    sources = {
        **{k: v for k, v in local_sources.items() if k != "files"},
        "game_version": version,
        "collected_at": format_utc(deps.now())[:10],
        "candidate": True,
        "files": {
            "talents.json": {
                "source": f"Client {version} : {decoded_note}",
                "certainty": "certain",
                "notes": ["rangs : variables d'infobulle au niveau de base du sort (decode_rules.json)"],
            },
            "spells.json": {
                **files.get("spells.json", {}),
                "source": f"Client {version} : rangs {decoded_note}",
                "certainty": "certain",
                "notes": [
                    *files.get("spells.json", {}).get("notes", []),
                    f"rangs décodés du client ; autres champs hérités de {base_version}",
                ],
            },
            "spell_scaling.json": {
                "source": f"Client {version} : points de base par niveau, {decoded_note}",
                "certainty": "certain",
                "notes": [
                    "MaxLevel 0 résolu au plafond de niveau (decode_rules.json)",
                    "utility : armures du Mage, niveau d'apprentissage et effets (decode_rules.json.utility_spells)",
                    "talent_cooldowns : recharges des talents actifs (decode_rules.json.talent_cooldowns)",
                ],
            },
            **{
                name: {
                    "source": f"Client {version} : {decoded_note}",
                    "certainty": "certain",
                    "notes": [
                        class_notes[name],
                        class_certainty_note.get(
                            name, "classement PvP : table de decode_rules.json, certitude probable"
                        ),
                    ],
                }
                for name in decoded_classes
            },
            **{name: inherited_entry(name) for name in inherited},
        },
    }
    if rules.get("retired_files"):
        sources["retired_files"] = copy.deepcopy(rules["retired_files"])
    if out.exists():
        shutil.rmtree(out)
    vdir = out / version
    vdir.mkdir(parents=True)
    _write_json(vdir / "talents.json", talents)
    _write_json(vdir / "spells.json", spells)
    _write_json(vdir / "spell_scaling.json", scaling)
    for name, doc in decoded_classes.items():
        _write_json(vdir / name, doc)
    for name, doc in inherited.items():
        _write_json(vdir / name, doc)
    _write_json(vdir / SOURCES_NAME, sources)
    write_manifest(out)
    return Candidate(
        root=out,
        version=version,
        talents=sum(len(t["talents"]) for t in talents["trees"]),
        spells=len(rules["spells"]),
        spell_ranks=sum(len(spells["spells"][k]["ranks"]) for k in rules["spells"]),
        observations=[*_observations(talents, spells, base), *extra_notes],
    )
