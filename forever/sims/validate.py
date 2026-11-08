"""DPS mesuré dans les journaux de combat comparé au calcul de la même tranche (SIM2, plan 3e « Mesure et
recoupement »). Aucun calcul de jeu ici : la mesure vient du code existant (`forever.kill_time.fight_durations` :
combats du joueur et de son familier terminés par la mort du monstre, dégâts compris ; `LoggerDB.level_at` : niveau du
personnage au début de chaque combat, par GUID et heure locale), le calcul d'une fonction injectée (par défaut
`run_from_sources` de wowsims corrigé, au niveau mesuré) et le seuil de bruit de `forever.sims.builds.decide` (deux
fois l'erreur type combinée de la moyenne mesurée et de la moyenne simulée).

Certitude d'une tranche : `probable` si elle est recoupée, c'est-à-dire au moins `measures.kill_time.min_samples`
combats mesurés (`mechanics.json`) et un écart sous le bruit (« non départagé ») ; sinon `suppose`. Un écart
au-delà du bruit est à consigner dans `docs/OPEN_QUESTIONS.md` (plan 3e). La provenance de la réponse n'est
`probable` que si toutes les tranches le sont."""

from __future__ import annotations

import statistics
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, NamedTuple

from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError
from forever.kill_time import fight_durations
from forever.pipeline.addon_sv import Character, LoggerDB
from forever.pipeline.combatlog import read_log
from forever.provenance import local_provenance

GROUPS = ("bracket", "level")  # regroupement des combats : tranche de niveaux (défaut) ou niveau
AGREE = "non départagé"
Certainty = Literal["certain", "probable", "suppose"]


class SimRequest(NamedTuple):
    class_name: str  # nom anglais de la classe (« Hunter »)
    race: str  # race du personnage lue dans ForeverLogger
    level: int
    talents: dict[str, int] | None  # nos clés de talents du dernier relevé au niveau ou en dessous (None : inconnus)


Simulate = Callable[[SimRequest], Mapping[str, Any]]


class Fight(NamedTuple):
    level: int
    seconds: float
    damage: float
    pet_damage: float

    @property
    def dps(self) -> float:
        return self.damage / self.seconds


class Measured(NamedTuple):
    guid: str
    name: str | None
    realm: str | None
    class_name: str
    race: str | None
    character: Character
    by_level: dict[int, list[Fight]]
    unattributed: int  # combats sans niveau connu (aucun relevé de ForeverLogger avant le combat)
    skipped: int  # combats de durée nulle (monstre tué d'un coup)


def _find(target: str, loggers: Sequence[LoggerDB]) -> tuple[LoggerDB, Character]:
    wanted = target.strip().lower()
    for db in loggers:
        for guid, c in db.characters.items():
            names = {guid.lower(), (c.name or "").lower(), f"{c.name or ''}-{c.realm or ''}".lower()}
            if wanted in names:
                return db, c
    raise InvalidArgumentError(
        f"Personnage inconnu de ForeverLogger : « {target} ».",
        "donner le nom ou le GUID d'un personnage relevé par ForeverLogger (SavedVariables du compte)",
    )


def measure_character(character: str, *, logs: Sequence[Path], loggers: Sequence[LoggerDB]) -> Measured:
    """Combats du personnage (nom, « nom-royaume » ou GUID) dans les journaux, par niveau du personnage au début du
    combat (ForeverLogger)."""
    from forever.profile import CLASS_NAMES

    db, found = _find(character, loggers)
    class_name = CLASS_NAMES.get((found.class_ or "").lower())
    if class_name is None:
        raise InvalidArgumentError(f"Classe inconnue pour {found.name} : « {found.class_} ».",
                                   "relancer le jeu avec ForeverLogger pour relever le personnage")  # fmt: skip
    by_level: dict[int, list[Fight]] = {}
    unattributed = skipped = 0
    for path in logs:
        _, stream = read_log(path)
        for fight in fight_durations(list(stream), found.guid):
            level = db.level_at(found.guid, fight.start)
            if level is None:
                unattributed += 1
            elif fight.seconds <= 0:
                skipped += 1
            else:
                by_level.setdefault(level, []).append(Fight(level, fight.seconds, fight.damage, fight.pet_damage))
    return Measured(found.guid, found.name, found.realm, class_name, found.race, found, by_level, unattributed,
                    skipped)  # fmt: skip


def bracket_of(level: int) -> str:
    """Tranche de niveaux d'un niveau (tranches de `forever.sims.brackets.BRACKETS`, « 1-9 » en dessous)."""
    from forever.sims.brackets import BRACKETS

    for label in BRACKETS:
        low, _, high = label.partition("-")
        if int(low) <= level <= int(high or low):
            return label
    return "1-9"


def _talents_at(deps: Deps, measured: Measured, level: int) -> dict[str, int] | None:
    """Talents du dernier relevé de ForeverLogger au niveau `level` ou en dessous, en nos clés (None si inconnus)."""
    snaps = [s for s in measured.character.snapshots if s.talents and s.level is not None and s.level <= level]
    if not snaps:
        return None
    try:
        from forever.profile_import import node_keys
        from forever.store import load_version

        known = node_keys(load_version(deps)).get(measured.class_name) or {}
    except ForeverError:
        return None
    last = max(snaps, key=lambda s: (s.level or 0, s.time or 0))
    keys = {known[str(n)]: r for n, r in (last.talents or {}).items() if str(n) in known and r > 0}
    return keys or None


def _measured(fights: Sequence[Fight]) -> dict[str, Any]:
    values = [f.dps for f in fights]
    seconds = sum(f.seconds for f in fights)
    damage = sum(f.damage for f in fights)
    pet = sum(f.pet_damage for f in fights)
    return {
        "fights": len(values),
        "seconds": seconds,
        "dps": statistics.fmean(values),
        "stdev": statistics.stdev(values) if len(values) >= 2 else None,
        "pet_share": pet / damage if damage > 0 else 0.0,
    }


def _gap(measured: Mapping[str, Any], simulated: Mapping[str, Any]) -> dict[str, Any]:
    from forever.sims.builds import decide

    if measured["stdev"] is None:  # un seul combat : bruit inconnu
        return {"absolute": measured["dps"] - float(simulated["dps"]), "relative": _relative(measured, simulated),
                "threshold": None, "verdict": "trop peu de combats"}  # fmt: skip
    noise = decide(
        simulated,
        {"dps": measured["dps"], "stdev": measured["stdev"], "iterations": measured["fights"]},
    )
    if abs(noise["gain"]) <= noise["threshold"]:
        verdict = AGREE
    else:
        verdict = "mesuré au-dessus du calcul" if noise["gain"] > 0 else "mesuré en dessous du calcul"
    return {"absolute": noise["gain"], "relative": _relative(measured, simulated), "threshold": noise["threshold"],
            "verdict": verdict}  # fmt: skip


def _relative(measured: Mapping[str, Any], simulated: Mapping[str, Any]) -> float | None:
    sim = float(simulated["dps"])
    return (measured["dps"] - sim) / sim if sim > 0 else None


def validate_character(
    deps: Deps,
    character: str,
    *,
    logs: Sequence[Path],
    loggers: Sequence[LoggerDB],
    simulate: Simulate | None = None,
    group: str = "bracket",
    preset: str | None = None,
) -> dict[str, Any]:
    """Par tranche (ou par niveau) : DPS mesuré (moyenne, écart type, combats, durée), DPS calculé au niveau mesuré
    (médiane des niveaux de la tranche), écart relatif et verdict, certitude (voir le module)."""
    from forever.gamedata import MECHANICS_FILE
    from forever.kill_time import kill_params
    from forever.store import load_version

    if group not in GROUPS:
        raise InvalidArgumentError(f"Regroupement inconnu : « {group} ».", "choisir " + ", ".join(GROUPS))
    min_samples = kill_params(load_version(deps).read_json(MECHANICS_FILE)["values"]).min_samples
    measured = measure_character(character, logs=logs, loggers=loggers)
    if not measured.race:
        raise InvalidArgumentError(f"Race inconnue pour {measured.name}.",
                                   "relancer le jeu avec ForeverLogger pour relever le personnage")  # fmt: skip
    run = simulate if simulate is not None else default_simulate(deps, preset=preset)
    groups: dict[str, list[Fight]] = {}
    for level in sorted(measured.by_level):
        key = bracket_of(level) if group == "bracket" else str(level)
        groups.setdefault(key, []).extend(measured.by_level[level])
    rows: list[dict[str, Any]] = []
    for key, fights in groups.items():
        levels = sorted({f.level for f in fights})
        sim_level = int(statistics.median_low([f.level for f in fights]))
        row: dict[str, Any] = {"bracket" if group == "bracket" else "level": key if group == "bracket" else int(key),
                               "levels": levels, "sim_level": sim_level, "measured": _measured(fights)}  # fmt: skip
        request = SimRequest(measured.class_name, measured.race, sim_level, _talents_at(deps, measured, sim_level))
        try:
            simulated = dict(run(request))
        except ForeverError as err:
            row.update(simulated={"error": err.to_info()}, gap=None, certainty="suppose")
            rows.append(row)
            continue
        row["simulated"] = simulated
        row["gap"] = _gap(row["measured"], simulated)
        agreed = row["gap"]["verdict"] == AGREE and row["measured"]["fights"] >= min_samples
        row["certainty"] = "probable" if agreed else "suppose"
        rows.append(row)
    notes = [
        (
            "DPS mesuré : dégâts du joueur et de son familier sur le monstre (dépassement retiré), du premier coup à "
            "sa mort, combats terminés par la mort du monstre seulement ; niveau lu dans ForeverLogger par GUID et heure"
        ),
        (
            "DPS calculé : fonction de simulation au niveau médian de la tranche (par défaut wowsims corrigé, "
            "run_from_sources : combat de durée fixe contre une cible du niveau, équipement de GearQuest et parcours "
            "de talents du plan, pas l'équipement ni les talents relevés dans le journal)"
        ),
        (
            f"« {AGREE} » : écart sous deux fois l'erreur type combinée des deux moyennes ; certitude probable si au "
            f"moins {min_samples} combats (measures.kill_time.min_samples) et écart sous le bruit, sinon suppose"
        ),
    ]
    if any(r.get("gap") and r["gap"]["verdict"] not in (AGREE, "trop peu de combats") for r in rows):
        notes.append("écart au-delà du bruit : à consigner dans docs/OPEN_QUESTIONS.md (plan SIM2, 3e)")
    if measured.unattributed:
        notes.append(f"{measured.unattributed} combat(s) sans niveau connu (aucun relevé ForeverLogger avant) écartés")
    if measured.skipped:
        notes.append(f"{measured.skipped} combat(s) de durée nulle écartés")
    overall: Certainty = "probable" if rows and all(r["certainty"] == "probable" for r in rows) else "suppose"
    return {
        "character": {
            "guid": measured.guid,
            "name": measured.name,
            "realm": measured.realm,
            "class": measured.class_name,
            "race": measured.race,
        },
        "group": group,
        "logs": len(logs),
        "rows": rows,
        "unattributed": measured.unattributed,
        "provenance": local_provenance(deps, certainty=overall, assumptions=notes),
    }


def default_simulate(deps: Deps, preset: str | None = None) -> Simulate:
    """Simulation par défaut : `run_from_sources` (wowsims corrigé) au niveau demandé, race du personnage, préréglage
    `preset` ou celui de la classe dont l'arbre principal est celui des talents relevés (sinon le premier)."""

    def run(request: SimRequest) -> Mapping[str, Any]:
        from forever.sims.analysis import dps_presets
        from forever.sims.brackets import run_from_sources

        key = preset or _preset_for(deps, request, [k for k, _ in dps_presets(deps)])
        doc = run_from_sources(deps, preset=key, race=request.race, brackets=str(request.level))
        row = (doc.get("rows") or [{}])[0]
        if "error" in row:
            raise ForeverError(str(row["error"]["code"]), str(row["error"]["message"]), str(row["error"]["action"]))
        return {"dps": row["dps"], "stdev": row["stdev"], "iterations": row.get("iterations"), "preset": key,
                "level": row["level"], "assumptions": doc["provenance"]["assumptions"]}  # fmt: skip

    return run


def _preset_for(deps: Deps, request: SimRequest, keys: Sequence[str]) -> str:
    from forever.pipeline.wowsims_build import wowsims_dir
    from forever.sims import wowsims
    from forever.sims.engines import ClassTalents, class_of

    presets = [p for p in wowsims.read_presets(wowsims_dir(deps.cache_dir) / "forever") if p.key in keys]
    mine = [p for p in presets if class_of(p) == request.class_name]
    if not mine:
        raise InvalidArgumentError(f"Aucun préréglage de dégâts pour {request.class_name}.",
                                   "donner preset (voir forever sims presets)")  # fmt: skip
    if request.talents:
        conv = ClassTalents(deps, request.class_name)
        tree = conv.lead_tree(request.talents)
        same = [p for p in mine if conv.lead_tree(conv.wowsims.decode(p.talents)) == tree]
        if same:
            return same[0].key
    return mine[0].key
