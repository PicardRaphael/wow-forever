"""Équipement (CJ1, bloc 4, T10a revue, décisions 272 et 276) : poids des statistiques du Mage calculés par notre
moteur et exportés vers Naowh Forever (`NFSW1:`) et Forever Companion (Pawn v1) ; les listes BiS, le leveling et
« est-ce une amélioration ? » s'appuient sur les addons qui calculent déjà (`forever/pipeline/gear_sources.py`)."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from forever.config import Deps

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
class Access:
    """Ce qu'il faut savoir pour dire si un objet s'obtient à un niveau (essai CJ-6 du 2026-10-15) : quêtes du livre
    par nom (`level`, `min_level`, `faction`), niveau d'ouverture du donjon qui lâche un objet, écart d'une quête
    rouge (`leveling.quest_band.red_min_diff`, registre I7), métiers appris du personnage (noms anglais, minuscules)."""

    quests: Callable[[str], Sequence[Mapping[str, Any]]]
    dungeon_level: Callable[[int], int | None]
    red_min_diff: int
    professions: frozenset[str] = frozenset()


class LevelingPicks(list[dict[str, Any]]):
    """Choix retenus par emplacement, plus les objets mis à part (source inconnue) et écartés (raison)."""

    def __init__(self, picks: list[dict[str, Any]], set_aside: list[dict[str, Any]], excluded: list[dict[str, Any]]):
        super().__init__(picks)
        self.set_aside = set_aside
        self.excluded = excluded


DROP_RANGE = re.compile(r"level (\d+)\s*-\s*(\d+)")  # « World drop around level 11-16. » (GearQuest Forever)
QUEST_SOURCES = ("quest_reward", "seasonal_quest")
DUNGEON_SOURCES = ("boss_drop", "raid_trash")


def obtainable(fact: Mapping[str, Any], item: int, level: int, faction: str | None, access: Access) -> tuple[str, str]:
    """(« ok » | « out » | « aside », raison) : l'objet s'obtient-il au niveau `level` ? Niveau requis au plus
    `level` ; quête du camp prise à ce niveau et pas rouge ; butin dont la plage commence au plus à `level` ; donjon
    ouvert à ce niveau ; métier appris ; sinon mis à part (source ou niveau inconnus). Registre : I21"""
    required = fact.get("reqLevel")
    if isinstance(required, int) and required > level:
        return "out", f"niveau requis {required}"
    kind = fact.get("sourceType")
    if kind in QUEST_SOURCES:
        name = str(fact.get("questName") or "")
        if not name:
            return "aside", "quête sans nom chez GearQuest"
        quests = [q for q in access.quests(name) if q.get("faction") in (None, "both", (faction or "").lower())]
        if not quests:
            mine = access.quests(name)
            return ("out", f"quête « {name} » de l'autre camp") if mine else ("aside", f"quête « {name} » inconnue")
        known = [q for q in quests if isinstance(q.get("level"), int)]
        if not known:
            return "aside", f"quête « {name} » sans niveau connu"
        for q in known:
            low = int(q["min_level"]) if isinstance(q.get("min_level"), int) else 1
            if low <= level and q["level"] - level < access.red_min_diff:
                return "ok", f"quête « {name} », niveau {q['level']}"
        q = min(known, key=lambda q: q["level"])
        low = int(q["min_level"]) if isinstance(q.get("min_level"), int) else 1
        if low > level:
            return "out", f"quête « {name} » prise au niveau {low}"
        return "out", f"quête « {name} » de niveau {q['level']}, rouge au niveau {level}"
    if kind == "profession":
        craft = str(fact.get("profession") or "")
        if craft.lower() in access.professions:
            return "ok", f"métier {craft}"
        return "out", f"métier {craft or 'inconnu'} non appris"
    if kind in DUNGEON_SOURCES:
        opens = access.dungeon_level(item)
        if opens is None:
            return "aside", "donjon et niveau inconnus"
        if opens > level:
            return "out", f"donjon ouvert au niveau {opens}"
        return "ok", f"donjon ouvert au niveau {opens}"
    if kind == "vendor":
        return "ok", "marchand"
    found = DROP_RANGE.search(str(fact.get("instructions") or ""))
    if found:
        low = int(found.group(1))
        if low > level:
            return "out", f"butin des niveaux {found.group(1)} à {found.group(2)}"
        return "ok", f"butin des niveaux {found.group(1)} à {found.group(2)}"
    if kind == "unsourced" or not kind:
        return "aside", "source inconnue de GearQuest"
    return "aside", f"source « {kind} » sans niveau connu"


def level_access(deps: Deps, professions: list[str]) -> Access:
    """`Access` lu dans nos données : quêtes du livre par nom, donjons de DJ1 (niveau bas de leur plage), écart
    d'une quête rouge (`mechanics.json`), métiers donnés (noms anglais). Registre : I21"""
    from forever.dungeons import build_dungeons, where_item
    from forever.gamedata import load_game_data
    from forever.quests import build_quests, value

    book = build_quests(deps)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for q in book.quests.values():
        quest_name = value(q, "name")
        if isinstance(quest_name, str):
            by_name.setdefault(quest_name, []).append(
                {"level": value(q, "level"), "min_level": value(q, "min_level"), "faction": value(q, "faction")}
            )
    dungeons = build_dungeons(deps)

    def dungeon_level(item: int) -> int | None:
        lows = []
        for found in where_item(dungeons, item):
            levels = ((dungeons.dungeons[found["dungeon"]].get("fields") or {}).get("levels") or {}).get("value")
            if isinstance(levels, dict) and isinstance(levels.get("min"), int):
                lows.append(levels["min"])
        return min(lows) if lows else None

    red = load_game_data(deps).leveling.quest_band.red_min_diff
    return Access(
        quests=lambda name: by_name.get(name, []),
        dungeon_level=dungeon_level,
        red_min_diff=int(red),
        professions=frozenset(p.strip().lower() for p in professions if p.strip()),
    )


def leveling_gear(
    addons: Any,
    class_token: str,
    *,
    level: int,
    faction: str | None = None,
    spec: str | None = None,
    access: Access | None = None,
) -> LevelingPicks:
    """Équipement de leveling de GearQuest Forever (décision 276) : pour chaque emplacement, le premier choix de
    l'addon dont la plage de niveaux contient `level`, pour le camp (et la spécialisation si donnée), avec ce que
    l'addon dit pour l'obtenir et son niveau requis ; avec `access` (essai CJ-6), seulement un objet obtenable à ce
    niveau (`obtainable`), les autres écartés avec leur raison ou mis à part. Registre : I21"""
    from forever.pipeline.gear_sources import read_gearquest_facts, read_gearquest_picks

    picks = read_gearquest_picks(addons, class_token)
    facts = read_gearquest_facts(addons, class_token)
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
        for p in sorted(candidates, key=lambda p: p.rank):
            if p.item in seen:
                continue
            seen.add(p.item)
            fact = facts.get(p.item) or {}
            required = fact.get("reqLevel") if isinstance(fact.get("reqLevel"), int) else None
            if access is not None:
                verdict, reason = obtainable(fact, p.item, level, faction, access)
            elif required is not None and required > level:
                verdict, reason = "out", f"niveau requis {required}"
            else:
                verdict, reason = "ok", ""
            entry = {"slot": slot, "item": p.item, "name": fact.get("name"), "required_level": required}
            if verdict == "aside":
                set_aside.append({**entry, "reason": reason})
                continue
            if verdict == "out":
                excluded.append({**entry, "reason": reason})
                continue
            out.append(
                {
                    **entry,
                    "zone": fact.get("zone"),
                    "source": fact.get("sourceType"),
                    "how": fact.get("instructions"),
                    "access": reason or None,
                    "rank": p.rank,
                    "levels": [p.min_level, p.max_level],
                    "spec": p.spec,
                }
            )
            break
    return LevelingPicks(out, set_aside, excluded)


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


def _weights_for(
    deps: Deps, addons: Any, cls: str, *, level: int, race: str, spec: str
) -> tuple[dict[str, float], str]:
    if cls == "MAGE":
        key = spec or DEFAULT_SPECS["MAGE"]
        report = mage_weights(deps, level=level, race=race, rotation=key.split("-")[0])
        return mage_guide_weights(report, spec_key=key), f"moteur du Mage (niveau {level})"
    return companion_weights(addons, cls), "Forever Companion (échelle de la classe, suppose)"


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
        report = mage_weights(deps, level=level, race=race, rotation=key.split("-")[0])
        label = name or f"Forever · Mage · {level}"
        return {**report, "naowh": naowh_weight_line(report, spec=key), "pawn": pawn_line(report, label=label)}
    if action == "bis":
        key = spec or DEFAULT_SPECS.get(cls) or ""
        if not key:
            raise InvalidArgumentError("Spécialisation requise (clé de Naowh, ex. fury-warrior).", "donner --spec")
        weights, source = _weights_for(deps, addons, cls, level=level, race=race, spec=key)
        out = personal_bis(addons, spec_key=key, weights=weights, name=name or f"Forever · {key}", faction=faction)
        if cls == "MAGE":  # CJ1, bloc 5 : poids à coller aussi, depuis la même demande
            report = mage_weights(deps, level=level, race=race, rotation=key.split("-")[0])
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
        access = level_access(deps, professions or [])
        picks = leveling_gear(addons, cls, level=level, faction=faction, spec=spec, access=access)
        assumptions = [
            "choix de leveling de GearQuest Forever lus en local (premier choix obtenable de chaque emplacement)",
            (
                f"obtenable au niveau {level} : niveau requis au plus {level}, quête du camp prise à ce niveau et pas "
                "rouge (même seuil que les routes), butin dont la plage commence à ce niveau, donjon ouvert à ce "
                "niveau, objet de métier seulement avec le métier ; source ou niveau inconnus : mis à part"
            ),
            "zone de la quête non vérifiée au-delà de son camp et de son niveau",
        ]
        return {
            "class": cls,
            "level": level,
            "picks": list(picks),
            "set_aside": picks.set_aside,
            "excluded": picks.excluded,
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
