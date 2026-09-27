"""Simulation de leveling pour la CLI (`forever sim leveling`) et le serveur MCP (`forever_sim_leveling`) :
validation des paramètres et du build, Monte Carlo et modèle analytique, PV du monstre, provenance.

Aucun calcul ici : les simulateurs (`forever/sim/`) orchestrent les fonctions du moteur (`forever/engine/`)."""

from __future__ import annotations

import difflib
from collections.abc import Mapping
from typing import Any, TypedDict, cast

from forever.config import Deps
from forever.engine.model import CharacterOverrides, GameData, MonsterHp
from forever.engine.monsters import mob_hp
from forever.engine.talents import check_build
from forever.errors import InvalidArgumentError
from forever.freshness import freshness_for_version
from forever.gamedata import build_game_data
from forever.provenance import Certainty, Provenance, make_provenance, min_certainty
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import KillResult, mc, options_with_defaults
from forever.store import VersionData, load_version

MECHANICS_FILE = "mechanics.json"
SCALING_FILE = "spell_scaling.json"
RACIALS_FILE = "racials.json"
LEVELING_PREFIX = "leveling."
MAX_N = 100_000  # borne de méthode (temps de calcul), pas un chiffre de jeu
CERTAINTIES: tuple[Certainty, ...] = ("certain", "probable", "suppose")


class MobHpInfo(TypedDict):
    level: int
    value: float
    certainty: str
    source: str


class LevelingReport(TypedDict):
    level: int
    race: str
    rotation: str
    talents: dict[str, int]
    n: int
    seed: int
    options: dict[str, Any]
    monte_carlo: KillResult
    analytic: KillResult
    analytic_gap: float
    mob_hp: MobHpInfo
    provenance: Provenance


def parse_talents(text: str | None) -> dict[str, int]:
    """`clé=rang,clé=rang` -> points ; InvalidArgumentError si un élément est mal formé."""
    pts: dict[str, int] = {}
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        key, sep, value = part.partition("=")
        if not sep or not key.strip() or not value.strip().lstrip("-").isdigit():
            raise InvalidArgumentError(
                f"Talent mal formé « {part} ».", "écrire --talents clé=rang,clé=rang (ex. improvedFrostbolt=3)"
            )
        pts[key.strip()] = int(value)
    return pts


def check_talents(gd: GameData, pts: Mapping[str, int], level: int) -> None:
    """Clés connues et build légal au niveau donné (InvalidArgumentError, message en français)."""
    negative = [k for k, v in pts.items() if v < 0]
    if negative:
        raise InvalidArgumentError(
            f"Rang de talent négatif : {', '.join(negative)}.", "donner des rangs positifs ou nuls"
        )
    unknown = [k for k in pts if k not in gd.talents]
    if unknown:
        close = difflib.get_close_matches(unknown[0], list(gd.talents), n=3, cutoff=0.6)
        hint = f" ; proches : {', '.join(close)}" if close else ""
        raise InvalidArgumentError(
            f"Talent inconnu : {', '.join(unknown)}{hint}.", "utiliser les clés de talents.json (ex. improvedFrostbolt)"
        )
    errors = check_build(gd, pts, level)
    if errors:
        raise InvalidArgumentError(f"Build illégal au niveau {level} : {' ; '.join(errors)}.", "corriger les talents")


def level_cap(data: VersionData) -> int:
    return int(data.read_json(SCALING_FILE)["level_cap"])


def check_level(level: int, cap: int, what: str = "Niveau") -> None:
    if not 1 <= level <= cap:
        raise InvalidArgumentError(f"{what} {level} hors de 1-{cap}.", f"donner un niveau de 1 à {cap}")


def check_race(data: VersionData, race: str) -> None:
    races = sorted(data.read_json(RACIALS_FILE)["races"])
    if race not in races:
        raise InvalidArgumentError(f"Race inconnue « {race} ».", f"choisir parmi {', '.join(races)} (racials.json)")


def constants_certainty(data: VersionData) -> Certainty:
    """Certitude la plus basse des constantes `leveling.*` de `mechanics.json`."""
    values = data.read_json(MECHANICS_FILE)["values"]
    found = [v.get("certainty") for k, v in values.items() if k.startswith(LEVELING_PREFIX)]
    return min_certainty(cast(Certainty, c) for c in found if c in CERTAINTIES)


def target_hp(gd: GameData, level: int, mob_source: str) -> MonsterHp:
    try:
        return mob_hp(gd, level, mob_source)  # type: ignore[arg-type]
    except ValueError as exc:
        raise InvalidArgumentError(f"{exc}.", "choisir un niveau de monstre couvert par les données") from exc


def assumptions(options: Mapping[str, Any], hp: MonsterHp, talents: Mapping[str, int], n: int, seed: int) -> list[str]:
    spec = ", ".join(f"{k} {v}" for k, v in sorted(talents.items())) or "aucun"
    return [
        f"mob_source {options['mob_source']} : PV du monstre {hp.value:g} ({hp.certainty}, {hp.source})",
        f"spell_level {options['spell_level']} : "
        + ("dégâts des rangs au niveau du personnage" if options["spell_level"] == "character" else "dégâts des rangs"),
        f"talents : {spec}",
        f"Monte Carlo : n = {n}, graine {seed} ; analytique : espérance fermée (seed)",
        "constantes leveling.* du seed sim_leveling.py (EST, suppose) ; XP de monstre : règle Classic (T04c)",
    ]


def simulate_leveling(
    deps: Deps,
    level: int,
    *,
    race: str = "Orc",
    rotation: str = "frost",
    talents: Mapping[str, int] | None = None,
    n: int = 1500,
    seed: int = 12345,
    mob_source: str = "measured",
    spell_level: str = "character",
    level_diff: int | None = None,
    nova: bool = False,
    over: CharacterOverrides | None = None,
) -> LevelingReport:
    """Monte Carlo (moyenne de `n` combats, graine fixe) et analytique pour un build, avec la provenance."""
    data = load_version(deps)
    gd = build_game_data(data)
    cap = level_cap(data)
    check_level(level, cap)
    check_race(data, race)
    if not 1 <= n <= MAX_N:
        raise InvalidArgumentError(f"n = {n} hors de 1-{MAX_N}.", f"donner un nombre de combats de 1 à {MAX_N}")
    pts = dict(talents or {})
    check_talents(gd, pts, level)
    raw: dict[str, Any] = {"mob_source": mob_source, "spell_level": spell_level, "nova": nova}
    if level_diff is not None:
        raw["level_diff"] = level_diff
    try:
        options = options_with_defaults(gd, rotation, raw)
    except ValueError as exc:
        raise InvalidArgumentError(f"{exc}.", "voir `forever sim leveling --help`") from exc
    check_level(level + options["level_diff"], cap, "Niveau du monstre")
    hp = target_hp(gd, level + options["level_diff"], options["mob_source"])
    try:
        m = mc(gd, level, pts, race, rotation, n, seed, over, **raw)
        a = kill_analytic(gd, level, pts, race, rotation, over, **raw)
    except ValueError as exc:
        raise InvalidArgumentError(f"{exc}.", "choisir un niveau où le sort principal est appris") from exc
    certainty = min_certainty([cast(Certainty, hp.certainty), constants_certainty(data), "suppose"])
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty=certainty,
        assumptions=[*fresh["assumptions"], *assumptions(options, hp, pts, n, seed)],
    )
    return {
        "level": level,
        "race": race,
        "rotation": rotation,
        "talents": pts,
        "n": n,
        "seed": seed,
        "options": options,
        "monte_carlo": m,
        "analytic": a,
        "analytic_gap": a["total"] / m["total"] - 1,
        "mob_hp": {
            "level": level + options["level_diff"],
            "value": hp.value,
            "certainty": hp.certainty,
            "source": hp.source,
        },
        "provenance": provenance,
    }
