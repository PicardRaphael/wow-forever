"""Équipement (CJ1, bloc 4, T10a revue, décisions 272 et 276) : poids des statistiques du Mage calculés par notre
moteur et exportés vers Naowh Forever (`NFSW1:`) et Forever Companion (Pawn v1) ; les listes BiS, le leveling et
« est-ce une amélioration ? » s'appuient sur les addons qui calculent déjà (`forever/pipeline/gear_sources.py`)."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from forever.classic import ENGINE_FILES, classic_note
from forever.config import Deps
from forever.sims.report import MAGE_ENGINE_FROZEN

if TYPE_CHECKING:
    from forever.engine.model import CharacterOverrides

# Pas des différences finies (réglages de méthode, pas des valeurs du jeu) : points pour les statistiques simples,
# fraction pour critique et toucher de l'équipement.
WEIGHT_STEPS = {"intellect": 10.0, "spirit": 10.0, "sp": 10.0, "crit_gear": 0.01, "hit_gear": 0.01}
PERCENT_STATS = ("crit_gear", "hit_gear")  # poids exportés par point de pourcentage (fraction × 100)
PERCENT = 100.0  # conversion fraction -> point de pourcentage
DIGITS = 3  # chiffres gardés après la virgule (export lisible, aller-retour exact)
NAOWH_KEYS = {"intellect": "int", "spirit": "spi", "sp": "spell", "crit_gear": "scrit", "hit_gear": "shit"}
PAWN_KEYS = {
    "intellect": "Intellect",
    "spirit": "Spirit",
    "sp": "SpellPower",
    "crit_gear": "SpellCritRating",
    "hit_gear": "SpellHitRating",
}


def mage_weights(
    deps: Deps,
    *,
    level: int,
    race: str = "Orc",
    rotation: str = "frost",
    talents: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Poids du Mage au niveau `level` : gain d'XP par heure du leveling (analytique du moteur, combat, repos et
    course) par point de chaque statistique, normalisé sur l'Intelligence ; critique et toucher par point de
    pourcentage. Registre : I3"""
    from forever.engine.character import character
    from forever.engine.weights import normalize_weights, stat_weights
    from forever.errors import InvalidArgumentError
    from forever.freshness import freshness_for_version
    from forever.gamedata import build_game_data
    from forever.leveling import check_level, check_race, check_talents, level_cap
    from forever.provenance import make_provenance
    from forever.sim.leveling_analytic import kill_analytic
    from forever.store import load_version

    data = load_version(deps)
    gd = build_game_data(data)
    check_level(level, level_cap(data))
    check_race(data, race)
    pts = dict(talents or {})
    check_talents(gd, pts, level)
    me = character(gd, level, race)
    base = {"intellect": me.intellect, "spirit": me.spirit, "sp": me.sp, "crit_gear": 0.0, "hit_gear": 0.0}

    def xp_h(over: Any) -> float:
        return float(kill_analytic(gd, level, pts, race, rotation, cast("CharacterOverrides", dict(over)))["xp_h"])

    try:
        raw = stat_weights(xp_h, base, WEIGHT_STEPS)
        normalized = normalize_weights(
            {k: v / PERCENT if k in PERCENT_STATS else v for k, v in raw.items()}, reference="intellect"
        )
    except ValueError as exc:
        raise InvalidArgumentError(
            f"Poids du Mage impossibles au niveau {level} : {exc}.", "choisir un niveau où le sort principal est appris"
        ) from exc
    weights = {k: round(v, DIGITS) for k, v in normalized.items()}
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty="suppose",
        assumptions=[
            *fresh["assumptions"],
            (
                f"poids : gain d'XP par heure du leveling du Mage (analytique du moteur, rotation {rotation}) par "
                "point de chaque statistique, différences finies avant sur la fiche estimée du niveau, Intelligence "
                "= 1 ; critique et toucher par point de pourcentage"
            ),
            "équipement porté non pris en compte ; talents seulement s'ils sont donnés ; écoles = puissance des sorts",
            MAGE_ENGINE_FROZEN,
            *filter(None, [classic_note(deps.data_dir / data.game_version, ENGINE_FILES)]),
        ],
    )
    return {"level": level, "race": race, "rotation": rotation, "weights": weights, "provenance": provenance}


def naowh_weight_line(report: dict[str, Any], *, spec: str) -> str:
    """Ligne `NFSW1:` (Naowh Forever, « Import weights ») des poids d'un rapport de `mage_weights`."""
    from forever.exports.naowh import naowh_weights

    return naowh_weights(spec, {NAOWH_KEYS[k]: v for k, v in report["weights"].items() if k in NAOWH_KEYS})


def pawn_line(report: dict[str, Any], *, label: str) -> str:
    """Échelle Pawn v1 (Forever Companion, « Import scale… ») des poids d'un rapport de `mage_weights`."""
    from forever.exports.pawn import pawn_scale

    return pawn_scale(label, "MAGE", {PAWN_KEYS[k]: v for k, v in report["weights"].items() if k in PAWN_KEYS})


# --- liste BiS personnelle (CJ1, bloc 4) ---------------------------------------------------------------------------

# Emplacements nommés de Forever Companion -> emplacements d'inventaire (constantes de l'interface du jeu).
COMPANION_SLOTS: dict[str, tuple[int, ...]] = {
    "head": (1,),
    "neck": (2,),
    "shoulder": (3,),
    "back": (15,),
    "chest": (5,),
    "wrist": (9,),
    "hands": (10,),
    "waist": (6,),
    "legs": (7,),
    "feet": (8,),
    "finger": (11, 12),
    "trinket": (13, 14),
    "main hand": (16,),
    "off hand": (17,),
    "ranged": (18,),
}
PAIRED = ((11, 12), (13, 14))  # deux bagues, deux bijoux : deux objets distincts
# objets dont l'origine dépend du camp : types de GearQuest Forever et genres du lieu de butin de Naowh Forever
CAMP_SOURCES = ("quest_reward", "seasonal_quest", "vendor")
NAOWH_CAMP_KINDS = ("Quest", "Reputation", "PvP Rank")
CAMP_NOTE = (
    "objets de l'autre camp écartés : mention du camp chez Naowh, sinon objet absent du classement de GearQuest "
    "pour ce camp quand son origine dépend du camp (quête, marchand, réputation, rang JcJ ; suppose)"
)
# Statistiques de l'échelle de Forever Companion -> clés de Forever Guide (`GearData.lua`).
PAWN_TO_GUIDE = {
    "Strength": "str",
    "Agility": "agi",
    "Stamina": "sta",
    "Intellect": "int",
    "Spirit": "spi",
    "Ap": "ap",
    "Rap": "rap",
    "FeralAp": "fap",
    "HitRating": "hit",
    "CritRating": "crit",
    "MeleeDps": "dps",
    "SpellPower": "sp",
    "SpellDamage": "sp",
    "Healing": "hp",
    "ArcaneSpellDamage": "arc",
    "FireSpellDamage": "fir",
    "FrostSpellDamage": "fro",
    "HolySpellDamage": "hol",
    "NatureSpellDamage": "nat",
    "ShadowSpellDamage": "sha",
    "SpellHitRating": "shit",
    "SpellCritRating": "scrit",
    "Armor": "armor",
    "DefenseRating": "def",
    "DodgeRating": "dodge",
    "ParryRating": "parry",
    "BlockRating": "block",
    "BlockValue": "bv",
}
# Statistiques des poids par défaut de Naowh -> clés de Forever Guide (hâte et menace : sans clé chez Guide).
NAOWH_TO_GUIDE = {
    "str": "str", "agi": "agi", "sta": "sta", "int": "int", "spi": "spi", "ap": "ap", "rap": "rap", "dps": "dps",
    "hit": "hit", "crit": "crit", "shit": "shit", "scrit": "scrit", "mp5": "mp5", "def": "def", "dodge": "dodge",
    "block": "block", "armor": "armor", "spell": "sp", "heal": "hp", "arcane": "arc", "fire": "fir", "frost": "fro",
    "holy": "hol", "nature": "nat", "shadow": "sha",
}  # fmt: skip
ROLE_WORDS = ("dps", "tank", "healer")  # rôle porté par une clé de spécialisation ou un libellé d'échelle
# Poids du Mage (moteur) -> clés de Forever Guide ; l'école de la spécialisation vaut la puissance des sorts.
MAGE_TO_GUIDE = {"intellect": "int", "spirit": "spi", "sp": "sp", "crit_gear": "scrit", "hit_gear": "shit"}
SCHOOLS = {"fire": "fir", "frost": "fro", "arcane": "arc"}


def companion_weights(addons: Any, class_token: str, *, index: int = 0) -> dict[str, float]:
    """Poids de l'échelle de Forever Companion d'une classe (la `index`-ième), en clés de Forever Guide (`suppose`)."""
    from forever.pipeline.gear_sources import read_companion_scales

    scales = read_companion_scales(addons).get(class_token.upper()) or []
    if not scales:
        return {}
    out: dict[str, float] = {}
    for stat, weight in scales[min(index, len(scales) - 1)].weights.items():
        key = PAWN_TO_GUIDE.get(stat)
        if key:
            out[key] = out.get(key, 0.0) + weight
    return out


def _guide_keys(scale: Mapping[str, float], table: Mapping[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for stat, weight in scale.items():
        key = table.get(stat)
        if key:
            out[key] = out.get(key, 0.0) + weight
    return out


def naowh_weights(addons: Any, spec_key: str) -> dict[str, float]:
    """Poids par défaut de Naowh Forever d'une spécialisation (niveau 60, `suppose`), en clés de Forever Guide ; vide
    sans l'addon ou la spécialisation."""
    from forever.pipeline.gear_sources import read_naowh_weights

    data = read_naowh_weights(addons)
    spec = data.specs.get(spec_key) if data is not None else None
    return _guide_keys(spec.weights, NAOWH_TO_GUIDE) if spec is not None else {}


def companion_spec_weights(
    addons: Any, class_token: str, spec_key: str, trees: Sequence[str]
) -> tuple[dict[str, float], str] | None:
    """Échelle de Forever Companion d'une spécialisation : celle de son onglet de talents (`trees` : noms des arbres de
    la classe, dans l'ordre du client), départagée par le rôle du libellé (Feral DPS ou Feral Tank) ; None si aucune
    échelle n'est sur cet onglet."""
    from forever.pipeline.gear_sources import read_companion_scales

    words = spec_key.removesuffix(f"-{class_token.lower()}").split("-")
    role = next((w for w in words if w in ROLE_WORDS), None)
    base = " ".join(w for w in words if w not in ROLE_WORDS)
    tab = next((i + 1 for i, name in enumerate(trees) if base and name.lower().startswith(base)), None)
    scales = [s for s in read_companion_scales(addons).get(class_token.upper()) or [] if s.tab == tab]
    if not scales:
        return None
    pick = next((s for s in scales if role and role in s.label.lower()), scales[0])
    return _guide_keys(pick.weights, PAWN_TO_GUIDE), pick.label


def mage_guide_weights(report: dict[str, Any], *, spec_key: str) -> dict[str, float]:
    """Poids d'un rapport de `mage_weights` en clés de Forever Guide (école de la spécialisation comprise)."""
    out = {MAGE_TO_GUIDE[k]: v for k, v in report["weights"].items() if k in MAGE_TO_GUIDE}
    school = SCHOOLS.get(spec_key.split("-")[0])
    if school and "sp" in out:
        out[school] = out["sp"]
    return out


def _companion_key(cls: str, spec: str) -> str:
    return f"{spec.lower().replace(' ', '-')}-{cls.lower()}"


def _score(stats: dict[str, float] | None, weights: dict[str, float]) -> float | None:
    if stats is None:
        return None
    return round(sum(weights.get(k, 0.0) * v for k, v in stats.items()), 3)


def personal_bis(
    addons: Any, *, spec_key: str, weights: dict[str, float], name: str, faction: str | None = None
) -> dict[str, Any]:
    """Liste BiS personnelle d'une spécialisation (décision 276) : candidats de Naowh Forever puis de Forever
    Companion par emplacement, classés par `weights` (clés de Forever Guide) sur les statistiques de Forever Guide ;
    objet sans statistiques connues après les objets chiffrés, dans l'ordre des addons ; bagues et bijoux sur deux
    emplacements distincts ; lieu de butin de Naowh ; objets de l'autre camp écartés (`faction` : mention de Naowh,
    sinon objet choisi par GearQuest pour l'autre camp seulement quand son origine dépend du camp) ; chaîne `!NBIS1!`
    (None sans liste)."""
    from forever.exports.naowh import naowh_bis
    from forever.pipeline.gear_sources import (
        read_companion_bis,
        read_gearquest_facts,
        read_gearquest_picks,
        read_guide_gear,
        read_naowh_bis,
    )

    gear = read_guide_gear(addons)
    naowh, sources = read_naowh_bis(addons)
    companion = read_companion_bis(addons)
    lists: dict[int, list[tuple[int, str]]] = {}
    spec = naowh.get(spec_key)
    for slot, ids in (spec.slots if spec else {}).items():
        lists.setdefault(slot, []).extend((i, "Naowh Forever") for i in ids)
    for (cls, cspec), named in companion.items():
        if _companion_key(cls, cspec) != spec_key:
            continue
        for slot_name, ids in named.items():
            for slot in COMPANION_SLOTS.get(slot_name, ()):
                lists.setdefault(slot, []).extend((i, "Forever Companion") for i in ids)
    if faction:  # objets réservés à l'autre camp d'après le lieu de butin de Naowh (« Quest (Horde) »…)
        other = {"horde": "(Alliance)", "alliance": "(Horde)"}.get(faction.lower())
        banned = {i for i, s in sources.items() if other and s.rstrip().endswith(other)}
        # sinon d'après GearQuest (une liste de choix par camp) : objet choisi pour l'autre camp seulement, quand son
        # origine dépend du camp (quête, marchand, réputation, rang JcJ) ; jamais un objet fabriqué ou lâché
        marked = {i for i, s in sources.items() if s.rstrip().endswith(("(Alliance)", "(Horde)"))}
        facts = read_gearquest_facts(addons, spec.class_token) if spec else {}
        camps: dict[int, set[str]] = {}
        for p in read_gearquest_picks(addons, spec.class_token) if spec else []:
            if p.faction:
                camps.setdefault(p.item, set()).add(p.faction.lower())

        def camp_bound(item: int) -> bool:
            kind = sources.get(item, "").rsplit("·", 1)[-1].strip()
            return facts.get(item, {}).get("sourceType") in CAMP_SOURCES or kind in NAOWH_CAMP_KINDS

        banned |= {i for i, c in camps.items() if i not in marked and faction.lower() not in c and camp_bound(i)}
        lists = {slot: [(i, o) for i, o in entries if i not in banned] for slot, entries in lists.items()}
    origins: dict[int, set[str]] = {}
    for entries in lists.values():
        for item, origin in entries:
            origins.setdefault(item, set()).add(origin)

    def ranked(slot: int) -> list[int]:
        seen = list(dict.fromkeys(i for i, _ in lists.get(slot, [])))
        scored = [i for i in seen if i in gear]
        scored.sort(key=lambda i: -(_score(gear[i].stats, weights) or 0.0))
        return scored + [i for i in seen if i not in gear]

    chosen: dict[int, int] = {}
    extra: dict[int, list[int]] = {}
    for slot in sorted(lists):
        order = ranked(slot)
        pair = next((p for p in PAIRED if slot in p), None)
        if pair and slot == pair[1] and pair[0] in chosen:
            order = [i for i in order if i != chosen[pair[0]]]
        if order:
            chosen[slot] = order[0]
            extra[slot] = order[1:]
    items = [
        {
            "slot": slot,
            "item": item,
            "chosen": item == chosen.get(slot),
            "score": _score(gear[item].stats, weights) if item in gear else None,
            "source": sources.get(item),
            "lists": sorted(origins.get(item, ())),
        }
        for slot in sorted(lists)
        for item in [chosen.get(slot), *extra.get(slot, [])]
        if item is not None
    ]
    export = naowh_bis(name, spec_key, chosen, extra) if chosen else None
    return {"spec": spec_key, "name": name, "slots": chosen, "extra": extra, "items": items, "export": export}


# --- leveling et « est-ce une amélioration ? » (CJ1, bloc 4) --------------------------------------------------------

# Type d'emplacement de l'objet (INVTYPE du client, celui de Forever Guide) -> emplacements d'inventaire (interface).
INVTYPE_SLOTS: dict[int, tuple[int, ...]] = {
    1: (1,), 2: (2,), 3: (3,), 5: (5,), 6: (6,), 7: (7,), 8: (8,), 9: (9,), 10: (10,), 11: (11, 12), 12: (13, 14),
    13: (16, 17), 14: (17,), 15: (18,), 16: (15,), 17: (16,), 20: (5,), 21: (16,), 22: (17,), 23: (17,), 25: (18,),
    26: (18,), 28: (18,),
}  # fmt: skip


@dataclass(frozen=True)
class DungeonDrop:
    """Objet lâché dans un donjon (livre des donjons de DJ1) : donjon, boss, taux (fraction), niveau d'ouverture."""

    item: int
    dungeon: str
    boss: str
    rate: float | None
    opens: int | None
    name: str | None = None


@dataclass(frozen=True)
class Access:
    """Ce qu'il faut savoir pour dire si un objet s'obtient à un niveau (essai CJ-6 du 2026-10-15) : quêtes du livre
    par nom (`level`, `min_level`, `faction`), niveau d'ouverture du donjon qui lâche un objet, écart d'une quête
    rouge (`leveling.quest_band.red_min_diff`, registre I7), métiers appris du personnage (noms anglais, minuscules)."""

    quests: Callable[[str], Sequence[Mapping[str, Any]]]
    dungeon_level: Callable[[int], int | None]
    red_min_diff: int
    professions: frozenset[str] = frozenset()
    # décision 282 : zones (noms) de ma route de leveling (None : inconnues, ordre de GearQuest gardé) et zones de
    # départ des autres races (jamais proposées hors de ma route)
    route_zones: frozenset[str] | None = None
    other_start_zones: frozenset[str] = frozenset()
    # fin du bloc 4c : butin de donjon d'un objet (boss, taux) et tout le butin des donjons (autre source)
    dungeon_drops: Callable[[int], Sequence[DungeonDrop]] | None = None
    all_dungeon_drops: Callable[[], Sequence[DungeonDrop]] | None = None
    race_ok: Callable[[Any], bool] | None = None  # masque de races d'une quête permis pour ma race (None : non vérifié)


class LevelingPicks(list[dict[str, Any]]):
    """Choix retenus par emplacement, plus les objets mis à part (source inconnue) et écartés (raison)."""

    def __init__(self, picks: list[dict[str, Any]], set_aside: list[dict[str, Any]], excluded: list[dict[str, Any]]):
        super().__init__(picks)
        self.set_aside = set_aside
        self.excluded = excluded


DROP_RANGE = re.compile(r"level (\d+)\s*-\s*(\d+)")  # « World drop around level 11-16. » (GearQuest Forever)
QUEST_SOURCES = ("quest_reward", "seasonal_quest")
DUNGEON_SOURCES = ("boss_drop", "raid_trash")


def _quest_detail(quest: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Donneur, zone, position et quêtes à faire d'abord d'une quête du livre (fin du bloc 4c)."""
    if not quest or not isinstance(quest.get("giver"), Mapping):
        return None
    giver = quest["giver"]
    return {
        "id": quest.get("id"),
        "giver": giver.get("name"),
        "zone": giver.get("zone"),
        "x": giver.get("x"),
        "y": giver.get("y"),
        "after": list(quest.get("after") or []),
    }


def _dungeon_detail(drops: Sequence[DungeonDrop]) -> dict[str, Any] | None:
    """Donjon, boss et taux du meilleur butin connu d'un objet (fin du bloc 4c)."""
    if not drops:
        return None
    best = max(drops, key=lambda d: d.rate if d.rate is not None else -1.0)
    return {"dungeon": best.dungeon, "boss": best.boss, "rate": best.rate}


def obtainable(fact: Mapping[str, Any], item: int, level: int, faction: str | None, access: Access) -> tuple[str, str]:
    """(« ok » | « out » | « aside », raison) : voir `obtainable_detail`. Registre : I21"""
    verdict, reason, _quest = obtainable_detail(fact, item, level, faction, access)
    return verdict, reason


def obtainable_detail(
    fact: Mapping[str, Any], item: int, level: int, faction: str | None, access: Access
) -> tuple[str, str, Mapping[str, Any] | None]:
    """(« ok » | « out » | « aside », raison) : l'objet s'obtient-il au niveau `level` ? Niveau requis au plus
    `level` ; quête du camp prise à ce niveau et pas rouge ; butin dont la plage commence au plus à `level` ; donjon
    ouvert à ce niveau ; métier appris ; sinon mis à part (source ou niveau inconnus). Registre : I21"""
    required = fact.get("reqLevel")
    if isinstance(required, int) and required > level:
        return "out", f"niveau requis {required}", None
    kind = fact.get("sourceType")
    zone = fact.get("zone")
    my_route = access.route_zones or frozenset()
    if kind != "world_drop" and zone in access.other_start_zones and zone not in my_route:
        return "out", f"zone de départ d'une autre race ({zone}), hors de ta route", None
    if kind in QUEST_SOURCES:
        name = str(fact.get("questName") or "")
        if not name:
            return "aside", "quête sans nom chez GearQuest", None
        quests = [q for q in access.quests(name) if q.get("faction") in (None, "both", (faction or "").lower())]
        if access.race_ok is not None and quests:
            ours = [q for q in quests if access.race_ok(q.get("races"))]
            if not ours:
                return "out", f"quête « {name} » d'une autre race", None
            quests = ours
        if not quests:
            mine = access.quests(name)
            return (
                ("out", f"quête « {name} » de l'autre camp", None)
                if mine
                else ("aside", f"quête « {name} » inconnue", None)
            )
        known = [q for q in quests if isinstance(q.get("level"), int)]
        if not known:
            return "aside", f"quête « {name} » sans niveau connu", None
        for q in known:
            low = int(q["min_level"]) if isinstance(q.get("min_level"), int) else 1
            if low <= level and q["level"] - level < access.red_min_diff:
                return "ok", f"quête « {name} », niveau {q['level']}", q  # quête retenue : son détail suit
        q = min(known, key=lambda q: q["level"])
        low = int(q["min_level"]) if isinstance(q.get("min_level"), int) else 1
        if low > level:
            return "out", f"quête « {name} » prise au niveau {low}", None
        return "out", f"quête « {name} » de niveau {q['level']}, rouge au niveau {level}", None
    if kind == "profession":
        craft = str(fact.get("profession") or "")
        if craft.lower() in access.professions:
            return "ok", f"métier {craft}", None
        return "out", f"métier {craft or 'inconnu'} non appris", None
    if kind in DUNGEON_SOURCES:
        opens = access.dungeon_level(item)
        if opens is None:
            return "aside", "donjon et niveau inconnus", None
        if opens > level:
            return "out", f"donjon ouvert au niveau {opens}", None
        return "ok", f"donjon ouvert au niveau {opens}", None
    if kind == "vendor":
        return "ok", "marchand", None
    found = DROP_RANGE.search(str(fact.get("instructions") or ""))
    if found:
        low = int(found.group(1))
        if low > level:
            return "out", f"butin des niveaux {found.group(1)} à {found.group(2)}", None
        return "ok", f"butin des niveaux {found.group(1)} à {found.group(2)}", None
    if kind == "unsourced" or not kind:
        return "aside", "source inconnue de GearQuest", None
    return "aside", f"source « {kind} » sans niveau connu", None


def other_start_zones(values: Any, race: str) -> set[str]:
    """Zones de départ des autres races (table des données, décision 283), sans la mienne. Registre : I21"""
    from forever.route import START_ZONES_KEY, race_start_zone

    mine = (race_start_zone(values, race) or {}).get("zone")
    table = values[START_ZONES_KEY]["value"] if START_ZONES_KEY in values else {}
    return {entry["zone"] for entry in table.values() if isinstance(entry, dict) and entry.get("zone") != mine}


def route_zones(
    deps: Deps, *, class_name: str, race: str, faction: str, below: int
) -> tuple[frozenset[str] | None, frozenset[str]]:
    """(zones de ma route, zones de départ des autres races), noms de zone : zones des quêtes que le parcours gratuit
    de RestedXP de ma race et de ma classe prend dans ses guides qui commencent sous le niveau `below`, et zones de
    départ des autres races lues dans la table des données (décision 283) ; (None, vide) sans RestedXP ou sans parcours (décision
    282, lecture locale). Registre : I21"""
    from types import SimpleNamespace

    from forever.errors import InvalidArgumentError
    from forever.gamedata import MECHANICS_FILE
    from forever.quests import build_quests, value
    from forever.route import reference_zones
    from forever.rxp_guides import read_rxp_guides, who_for
    from forever.store import load_version

    if deps.wow_dir is None:
        return None, frozenset()
    try:
        library = read_rxp_guides(deps.wow_dir / "Interface" / "AddOns")
    except InvalidArgumentError:
        return None, frozenset()
    book = build_quests(deps)
    quests = {
        qid: SimpleNamespace(
            zone=value(q, "map") if isinstance(value(q, "map"), int) else None,
            giver=value(q, "map") if isinstance(value(q, "map"), int) else None,  # carte du donneur, pour son départ
        )
        for qid, q in book.quests.items()
    }

    def names(maps: frozenset[int]) -> frozenset[str]:
        return frozenset(book.zone_names[m] for m in maps if m in book.zone_names)

    mine = names(reference_zones(library, who_for(class_name, race, faction), quests, below=below))
    others = other_start_zones(load_version(deps).read_json(MECHANICS_FILE)["values"], race)  # décision 283
    return (mine or None), frozenset(others - mine)


def level_access(
    deps: Deps,
    professions: list[str],
    *,
    class_name: str | None = None,
    race: str | None = None,
    faction: str | None = None,
    below: int | None = None,
) -> Access:
    """`Access` lu dans nos données : quêtes du livre par nom, donjons de DJ1 (niveau bas de leur plage), écart
    d'une quête rouge (`mechanics.json`), métiers donnés (noms anglais) ; avec la classe, la race et le camp, les
    zones de ma route et celles du départ des autres races (`route_zones`). Registre : I21"""
    from forever.dungeons import build_dungeons, where_item
    from forever.gamedata import load_game_data
    from forever.quests import build_quests, value

    book = build_quests(deps)
    names = {qid: value(q, "name") for qid, q in book.quests.items()}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for qid, q in book.quests.items():
        quest_name = value(q, "name")
        if isinstance(quest_name, str):
            giver = value(q, "giver") if isinstance(value(q, "giver"), dict) else {}
            first = [*(value(q, "prereq_all") or []), *(value(q, "prereq_any") or [])[:1]]  # fin du bloc 4c
            by_name.setdefault(quest_name, []).append(
                {
                    "id": qid,
                    "races": value(q, "races"),
                    "level": value(q, "level"),
                    "min_level": value(q, "min_level"),
                    "faction": value(q, "faction"),
                    "giver": {
                        "name": giver.get("name"),
                        "zone": book.zone_names.get(giver["map"]) if isinstance(giver.get("map"), int) else None,
                        "x": giver.get("x"),
                        "y": giver.get("y"),
                    }
                    if giver
                    else None,
                    "after": list(dict.fromkeys(names[i] for i in first if isinstance(names.get(i), str))),
                }
            )
    dungeons = build_dungeons(deps)
    drops: list[DungeonDrop] = []  # fin du bloc 4c : tout le butin des donjons, boss et taux
    for d in dungeons.dungeons.values():
        levels = ((d.get("fields") or {}).get("levels") or {}).get("value")
        opens = levels.get("min") if isinstance(levels, dict) and isinstance(levels.get("min"), int) else None
        for boss in d.get("bosses") or []:
            for entry in boss.get("loot") or []:
                if isinstance(entry.get("item"), int):
                    rate = entry["rate"] if isinstance(entry.get("rate"), int | float) else None
                    drops.append(DungeonDrop(entry["item"], d["name"], boss["name"], rate, opens))
    by_item: dict[int, list[DungeonDrop]] = {}
    for drop in drops:
        by_item.setdefault(drop.item, []).append(drop)

    def dungeon_level(item: int) -> int | None:
        lows = []
        for found in where_item(dungeons, item):
            levels = ((dungeons.dungeons[found["dungeon"]].get("fields") or {}).get("levels") or {}).get("value")
            if isinstance(levels, dict) and isinstance(levels.get("min"), int):
                lows.append(levels["min"])
        return min(lows) if lows else None

    red = load_game_data(deps).leveling.quest_band.red_min_diff
    mine, others = (
        route_zones(deps, class_name=class_name, race=race, faction=faction, below=below)
        if class_name and race and faction and below
        else (None, frozenset())
    )
    return Access(
        quests=lambda name: by_name.get(name, []),
        dungeon_level=dungeon_level,
        red_min_diff=int(red),
        professions=frozenset(p.strip().lower() for p in professions if p.strip()),
        route_zones=mine,
        other_start_zones=others,
        dungeon_drops=lambda item: by_item.get(item, []),
        all_dungeon_drops=lambda: drops,
        race_ok=_race_check(deps, race),
    )


def _race_check(deps: Deps, race: str | None) -> Callable[[Any], bool] | None:
    """Masque de races d'une quête permis pour `race` (même règle que les routes, `race_allowed`). Registre : I21"""
    if not race:
        return None
    from forever.route import race_allowed
    from forever.store import load_version

    races = load_version(deps).read_json("races.json").get("races") or {}
    if race not in races:
        return None
    race_id = int(races[race]["id"])
    return lambda mask: race_allowed(mask, race_id, races)


def leveling_gear(
    addons: Any,
    class_token: str,
    *,
    level: int,
    faction: str | None = None,
    spec: str | None = None,
    access: Access | None = None,
    weights: Mapping[str, float] | None = None,
    loaded: tuple[Any, Any, Any] | None = None,
) -> LevelingPicks:
    """Équipement de leveling de GearQuest Forever (décision 276) : pour chaque emplacement, le premier choix de
    l'addon dont la plage de niveaux contient `level`, pour le camp (et la spécialisation si donnée), avec ce que
    l'addon dit pour l'obtenir et son niveau requis ; avec `access` (essai CJ-6), seulement un objet obtenable à ce
    niveau (`obtainable`), les autres écartés avec leur raison ou mis à part ; avec `weights` (Mage, bloc 4c), le
    meilleur objet obtenable par nos poids (statistiques de Forever Guide) passe devant, le choix de GearQuest gardé
    dans `gearquest_choice`. Registre : I21"""
    from forever.pipeline.gear_sources import read_gearquest_facts, read_gearquest_picks, read_guide_gear

    if loaded is None:  # tranche de niveaux : fichiers lus une fois par l'appelant (`loaded`)
        loaded = (read_gearquest_picks(addons, class_token), read_gearquest_facts(addons, class_token), None)
    picks, facts, guide = loaded
    if guide is None and access is not None and access.all_dungeon_drops is not None:
        guide = read_guide_gear(addons)  # autre source : types d'objets et statistiques de Forever Guide
    stats = (guide if guide is not None else read_guide_gear(addons)) if weights else {}

    def score(item: int) -> float | None:
        """Score par nos poids ; None sans statistiques connues (objet à suffixe aléatoire : « - » chez Forever Guide)."""
        if not weights or item not in stats or not stats[item].stats:
            return None
        return _score(stats[item].stats, dict(weights))

    ranked: dict[str, list[Any]] = {}
    for p in picks:
        if not p.min_level <= level <= p.max_level:
            continue
        if faction and p.faction and p.faction.lower() != faction.lower():
            continue
        if spec and p.spec and p.spec.lower() != spec.lower():
            continue
        ranked.setdefault(p.slot, []).append(p)
    out: list[dict[str, Any]] = []
    set_aside: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for slot, candidates in ranked.items():
        seen: set[int] = set()
        oks: list[dict[str, Any]] = []
        for p in sorted(candidates, key=lambda p: p.rank):
            if p.item in seen:
                continue
            seen.add(p.item)
            fact = facts.get(p.item) or {}
            required = fact.get("reqLevel") if isinstance(fact.get("reqLevel"), int) else None
            if access is not None:
                verdict, reason, matched = obtainable_detail(fact, p.item, level, faction, access)
            elif required is not None and required > level:
                verdict, reason, matched = "out", f"niveau requis {required}", None
            else:
                verdict, reason, matched = "ok", "", None
            entry = {"slot": slot, "item": p.item, "name": fact.get("name"), "required_level": required}
            if verdict in ("aside", "out"):
                if not oks:  # seulement ce qui passait avant le premier choix obtenable
                    (set_aside if verdict == "aside" else excluded).append({**entry, "reason": reason})
                continue
            found = DROP_RANGE.search(str(fact.get("instructions") or ""))
            oks.append(
                {
                    **entry,
                    "quality": fact.get("quality") if isinstance(fact.get("quality"), int) else None,
                    "drop_levels": [int(found.group(1)), int(found.group(2))]
                    if found and fact.get("sourceType") == "world_drop"
                    else None,
                    "score": score(p.item),
                    "zone": fact.get("zone"),
                    "source": fact.get("sourceType"),
                    "how": fact.get("instructions"),
                    "access": reason or None,
                    "quest": fact.get("questName"),
                    "quest_detail": _quest_detail(matched),
                    "quest_min_level": matched.get("min_level") if matched else None,  # bloc 4d : fin de la route
                    "dungeon_detail": _dungeon_detail(access.dungeon_drops(p.item))
                    if access is not None
                    and access.dungeon_drops is not None
                    and fact.get("sourceType") in DUNGEON_SOURCES
                    else None,
                    "rank": p.rank,
                    "levels": [p.min_level, p.max_level],
                    "spec": p.spec,
                }
            )
            if not weights and (access is None or access.route_zones is None):
                break  # sans poids ni route : le premier choix obtenable de GearQuest suffit
        if not oks:
            continue
        if access is not None and access.route_zones is not None:  # décision 282 : ma route d'abord
            on_route = [
                o for o in oks if o.get("source") == "world_drop" or o.get("zone") in (None, *access.route_zones)
            ]
            if on_route:
                oks = on_route
            else:  # faute de mieux : détour signalé
                oks = [{**o, "detour": o.get("zone")} for o in oks]
        first = oks[0]
        scored = [o for o in oks if o["score"] is not None]
        best = max(scored, key=lambda o: o["score"]) if scored else first
        if best is not first and first["score"] is not None and best["score"] > first["score"]:
            keep = {k: first[k] for k in ("item", "name", "quality", "score", "rank")}
            out.append({**best, "gearquest_choice": keep})
        else:
            out.append(first)
    if access is not None and access.all_dungeon_drops is not None:
        out += _other_sources(addons, picks, guide, {o["slot"] for o in out}, level, access, weights)
    return LevelingPicks(out, set_aside, excluded)


def _other_sources(
    addons: Any,
    picks: Sequence[Any],
    guide: Mapping[int, Any] | None,
    filled: set[str],
    level: int,
    access: Access,
    weights: Mapping[str, float] | None,
) -> list[dict[str, Any]]:
    """Autre source quand GearQuest n'a rien d'obtenable pour un emplacement (fin du bloc 4c) : butin d'un donjon
    ouvert au niveau, d'un type d'objet (emplacement et sous-classe de Forever Guide) que GearQuest donne à la classe
    pour cet emplacement, niveau requis au plus `level` ; le meilleur par nos poids, sinon par qualité. Registre : I21"""
    from forever.pipeline.gear_sources import read_guide_gear

    stats = guide if guide is not None else read_guide_gear(addons)
    kinds: dict[str, set[tuple[int, int]]] = {}
    for p in picks:  # types d'objets que GearQuest donne à la classe, emplacement par emplacement
        g = stats.get(p.item)
        if g is not None:
            kinds.setdefault(p.slot, set()).add((g.inv_type, g.subclass))
    drops = list(access.all_dungeon_drops() if access.all_dungeon_drops else [])
    out = []
    for slot, allowed in kinds.items():
        if slot in filled:
            continue
        found = []
        for d in drops:
            g = stats.get(d.item)
            if g is None or (g.inv_type, g.subclass) not in allowed or g.req_level > level:
                continue
            if d.opens is None or d.opens > level:
                continue
            found.append((d, g))
        if not found:
            continue

        def rank(pair: tuple[DungeonDrop, Any]) -> tuple[float, int, int]:
            _drop, g = pair
            value = _score(g.stats, dict(weights)) if weights and g.stats else None
            return (value if value is not None else -1.0, g.quality, g.req_level)

        d, g = max(found, key=rank)
        same = [x for x, _ in found if x.item == d.item]
        out.append(
            {
                "slot": slot,
                "item": d.item,
                "name": d.name,
                "required_level": g.req_level,
                "quality": g.quality,
                "drop_levels": None,
                "score": _score(g.stats, dict(weights)) if weights and g.stats else None,
                "zone": d.dungeon,
                "source": "boss_drop",
                "how": None,
                "access": f"donjon ouvert au niveau {d.opens}",
                "quest": None,
                "quest_detail": None,
                "dungeon_detail": _dungeon_detail(same),
                "other_source": "butin de donjon (Forever Guide et livre des donjons), GearQuest n'ayant rien ici",
                "rank": None,
                "levels": None,
                "spec": None,
            }
        )
    return out


def is_upgrade(addons: Any, *, item: int, equipped: list[int], weights: dict[str, float]) -> dict[str, Any]:
    """« Est-ce une amélioration ? » (décision 276) : score de l'objet par `weights` (clés de Forever Guide) face à
    l'objet porté le plus faible de ses emplacements ; « non calculé » sans statistiques connues."""
    from forever.pipeline.gear_sources import read_guide_gear

    gear = read_guide_gear(addons)
    target = gear.get(item)
    if target is None or not weights:
        why = "statistiques inconnues de Forever Guide" if target is None else "aucun poids pour cette classe"
        return {
            "item": item,
            "verdict": "non calculé",
            "why": why,
            "slot": None,
            "score": None,
            "equipped": None,
            "equipped_score": None,
            "delta": None,
        }
    slots = INVTYPE_SLOTS.get(target.inv_type, ())
    score = _score(target.stats, weights) or 0.0
    rivals = [
        (other, _score(gear[other].stats, weights) or 0.0)
        for other in equipped
        if other in gear and set(INVTYPE_SLOTS.get(gear[other].inv_type, ())) & set(slots)
    ]
    worst: tuple[int | None, float] = (None, 0.0)  # emplacement libre
    if rivals and len(rivals) >= len(slots):
        worst = min(rivals, key=lambda r: r[1])
    delta = round(score - worst[1], 3)
    return {
        "item": item,
        "slot": slots[0] if slots else None,
        "score": score,
        "equipped": worst[0],
        "equipped_score": worst[1] if worst[0] is not None else None,
        "delta": delta,
        "verdict": "amélioration" if delta > 0 else "pas mieux",
    }


# --- rapport commun de la CLI et de l'outil MCP -------------------------------------------------------------------

DEFAULT_SPECS = {"MAGE": "frost-mage"}


def _addons_dir(deps: Deps) -> Any:
    from forever.errors import InvalidArgumentError

    if deps.wow_dir is None:
        raise InvalidArgumentError("Dossier du jeu inconnu (FOREVER_WOW_DIR).", "régler FOREVER_WOW_DIR")
    return deps.wow_dir / "Interface" / "AddOns"


MAGE_ROTATIONS = ("fire", "frost", "arcane")  # rotations dont le moteur calcule les poids (sort principal : MAIN)


def spell_label(rotation: str) -> str:
    """Nom du sort principal d'une rotation, tiré de sa clé (« fireball » -> « Fireball »)."""
    from forever.sim.encounter import MAIN

    return MAIN.get(rotation, rotation).replace("_", " ").title()


def learned_mage_weights(
    deps: Deps, *, level: int, race: str, preferred: str, talents: Mapping[str, int] | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """Poids du Mage au niveau `level` avec la rotation `preferred` si son sort principal est appris, sinon avec une
    autre rotation dont le sort est appris à ce niveau (Fireball au niveau 1) ; (None, None) si aucune ne se calcule
    (l'appelant garde alors l'ordre de GearQuest). Bug de l'écran Équipement du 2026-10-15 : « frostbolt n'est pas
    appris au niveau 1 ». Registre : I3"""
    for rotation in (preferred, *(r for r in MAGE_ROTATIONS if r != preferred)):
        try:
            return mage_weights(deps, level=level, race=race, rotation=rotation, talents=dict(talents or {})), rotation
        except Exception:  # noqa: BLE001, S112 : sort pas appris ou calcul impossible : rotation suivante, puis GearQuest
            continue
    return None, None


def talent_plan(deps: Deps, *, level: int, race: str, current: Mapping[str, int] | None) -> list[dict[str, Any]]:
    """Plan de talents du Mage jusqu'au niveau `level` : ordre de prise point par point du build de leveling calculé
    (le même que le bouton Talents), depuis mes talents actuels s'ils sont connus. Registre : I3"""
    from forever.build import build_report
    from forever.store import load_version

    key = (load_version(deps).data_sha, level, race, tuple(sorted((current or {}).items())))
    if key not in _PLANS:  # même plan pour les poids, la liste BiS et l'équipement d'une même demande
        report = build_report(deps, "leveling", level, race=race, current=current or None, sensitivity=False)
        _PLANS[key] = list(report.get("order") or [])
    return _PLANS[key]


_PLANS: dict[tuple[Any, ...], list[dict[str, Any]]] = {}


def mage_talents_for(
    deps: Deps, *, level: int, race: str, talents: Mapping[str, int] | None, talents_level: int | None
) -> tuple[dict[str, int], str, str | None]:
    """(talents, source, rotation du plan) pour les poids du Mage au niveau `level` : mes talents si `level` est mon
    niveau, sinon mon plan de talents, aucun avant le premier point ou si le plan ne se calcule pas. Registre : I3"""
    from forever.gamedata import build_game_data
    from forever.store import load_version

    if talents is not None and talents_level == level:
        return dict(talents), "actuels", None
    if level < build_game_data(load_version(deps)).constants.talents.first_level:
        return {}, "aucun", None
    try:
        chosen, rotation = talents_from_plan(talent_plan(deps, level=level, race=race, current=talents), level)
    except Exception:  # noqa: BLE001 : plan impossible : poids sans talents
        return {}, "aucun", None
    return chosen, ("plan" if chosen else "aucun"), rotation


def talents_from_plan(plan: list[dict[str, Any]], level: int) -> tuple[dict[str, int], str | None]:
    """Talents pris au niveau `level` selon le plan (points des niveaux au plus `level`) et la rotation du dernier
    point pris (None sans point)."""
    talents: dict[str, int] = {}
    rotation = None
    for step in plan:
        if isinstance(step.get("level"), int) and step["level"] <= level and step.get("talent"):
            talents[step["talent"]] = talents.get(step["talent"], 0) + 1
            rotation = (step.get("choice") or {}).get("rotation") or step.get("rotation") or rotation
    return talents, rotation


def _talent_names(deps: Deps) -> dict[str, str]:
    """Noms des talents tels qu'en jeu (données du client)."""
    from forever.gamedata import build_game_data
    from forever.store import load_version

    return {k: talent.name for k, talent in build_game_data(load_version(deps)).talents.items()}


def _talent_notes(used: Mapping[int, Mapping[str, Any]], names: Mapping[str, str]) -> list[str]:
    """Phrase de joueur : le build qui a servi aux poids (talents actuels, plan de talents, aucun)."""
    sources = {u["source"] for u in used.values()}
    notes = []
    if "actuels" in sources:
        lv = next(lv for lv, u in sorted(used.items()) if u["source"] == "actuels")
        notes.append(f"Talents des poids au niveau {lv} : tes talents actuels.")
    planned = [lv for lv, u in sorted(used.items()) if u["source"] == "plan"]
    if planned:
        last = used[planned[-1]]["talents"]
        build = ", ".join(f"{names.get(k, k)} {v}" for k, v in sorted(last.items(), key=lambda kv: -kv[1]))
        span = f"au niveau {planned[0]}" if len(planned) == 1 else f"des niveaux {planned[0]} à {planned[-1]}"
        notes.append(f"Talents des poids {span} : ton plan de talents (build calculé, au dernier niveau : {build}).")
    none = [lv for lv, u in sorted(used.items()) if u["source"] == "aucun"]
    if none:
        span = f"Au niveau {none[0]}" if len(none) == 1 else f"Aux niveaux {none[0]} à {none[-1]}"
        notes.append(f"{span}, aucun point de talent : poids sans talents.")
    return notes


def _rotation_notes(rotations: Mapping[int, str | None], wanted: Mapping[int, str] | str) -> list[str]:
    """Phrases de joueur : niveaux où le sort voulu (spécialisation, ou rotation du plan de talents) n'est pas encore
    appris, niveaux sans poids."""
    notes: list[str] = []
    runs: list[tuple[int, int, str | None, str]] = []
    for lv in sorted(rotations):
        rot = rotations[lv]
        want = wanted if isinstance(wanted, str) else wanted.get(lv, rot or "")
        if runs and runs[-1][2] == rot and runs[-1][3] == want and runs[-1][1] == lv - 1:
            runs[-1] = (runs[-1][0], lv, rot, want)
        else:
            runs.append((lv, lv, rot, want))
    for low, high, rot, want in runs:
        span = f"Au niveau {low}" if low == high else f"Aux niveaux {low} à {high}"
        if rot is None:
            notes.append(f"{span}, poids du Mage non calculés : objets dans l'ordre de GearQuest.")
        elif rot != want:
            notes.append(
                f"{span}, {spell_label(want)} n'est pas encore appris : nos poids y sont calculés avec "
                f"{spell_label(rot)}."
            )
    return notes


def _weights_for(
    deps: Deps,
    addons: Any,
    cls: str,
    *,
    level: int,
    race: str,
    spec: str,
    talents: Mapping[str, int] | None = None,
    talents_level: int | None = None,
) -> tuple[dict[str, float], str]:
    if cls == "MAGE":
        key = spec or DEFAULT_SPECS["MAGE"]
        pts, _source, _rotation = mage_talents_for(
            deps, level=level, race=race, talents=talents, talents_level=talents_level
        )
        report, used = learned_mage_weights(deps, level=level, race=race, preferred=key.split("-")[0], talents=pts)
        if report is not None:
            how = "" if used == key.split("-")[0] else f", avec {spell_label(str(used))}, seul sort appris"
            return mage_guide_weights(report, spec_key=key), f"moteur du Mage (niveau {level}{how})"
    if spec:  # plan « Sources d'abord » : échelle de la spécialisation, sinon poids par défaut de Naowh
        found = companion_spec_weights(addons, cls, spec, _class_trees(deps, cls))
        if found is not None and found[0]:
            return found[0], f"Forever Companion (échelle « {found[1]} » de la spécialisation, suppose)"
        naowh = naowh_weights(addons, spec)
        if naowh:
            from forever.pipeline.gear_sources import read_naowh_weights

            data = read_naowh_weights(addons)
            date = data.updated if data is not None and data.updated else "date inconnue"
            return naowh, f"Naowh Forever (poids par défaut de la spécialisation, niveau 60, {date}, suppose)"
    return companion_weights(addons, cls), "Forever Companion (échelle de la classe, suppose)"


def _class_trees(deps: Deps, class_token: str) -> list[str]:
    """Noms des arbres de talents d'une classe, dans l'ordre du client (`classes.json`) ; vide si la classe manque."""
    from forever.store import load_version

    classes = load_version(deps).read_json("classes.json")["classes"]
    entry = next((v for k, v in classes.items() if k.upper() == class_token.upper()), None)
    return [str(t.get("name") or "") for t in entry["trees"]] if entry else []


def _provenance(deps: Deps, assumptions: list[str]) -> Any:
    from forever.provenance import local_provenance

    return local_provenance(deps, certainty="suppose", assumptions=assumptions)


def gear_report(
    deps: Deps,
    action: str,
    *,
    class_name: str = "Mage",
    level: int = 60,
    race: str = "Orc",
    spec: str | None = None,
    faction: str | None = None,
    item: int | None = None,
    equipped: list[int] | None = None,
    name: str | None = None,
    professions: list[str] | None = None,
    to_level: int | None = None,
    talents: Mapping[str, int] | None = None,
    talents_level: int | None = None,
) -> dict[str, Any]:
    """Rapport de `forever gear` et de `forever_gear` : `weights` (poids du Mage, lignes NFSW1 et Pawn v1), `bis`
    (liste personnelle et `!NBIS1!`), `leveling` (GearQuest Forever), `upgrade` (« est-ce une amélioration ? »)."""
    from forever.errors import InvalidArgumentError

    cls = class_name.strip().upper()
    addons = _addons_dir(deps)
    if action == "weights":
        if cls != "MAGE":
            raise InvalidArgumentError(
                "Poids calculés pour le Mage seulement (autres classes : échelle de Forever Companion).",
                "donner --class Mage, ou forever gear bis, qui classe avec l'échelle de Forever Companion",
            )
        key = spec or DEFAULT_SPECS["MAGE"]
        pts, source, _rotation = mage_talents_for(
            deps, level=level, race=race, talents=talents, talents_level=talents_level
        )
        found, used = learned_mage_weights(deps, level=level, race=race, preferred=key.split("-")[0], talents=pts)
        if found is None:
            raise InvalidArgumentError(
                f"Poids du Mage non calculés au niveau {level} : aucun sort de dégâts calculé n'y est appris.",
                "choisir un niveau plus haut",
            )
        label = name or f"Forever · Mage · {level}"
        used_talents = {level: {"source": source, "talents": pts}}
        notes = [*_rotation_notes({level: used}, key.split("-")[0]), *_talent_notes(used_talents, _talent_names(deps))]
        return {
            **found,
            "naowh": naowh_weight_line(found, spec=key),
            "pawn": pawn_line(found, label=label),
            "weights_notes": notes,
        }
    if action == "bis":
        key = spec or DEFAULT_SPECS.get(cls) or ""
        if not key:
            raise InvalidArgumentError("Spécialisation requise (clé de Naowh, ex. fury-warrior).", "donner --spec")
        weights, source = _weights_for(
            deps, addons, cls, level=level, race=race, spec=key, talents=talents, talents_level=talents_level
        )
        out = personal_bis(addons, spec_key=key, weights=weights, name=name or f"Forever · {key}", faction=faction)
        if cls == "MAGE":  # CJ1, bloc 5 : poids à coller aussi, depuis la même demande
            pts, _src, _rot = mage_talents_for(
                deps, level=level, race=race, talents=talents, talents_level=talents_level
            )
            report, _used = learned_mage_weights(deps, level=level, race=race, preferred=key.split("-")[0], talents=pts)
            if report is not None:
                out["naowh"] = naowh_weight_line(report, spec=key)
                out["pawn"] = pawn_line(report, label=f"{name or 'Forever · Mage'} · poids")
        assumptions = [
            (
                f"listes BiS de Naowh Forever et de Forever Companion lues en local, classées par les poids : {source} ; "
                "statistiques des objets de Forever Guide (objets inconnus après les objets chiffrés)"
            ),
            f"lieux de butin de Naowh Forever ; {CAMP_NOTE}",
        ]
        return {**out, "weights": weights, "weights_source": source, "provenance": _provenance(deps, assumptions)}
    if action == "leveling":
        top = to_level if to_level is not None and to_level > level else level
        access = level_access(
            deps, professions or [], class_name=cls.capitalize(), race=race, faction=faction, below=top + 1
        )
        last = to_level if to_level is not None and to_level > level else level
        from forever.pipeline.gear_sources import read_gearquest_facts, read_gearquest_picks, read_guide_gear

        loaded = (
            read_gearquest_picks(addons, cls),
            read_gearquest_facts(addons, cls),
            read_guide_gear(addons) if cls == "MAGE" else None,
        )

        key = spec if spec and "-" in spec else DEFAULT_SPECS["MAGE"]
        preferred = key.split("-")[0]
        rotations: dict[int, str | None] = {}
        wanted_at: dict[int, str] = {}
        talents_used: dict[int, dict[str, Any]] = {}
        gaps: list[dict[str, Any]] = []
        plan_cache: list[list[dict[str, Any]]] = []
        plan_errors: list[str] = []

        def talents_at(lv: int) -> tuple[dict[str, int], str, str | None]:
            """(talents, source, rotation du plan) : mes talents à mon niveau, sinon mon plan de talents (calculé une
            fois jusqu'au haut de la tranche), aucun avant le premier point."""
            if talents is not None and talents_level == lv:
                return dict(talents), "actuels", None
            if not plan_cache:
                from forever.gamedata import build_game_data
                from forever.store import load_version

                first_point = build_game_data(load_version(deps)).constants.talents.first_level
                if last < first_point:  # aucun point dans la tranche : pas de plan à calculer
                    plan_cache.append([])
                else:
                    try:  # un seul plan, jusqu'au haut de la tranche : son ordre donne les talents de chaque niveau
                        plan_cache.append(talent_plan(deps, level=last, race=race, current=talents))
                    except Exception as exc:  # noqa: BLE001 : plan impossible : poids sans talents, dit au joueur
                        plan_errors.append(f"{type(exc).__name__}: {exc}")
                        plan_cache.append([])
            chosen, rotation = talents_from_plan(plan_cache[0], lv)
            return chosen, ("plan" if chosen else "aucun"), rotation

        def at(lv: int) -> tuple[LevelingPicks, dict[str, Any], dict[str, float] | None]:
            """Choix obtenables au niveau `lv` ; Mage : nos poids à ce niveau (sort réellement appris) et leurs lignes
            à copier ; sans poids, ordre de GearQuest."""
            found: dict[str, Any] = {}
            weights_at: dict[str, float] | None = None
            if cls == "MAGE":  # bloc 4c : Mage reclassé par nos poids ; autres classes : ordre de GearQuest
                pts, source, plan_rotation = talents_at(lv)
                wanted = preferred if spec and "-" in spec else (plan_rotation or preferred)
                report, used = learned_mage_weights(deps, level=lv, race=race, preferred=wanted, talents=pts)
                if report is None and pts:  # talents refusés à ce niveau : poids sans talents plutôt que rien
                    report, used = learned_mage_weights(deps, level=lv, race=race, preferred=wanted)
                    pts, source = {}, "aucun"
                rotations[lv] = used
                wanted_at[lv] = wanted
                talents_used[lv] = {"source": source, "talents": pts, "rotation": used}
                if report is not None:
                    weights_at = mage_guide_weights(report, spec_key=key)
                    label = name or f"Forever · Mage · niveau {lv}"
                    found = {"naowh": naowh_weight_line(report, spec=key), "pawn": pawn_line(report, label=label)}
            gq_spec = None if cls == "MAGE" else (spec.split("-")[0] if spec else None)  # spécialisation de GearQuest
            chosen = leveling_gear(
                addons, cls, level=lv, faction=faction, spec=gq_spec, access=access, weights=weights_at, loaded=loaded,
            )  # fmt: skip
            return chosen, found, weights_at

        def safe_at(lv: int) -> tuple[LevelingPicks, dict[str, Any], dict[str, float] | None] | None:
            """Un niveau en échec ne fait jamais tomber la tranche : il est noté (`gaps`) et sauté."""
            try:
                return at(lv)
            except Exception as exc:  # noqa: BLE001 : détail technique gardé dans `gaps`, jamais montré au joueur
                gaps.append({"level": lv, "error": f"{type(exc).__name__}: {exc}"})
                return None

        first = safe_at(level)
        picks, lines, level_weights = first if first is not None else (LevelingPicks([], [], []), {}, None)
        segments: list[dict[str, Any]] = []
        set_aside = list(picks.set_aside)
        excluded = list(picks.excluded)
        if last > level:  # bloc 4c : tranche de niveaux, un segment par palier où l'objet visé change
            open_: dict[str, dict[str, Any]] = {}
            for lv in range(level, last + 1):
                got = (picks, lines, level_weights) if lv == level else safe_at(lv)
                if got is None or (lv == level and first is None):
                    for slot in list(open_):  # niveau manquant : les segments ouverts se ferment avant lui
                        segments.append(open_.pop(slot))
                    continue
                chosen, found, _ = got
                if lv == last:
                    lines = found
                seen_items = {a["item"] for a in set_aside}
                set_aside += [a for a in chosen.set_aside if a["item"] not in seen_items]
                seen_items = {e["item"] for e in excluded}
                excluded += [e for e in chosen.excluded if e["item"] not in seen_items]
                now = {c["slot"]: c for c in chosen}
                for slot in list(open_):
                    if slot not in now or now[slot]["item"] != open_[slot]["item"]:
                        segments.append(open_.pop(slot))
                for slot, c in now.items():
                    if slot in open_:
                        open_[slot]["to"] = lv
                    else:
                        open_[slot] = {**c, "from": lv, "to": lv}
            segments += list(open_.values())
        assumptions = [
            "choix de leveling de GearQuest Forever lus en local (premier choix obtenable de chaque emplacement)",
            (
                f"obtenable au niveau {level} : niveau requis au plus {level}, quête du camp prise à ce niveau et pas "
                "rouge (même seuil que les routes), butin dont la plage commence à ce niveau, donjon ouvert à ce "
                "niveau, objet de métier seulement avec le métier ; source ou niveau inconnus : mis à part"
            ),
            "zone de la quête non vérifiée au-delà de son camp et de son niveau",
            (
                f"Mage : objets obtenables reclassés par nos poids (moteur du Mage, niveau {level}) sur les statistiques "
                "de Forever Guide ; choix de GearQuest gardé quand il diffère"
                if level_weights
                else "ordre de GearQuest Forever (poids calculés pour le Mage seulement)"
            ),
        ]
        if plan_errors:
            gaps.append({"level": last, "error": f"plan de talents : {plan_errors[0]}", "plan": True})
        notes = [*_rotation_notes(rotations, wanted_at), *_talent_notes(talents_used, _talent_names(deps))] if cls == "MAGE" else [
            "Poids calculés pour le Mage seulement : objets dans l'ordre de GearQuest."
        ]  # fmt: skip
        for gap in gaps:
            if gap.get("plan"):
                notes.append("Plan de talents non calculé : poids sans talents (problème noté de mon côté).")
            else:
                notes.append(f"Niveau {gap['level']} : équipement non calculé (problème de données noté de mon côté).")
        return {
            **lines,
            "rotations": {str(lv): rot for lv, rot in sorted(rotations.items())},
            "talents_used": {
                str(lv): ({"source": u["source"], "talents": u["talents"]} if u["source"] == "actuels" else dict(u))
                for lv, u in sorted(talents_used.items())
            },
            "weights_notes": notes,
            "gaps": gaps,
            "class": cls,
            "level": level,
            "to_level": last,
            "picks": list(picks),
            "segments": segments,
            "set_aside": set_aside,
            "excluded": excluded,
            "professions": sorted(access.professions),
            "provenance": _provenance(deps, assumptions),
        }
    if action == "upgrade":
        if item is None:
            raise InvalidArgumentError("Objet requis.", "donner l'identifiant de l'objet (lien Maj+clic)")
        weights, source = _weights_for(deps, addons, cls, level=level, race=race, spec=spec or "")
        out = is_upgrade(addons, item=item, equipped=list(equipped or []), weights=weights)
        assumptions = [
            f"poids : {source} ; statistiques des objets de Forever Guide ; Naowh Score : le leur, non repris"
        ]
        return {**out, "weights_source": source, "provenance": _provenance(deps, assumptions)}
    if action == "route":  # CJ1, bloc 4b : route d'équipement des objets de la liste BiS personnelle
        from forever.gear_route import CHANCE, gear_route

        key = spec or DEFAULT_SPECS.get(cls) or ""
        if not key:
            raise InvalidArgumentError("Spécialisation requise (clé de Naowh, ex. fury-warrior).", "donner --spec")
        weights, source = _weights_for(deps, addons, cls, level=level, race=race, spec=key)
        bis = personal_bis(addons, spec_key=key, weights=weights, name=name or f"Forever · {key}", faction=faction)
        route = gear_route(deps, addons, bis)
        assumptions = [
            (
                f"objets de la liste BiS personnelle ({source}) ; origines : boss et taux de DJ1 (Naowh d'abord), "
                "quêtes du livre (récompenses de Forever Guide et de GearQuest), sinon lieu de Naowh Forever"
            ),
            (
                f"passages d'un donjon : espérance pour obtenir tous ses objets voulus et nombre pour {int(CHANCE * 10)} "
                "chances sur 10, chaque objet tombant indépendamment à son taux ; butin partagé en groupe non compté"
            ),
            CAMP_NOTE,
        ]
        return {"spec": key, "export": bis["export"], **route, "provenance": _provenance(deps, assumptions)}
    raise InvalidArgumentError(f"Action inconnue : {action}.", "weights, bis, leveling, upgrade ou route")
