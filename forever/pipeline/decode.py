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
from forever.pipeline.fetch import DEFAULT_LOCALE, wago_dir
from forever.pipeline.tables import Row, read_table
from forever.pipeline.tooltip import half_up, normalize, tooltip_values
from forever.timefmt import format_utc

RULES_NAME = "decode_rules.json"
DECODED_FILES = ("talents.json", "spells.json")
INHERITED_FILES = (
    "racials.json",
    "leveling.json",
    "mechanics.json",
    "respec.json",
    "overrides.json",
    "meta.json",
    "monsters.json",
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


def decode_spells(
    tables: Tables, rules: Mapping[str, Any], inherited: Mapping[str, Any], version: str
) -> dict[str, Any]:
    """Contenu de `spells.json` : rangs décodés (`rank_format`), noms anglais et français, identifiants des rangs ;
    les autres champs (portée, ralentissement, sorts utilitaires…) sont repris de `inherited`."""
    if list(inherited.get("rank_format", [])) != list(rules["rank_format"]):
        raise DataSchemaError(f"rank_format de {RULES_NAME} différent de celui de spells.json hérité.")
    client = _Client(tables, rules)
    lines = set(rules["skill_lines"].values())
    methods = set(rules["spell_ranks"]["acquire_methods"])
    rank_re = re.compile(rules["spell_ranks"]["rank_subtext"])
    wanted = {name: key for key, name in rules["spells"].items()}
    found: dict[str, dict[int, int]] = defaultdict(dict)
    for r in tables["SkillLineAbility"]:
        spell = int(r["Spell"])
        key = wanted.get(client.names.get(spell, ""))
        if key is None or int(r["SkillLine"]) not in lines or int(r["AcquireMethod"]) not in methods:
            continue
        match = rank_re.match(str(client.spell.get(spell, {}).get("NameSubtext_lang", "")))
        if not match:
            raise DataSchemaError(f"Sort {spell} ({rules['spells'][key]}) : rang illisible dans NameSubtext.")
        rank = int(match[1])
        if found[key].get(rank, spell) != spell:
            raise DataSchemaError(f"{key} : deux sorts pour le rang {rank} ({found[key][rank]}, {spell}).")
        found[key][rank] = spell
    doc = copy.deepcopy(dict(inherited))
    doc["build"] = version
    doc["inherited_from"] = inherited.get("build")
    doc["source"] = f"Client {version} : tables Spell* et SkillLineAbility (wago.tools) décodées par forever decode"
    for key, name in rules["spells"].items():
        ranks = found.get(key, {})
        if not ranks or sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise DataSchemaError(f"{key} ({name}) : rangs incomplets dans le client ({sorted(ranks)}).")
        ids = [ranks[r] for r in sorted(ranks)]
        entry = dict(doc["spells"].get(key, {}))
        entry["ranks"] = [_rank_row(client, i, rules) for i in ids]
        entry["name"] = name
        entry["name_fr"] = client.names_fr.get(ids[0], "")
        entry["spell_ids"] = ids
        doc["spells"][key] = entry
    return doc


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
    if out.exists() and any(out.iterdir()) and (not force or not _is_candidate(out, version)):
        raise CandidateExistsError(str(out))
    tables = load_tables(csv_dir, rules)
    talents = decode_talents(tables, rules, version)
    spells = decode_spells(tables, rules, _read_json(base / "spells.json"), version)
    inherited = {}
    for name in INHERITED_FILES:
        doc = _read_json(base / name)
        if not isinstance(doc, dict):
            raise DataSchemaError(f"{base / name} : objet JSON attendu pour y noter inherited_from.")
        inherited[name] = {**doc, "inherited_from": base_version}
    local_sources = _read_json(base / SOURCES_NAME)
    files = local_sources.get("files", {})
    decoded_note = f"tables du client {version} (wago.tools, {csv_dir.name}) décodées par forever decode"
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
            **{
                name: {
                    **files.get(name, {"source": "inconnue", "certainty": "suppose"}),
                    "inherited_from": base_version,
                    "notes": [*files.get(name, {}).get("notes", []), f"hérité de {base_version}"],
                }
                for name in INHERITED_FILES
            },
        },
    }
    if out.exists():
        shutil.rmtree(out)
    vdir = out / version
    vdir.mkdir(parents=True)
    _write_json(vdir / "talents.json", talents)
    _write_json(vdir / "spells.json", spells)
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
        observations=_observations(talents, spells, base),
    )
