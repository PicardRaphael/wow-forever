"""Objectifs de leveling (T04d, bloc F) : XP par heure par zone et par donjon, pour toutes les classes.

Pour un personnage (classe, camp, niveau, repos), chaque zone et chaque donjon accessibles :

- zone : XP des quêtes disponibles non grises (modèle d'XP, `forever/engine/xp.py`) + XP des monstres de leurs
  objectifs, sur le temps total (monstres × temps par monstre + surcoût par quête) ;
- donjon, **premier passage avec quêtes** : XP des monstres (bonus de donjon, élite, groupe) + XP de toutes ses
  quêtes accessibles (prérequis manquants listés), sur le temps total (prise des quêtes, trajet, donjon, retour) ;
- donjon, **passages suivants** : XP des monstres seule, sur la durée du donjon.

Temps par monstre : moteur pour le Mage (simulateur de leveling, analytique), sinon mesuré ou estimé
(`forever/kill_time.py`) ; la source est rendue. Hypothèses de temps (`leveling.objectives` de `mechanics.json`,
`suppose`) : le classement peut en dépendre plus que de l'XP, la sortie le dit. La phrase de conseil est construite
ici à partir des chiffres de l'objectif, jamais par un modèle de langage. Aucun chiffre de jeu ici."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.engine.leveling import gray_level
from forever.engine.xp import ActiveAura, Party, QuestXpInput, mob_kill_xp, quest_xp
from forever.errors import InvalidArgumentError
from forever.kill_time import kill_params, kill_time, load_kill_times
from forever.pipeline.questie import CLASS_MASKS
from forever.quests import QuestBook, build_quests, value

KINDS = ("zone", "dungeon_first", "dungeon_repeat")
SECONDS_PER_MINUTE = 60.0  # conversions d'unité
SECONDS_PER_HOUR = 3600.0
MAGE = "mage"
ENGINE_N = 200  # combats du Monte Carlo du Mage pour son temps par monstre (l'analytique est retenue)
OBJECTIVES_KEY = "leveling.objectives"


def _params(values: dict[str, Any]) -> dict[str, float]:
    try:
        return {k: float(v) for k, v in values[OBJECTIVES_KEY]["value"].items()}
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidArgumentError(
            f"mechanics.json : {OBJECTIVES_KEY} illisible ({exc}).", "installer une version de données de T04d"
        ) from exc


def _engine_kill_time(deps: Deps, level: int, race: str | None) -> dict[str, Any]:
    """Temps par monstre du Mage : total de l'analytique du simulateur (combat, repos, course).

    Registre : I6, I14"""
    from forever.leveling import simulate_leveling

    report = simulate_leveling(deps, level, race=race, n=ENGINE_N)
    seconds = float(report["analytic"]["total"])
    return {
        "source": "engine",
        "seconds": seconds,
        "low": seconds,
        "high": seconds,
        "samples": 0,
        "certainty": report["provenance"]["certainty"],
        "method": "simulateur de leveling du Mage (analytique, sans talent, rotation givre)",
        "scope": "total",
        "combat_s": float(report["analytic"]["combat"]),
    }


def _eligible(quest: dict[str, Any], cls: str, faction: str | None, level: int, gray: int, red: int) -> bool:
    """Quête prise en compte : camp et classe permis, niveau requis atteint, ni grise ni rouge (couleurs de
    `leveling.quest_band`), XP connue.

    Registre : I7, I14"""
    side = value(quest, "faction")
    if faction is not None and side not in (faction, "both", None):
        return False
    classes = value(quest, "classes")
    if isinstance(classes, int) and classes and cls in CLASS_MASKS and not classes & CLASS_MASKS[cls]:
        return False
    lvl, min_level = value(quest, "level"), value(quest, "min_level")
    if not isinstance(lvl, int) or not isinstance(min_level, int) or min_level > level or lvl <= gray:
        return False
    if lvl >= level + red:
        return False
    return isinstance(value(quest, "xp"), int | float)


def _quest_xp(gd: Any, level: int, quest: dict[str, Any]) -> float:
    xp_field = quest["fields"]["xp"]
    return quest_xp(
        gd,
        level,
        QuestXpInput(value(quest, "level"), float(xp_field["value"]), xp_field["source"], xp_field["certainty"]),
    ).xp


def _objective(
    kind: str, name: str, quests: int, quest_xp_total: float, kills: float, kill_xp: float, seconds: float, **extra: Any
) -> dict[str, Any]:
    xp = quest_xp_total + kills * kill_xp
    return {
        "kind": kind,
        "name": name,
        "quests": quests,
        "quest_xp": quest_xp_total,
        "kills": kills,
        "kill_xp": kill_xp,
        "xp": xp,
        "seconds": seconds,
        "minutes": seconds / SECONDS_PER_MINUTE,
        "xp_h": xp / (seconds / SECONDS_PER_HOUR) if seconds > 0 else 0.0,
        **extra,
    }


def _advice(best: dict[str, Any] | None) -> str:
    if best is None:
        return "aucun objectif chiffré : aucune quête accessible n'a d'XP connue dans les sources lues"
    if best["kind"] == "dungeon_first":
        return (
            f"fais {best['name']} une fois avec ses quêtes : environ {round(best['xp'])} XP en "
            f"{round(best['minutes'])} minutes (environ {round(best['xp_h'])} XP par heure)"
        )
    if best["kind"] == "dungeon_repeat":
        return f"refais {best['name']} : environ {round(best['xp_h'])} XP par heure"
    return f"continue dehors : {best['name']} (environ {round(best['xp_h'])} XP par heure)"


def objectives(
    deps: Deps,
    *,
    class_name: str,
    level: int,
    faction: str | None = None,
    race: str | None = None,
    rested: float = 0.0,
    party: int = 1,
    dungeon_party: int | None = None,
    limit: int = 5,
    wow_dir: Path | None = None,
    sleeping_bag: int | None = None,
    food: bool = False,
    legacy_rested_rank: int | None = None,
    hours: float | None = None,
    auras: Sequence[ActiveAura] = (),
) -> dict[str, Any]:
    """Objectifs classés par XP par heure, temps par monstre et sa source, conseil, provenance.

    Registre : I14"""
    from forever.freshness import freshness_for_version
    from forever.gamedata import MECHANICS_FILE, build_game_data
    from forever.leveling import check_level, level_cap
    from forever.provenance import make_provenance
    from forever.store import load_version

    cls = class_name.strip().lower()
    if cls not in CLASS_MASKS:
        raise InvalidArgumentError(f"Classe inconnue : {class_name}.", f"choisir parmi : {', '.join(CLASS_MASKS)}")
    if faction is not None and faction not in ("horde", "alliance"):
        raise InvalidArgumentError(f"Camp inconnu : {faction}.", "choisir horde ou alliance")
    data = load_version(deps)
    check_level(level, level_cap(data))
    gd = build_game_data(data)
    values = data.read_json(MECHANICS_FILE)["values"]
    p = _params(values)
    group = int(dungeon_party or p["dungeon_party"])
    # même règle pour toutes les classes : temps mesuré sur les relevés du joueur d'abord ; à défaut, moteur
    # (Mage) ou estimation ; le temps du moteur du Mage reste rendu à côté d'une mesure, pour comparaison
    measured = kill_time(kill_params(values), class_name=cls, level=level, measures=load_kill_times(deps))
    kt = {**measured._asdict()}
    if cls == MAGE:
        engine = _engine_kill_time(deps, level, race)
        if measured.source == "measured":
            kt["engine"] = engine
        else:
            kt = engine
    book: QuestBook = build_quests(deps, wow_dir=wow_dir)
    gray = gray_level(gd, level)
    red = gd.leveling.quest_band.red_min_diff
    available = [q for q in book.quests.values() if _eligible(q, cls, faction, level, gray, red)]
    solo = Party(tuple([level] * party)) if party > 1 else None
    zones: dict[str, list[dict[str, Any]]] = {}
    dungeons: dict[str, list[dict[str, Any]]] = {}
    for quest in available:
        dungeon = value(quest, "dungeon")
        if dungeon:
            dungeons.setdefault(dungeon, []).append(quest)
            continue
        zone = book.zone_names.get(value(quest, "map")) if isinstance(value(quest, "map"), int) else None
        if zone:
            zones.setdefault(zone, []).append(quest)
    rows: list[dict[str, Any]] = []
    for zone, quests in zones.items():
        quest_total = sum(_quest_xp(gd, level, q) for q in quests)
        kills = p["kills_per_quest"] * len(quests)
        mob_level = round(statistics.median(value(q, "level") for q in quests))
        kill_xp = mob_kill_xp(gd, level, mob_level, party=solo).xp
        seconds = kills * kt["seconds"] + p["quest_overhead_s"] * len(quests)
        rows.append(_objective("zone", zone, len(quests), quest_total, kills, kill_xp, seconds, mob_level=mob_level))
    out_dungeons = []
    for name, quests in sorted(dungeons.items()):
        ids = {q["id"] for q in quests}
        missing = sorted(
            {
                pre
                for q in quests
                for pre in [*(value(q, "prereq_all") or []), *(value(q, "prereq_any") or [])]
                if pre not in ids
            }
        )
        quest_total = sum(_quest_xp(gd, level, q) for q in quests)
        mob_level = max(level, round(statistics.median(value(q, "level") for q in quests)))
        kill_xp = mob_kill_xp(gd, level, mob_level, elite=True, dungeon=True, party=Party(tuple([level] * group))).xp
        kills = p["dungeon_kills"]
        inside = kills * kt["seconds"] / p["dungeon_group_speedup"]
        first = _objective(
            "dungeon_first",
            name,
            len(quests),
            quest_total,
            kills,
            kill_xp,
            inside + 2 * p["dungeon_travel_s"] + p["quest_overhead_s"] * len(quests),
            missing_prereqs=missing,
            mob_level=mob_level,
        )
        repeat = _objective("dungeon_repeat", name, 0, 0.0, kills, kill_xp, inside, mob_level=mob_level)
        out_dungeons.append({"name": name, "first_pass": first, "repeat": repeat})
        rows += [first, repeat]
    rows.sort(key=lambda r: -r["xp_h"])
    best = rows[0] if rows else None
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty="suppose",
        assumptions=[
            *fresh["assumptions"],
            f"temps par monstre : {kt['source']} ({kt['method']}, {kt['certainty']}) ; durée : "
            + ("combat, récupération et déplacement" if kt.get("scope") == "total" else "combat seul (sous-estime)"),
            f"hypothèses de temps {OBJECTIVES_KEY} (suppose) : le classement peut en dépendre plus que de l'XP",
            (
                "XP des quêtes : client si la quête a été vue, sinon addon ou Questie (suppose) ; monstres des "
                "objectifs au niveau médian des quêtes"
            ),
            *(["repos non appliqué au classement (réservoir donné : rested)"] if rested else []),
            *book.notes[:1],
        ],
    )
    return {
        "class": cls,
        "level": level,
        "faction": faction,
        "race": race,
        "kill_time": kt,
        "zones": sorted((r for r in rows if r["kind"] == "zone"), key=lambda r: -r["xp_h"])[:limit],
        "dungeons": out_dungeons,
        "best": best,
        "advice": _advice(best),
        "provenance": provenance,
    }
