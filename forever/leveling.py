"""Simulation de leveling pour la CLI (`forever sim leveling`) et le serveur MCP (`forever_sim_leveling`) :
validation des paramètres et du build, Monte Carlo et modèle analytique, PV du monstre, provenance.

Aucun calcul ici : les simulateurs (`forever/sim/`) orchestrent les fonctions du moteur (`forever/engine/`)."""

from __future__ import annotations

import difflib
import statistics
from collections.abc import Mapping
from typing import Any, TypedDict, cast

from forever.config import Deps
from forever.engine.model import CharacterOverrides, GameData, MonsterHp
from forever.engine.monsters import mob_hp
from forever.engine.talents import check_build
from forever.errors import InvalidArgumentError
from forever.freshness import freshness_for_version
from forever.gamedata import RACES_FILE, RULES, build_game_data, mage_races
from forever.provenance import Certainty, Provenance, make_provenance, min_certainty
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import KillResult, McStats, mc, mc_stats, options_with_defaults
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
    inputs: dict[str, Any]  # valeurs d'entrée et leur origine (T06b)
    rotation: str
    talents: dict[str, int]
    n: int
    seed: int
    options: dict[str, Any]
    monte_carlo: KillResult
    monte_carlo_stats: dict[str, Any] | None  # moyenne, dispersion, intervalle (T06b)
    analytic: KillResult
    analytic_gap: float
    mob_hp: MobHpInfo
    provenance: Provenance


DEFAULT_RACE = "Orc"  # race par défaut des outils de calcul (T04), toujours signalée dans `inputs` (T06b)
DEFAULT_RACE_NOTE = (
    "race non donnée : Orc par défaut (donnée personnelle : la demander au joueur ou lire forever_player_profile)"
)


def given(value: Any, default: Any) -> dict[str, Any]:
    """Valeur d'entrée et son origine : `argument` (donnée par l'appelant) ou `default` (défaut de l'outil)."""
    return {"value": value if value is not None else default, "origin": "argument" if value is not None else "default"}


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


def canonical_race(data: VersionData, race: str) -> str:
    """Race écrite comme dans les données, sans souci de casse (« orc » → « Orc ») ; inchangée si inconnue."""
    return next((r for r in mage_races(data) if r.lower() == race.strip().lower()), race)


def check_race(data: VersionData, race: str) -> None:
    races = mage_races(data)
    if race not in races:
        source = RACES_FILE if (data.path / RACES_FILE).is_file() else RACIALS_FILE
        raise InvalidArgumentError(f"Race inconnue « {race} ».", f"choisir parmi {', '.join(races)} ({source})")


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


def damage_assumptions(options: Mapping[str, Any], low_level_default: bool) -> list[str]:
    """Hypothèses de calcul des dégâts du mode forever (T04e) ; aucune en mode seed (formule du seed)."""
    if options["rules"] != "forever":
        return []
    penalty = low_level_default if options.get("low_level_penalty") is None else options["low_level_penalty"]
    origin = "défaut des données" if options.get("low_level_penalty") is None else "option"
    return [
        "coefficients de puissance des sorts du client (SpellEffect.EffectBonusCoefficient), tics de DoT compris",
        f"pénalité des sorts de bas niveau : {'appliquée' if penalty else 'non appliquée'} ({origin}, suppose)",
        "bonus de dégâts en pourcentage multipliés entre sources (probable)",
    ]


def ratio_assumption(gd: GameData) -> str:
    """Origine des ratios du personnage (critique par Intelligence, mana de base, XP par niveau, constante d'armure)
    et des utilitaires du Mage."""
    what = "critique par Intelligence, mana de base, XP par niveau, constante d'armure"
    if gd.character_ratios == "client":
        inherited = f", hérité de {gd.character_ratios_from}" if gd.character_ratios_from else ""
        head = f"ratios du personnage décodés du client (character_scaling.json{inherited}) : {what}"
    else:
        head = f"ratios du personnage estimés (mechanics.json, fm.py) : {what}"
    return f"{head} ; utilitaires du Mage lus dans {gd.utility_source}"


def assumptions(
    options: Mapping[str, Any],
    hp: MonsterHp,
    talents: Mapping[str, int],
    n: int,
    seed: int,
    low_level_default: bool,
) -> list[str]:
    spec = ", ".join(f"{k} {v}" for k, v in sorted(talents.items())) or "aucun"
    return [
        f"mob_source {options['mob_source']} : PV du monstre {hp.value:g} ({hp.certainty}, {hp.source})",
        f"spell_level {options['spell_level']} : "
        + ("dégâts des rangs au niveau du personnage" if options["spell_level"] == "character" else "dégâts des rangs"),
        f"rules {options['rules']} : "
        + ("corrections de Forever (T04c)" if options["rules"] == "forever" else "comportement du seed à l'identique"),
        (
            "armure du seed : Frost Armor à tout niveau, Mage Armor pour la régénération dès son premier rang (seed)"
            if options["rules"] == "seed"
            else f"armor {options['armor']} : armure portée selon le niveau d'apprentissage lu dans le client"
            + (" (auto)" if options["armor"] == "auto" else " (forcée)")
        ),
        f"talents : {spec}",
        f"Monte Carlo : n = {n}, graine {seed} ; analytique : espérance fermée (seed)",
        "constantes leveling.* du seed sim_leveling.py (EST, suppose) ; XP de monstre : règle Classic (T04c)",
        *damage_assumptions(options, low_level_default),
    ]


MIN_STATS_N = 2  # dispersion : au moins deux combats


def _stats_dict(stats: McStats | None, confidence: float) -> dict[str, Any] | None:
    """Moyenne, écart type, erreur type, nombre de combats et intervalle de la moyenne du temps par monstre (T06b)."""
    if stats is None:
        return None
    half = statistics.NormalDist().inv_cdf((1 + confidence) / 2) * stats.se
    return {
        "mean": stats.mean,
        "sd": stats.sd,
        "se": stats.se,
        "n": stats.n,
        "low": stats.mean - half,
        "high": stats.mean + half,
        "confidence": confidence,
    }


def simulate_leveling(
    deps: Deps,
    level: int,
    *,
    race: str | None = None,
    rotation: str = "frost",
    talents: Mapping[str, int] | None = None,
    n: int = 1500,
    seed: int = 12345,
    mob_source: str = "measured",
    spell_level: str = "character",
    level_diff: int | None = None,
    nova: bool = False,
    over: CharacterOverrides | None = None,
    rules: str = "forever",
    armor: str = "auto",
    ab_stacks: int | None = None,
    ab_dump: str | None = None,
    low_level_penalty: bool | None = None,
) -> LevelingReport:
    """Monte Carlo (moyenne de `n` combats, graine fixe) et analytique pour un build, avec la provenance.

    `low_level_penalty` : pénalité des sorts de bas niveau (None : `coefficient.low_level_default` des données)."""
    inputs = {
        "race": given(race, DEFAULT_RACE),
        "level": given(level, None),
        "talents": given(dict(talents) if talents is not None else None, {}),
    }
    race = race if race is not None else DEFAULT_RACE
    data = load_version(deps)
    if rules not in RULES:
        raise InvalidArgumentError(f"Règles inconnues : {rules}.", "choisir forever ou seed")
    gd = build_game_data(data, rules=rules)
    cap = level_cap(data)
    check_level(level, cap)
    check_race(data, race)
    if not 1 <= n <= MAX_N:
        raise InvalidArgumentError(f"n = {n} hors de 1-{MAX_N}.", f"donner un nombre de combats de 1 à {MAX_N}")
    pts = dict(talents or {})
    check_talents(gd, pts, level)
    raw: dict[str, Any] = {
        "mob_source": mob_source,
        "spell_level": spell_level,
        "nova": nova,
        "rules": rules,
        "armor": armor,
        "low_level_penalty": low_level_penalty,
    }
    if ab_stacks is not None:
        raw["ab_stacks"] = ab_stacks
    if ab_dump is not None:
        raw["ab_dump"] = ab_dump
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
        stats = mc_stats(gd, level, pts, race, rotation, n, seed, over, **raw) if n >= MIN_STATS_N else None
    except ValueError as exc:
        raise InvalidArgumentError(
            f"{exc}.", "choisir un niveau où le sort principal (et l'armure demandée) est appris"
        ) from exc
    certainty = min_certainty([cast(Certainty, hp.certainty), constants_certainty(data), "suppose"])
    fresh = freshness_for_version(deps, data.game_version, allow_network=False)
    provenance = make_provenance(
        deps,
        game_version=data.game_version,
        data_sha=data.data_sha,
        freshness=fresh["freshness"],
        certainty=certainty,
        assumptions=[
            *fresh["assumptions"],
            *assumptions(options, hp, pts, n, seed, gd.constants.coefficients.low_level_default),
            ratio_assumption(gd),
            *([DEFAULT_RACE_NOTE] if inputs["race"]["origin"] == "default" else []),
        ],
    )
    return {
        "level": level,
        "race": race,
        "inputs": inputs,
        "rotation": rotation,
        "talents": pts,
        "n": n,
        "seed": seed,
        "options": options,
        "monte_carlo": m,
        "monte_carlo_stats": _stats_dict(stats, gd.build.confidence),
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
