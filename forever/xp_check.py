"""Vérification passive du modèle d'XP sur les relevés du joueur (T04d, bloc G, décision 247).

`forever xp check` compare, sans rien écrire, le modèle d'XP (`forever/engine/xp.py`) aux gains relevés par
ForeverLogger : gains de monstre (niveau du monstre lu sur la cible relevée, sinon niveau fixe de la base de Questie
quand le nom désigne un seul PNJ de niveau fixe ; écartés et comptés sinon) et quêtes rendues (`xpReward` comparé à
l'XP du client pour une quête vue). Par règle : nombre de cas, écart médian, cas hors tolérance et verdict
(`vérifié`, `écart`, `à vérifier`) ; ce qui reste à vérifier renvoie à sa question ouverte. Jamais d'échec faute de
relevé : sans relevé, tout est « à vérifier ». Tolérance et cas minimaux : `measures.xp_check` de `mechanics.json`."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.engine.model import GameData
from forever.engine.xp import Party, QuestXpInput, mob_kill_xp, quest_xp, xp_rules
from forever.pipeline.addon_sv import LoggerDB, XpGain, read_logger_db
from forever.pipeline.quest_rewards import QUEST_FILE, seen_quest_xp

VERDICTS = ("vérifié", "écart", "à vérifier")
# Règle -> (libellé, question ouverte qui reste tant qu'elle n'est pas vérifiée)
RULES: dict[str, tuple[str, str]] = {
    "kill_xp": ("XP d'un monstre de même niveau (PerKill du client)", "LVL1"),
    "xp.mob_level_difference": ("écart de niveau du monstre", "LVL1"),
    "xp.elite_factor": ("monstres élites", "LVL8"),
    "xp.dungeon_kill_bonus": ("bonus des monstres de donjon", "LVL5"),
    "xp.group": ("XP en groupe", "LVL4"),
    "xp.rested": ("repos", "LVL10"),
    "quest_xp": ("XP des quêtes vues par le client (QuestXP × multiplicateur)", "LVL6"),
    "xp.quest_level_difference": ("XP des quêtes selon l'écart de niveau", "LVL7"),
}


ELITE_CLASSES = ("elite", "rareelite", "worldboss")
DUNGEON_TYPES = ("party", "raid")
LOGGER_FILE = "ForeverLogger.lua"


def _mob_level(gain: XpGain, questie_levels: dict[str, int]) -> int | None:
    target = gain.target or {}
    if gain.monster and target.get("name") == gain.monster and isinstance(target.get("level"), int):
        level = target["level"]
        return level if level > 0 else None
    if gain.monster and gain.monster in questie_levels:
        return questie_levels[gain.monster]
    return None


def _case(rule: str, observed: float, expected: float) -> tuple[str, float]:
    gap = 0.0 if expected == observed else (observed - expected) / expected if expected else float("inf")
    return rule, gap


def _gain_cases(gd: GameData, gain: XpGain, mob: int) -> list[tuple[str, float]]:
    rules = xp_rules(gd)
    if gain.level is None:
        return []
    player: int = gain.level
    target = gain.target or {}
    elite = str(target.get("classification") or "") in ELITE_CLASSES
    inside = (gain.instance or {}).get("inside") is True and (gain.instance or {}).get("type") in DUNGEON_TYPES
    group = gain.group or {}
    levels = [lv for lv in group.get("levels") or [] if isinstance(lv, int)]
    size = group.get("size") if isinstance(group.get("size"), int) else 0
    party = Party((player, *levels)) if size and size > 1 and len(levels) == size - 1 else None
    if (size and size > 1 and party is None) or (gain.group_bonus and party is None):
        return []  # groupe sans les niveaux de chaque membre (ou ancien gain avec bonus de groupe) : non comparable
    rested = gain.rested_bonus or 0
    base_observed = float((gain.amount or 0) - rested)  # le bonus de repos est compris dans le montant
    model = mob_kill_xp(gd, player, mob, elite=elite, dungeon=inside, party=party).xp
    if party is not None:
        rule = "xp.group"
    elif inside:
        rule = "xp.dungeon_kill_bonus"
    elif elite:
        rule = "xp.elite_factor"
    elif mob != player:
        rule = "xp.mob_level_difference"
    else:
        rule = "kill_xp"
    cases = [_case(rule, base_observed, model)]
    if rested:
        cases.append(_case("xp.rested", float(rested), base_observed * (rules.rested_factor - 1)))
    return cases


def check_records(
    gd: GameData,
    rewards: dict[str, Any] | None,
    loggers: Sequence[LoggerDB],
    *,
    tolerance: float,
    min_cases: int,
    questie_levels: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Comparaison du modèle aux relevés : `{"rules": [...], "skipped": {...}, "to_verify": [...]}`."""
    fixed = questie_levels or {}
    gaps: dict[str, list[float]] = {key: [] for key in RULES}
    skipped = {"sans niveau de monstre": 0, "sans montant": 0, "groupe sans niveaux": 0, "quête non vue": 0}
    for db in loggers:
        for character in db.characters.values():
            for gain in character.xp:
                if gain.kind != "monster" or gain.level is None:
                    continue
                if gain.amount is None:
                    skipped["sans montant"] += 1
                    continue
                mob = _mob_level(gain, fixed)
                if mob is None:
                    skipped["sans niveau de monstre"] += 1
                    continue
                cases = _gain_cases(gd, gain, mob)
                if not cases:
                    skipped["groupe sans niveaux"] += 1
                for rule, gap in cases:
                    gaps[rule].append(gap)
            for turn_in in character.quest_turnins:
                if turn_in.xp_reward is None or turn_in.level is None:
                    continue
                base = seen_quest_xp(rewards or {}, turn_in.quest_id)
                seen = ((rewards or {}).get("seen_quests") or {}).get(str(turn_in.quest_id))
                if base is None or seen is None:
                    skipped["quête non vue"] += 1
                    continue
                model = quest_xp(gd, turn_in.level, QuestXpInput(seen["level"], base, "client", "probable"))
                rule = "xp.quest_level_difference" if len(model.terms) > 1 else "quest_xp"
                gaps[rule].append(_case(rule, float(turn_in.xp_reward), model.xp)[1])
    rows = []
    for key, (label, question) in RULES.items():
        values = gaps[key]
        outside = sum(1 for g in values if abs(g) > tolerance)
        if outside:
            verdict = "écart"
        elif len(values) >= min_cases:
            verdict = "vérifié"
        else:
            verdict = "à vérifier"
        rows.append(
            {
                "rule": key,
                "label": label,
                "cases": len(values),
                "median_gap": statistics.median(values) if values else None,
                "outside": outside,
                "verdict": verdict,
                "question": question,
            }
        )
    return {
        "rules": rows,
        "skipped": skipped,
        "to_verify": [r for r in rows if r["verdict"] != "vérifié"],
        "tolerance": tolerance,
        "min_cases": min_cases,
    }


def xp_check(deps: Deps, *, sv_dir: Path | None = None, questie_dir: Path | None = None) -> dict[str, Any]:
    """`forever xp check` : relevés de ForeverLogger de tous les comptes (ou de `sv_dir`), avec la provenance ; ne
    lève jamais faute de relevé."""
    from forever.freshness import freshness_for_version
    from forever.gamedata import MECHANICS_FILE, build_game_data
    from forever.provenance import make_provenance
    from forever.store import load_version

    data = load_version(deps)
    gd = build_game_data(data)
    params = data.read_json(MECHANICS_FILE)["values"]["measures.xp_check"]["value"]
    rewards = data.read_json(QUEST_FILE) if (data.path / QUEST_FILE).is_file() else None
    wow = deps.wow_dir
    if sv_dir is not None:
        paths = [sv_dir / LOGGER_FILE]
    elif wow is not None:
        paths = sorted(wow.glob(f"WTF/Account/*/SavedVariables/{LOGGER_FILE}"))
    else:
        paths = []
    loggers = [read_logger_db(path) for path in paths if path.is_file()]
    if questie_dir is None and wow is not None:
        questie_dir = wow / "Interface" / "AddOns" / "Questie"
    fixed: dict[str, int] = {}
    notes: list[str] = []
    if questie_dir is not None and questie_dir.is_dir():
        from forever.pipeline.questie import read_questie

        levels: dict[str, set[int]] = {}
        for npc in read_questie(questie_dir).npcs().values():
            if npc.min_level == npc.max_level:
                levels.setdefault(npc.name, set()).add(npc.min_level)
        fixed = {name: next(iter(lv)) for name, lv in levels.items() if len(lv) == 1}
        notes.append(
            "niveau des monstres sans cible relevée : niveau fixe de la base de Questie (nom à un seul niveau)"
        )
    report = check_records(
        gd,
        rewards,
        loggers,
        tolerance=float(params["tolerance"]),
        min_cases=int(params["min_cases"]),
        questie_levels=fixed,
    )
    if not loggers:
        notes.append("aucun relevé de ForeverLogger : tout reste à vérifier (décision 247, vérification passive)")
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty="probable" if loggers else "suppose",
        assumptions=[
            *fresh["assumptions"],
            f"relevés lus en local : {len(loggers)} SavedVariable(s) ForeverLogger, rien n'est écrit",
            *notes,
        ],
    )
    return {**report, "loggers": len(loggers), "provenance": provenance}
