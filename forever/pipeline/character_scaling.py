"""Ratios du personnage décodés du client (`character_scaling.json`, T08b, bloc A).

Par classe et par niveau (1 au plafond de `decode_rules.json`) : mana de base, critique des sorts par point
d'Intelligence et critique par point d'Agilité (fractions), PV par point d'Endurance (`PlayerExpectedStat`, colonne
au sens probable) ; courbes de régénération de PV par l'Esprit (`GlobalCurve`, sous-type = classe, points dans
`CurvePoint`). Pour tous : XP pour passer chaque niveau (`LevelExperience`), paliers du repos (`Exhaustion`),
constante d'armure par niveau (`ExpectedStat`).

Recoupement par les GameTables (`decode_rules.json` `character_scaling.crosscheck`) : `concorde`, `ecart` (chaque
écart listé, la valeur DB2 reste celle du fichier : jamais tranché en silence) ou `absente`. Toutes les constantes de
lecture viennent de `decode_rules.json` ; aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import CsvMissingError, DataSchemaError
from forever.pipeline.fetch import DEFAULT_LOCALE, GAMETABLES_DIR
from forever.pipeline.tables import Row, column_value, read_table

CHARACTER_FILE = "character_scaling.json"
CHARACTER_FILES = (CHARACTER_FILE,)
SCHEMA_VERSION = 1
PLAYER_KEYS = ("base_mana", "spell_crit_per_intellect", "crit_per_agility", "hp_per_stamina")

GameTable = list[dict[str, float]]


def character_table_files(rules: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(table, chemin relatif) des tables des ratios (`character_tables`), plus `ChrClasses` et `CurvePoint`."""
    names = list(rules.get("character_tables", []))
    if not names:
        return []
    return [
        (name, f"{DEFAULT_LOCALE}/{name}.csv")
        for name in dict.fromkeys([*names, "ChrClasses", "CurvePoint", "SkillLineXTraitTree"])
    ]


def load_character_tables(csv_dir: Path, rules: Mapping[str, Any]) -> dict[str, list[Row]]:
    files = character_table_files(rules)
    missing = [rel for _, rel in files if not (csv_dir / rel).is_file()]
    if missing:
        raise CsvMissingError(csv_dir.name, missing)
    return {name: list(read_table(csv_dir / rel, name)) for name, rel in files}


def read_gametable(path: Path) -> GameTable:
    """Lignes d'une GameTable (texte à tabulations, entête nommée) ; DataSchemaError si une cellule n'est pas un
    nombre."""
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    except (OSError, UnicodeDecodeError) as exc:
        raise DataSchemaError(f"GameTable illisible : {path} ({exc}).") from exc
    if not lines:
        return []
    header = lines[0].split("\t")
    table: GameTable = []
    for n, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        try:
            table.append({h: float(c) for h, c in zip(header, cells, strict=False)})
        except ValueError as exc:
            raise DataSchemaError(f"GameTable {path.name} : valeur non numérique ligne {n}.") from exc
    return table


def load_gametables(gt_dir: Path, rules: Mapping[str, Any]) -> dict[str, GameTable | None]:
    """GameTables de `decode_rules.json` présentes dans `gt_dir` (`<nom>.txt`) ; None : absente."""
    out: dict[str, GameTable | None] = {}
    for name in rules.get("gametables", {}):
        path = gt_dir / f"{name}.txt"
        out[str(name)] = read_gametable(path) if path.is_file() else None
    return out


def gametables_dir(csv_dir: Path) -> Path:
    return csv_dir / GAMETABLES_DIR


def _by_level(rows: Sequence[Row], level_col: str, cap: int, where: str) -> dict[int, Row]:
    found = {int(r[level_col]): r for r in rows if 1 <= int(r[level_col]) <= cap}
    missing = [lv for lv in range(1, cap + 1) if lv not in found]
    if missing:
        raise DataSchemaError(f"{where} : niveaux absents {missing[:5]}.")
    return found


def _crosscheck(
    spec: Mapping[str, Any], doc: Mapping[str, Any], gametables: Mapping[str, GameTable | None], cap: int
) -> dict[str, Any]:
    value, name, column = str(spec["value"]), str(spec["gametable"]), str(spec["column"])
    table = gametables.get(name)
    entry: dict[str, Any] = {"value": value, "gametable": name, "column": column}
    if table is None:
        return {**entry, "status": "absente", "gaps": []}
    by_level = {int(r["Level"]): r for r in table if "Level" in r}
    gaps: list[dict[str, Any]] = []

    def compare(cls: str | None, level: int, db2: float, col: str) -> None:
        row = by_level.get(level)
        gt = None if row is None else row.get(col)
        if gt is None or abs(gt - db2) > 1e-9 * max(1.0, abs(db2)):
            gaps.append({"class": cls, "level": level, "db2": db2, "gametable": gt})

    if value in PLAYER_KEYS:
        for cls, data in doc["classes"].items():
            col = cls if column == "class" else column
            for i, v in enumerate(data[value]):
                compare(cls, i + 1, v, col)
    else:
        for i, v in enumerate(doc[value]):
            compare(None, i + 1, v, column)
    return {**entry, "status": "ecart" if gaps else "concorde", "gaps": gaps}


def decode_character_scaling(
    tables: Mapping[str, Sequence[Row]],
    rules: Mapping[str, Any],
    gametables: Mapping[str, GameTable | None],
    version: str,
) -> dict[str, Any]:
    spec = rules["character_scaling"]
    cap = int(rules["levels"]["level_cap"])
    content = int(spec["content_set_id"])
    columns = dict(spec["player_columns"])  # un nom de colonne, ou une liste de noms (le nouveau d'abord)
    class_ids = {str(r["Name_lang"]): int(r["ID"]) for r in tables["ChrClasses"]}
    pes = [r for r in tables["PlayerExpectedStat"] if int(r["ContentSetID"]) == content]
    curves = tables["GlobalCurve"]
    points = tables["CurvePoint"]
    classes: dict[str, Any] = {}
    for cls in rules["classes"]:
        if cls not in class_ids:
            raise DataSchemaError(f"Classe {cls} absente de ChrClasses.")
        cid = class_ids[cls]
        rows = _by_level([r for r in pes if int(r["ClassID"]) == cid], "Level", cap, f"PlayerExpectedStat ({cls})")
        entry: dict[str, Any] = {"class_id": cid}
        for key in PLAYER_KEYS:
            entry[key] = [float(column_value(rows[lv], columns[key])) for lv in range(1, cap + 1)]
        regen: dict[str, Any] = {}
        for key, curve_type in spec["hp_regen_curve_types"].items():
            curve = next(
                (int(c["CurveID"]) for c in curves if int(c["Type"]) == int(curve_type) and int(c["Subtype"]) == cid),
                None,
            )
            if curve is None:
                regen[key] = None
                continue
            pts = sorted((p for p in points if int(p["CurveID"]) == curve), key=lambda p: int(p["OrderIndex"]))
            regen[key] = [[float(p["Pos_0"]), float(p["Pos_1"])] for p in pts]
        entry["hp_regen"] = regen
        classes[cls] = entry
    xp_rows = _by_level(
        [r for r in tables["LevelExperience"] if int(r["ContentSetID"]) == content], "Level", cap, "LevelExperience"
    )
    expansion = int(spec["expected_stat_expansion_id"])
    armor_rows = _by_level(
        [r for r in tables["ExpectedStat"] if int(r["ExpansionID"]) == expansion and int(r["ContentSetID"]) == content],
        "Lvl",
        cap,
        "ExpectedStat",
    )
    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "build": version,
        "source": f"Client {version} : PlayerExpectedStat, LevelExperience, Exhaustion, ExpectedStat, GlobalCurve et "
        "CurvePoint (wago.tools) décodés par forever decode ; recoupement par les GameTables",
        "level_cap": cap,
        "classes": classes,
        "xp_to_next": [int(xp_rows[lv]["Experience"]) for lv in range(1, cap)],
        "rested": [
            {
                "name": str(r["Name_lang"]),
                "xp": int(r["Xp"]),
                "factor": float(r["Factor"]),
                "outdoor_hours": float(r["OutdoorHours"]),
                "inn_hours": float(r["InnHours"]),
                "threshold": float(r["Threshold"]),
            }
            for r in sorted(tables["Exhaustion"], key=lambda r: int(r["ID"]))
        ],
        "armor_constant": [float(armor_rows[lv]["ArmorConstant"]) for lv in range(1, cap + 1)],
        "notes": [
            (
                "hp_per_stamina : colonne sans nom de PlayerExpectedStat lue comme PV par Endurance (sens probable, "
                "recoupé par la GameTable hppersta) ; non utilisée par le moteur (PV de base absents du client)"
            ),
            "armor_constant : table lue par le serveur inconnue (probable) ; armormitigationbylvl en écart",
            "hp_regen : courbes de régénération de PV par l'Esprit ; formule qui les combine au serveur, non utilisée",
            "rested : paliers du repos, non modélisés (D7)",
        ],
    }
    doc["talents"] = _talent_rules(tables, rules)
    doc["crosscheck"] = [_crosscheck(c, doc, gametables, cap) for c in spec.get("crosscheck", [])]
    return doc


def _talent_rules(tables: Mapping[str, Sequence[Row]], rules: Mapping[str, Any]) -> dict[str, Any]:
    """Premier niveau qui donne un point de talent (`NumTalentsAtLevel`, identifiant = niveau) et points dépensés
    exigés par palier pour chaque classe (`TraitCond.SpentAmountRequired` de l'arbre de la classe) : pas de la suite
    k × pas ; None si les seuils ne forment pas une telle suite (signalé, jamais deviné)."""
    first = min((int(r["ID"]) for r in tables["NumTalentsAtLevel"] if int(r["NumTalents"]) > 0), default=None)
    tree_of = {int(r["SkillLineID"]): int(r["TraitTreeID"]) for r in tables["SkillLineXTraitTree"]}
    per_tier: dict[str, int | None] = {}
    for cls, spec in rules["classes"].items():
        trees = {tree_of[s] for s in spec.get("skill_lines", []) if s in tree_of}
        spent = sorted(
            {int(r["SpentAmountRequired"]) for r in tables["TraitCond"] if int(r["TraitTreeID"]) in trees} - {0}
        )
        step = spent[0] if spent else None
        ok = step is not None and spent == [step * (i + 1) for i in range(len(spent))]
        per_tier[cls] = step if ok else None
    return {"first_level": first, "points_per_tier": per_tier}


def character_errors(doc: Any, classes: Sequence[str]) -> list[str]:
    """Contrôle de forme : classes attendues, niveaux 1 au plafond sans trou, XP du niveau 1 au plafond - 1."""
    if not isinstance(doc, dict):
        return [f"{CHARACTER_FILE} : objet attendu"]
    errors: list[str] = []
    cap = doc.get("level_cap")
    if not isinstance(cap, int) or cap < 2:
        return [f"{CHARACTER_FILE} : level_cap entier attendu"]
    raw_classes = doc.get("classes")
    got: dict[str, Any] = raw_classes if isinstance(raw_classes, dict) else {}
    errors += [f"{CHARACTER_FILE} : classe {c} absente" for c in classes if c not in got]
    for cls, entry in got.items():
        for key in PLAYER_KEYS:
            values = entry.get(key) if isinstance(entry, dict) else None
            if not isinstance(values, list) or len(values) != cap:
                errors.append(f"{CHARACTER_FILE} : {cls} {key} : {cap} niveaux attendus")
            elif any(not isinstance(v, int | float) or v < 0 for v in values):
                errors.append(f"{CHARACTER_FILE} : {cls} {key} : nombres positifs attendus")
    for key, n in (("xp_to_next", cap - 1), ("armor_constant", cap)):
        values = doc.get(key)
        if not isinstance(values, list) or len(values) != n:
            errors.append(f"{CHARACTER_FILE} : {key} : {n} valeurs attendues")
    return errors
