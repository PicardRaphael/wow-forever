"""Construction de `GameData` depuis les fichiers d'une version (seul module qui lit le JSON brut du moteur).

Le moteur reste pur : il reçoit `GameData` en paramètre. Tout écart de schéma lève `DataSchemaError`."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.engine.diminishing import DrRules
from forever.engine.model import (
    ArmorRank,
    BuildMethod,
    CharacterModel,
    ClassKnowledge,
    CoefficientRules,
    CombatRules,
    Constants,
    FireVulnerability,
    FixedCoefficient,
    GameData,
    IntPerCrit,
    LevelingConstants,
    MobModel,
    MonsterHp,
    MonsterTable,
    Preset,
    PvpRules,
    QuestBand,
    QuestieCorrection,
    Racials,
    Rank,
    RankScaling,
    RespecRules,
    Restore,
    ScalingComponent,
    Scenario,
    Spell,
    StatGrowth,
    Talent,
    TalentRules,
    Utility,
    Variant,
)
from forever.errors import DataSchemaError, InvalidArgumentError
from forever.store import VersionData, load_version

MECHANICS_FILE = "mechanics.json"
SPELLS_FILE = "spells.json"
TALENTS_FILE = "talents.json"
LEVELING_FILE = "leveling.json"
RACIALS_FILE = "racials.json"  # relevé communautaire (versions antérieures à PV1)
RACES_FILE = "races.json"  # races et raciaux décodés du client (PV1, décision 106)
SEED_RACIALS_FILE = "_seed_racials.json"  # copie figée du relevé, lue en mode seed (PV1, D5)
CLASSES_FILE = "classes.json"  # savoir des 9 classes (PV1)
META_FILE = "meta.json"
BETA_CAP_KEY = "build.beta_level_cap"  # retirée par forever install (T08b, D2) : plafond dans meta.json game_state
CHARACTER_FILE = "character_scaling.json"  # ratios du personnage décodés du client (T08b, mode forever)
MONSTERS_FILE = "monsters.json"
SCALING_FILE = "spell_scaling.json"
RESPEC_FILE = "respec.json"
# Copies figées du seed (T06b, décision D2) : le mode seed lit ces deux fichiers à la place de spells.json et
# talents.json ; tout le reste de la version est partagé entre les deux modes.
SEED_FILES = {SPELLS_FILE: "_seed_spells.json", TALENTS_FILE: "_seed_talents.json"}
RULES = ("forever", "seed")
# Valeurs acceptées des hypothèses nommées de mechanics.json (T05, décision 81) : noms de règles, pas des chiffres.
CHOICES = {
    "leveling.ignite_rule": ("rolling", "independent"),
    "leveling.mob_source": ("measured", "seed"),
    "mana.regen_stacking": ("sum", "max"),
    "damage.bonus_stacking": ("multiplicative", "additive"),
    "coefficient.ice_lance_source": ("client", "seed"),
}
SCALING_KINDS = ("direct", "dot", "channel")
MS_PER_S = 1000.0  # conversion d'unité : durées du client en millisecondes
SCALING_SCHEMA = 2  # spell_scaling.json : bonus_coefficient et period_ms par composant, auras (T04e)

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


def _spells(raw: Any, file: str = SPELLS_FILE) -> dict[str, Spell]:
    r = _Reader(file)
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
        slow_dur = None
        if "slow_dur" in s:
            slow_dur = tuple(r.num({"v": v}, "v", f"{where}.slow_dur") for v in r.list_(s, "slow_dur", where))
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
            slow_dur=slow_dur,
        )
    return spells


def _talents(raw: Any, file: str = TALENTS_FILE) -> tuple[dict[str, Talent], tuple[str, ...]]:
    r = _Reader(file)
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
                duration_s=r.opt_num(t, "duration_s", f"{where}.duration_s"),
            )
    return talents, tuple(trees)


def _rules(raw: Any) -> CombatRules:
    r = _Reader(LEVELING_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    cr = r.obj(raw, "combat_rules", "combat_rules")
    miss = r.obj(cr, "spell_miss_by_level_diff", "combat_rules.spell_miss_by_level_diff")
    levels = [k for k in miss if k != "-"]
    if "-" not in miss or "0" not in miss or not all(k.lstrip("-").isdigit() for k in levels):
        raise r.fail("combat_rules.spell_miss_by_level_diff", "table avec les clés « - », « 0 » et des écarts entiers")
    return CombatRules(
        gcd_s=r.num(cr, "gcd", "combat_rules.gcd"),
        spell_miss_by_level_diff={k: r.num(miss, k, f"combat_rules.spell_miss_by_level_diff.{k}") for k in miss},
        min_miss=r.num(cr, "min_miss", "combat_rules.min_miss"),
        crit_mult_spell=r.num(cr, "crit_mult_spell", "combat_rules.crit_mult_spell"),
        dot_can_crit=r.bool_(cr, "dot_can_crit", "combat_rules.dot_can_crit"),
        pushback_s=r.num(cr, "pushback_s", "combat_rules.pushback_s"),
    )


def _racials_from_races(raw: Any) -> Racials:
    """Grandeurs raciales du moteur du Mage décodées du client (`races.json`, `mage_values` de chaque race)."""
    r = _Reader(RACES_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    tables: dict[str, dict[str, float]] = {"sword_crit": {}, "spirit_pct": {}, "mana_pct": {}}
    for race, entry in r.obj(raw, "races", "races").items():
        values = r.obj(entry, "mage_values", f"races.{race}.mage_values") if isinstance(entry, dict) else None
        if values is None:
            raise r.fail(f"races.{race}", "objet")
        for key, table in tables.items():
            if key in values:
                table[race] = r.num(values, key, f"races.{race}.mage_values.{key}")
    return Racials(sword_crit=tables["sword_crit"], spirit_pct=tables["spirit_pct"], mana_pct=tables["mana_pct"])


def racials_source(version: VersionData, rules: str = "forever") -> str:
    """Fichier des raciaux lu par le moteur : `races.json` (client) en mode forever, la copie figée du relevé en mode
    seed ; `racials.json` pour une version antérieure à PV1."""
    wanted = SEED_RACIALS_FILE if rules == "seed" else RACES_FILE
    return wanted if (version.path / wanted).is_file() else RACIALS_FILE


def mage_races(version: VersionData) -> list[str]:
    """Races jouables en Mage : celles de `races.json` dont les classes permises comptent le Mage ; toutes celles de
    `racials.json` pour une version antérieure à PV1."""
    if (version.path / RACES_FILE).is_file():
        races = version.read_json(RACES_FILE)["races"]
        return sorted(name for name, r in races.items() if "Mage" in r.get("classes", []))
    return sorted(version.read_json(RACIALS_FILE)["races"])


class _ClassFile(Mapping[str, ClassKnowledge]):
    """`classes.json` lu à la première consultation (2 Mo : jamais chargé par les calculs du Mage)."""

    def __init__(self, version: VersionData) -> None:
        self._version = version
        self._raw: dict[str, Any] | None = None
        self._built: dict[str, ClassKnowledge] = {}

    def _classes(self) -> dict[str, Any]:
        if self._raw is None:
            try:
                doc = self._version.read_json(CLASSES_FILE)
            except (OSError, ValueError) as exc:
                raise DataSchemaError(f"{CLASSES_FILE} illisible ({exc}).") from exc
            classes = doc.get("classes") if isinstance(doc, dict) else None
            if not isinstance(classes, dict):
                raise _Reader(CLASSES_FILE).fail("classes", "objet")
            self._raw = classes
        return self._raw

    def __getitem__(self, name: str) -> ClassKnowledge:
        if name not in self._built:
            raw = self._classes()[name]
            r = _Reader(CLASSES_FILE)
            trees = raw.get("trees") if isinstance(raw, dict) else None
            if not isinstance(trees, list) or not all(isinstance(t, dict) and "talents" in t for t in trees):
                raise r.fail(f"classes.{name}.trees", "liste d'arbres")
            self._built[name] = ClassKnowledge(
                name=name,
                id=r.int_(raw, "id", f"classes.{name}.id"),
                trees=tuple(trees),
                spells=r.obj(raw, "spells", f"classes.{name}.spells"),
                pet_spells=raw.get("pet_spells") or {},
                unresolved_nodes=tuple(raw.get("unresolved_nodes") or ()),
                unresolved_spells=tuple(raw.get("unresolved_spells") or ()),
            )
        return self._built[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._classes())

    def __len__(self) -> int:
        return len(self._classes())


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


def _monster_hp(r: _Reader, raw: Any, where: str, value_key: str) -> MonsterHp:
    if not isinstance(raw, dict):
        raise r.fail(where, "objet")
    certainty = r.str_(raw, "certainty", f"{where}.certainty")
    if certainty not in ("certain", "probable", "suppose"):
        raise r.fail(f"{where}.certainty", "certain, probable ou suppose")
    return MonsterHp(
        value=r.int_(raw, value_key, f"{where}.{value_key}"),
        certainty=certainty,
        source=r.str_(raw, "source", f"{where}.source"),
    )


def _level_key(r: _Reader, key: str, where: str) -> int:
    if not key.isdigit():
        raise r.fail(where, "clé de niveau entière")
    return int(key)


def _monsters(raw: Any) -> MonsterTable:
    r = _Reader(MONSTERS_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    by_level = {
        _level_key(r, k, "hp_by_level"): _monster_hp(r, v, f"hp_by_level.{k}", "value")
        for k, v in r.obj(raw, "hp_by_level", "hp_by_level").items()
    }
    npcs: dict[int, dict[int, MonsterHp]] = {}
    for npc_id, npc in r.obj(raw, "npcs", "npcs").items():
        where = f"npcs.{npc_id}"
        if not isinstance(npc, dict):
            raise r.fail(where, "objet")
        npcs[_level_key(r, npc_id, "npcs")] = {
            _level_key(r, k, f"{where}.levels"): _monster_hp(r, v, f"{where}.levels.{k}", "max_hp")
            for k, v in r.obj(npc, "levels", f"{where}.levels").items()
        }
    raw_corr = raw.get("questie_correction", "absent")
    if raw_corr == "absent":
        raise r.fail("questie_correction", "objet ou null (schéma 2)")
    return MonsterTable(hp_by_level=by_level, npcs=npcs, correction=_correction(r, raw_corr))


def _correction(r: _Reader, raw: Any) -> QuestieCorrection | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise r.fail("questie_correction", "objet ou null")
    levels: dict[int, float] = {}
    for k, v in r.obj(raw, "levels", "questie_correction.levels").items():
        if not isinstance(v, dict):
            raise r.fail(f"questie_correction.levels.{k}", "objet")
        levels[_level_key(r, k, "questie_correction.levels")] = r.num(v, "ratio", f"questie_correction.levels.{k}")
    span = r.list_(raw, "range", "questie_correction.range")
    if len(span) != 2 or not all(isinstance(x, int) and not isinstance(x, bool) for x in span):
        raise r.fail("questie_correction.range", "[niveau min, niveau max]")
    fit = raw.get("fit")
    if fit is not None and not isinstance(fit, dict):
        raise r.fail("questie_correction.fit", "objet ou null")
    return QuestieCorrection(
        levels=levels,
        slope=r.num(fit, "slope", "questie_correction.fit.slope") if fit else None,
        intercept=r.num(fit, "intercept", "questie_correction.fit.intercept") if fit else None,
        level_min=span[0],
        level_max=span[1],
    )


def _utility(raw: Any, file: str = SPELLS_FILE) -> Utility:
    """`spells.json.utility` : Frost Armor (ralenti des coups), Mage Armor (premier rang, régénération en
    incantation), nourriture et boisson conjurées (quantité et durée par rang)."""
    r = _Reader(file)
    u = r.obj(raw, "utility", "utility")
    frost = r.obj(u, "frost_armor", "utility.frost_armor")
    mage = r.obj(u, "mage_armor", "utility.mage_armor")
    ranks = r.list_(mage, "ranks", "utility.mage_armor.ranks")
    if not ranks or not isinstance(ranks[0], list) or not ranks[0]:
        raise r.fail("utility.mage_armor.ranks", "liste de rangs [niveau, …]")

    def restore(key: str) -> Restore:
        entry = r.obj(u, key, f"utility.{key}")
        levels = r.list_(entry, "spell_levels", f"utility.{key}.spell_levels")
        values = r.list_(entry, "restore", f"utility.{key}.restore")
        if len(levels) != len(values) or not all(isinstance(v, list) and len(v) == 2 for v in values):
            raise r.fail(f"utility.{key}", "spell_levels et restore [quantité, durée] de même longueur")
        return Restore(
            spell_levels=tuple(r.int_({"v": v}, "v", f"utility.{key}.spell_levels") for v in levels),
            restore=tuple(
                (r.num({"v": a}, "v", f"utility.{key}.restore"), r.num({"v": d}, "v", f"utility.{key}.restore"))
                for a, d in values
            ),
        )

    return Utility(
        frost_armor_duration_s=r.num(frost, "dur", "utility.frost_armor.dur"),
        frost_armor_swing_slow=r.num(frost, "attacker_swing_slow", "utility.frost_armor.attacker_swing_slow"),
        mage_armor_level=r.int_({"v": ranks[0][0]}, "v", "utility.mage_armor.ranks[1]"),
        mage_armor_regen=r.num(mage, "regen_while_casting", "utility.mage_armor.regen_while_casting"),
        water=restore("conjure_water"),
        food=restore("conjure_food"),
        **_pvp_utility(r, u),
    )


def _pvp_utility(r: _Reader, u: Mapping[str, Any]) -> dict[str, Any]:
    """Blink, Counterspell et rangs d'Ice Barrier (`spells.json.utility`) pour le profil PvP (T05)."""
    blink = r.obj(u, "blink", "utility.blink")
    cs = r.obj(u, "counterspell", "utility.counterspell")
    ib = r.obj(u, "ice_barrier", "utility.ice_barrier")
    evo = r.obj(u, "evocation", "utility.evocation")
    ranks = r.list_(ib, "ranks", "utility.ice_barrier.ranks")
    if not all(isinstance(x, list) and len(x) >= 2 for x in ranks):
        raise r.fail("utility.ice_barrier.ranks", "liste de rangs [niveau, absorption, …]")
    return {
        "blink_level": r.int_(blink, "level", "utility.blink.level"),
        "blink_cooldown_s": r.num(blink, "cooldown", "utility.blink.cooldown"),
        "counterspell_level": r.int_(cs, "level", "utility.counterspell.level"),
        "counterspell_cooldown_s": r.num(cs, "cooldown", "utility.counterspell.cooldown"),
        "counterspell_lockout_s": r.num(cs, "lockout", "utility.counterspell.lockout"),
        "evocation_level": r.int_(evo, "level", "utility.evocation.level"),
        "evocation_duration_s": r.num(evo, "duration", "utility.evocation.duration"),
        "evocation_regen_mult": r.num(evo, "regen_mult", "utility.evocation.regen_mult"),
        "ice_barrier": tuple(
            (
                r.int_({"v": x[0]}, "v", "utility.ice_barrier.ranks"),
                r.num({"v": x[1]}, "v", "utility.ice_barrier.ranks"),
            )
            for x in ranks
        ),
    }


def _pvp(values: Mapping[str, Any]) -> PvpRules:
    """`pvp.profile` et `pvp.weights` de `mechanics.json` (T05)."""
    m = _Reader(MECHANICS_FILE)
    profile = m.obj(m.obj(values, "pvp.profile", "pvp.profile"), "value", "pvp.profile")
    for key in ("ref", "cap", "scale", "racial_s", "sheets"):
        if key not in profile:
            raise m.fail(f"pvp.profile.{key}", "valeur du barème")
    raw = m.obj(m.obj(values, "pvp.weights", "pvp.weights"), "value", "pvp.weights")
    weights = {
        name: {k: m.num(m.obj(raw, name, f"pvp.weights.{name}"), k, f"pvp.weights.{name}.{k}") for k in profile["ref"]}
        for name in raw
    }
    return PvpRules(profile=profile, weights=weights)


def _leveling(values: Mapping[str, Any]) -> LevelingConstants:
    """Clés `leveling.*` de `mechanics.json`."""
    r = _Reader(MECHANICS_FILE)

    def obj(key: str) -> Mapping[str, Any]:
        return r.obj(r.obj(values, key, key), "value", key)

    def num(key: str) -> float:
        return r.num(r.obj(values, key, key), "value", key)

    hit, armor, xp = obj("leveling.mob_hit_damage"), obj("leveling.armor_reduction"), obj("leveling.mob_xp")
    ignite, speed = obj("leveling.ignite"), obj("leveling.projectile_speed")
    analytic, defaults = obj("leveling.analytic"), obj("leveling.defaults")
    return LevelingConstants(
        mob_hit_per_level=r.num(hit, "per_level", "leveling.mob_hit_damage"),
        mob_hit_per_level_squared=r.num(hit, "per_level_squared", "leveling.mob_hit_damage"),
        armor_base=r.num(armor, "base", "leveling.armor_reduction"),
        armor_per_attacker_level=r.num(armor, "per_attacker_level", "leveling.armor_reduction"),
        xp_base=r.num(xp, "base", "leveling.mob_xp"),
        xp_per_level=r.num(xp, "per_level", "leveling.mob_xp"),
        frostbite_freeze_s=num("leveling.frostbite_freeze_s"),
        dot_tick_s=num("leveling.dot_tick_s"),
        quest_band=_quest_band(r, obj("leveling.quest_band")),
        ignite_aura_id=r.int_(ignite, "aura_spell_id", "leveling.ignite"),
        ignite_duration_s=r.num(ignite, "duration_s", "leveling.ignite"),
        ignite_tick_s=r.num(ignite, "tick_s", "leveling.ignite"),
        ignite_cumulative=r.int_(ignite, "cumulative", "leveling.ignite"),
        ignite_rule=_choice(values, "leveling.ignite_rule"),
        frost_nova_retreat_yd=num("leveling.frost_nova_retreat_yd"),
        rest_hp_regen_fraction=num("leveling.rest_hp_regen_fraction"),
        projectile_speed_default=r.num(speed, "default", "leveling.projectile_speed"),
        projectile_speed_instant=r.num(speed, "instant", "leveling.projectile_speed"),
        analytic_min_cast_fraction=r.num(analytic, "min_cast_fraction", "leveling.analytic"),
        analytic_freeze_cap=r.num(analytic, "freeze_cap", "leveling.analytic"),
        analytic_winters_chill_casts=r.num(analytic, "winters_chill_casts", "leveling.analytic"),
        default_level_diff=r.int_(defaults, "level_diff", "leveling.defaults"),
        default_nova_break=r.num(defaults, "nova_break", "leveling.defaults"),
        default_run_between_s=r.num(defaults, "run_between_s", "leveling.defaults"),
        mob_source=_choice(values, "leveling.mob_source"),
    )


def _mob_model(raw: Any) -> MobModel:
    """`leveling.json.mob_model` (copie du seed) ; certitude « EST » du seed : `suppose`."""
    r = _Reader(LEVELING_FILE)
    mm = r.obj(raw, "mob_model", "mob_model")
    anchors = {
        _level_key(r, k, "mob_model.hp_anchors"): r.num(mm["hp_anchors"], k, f"mob_model.hp_anchors.{k}")
        for k in r.obj(mm, "hp_anchors", "mob_model.hp_anchors")
    }
    if not anchors:
        raise r.fail("mob_model.hp_anchors", "au moins une ancre")
    return MobModel(
        hp_anchors=anchors,
        swing_s=r.num(mm, "swing_s", "mob_model.swing_s"),
        crit=r.num(mm, "crit", "mob_model.crit"),
        crit_mult=r.num(mm, "crit_mult", "mob_model.crit_mult"),
        avoid_vs_mage=r.num(mm, "avoid_vs_mage", "mob_model.avoid_vs_mage"),
        run_speed=r.num(mm, "run_speed", "mob_model.run_speed"),
        melee_range=r.num(mm, "melee_range", "mob_model.melee_range"),
        certainty="suppose",
    )


def _scaling(raw: Any, spells: Mapping[str, Spell]) -> dict[str, tuple[RankScaling, ...]]:
    r = _Reader(SCALING_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    if raw.get("schema_version") != SCALING_SCHEMA:
        raise r.fail("schema_version", f"{SCALING_SCHEMA} (coefficients et périodes du client, T04e)")
    out: dict[str, tuple[RankScaling, ...]] = {}
    for key, ranks in r.obj(raw, "spells", "spells").items():
        where = f"spells.{key}"
        if not isinstance(ranks, list):
            raise r.fail(where, "liste de rangs")
        if key in spells and len(ranks) != len(spells[key].ranks):
            raise r.fail(where, f"{len(spells[key].ranks)} rangs comme spells.json")
        parsed = []
        for i, entry in enumerate(ranks, start=1):
            w = f"{where}[{i}]"
            if not isinstance(entry, dict):
                raise r.fail(w, "objet")
            components = []
            for j, c in enumerate(r.list_(entry, "components", f"{w}.components"), start=1):
                cw = f"{w}.components[{j}]"
                if not isinstance(c, dict) or c.get("kind") not in SCALING_KINDS:
                    raise r.fail(f"{cw}.kind", " ou ".join(SCALING_KINDS))
                components.append(
                    ScalingComponent(
                        spell_id=r.int_(c, "spell_id", cw),
                        index=r.int_(c, "index", cw),
                        kind=str(c["kind"]),
                        ticks=r.num(c, "ticks", cw),
                        base_level=r.int_(c, "base_level", cw),
                        max_level=r.int_(c, "max_level", cw),
                        base_points=r.num(c, "base_points", cw),
                        points_per_level=r.num(c, "points_per_level", cw),
                        variance=r.num(c, "variance", cw),
                        bonus_coefficient=r.num(c, "bonus_coefficient", cw),
                        period_ms=r.int_(c, "period_ms", cw),
                    )
                )
            parsed.append(
                RankScaling(
                    rank=r.int_(entry, "rank", w),
                    spell_id=r.int_(entry, "spell_id", w),
                    base_level=r.int_(entry, "base_level", w),
                    spell_level=r.int_(entry, "spell_level", w),
                    max_level=r.int_(entry, "max_level", w),
                    start_recovery_ms=r.int_(entry, "start_recovery_ms", w),
                    components=tuple(components),
                )
            )
        out[key] = tuple(parsed)
    return out


def _quest_band(r: _Reader, band: Mapping[str, Any]) -> QuestBand:
    where = "leveling.quest_band"
    rows = r.list_(band, "gray_rows", f"{where}.gray_rows")
    parsed = []
    for row in rows:
        ok = isinstance(row, list) and len(row) == 3 and isinstance(row[0], int) and isinstance(row[2], int)
        if not ok or not (row[1] is None or isinstance(row[1], int)):
            raise r.fail(f"{where}.gray_rows", "lignes [niveau max, retrait ou null, diviseur]")
        parsed.append((row[0], row[1], row[2]))
    return QuestBand(
        red_min_diff=r.int_(band, "red_min_diff", where),
        orange_min_diff=r.int_(band, "orange_min_diff", where),
        yellow_min_diff=r.int_(band, "yellow_min_diff", where),
        gray_rows=tuple(parsed),
    )


def _armors(raw: Any) -> dict[str, tuple[ArmorRank, ...]]:
    """`spell_scaling.json.utility` : rangs des armures du Mage (niveau d'apprentissage et effets du client)."""
    r = _Reader(SCALING_FILE)
    out: dict[str, tuple[ArmorRank, ...]] = {}
    for kind, ranks in r.obj(raw, "utility", "utility").items():
        where = f"utility.{kind}"
        if not isinstance(ranks, list) or not ranks:
            raise r.fail(where, "liste de rangs")
        parsed = []
        for i, entry in enumerate(ranks, start=1):
            w = f"{where}[{i}]"
            if not isinstance(entry, dict):
                raise r.fail(w, "objet")
            effects = r.obj(entry, "effects", f"{w}.effects")
            parsed.append(
                ArmorRank(
                    kind=kind,
                    rank=r.int_(entry, "rank", w),
                    spell_id=r.int_(entry, "spell_id", w),
                    learned_level=r.int_(entry, "learned_level", w),
                    effects={k: r.num(effects, k, f"{w}.effects") for k in effects},
                )
            )
        if [a.rank for a in parsed] != list(range(1, len(parsed) + 1)):
            raise r.fail(where, "rangs 1, 2, … dans l'ordre")
        out[kind] = tuple(parsed)
    return out


def _fire_vulnerability(raw: Any) -> FireVulnerability:
    """`spell_scaling.json.auras.fire_vulnerability` : aura d'Improved Scorch lue dans le client."""
    r = _Reader(SCALING_FILE)
    where = "auras.fire_vulnerability"
    fv = r.obj(r.obj(raw, "auras", "auras"), "fire_vulnerability", where)
    schools = r.list_(fv, "schools", f"{where}.schools")
    if not schools or not all(isinstance(s, str) for s in schools):
        raise r.fail(f"{where}.schools", "liste d'écoles")
    return FireVulnerability(
        spell_id=r.int_(fv, "spell_id", where),
        pct_per_stack=r.num(fv, "pct_per_stack", where),
        max_stacks=r.int_(fv, "max_stacks", where),
        duration_s=r.num(fv, "duration_ms", where) / MS_PER_S,
        schools=tuple(schools),
    )


def _choice(values: Mapping[str, Any], key: str) -> str:
    """Valeur d'une clé à choix de `mechanics.json` (`CHOICES`) ; DataSchemaError si elle n'est pas acceptée."""
    r = _Reader(MECHANICS_FILE)
    value = r.str_(r.obj(values, key, key), "value", key)
    if value not in CHOICES[key]:
        raise r.fail(key, " ou ".join(CHOICES[key]))
    return value


def _assumption_ranges(values: Mapping[str, Any]) -> dict[str, tuple[Variant, ...]]:
    """Champs `range` de `mechanics.json` : variantes (valeur, source) d'une hypothèse incertaine ; la valeur des
    données doit en faire partie et passe en premier (T05)."""
    r = _Reader(MECHANICS_FILE)
    out: dict[str, tuple[Variant, ...]] = {}
    for key, entry in values.items():
        if not isinstance(entry, dict) or "range" not in entry:
            continue
        items = r.list_(entry, "range", f"{key}.range")
        variants = tuple(
            Variant(r.obj({"v": v}, "v", f"{key}.range")["value"], r.str_(v, "source", f"{key}.range")) for v in items
        )
        current = [v for v in variants if v.value == entry.get("value")]
        if len(variants) < 2 or len(current) != 1:
            raise r.fail(f"{key}.range", "au moins deux variantes, dont la valeur des données")
        out[key] = (current[0], *(v for v in variants if v is not current[0]))
    return out


def _xp_to_next(raw: Any) -> tuple[int, ...]:
    """`leveling.json.xp_to_next.values` : XP pour passer au niveau suivant (courbe Classic conservée, T05)."""
    r = _Reader(LEVELING_FILE)
    values = r.list_(r.obj(raw, "xp_to_next", "xp_to_next"), "values", "xp_to_next.values")
    return tuple(r.int_({"v": v}, "v", "xp_to_next.values") for v in values)


def _talent_cooldowns(raw: Any) -> dict[str, float]:
    """`spell_scaling.json.talent_cooldowns` : recharge (s) des talents actifs, lue dans le client (T05)."""
    r = _Reader(SCALING_FILE)
    cds = r.obj(raw, "talent_cooldowns", "talent_cooldowns")
    return {key: r.num(r.obj(cds, key, f"talent_cooldowns.{key}"), "cooldown_ms", key) / MS_PER_S for key in cds}


def _respec(raw: Any, values: Mapping[str, Any]) -> RespecRules:
    """Barème de `respec.json` et clés `respec.*` de `mechanics.json` (T05)."""
    r = _Reader(RESPEC_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    schedule = r.list_(raw, "classic_schedule_gold", "classic_schedule_gold")
    if not schedule:
        raise r.fail("classic_schedule_gold", "liste non vide de prix en or")
    m = _Reader(MECHANICS_FILE)
    gph = m.obj(m.obj(values, "respec.gold_per_hour", "respec.gold_per_hour"), "value", "respec.gold_per_hour")
    if not gph:
        raise m.fail("respec.gold_per_hour", "table niveau -> or par heure non vide")
    return RespecRules(
        schedule_gold=tuple(r.num({"v": g}, "v", "classic_schedule_gold") for g in schedule),
        beta_observed_resets=m.int_(
            m.obj(values, "respec.beta_observed_resets", "respec.beta_observed_resets"),
            "value",
            "respec.beta_observed_resets",
        ),
        gold_per_hour={
            _level_key(m, k, "respec.gold_per_hour"): m.num(gph, k, "respec.gold_per_hour") for k in sorted(gph)
        },
        trip_minutes=m.num(m.obj(values, "respec.trip_minutes", "respec.trip_minutes"), "value", "respec.trip_minutes"),
    )


def _build_method(values: Mapping[str, Any], game_state: Mapping[str, Any] | None = None) -> BuildMethod:
    """Clés `build.*` de `mechanics.json` : plafond de la bêta, paramètres de décision (T05)."""
    m = _Reader(MECHANICS_FILE)

    def entry(key: str) -> Mapping[str, Any]:
        return m.obj(values, key, key)

    return BuildMethod(
        beta_level_cap=_beta_level_cap(m, values, game_state),
        confidence=m.num(entry("build.confidence"), "value", "build.confidence"),
        stability_seeds=m.int_(entry("build.stability_seeds"), "value", "build.stability_seeds"),
        scenarios=_scenarios(m, m.obj(entry("build.scenarios"), "value", "build.scenarios")),
        presets=_presets(m, m.obj(entry("build.presets"), "value", "build.presets")),
        contexts=_contexts(m, m.obj(entry("build.contexts"), "value", "build.contexts")),
        concord_threshold=m.num(entry("build.concord_threshold"), "value", "build.concord_threshold"),
    )


def _beta_level_cap(m: _Reader, values: Mapping[str, Any], game_state: Mapping[str, Any] | None) -> int:
    """Plafond de la bêta : fait d'installation (`meta.json` `game_state`, T08b, D2) ; l'ancienne clé de
    `mechanics.json` n'est lue que pour une version installée avant T08b, et refusée à côté de `game_state`."""
    old = values.get(BETA_CAP_KEY)
    if game_state and "beta_level_cap" in game_state:
        if old is not None:
            raise DataSchemaError(
                f"{MECHANICS_FILE} : {BETA_CAP_KEY} retirée depuis T08b (plafond de la bêta dans meta.json game_state)."
            )
        return _Reader(META_FILE).int_(game_state["beta_level_cap"], "value", "game_state.beta_level_cap.value")
    return m.int_(m.obj(values, BETA_CAP_KEY, BETA_CAP_KEY), "value", BETA_CAP_KEY)


def _presets(m: _Reader, raw: Mapping[str, Any]) -> dict[str, Preset]:
    """`build.presets` : préréglages de l'optimiseur (T05)."""
    out: dict[str, Preset] = {}
    for name in raw:
        where = f"build.presets.{name}"
        p = m.obj(raw, name, where)
        out[name] = Preset(**{k: m.int_(p, k, f"{where}.{k}") for k in ("beam", "depth", "shortlist", "mc_n")})
    return out


def _contexts(m: _Reader, raw: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """`build.contexts` : scénarios de chaque contexte de fin de partie (T05)."""
    out: dict[str, tuple[str, ...]] = {}
    for name in raw:
        items = m.list_(raw, name, f"build.contexts.{name}")
        out[name] = tuple(m.str_({"v": s}, "v", f"build.contexts.{name}") for s in items)
    return out


SCENARIO_HP = ("boss", "mob")


def _scenarios(m: _Reader, raw: Mapping[str, Any]) -> dict[str, Scenario]:
    """`build.scenarios` : scénarios provisoires de donjon et de raid (T05)."""
    out: dict[str, Scenario] = {}
    for name in raw:
        where = f"build.scenarios.{name}"
        s = m.obj(raw, name, where)
        hp = m.str_(s, "hp", f"{where}.hp")
        if hp not in SCENARIO_HP:
            raise m.fail(f"{where}.hp", " ou ".join(SCENARIO_HP))
        out[name] = Scenario(
            name=name,
            targets=m.int_(s, "targets", f"{where}.targets"),
            level_offset=m.int_(s, "level_offset", f"{where}.level_offset"),
            duration_s=m.num(s, "duration_s", f"{where}.duration_s"),
            freeze_immune=m.bool_(s, "freeze_immune", f"{where}.freeze_immune"),
            hp=hp,
        )
    return out


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
        low_level_default=r.bool_(entry("coefficient.low_level_default"), "value", "coefficient.low_level_default"),
        ice_lance_source=_choice(values, "coefficient.ice_lance_source"),
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
        miss_per_level_below=num("hit.miss_per_level_below"),
        regen_stacking=_choice(values, "mana.regen_stacking"),
        bonus_stacking=_choice(values, "damage.bonus_stacking"),
    )


def build_game_data(version: VersionData, rules: str = "forever") -> GameData:
    """Données typées d'une version déjà vérifiée ; lève DataSchemaError si une clé manque ou a un mauvais type.

    `rules="seed"` : sorts et talents lus dans les copies figées du seed (`SEED_FILES`, T06b), pour la parité ; le
    reste de la version est le même dans les deux modes."""
    if rules not in RULES:
        raise InvalidArgumentError(f"Règles inconnues : {rules}.", "choisir forever ou seed")
    files = {SPELLS_FILE: SPELLS_FILE, TALENTS_FILE: TALENTS_FILE, **(SEED_FILES if rules == "seed" else {})}
    try:
        names = (LEVELING_FILE, MONSTERS_FILE, SCALING_FILE, RESPEC_FILE)
        raw = {name: version.read_json(name) for name in names}
        racials_file = racials_source(version, rules)
        raw[racials_file] = version.read_json(racials_file)
        raw |= {name: version.read_json(file) for name, file in files.items()}
        raw_mechanics = version.read_json(MECHANICS_FILE)
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"Données de la version {version.game_version} illisibles ({exc}).") from exc
    values = _Reader(MECHANICS_FILE).obj(raw_mechanics, "values", "values")
    talents, trees = _talents(raw[TALENTS_FILE], files[TALENTS_FILE])
    spells = _spells(raw[SPELLS_FILE], files[SPELLS_FILE])
    constants = _constants(raw_mechanics)
    leveling = _leveling(values)
    xp_to_next = _xp_to_next(raw[LEVELING_FILE])
    ratios = "estimations"
    if rules == "forever" and (version.path / CHARACTER_FILE).is_file():
        try:
            raw_char = version.read_json(CHARACTER_FILE)
        except (OSError, ValueError) as exc:
            raise DataSchemaError(f"{CHARACTER_FILE} de {version.game_version} illisible ({exc}).") from exc
        constants, leveling, xp_to_next = _client_ratios(raw_char, constants, leveling)
        ratios = "client"
    utility, utility_source = _utility(raw[SPELLS_FILE], files[SPELLS_FILE]), files[SPELLS_FILE]
    if rules == "forever":
        constants, leveling = _client_mechanics(raw[SCALING_FILE], constants, leveling)
        mage = _mage_client_spells(version) if (version.path / CLASSES_FILE).is_file() else None
        if mage:
            utility, spells = _client_utility(mage, utility, spells, _spell_names(version))
            utility_source = CLASSES_FILE
    try:
        meta = version.read_json(META_FILE) if (version.path / META_FILE).is_file() else {}
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"{META_FILE} de {version.game_version} illisible ({exc}).") from exc
    game_state = meta.get("game_state") if isinstance(meta, dict) else None
    return GameData(
        game_version=version.game_version,
        spells=spells,
        talents=talents,
        talent_at={(t.tree, t.tier, t.col): t.key for t in talents.values()},
        trees=trees,
        rules=_rules(raw[LEVELING_FILE]),
        constants=constants,
        racials=_racials_from_races(raw[racials_file]) if racials_file == RACES_FILE else _racials(raw[racials_file]),
        monsters=_monsters(raw[MONSTERS_FILE]),
        scaling=_scaling(raw[SCALING_FILE], spells),
        mob_model=_mob_model(raw[LEVELING_FILE]),
        leveling=leveling,
        utility=utility,
        armors=_armors(raw[SCALING_FILE]),
        fire_vulnerability=_fire_vulnerability(raw[SCALING_FILE]),
        talent_cooldowns_s=_talent_cooldowns(raw[SCALING_FILE]),
        level_cap=_Reader(SCALING_FILE).int_(raw[SCALING_FILE], "level_cap", "level_cap"),
        xp_to_next=xp_to_next,
        pvp=_pvp(values),
        respec=_respec(raw[RESPEC_FILE], values),
        build=_build_method(values, game_state if isinstance(game_state, dict) else None),
        assumption_ranges=_assumption_ranges(values),
        classes=_ClassFile(version) if (version.path / CLASSES_FILE).is_file() else {},
        character_ratios=ratios,
        utility_source=utility_source,
    )


MAGE_CLASS = "Mage"  # moteur du Mage : ses ratios dans character_scaling.json
ABLATABLE: tuple[str, ...] = ()


def ablated(names: set[str]) -> Any:
    raise NotImplementedError
PERCENT = 100.0  # conversion d'unité : pourcentage du client -> fraction


@lru_cache(maxsize=8)
def _mage_spells_cached(path: str, data_sha: str) -> dict[str, Any]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    spells = doc.get("classes", {}).get(MAGE_CLASS, {}).get("spells", {}) if isinstance(doc, dict) else {}
    return {str(s.get("name")): s for s in spells.values() if isinstance(s, dict)}


def _mage_client_spells(version: VersionData) -> dict[str, Any]:
    """Sorts du Mage de `classes.json`, par nom anglais (lu une fois par version et empreinte : 2 Mo)."""
    try:
        return _mage_spells_cached(str(version.path / CLASSES_FILE), version.data_sha)
    except (OSError, ValueError) as exc:
        raise DataSchemaError(f"{CLASSES_FILE} illisible ({exc}).") from exc


def _spell_names(version: VersionData) -> dict[str, str]:
    """Clé de sort du dépôt -> nom anglais du client (`decode_rules.json` `spells`), vide sans règles."""
    if not (version.path / "decode_rules.json").is_file():
        return {}
    try:
        names = version.read_json("decode_rules.json").get("spells", {})
    except (OSError, ValueError, AttributeError):
        return {}
    return {str(k): str(v) for k, v in names.items()} if isinstance(names, dict) else {}


def _first_rank(spell: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    ranks = spell.get("ranks") if isinstance(spell, Mapping) else None
    return ranks[0] if isinstance(ranks, list) and ranks and isinstance(ranks[0], Mapping) else None


def _client_utility(
    mage: Mapping[str, Any], utility: Utility, spells: dict[str, Spell], names: Mapping[str, str]
) -> tuple[Utility, dict[str, Spell]]:
    """Mode forever (T08b, D2) : niveaux, recharges, durées, coupure de Counterspell et coûts en pourcentage du mana
    de base lus dans `classes.json` (décodé du client) quand il les porte ; le reste (absorption d'Ice Barrier,
    régénération de l'Évocation) garde la copie du seed."""
    changes: dict[str, Any] = {}

    def num(value: Any) -> float | None:
        return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None

    blink, cs, evo = (_first_rank(mage.get(n)) for n in ("Blink", "Counterspell", "Evocation"))
    if blink:
        changes |= {"blink_level": int(blink["level"]), "blink_cooldown_s": num(blink.get("cooldown_s"))}
    if cs:
        lockout = ((mage["Counterspell"].get("pvp") or {}).get("interrupt") or {}).get("lockout_s")
        changes |= {
            "counterspell_level": int(cs["level"]),
            "counterspell_cooldown_s": num(cs.get("cooldown_s")),
            "counterspell_lockout_s": num(lockout),
        }
    if evo:
        changes |= {"evocation_level": int(evo["level"]), "evocation_duration_s": num(evo.get("duration_s"))}
    barrier = (mage.get("Ice Barrier") or {}).get("ranks")
    if isinstance(barrier, list) and len(barrier) == len(utility.ice_barrier):
        changes["ice_barrier"] = tuple(
            (int(r["level"]), absorb) for r, (_, absorb) in zip(barrier, utility.ice_barrier, strict=True)
        )
    kept = {k: v for k, v in changes.items() if v is not None}
    new_spells = dict(spells)
    for key, spell in spells.items():
        rank = _first_rank(mage.get(names.get(key, "")))
        pct = num(((rank or {}).get("cost") or {}).get("pct"))
        if spell.mana_pct_base is not None and pct:
            new_spells[key] = replace(spell, mana_pct_base=pct / PERCENT)
    return replace(utility, **kept), new_spells


def _client_mechanics(
    raw_scaling: Any, constants: Constants, leveling: LevelingConstants
) -> tuple[Constants, LevelingConstants]:
    """Mode forever (T08b, bloc B) : aura d'Ignite et critique par cumul de Winter's Chill lus dans
    `spell_scaling.json` (`auras`) quand la version les porte ; sinon les copies de `mechanics.json`."""
    r = _Reader(SCALING_FILE)
    auras = raw_scaling.get("auras", {}) if isinstance(raw_scaling, dict) else {}
    ignite = auras.get("ignite")
    if isinstance(ignite, dict):
        leveling = replace(
            leveling,
            ignite_aura_id=r.int_(ignite, "spell_id", "auras.ignite.spell_id"),
            ignite_duration_s=r.num(ignite, "duration_ms", "auras.ignite.duration_ms") / MS_PER_S,
            ignite_tick_s=r.num(ignite, "period_ms", "auras.ignite.period_ms") / MS_PER_S,
            ignite_cumulative=r.int_(ignite, "cumulative", "auras.ignite.cumulative"),
        )
    wc = auras.get("winters_chill")
    if isinstance(wc, dict):
        constants = replace(
            constants,
            crit_per_winters_chill_stack=r.num(wc, "pct_per_stack", "auras.winters_chill.pct_per_stack") / PERCENT,
        )
    return constants, leveling


def _client_ratios(
    raw: Any, constants: Constants, leveling: LevelingConstants
) -> tuple[Constants, LevelingConstants, tuple[int, ...]]:
    """Ratios du client (`character_scaling.json`, T08b, bloc A) à la place des estimations, mode forever : critique
    par Intelligence et mana de base du Mage par niveau, constante d'armure par niveau, XP par niveau."""
    r = _Reader(CHARACTER_FILE)
    mage = r.obj(r.obj(raw, "classes", "classes"), MAGE_CLASS, f"classes.{MAGE_CLASS}")

    def numbers(obj: Any, key: str, where: str) -> tuple[float, ...]:
        values = r.list_(obj, key, where)
        if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in values):
            raise r.fail(where, "liste de nombres")
        return tuple(float(v) for v in values)

    character = replace(
        constants.character,
        spell_crit_per_int_by_level=numbers(mage, "spell_crit_per_intellect", "classes.Mage.spell_crit_per_intellect"),
        base_mana_by_level=numbers(mage, "base_mana", "classes.Mage.base_mana"),
    )
    xp = tuple(r.int_({"v": v}, "v", "xp_to_next") for v in r.list_(raw, "xp_to_next", "xp_to_next"))
    armor = numbers(raw, "armor_constant", "armor_constant")
    talents = raw.get("talents") if isinstance(raw.get("talents"), dict) else {}
    first = talents.get("first_level")
    per_tier = (talents.get("points_per_tier") or {}).get(MAGE_CLASS)
    if isinstance(first, int) and isinstance(per_tier, int):
        constants = replace(constants, talents=TalentRules(first_level=first, points_per_tier=per_tier))
    return replace(constants, character=character), replace(leveling, armor_constant_by_level=armor), xp


def load_game_data(deps: Deps) -> GameData:
    """Version courante, après contrôle d'intégrité (DataIntegrityError, ManifestMissingError)."""
    return build_game_data(load_version(deps))


PVP_RULES_FILE = "pvp_rules.json"  # règles du serveur des rendements décroissants (PV1, suppose)


def dr_rules(raw: Any) -> DrRules:
    """Règles des rendements décroissants lues dans `pvp_rules.json` (`diminishing_returns`, `suppose`) ; chaque
    entrée porte sa valeur, sa certitude et ses sources. DataSchemaError si une clé manque ou a un mauvais type."""
    r = _Reader(PVP_RULES_FILE)
    if not isinstance(raw, dict):
        raise r.fail("racine", "objet")
    dr = r.obj(raw, "diminishing_returns", "diminishing_returns")

    def entry(key: str) -> Any:
        found = dr.get(key)
        if not isinstance(found, dict) or "value" not in found:
            raise r.fail(f"diminishing_returns.{key}", "objet avec value")
        return found["value"]

    steps = entry("steps")
    if not isinstance(steps, list) or not steps or not all(isinstance(x, int | float) for x in steps):
        raise r.fail("diminishing_returns.steps.value", "liste de nombres")
    window, start, cap = entry("window_s"), entry("window_from"), entry("pvp_duration_cap_s")
    if isinstance(window, bool) or not isinstance(window, int | float):
        raise r.fail("diminishing_returns.window_s.value", "nombre")
    if start not in ("fin", "application"):
        raise r.fail("diminishing_returns.window_from.value", "« fin » ou « application »")
    if cap is not None and (isinstance(cap, bool) or not isinstance(cap, int | float)):
        raise r.fail("diminishing_returns.pvp_duration_cap_s.value", "nombre ou null")
    return DrRules(
        steps=tuple(float(x) for x in steps),
        window_s=float(window),
        window_from=str(start),
        pvp_cap_s=None if cap is None else float(cap),
    )
