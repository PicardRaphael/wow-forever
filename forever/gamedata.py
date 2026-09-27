"""Construction de `GameData` depuis les fichiers d'une version (seul module qui lit le JSON brut du moteur).

Le moteur reste pur : il reçoit `GameData` en paramètre. Tout écart de schéma lève `DataSchemaError`."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from forever.config import Deps
from forever.engine.model import (
    CharacterModel,
    CoefficientRules,
    CombatRules,
    Constants,
    FixedCoefficient,
    GameData,
    IntPerCrit,
    Racials,
    Rank,
    Spell,
    StatGrowth,
    Talent,
    TalentRules,
)
from forever.errors import DataSchemaError
from forever.store import VersionData, load_version

MECHANICS_FILE = "mechanics.json"
SPELLS_FILE = "spells.json"
TALENTS_FILE = "talents.json"
LEVELING_FILE = "leveling.json"
RACIALS_FILE = "racials.json"

# Colonnes attendues de `spells.json.rank_format`, dans l'ordre des champs de `Rank`.
RANK_COLUMNS = ("level", "min", "max", "dot_total", "dot_duration", "cast_s", "mana", "cooldown_s")

# Règles de `leveling.json.combat_rules` qui paramètrent une mécanique du registre (utilisées par `explain`).
COMBAT_RULE_MECHANICS: dict[str, tuple[str, ...]] = {
    "A3": ("spell_miss_by_level_diff", "min_miss"),
    "H1": ("spell_miss_by_level_diff",),
    "B1": ("gcd",),
    "A21": ("crit_mult_spell",),
    "A17": ("dot_can_crit",),
}


class _Reader:
    """Accès typé au JSON brut : chaque écart devient une DataSchemaError qui nomme le fichier et la clé."""

    def __init__(self, file: str) -> None:
        self.file = file

    def fail(self, where: str, expected: str) -> DataSchemaError:
        return DataSchemaError(f"{self.file} : « {where} » absent ou invalide ({expected} attendu).")

    def obj(self, parent: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any]:
        value = parent.get(key)
        if not isinstance(value, dict):
            raise self.fail(where, "objet")
        return value

    def num(self, parent: Mapping[str, Any], key: str, where: str) -> float:
        value = parent.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise self.fail(where, "nombre")
        return value

    def opt_num(self, parent: Mapping[str, Any], key: str, where: str) -> float | None:
        return None if parent.get(key) is None else self.num(parent, key, where)

    def int_(self, parent: Mapping[str, Any], key: str, where: str) -> int:
        value = parent.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise self.fail(where, "entier")
        return value

    def str_(self, parent: Mapping[str, Any], key: str, where: str) -> str:
        value = parent.get(key)
        if not isinstance(value, str):
            raise self.fail(where, "texte")
        return value

    def bool_(self, parent: Mapping[str, Any], key: str, where: str) -> bool:
        value = parent.get(key)
        if not isinstance(value, bool):
            raise self.fail(where, "booléen")
        return value

    def list_(self, parent: Mapping[str, Any], key: str, where: str) -> list[Any]:
        value = parent.get(key)
        if not isinstance(value, list):
            raise self.fail(where, "liste")
        return value


def _spells(raw: Any) -> dict[str, Spell]:
    r = _Reader(SPELLS_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    rank_format = r.list_(raw, "rank_format", "rank_format")
    if tuple(rank_format) != RANK_COLUMNS:
        raise r.fail("rank_format", " ; ".join(RANK_COLUMNS))
    spells: dict[str, Spell] = {}
    for key, s in r.obj(raw, "spells", "spells").items():
        where = f"spells.{key}"
        if not isinstance(s, dict):
            raise r.fail(where, "objet")
        ranks = []
        for i, row in enumerate(r.list_(s, "ranks", f"{where}.ranks"), start=1):
            if not isinstance(row, list) or len(row) != len(RANK_COLUMNS):
                raise r.fail(f"{where}.ranks[{i}]", f"liste de {len(RANK_COLUMNS)} valeurs")
            cells = dict(zip(RANK_COLUMNS, row, strict=True))
            cw = f"{where}.ranks[{i}]"
            ranks.append(
                Rank(
                    i,
                    r.int_(cells, "level", cw),
                    r.num(cells, "min", cw),
                    r.num(cells, "max", cw),
                    r.num(cells, "dot_total", cw),
                    r.num(cells, "dot_duration", cw),
                    r.num(cells, "cast_s", cw),
                    r.opt_num(cells, "mana", cw),
                    r.num(cells, "cooldown_s", cw),
                )
            )
        talent = s.get("talent")
        if talent is not None and not isinstance(talent, str):
            raise r.fail(f"{where}.talent", "texte")
        channel = s.get("channel", False)
        if not isinstance(channel, bool):
            raise r.fail(f"{where}.channel", "booléen")
        spells[key] = Spell(
            key=key,
            school=r.str_(s, "school", f"{where}.school"),
            ranks=tuple(ranks),
            range_yd=r.opt_num(s, "range", f"{where}.range"),
            talent=talent,
            channel=channel,
            slow=r.opt_num(s, "slow", f"{where}.slow"),
            mana_pct_base=r.opt_num(s, "mana_pct_base", f"{where}.mana_pct_base"),
            frozen_mult=r.opt_num(s, "frozen_mult", f"{where}.frozen_mult"),
            projectile_speed=r.opt_num(s, "projectile_speed", f"{where}.projectile_speed"),
        )
    return spells


def _talents(raw: Any) -> tuple[dict[str, Talent], tuple[str, ...]]:
    r = _Reader(TALENTS_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    talents: dict[str, Talent] = {}
    trees: list[str] = []
    for n, tree in enumerate(r.list_(raw, "trees", "trees")):
        if not isinstance(tree, dict):
            raise r.fail(f"trees[{n}]", "objet")
        tree_name = r.str_(tree, "name", f"trees[{n}].name")
        trees.append(tree_name)
        for t in r.list_(tree, "talents", f"trees[{n}].talents"):
            if not isinstance(t, dict):
                raise r.fail(f"trees[{n}].talents", "liste d'objets")
            key = r.str_(t, "key", f"{tree_name}.key")
            where = f"talents.{key}"
            ranks = []
            for i, row in enumerate(r.list_(t, "ranks", f"{where}.ranks"), start=1):
                if not isinstance(row, list):
                    raise r.fail(f"{where}.ranks[{i}]", "liste")
                ranks.append(tuple(r.num({"v": v}, "v", f"{where}.ranks[{i}]") for v in row))
            prereq_raw = t.get("prereq")
            prereq = None
            if prereq_raw is not None:
                if not isinstance(prereq_raw, dict):
                    raise r.fail(f"{where}.prereq", "objet")
                prereq = (r.int_(prereq_raw, "tier", f"{where}.prereq"), r.int_(prereq_raw, "col", f"{where}.prereq"))
            if key in talents:
                raise r.fail(where, "clé de talent unique")
            talents[key] = Talent(
                key=key,
                name=r.str_(t, "name", f"{where}.name"),
                tree=tree_name,
                tier=r.int_(t, "tier", f"{where}.tier"),
                col=r.int_(t, "col", f"{where}.col"),
                max_rank=r.int_(t, "max", f"{where}.max"),
                ranks=tuple(ranks),
                prereq=prereq,
            )
    return talents, tuple(trees)


def _rules(raw: Any) -> CombatRules:
    r = _Reader(LEVELING_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    cr = r.obj(raw, "combat_rules", "combat_rules")
    miss = r.obj(cr, "spell_miss_by_level_diff", "combat_rules.spell_miss_by_level_diff")
    levels = [k for k in miss if k != "-"]
    if "-" not in miss or not levels or not all(k.lstrip("-").isdigit() for k in levels):
        raise r.fail("combat_rules.spell_miss_by_level_diff", "table avec la clé « - » et des écarts entiers")
    return CombatRules(
        gcd_s=r.num(cr, "gcd", "combat_rules.gcd"),
        spell_miss_by_level_diff={k: r.num(miss, k, f"combat_rules.spell_miss_by_level_diff.{k}") for k in miss},
        min_miss=r.num(cr, "min_miss", "combat_rules.min_miss"),
        crit_mult_spell=r.num(cr, "crit_mult_spell", "combat_rules.crit_mult_spell"),
        dot_can_crit=r.bool_(cr, "dot_can_crit", "combat_rules.dot_can_crit"),
    )


def _racials(raw: Any) -> Racials:
    """Épée : `sword_spec.crit` ; esprit et mana : tout racial qui porte `spirit_pct` ou `mana_pct`."""
    r = _Reader(RACIALS_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    sword: dict[str, float] = {}
    spirit: dict[str, float] = {}
    mana: dict[str, float] = {}
    for race, traits in r.obj(raw, "races", "races").items():
        if not isinstance(traits, dict):
            raise r.fail(f"races.{race}", "objet")
        for name, trait in traits.items():
            if not isinstance(trait, dict):
                continue
            where = f"races.{race}.{name}"
            if name == "sword_spec":
                sword[race] = r.num(trait, "crit", f"{where}.crit")
            if "spirit_pct" in trait:
                spirit[race] = spirit.get(race, 0.0) + r.num(trait, "spirit_pct", f"{where}.spirit_pct")
            if "mana_pct" in trait:
                mana[race] = mana.get(race, 0.0) + r.num(trait, "mana_pct", f"{where}.mana_pct")
    return Racials(sword_crit=sword, spirit_pct=spirit, mana_pct=mana)


def _constants(raw: Any) -> Constants:
    r = _Reader(MECHANICS_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    values = r.obj(raw, "values", "values")

    def entry(key: str) -> Mapping[str, Any]:
        return r.obj(values, key, key)

    def num(key: str) -> float:
        return r.num(entry(key), "value", key)

    def obj(key: str) -> Mapping[str, Any]:
        return r.obj(entry(key), "value", key)

    bounds = r.list_(entry("coefficient.cast_bounds_s"), "value", "coefficient.cast_bounds_s")
    if len(bounds) != 2:
        raise r.fail("coefficient.cast_bounds_s", "liste [min, max]")
    low = obj("coefficient.low_level")
    fixed: dict[str, FixedCoefficient] = {}
    for spell, spec in obj("coefficient.fixed").items():
        where = f"coefficient.fixed.{spell}"
        if not isinstance(spec, dict) or ("value" in spec) == ("cast_s" in spec):
            raise r.fail(where, "objet avec value ou cast_s")
        slowed = spec.get("slowed", False)
        if not isinstance(slowed, bool):
            raise r.fail(f"{where}.slowed", "booléen")
        fixed[spell] = FixedCoefficient(
            value=r.num(spec, "value", where) if "value" in spec else None,
            cast_s=r.num(spec, "cast_s", where) if "cast_s" in spec else None,
            slowed=slowed,
        )
    coefficients = CoefficientRules(
        cast_divisor=num("coefficient.cast_divisor"),
        cast_min_s=r.num({"v": bounds[0]}, "v", "coefficient.cast_bounds_s"),
        cast_max_s=r.num({"v": bounds[1]}, "v", "coefficient.cast_bounds_s"),
        slow_factor=num("coefficient.slow_factor"),
        channel_cap_s=num("coefficient.channel_cap_s"),
        low_level_threshold=r.int_(low, "threshold", "coefficient.low_level.threshold"),
        low_level_penalty_per_level=r.num(low, "penalty_per_level", "coefficient.low_level.penalty_per_level"),
        fixed=fixed,
    )

    def growth(key: str) -> StatGrowth:
        g = obj(key)
        return StatGrowth(
            base=r.num(g, "base", key),
            per_level=r.num(g, "per_level", key),
            late_bonus_per_level=r.num(g, "late_bonus_per_level", key),
            late_from_level=r.int_(g, "late_from_level", key),
        )

    ipc = obj("character.int_per_crit")
    sp = obj("character.spell_power")
    base_mana = obj("character.base_mana")
    mana_int = obj("character.mana_from_intellect")
    hp = obj("character.hp")
    armor = obj("character.armor")
    regen = obj("character.spirit_regen")
    character = CharacterModel(
        crit_base=num("character.crit_base"),
        int_per_crit=IntPerCrit(
            level_min=r.int_(ipc, "level_min", "character.int_per_crit"),
            at_min=r.num(ipc, "at_min", "character.int_per_crit"),
            level_max=r.int_(ipc, "level_max", "character.int_per_crit"),
            at_max=r.num(ipc, "at_max", "character.int_per_crit"),
        ),
        intellect=growth("character.intellect"),
        spirit=growth("character.spirit"),
        spell_power_per_level=r.num(sp, "per_level", "character.spell_power"),
        spell_power_from_level=r.int_(sp, "from_level", "character.spell_power"),
        base_mana=r.num(base_mana, "base", "character.base_mana"),
        base_mana_per_level=r.num(base_mana, "per_level", "character.base_mana"),
        mana_first_points=r.num(mana_int, "first_points", "character.mana_from_intellect"),
        mana_per_point_after=r.num(mana_int, "per_point_after", "character.mana_from_intellect"),
        hp_base=r.num(hp, "base", "character.hp"),
        hp_per_level=r.num(hp, "per_level", "character.hp"),
        hp_per_level_squared=r.num(hp, "per_level_squared", "character.hp"),
        agility_base=r.num(armor, "agility_base", "character.armor"),
        agility_per_level=r.num(armor, "agility_per_level", "character.armor"),
        armor_per_agility=r.num(armor, "armor_per_agility", "character.armor"),
        armor_per_level=r.num(armor, "per_level", "character.armor"),
        regen_base=r.num(regen, "base", "character.spirit_regen"),
        regen_spirit_divisor=r.num(regen, "spirit_divisor", "character.spirit_regen"),
        regen_tick_s=r.num(regen, "tick_s", "character.spirit_regen"),
    )
    talent_mana = obj("mana.talent_rank_cost")
    return Constants(
        coefficients=coefficients,
        character=character,
        talents=TalentRules(
            first_level=r.int_(entry("talents.first_level"), "value", "talents.first_level"),
            points_per_tier=r.int_(entry("talents.points_per_tier"), "value", "talents.points_per_tier"),
        ),
        crit_per_winters_chill_stack=num("crit.winters_chill_per_stack"),
        talent_rank_mana_ratio=r.num(talent_mana, "ratio_of_next_rank", "mana.talent_rank_cost"),
        talent_rank_mana_default=r.num(talent_mana, "default", "mana.talent_rank_cost"),
        default_range_yd=num("spell.default_range_yd"),
    )


def build_game_data(version: VersionData) -> GameData:
    """Données typées d'une version déjà vérifiée ; lève DataSchemaError si une clé manque ou a un mauvais type."""
    try:
        raw = {name: version.read_json(name) for name in (SPELLS_FILE, TALENTS_FILE, LEVELING_FILE, RACIALS_FILE)}
        raw_mechanics = version.read_json(MECHANICS_FILE)
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"Données de la version {version.game_version} illisibles ({exc}).") from exc
    talents, trees = _talents(raw[TALENTS_FILE])
    return GameData(
        game_version=version.game_version,
        spells=_spells(raw[SPELLS_FILE]),
        talents=talents,
        talent_at={(t.tree, t.tier, t.col): t.key for t in talents.values()},
        trees=trees,
        rules=_rules(raw[LEVELING_FILE]),
        constants=_constants(raw_mechanics),
        racials=_racials(raw[RACIALS_FILE]),
    )


def load_game_data(deps: Deps) -> GameData:
    """Version courante, après contrôle d'intégrité (DataIntegrityError, ManifestMissingError)."""
    return build_game_data(load_version(deps))
