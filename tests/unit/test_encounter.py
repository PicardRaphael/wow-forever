"""Scénarios provisoires de donjon et de raid (T05, bloc E ; décision 82 ; registre H3, H5, I1).

Scénarios lus dans `mechanics.json` (`build.scenarios`, suppose) : boss de donjon (niveau + 2, 60 s), paquet (4
cibles, niveau + 1, PV du monstre normal, au plus 40 s), boss de raid (niveau + 3, 180 s) ; boss insensibles au gel
(règle Classic supposée). Tank présent : aucun coup reçu, aucun recul. Mana bornée, sans Évocation ni potion.
Réserve de mana réduite par la fiche (`over`, valeur de test) pour atteindre la fin de mana."""

import dataclasses
import random

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.casting import cast_time
from forever.engine.character import character
from forever.engine.spells import best_rank
from forever.sim.encounter import EncounterLog, encounter_analytic, encounter_fight, encounter_mc

FROST = {"improvedFrostbolt": 5, "iceShards": 5}
FROST_IL = {"improvedFrostbolt": 5, "frostbite": 3, "iceLance": 1}
FIRE = {"improvedFireball": 5, "ignite": 5}
ARC40 = {
    "arcaneFocus": 5,
    "improvedChanneling": 1,
    "arcaneConcentration": 5,
    "arcaneSubtlety": 2,
    "arcaneImpact": 3,
    "arcaneBlast": 1,
    "arcaneGeometry": 1,
    "arcaneMeditation": 3,
    "missileBarrage": 1,
    "presenceOfMind": 1,
    "arcaneMind": 4,
    "arcaneInstability": 3,
    "arcanePower": 1,
}
ROTATIONS = [("frost", FROST, {}), ("fire", FIRE, {}), ("arcane", ARC40, {"ab_dump": "arcane_missiles"})]
LOW_MANA = {"mana": 400.0}  # réserve de mana de test
# Réserve de test sans limite : compare les cycles des rotations sans la fin de mana (le Monte Carlo garde toujours une
# fraction de lancer inutilisée, l'analytique non ; au niveau 40, la rotation arcane épuise 2 322 mana en ~18 s).
NO_OOM = {"mana": 1e6}


def test_scenarios_come_from_the_data(game_data):
    entry = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["build.scenarios"]
    assert entry["certainty"] == "suppose" and "provisoire" in entry["source"]
    sc = game_data.build.scenarios
    assert set(sc) == {"dungeon_boss", "dungeon_pack", "raid_boss"}
    for name, raw in entry["value"].items():
        s = sc[name]
        assert (s.targets, s.level_offset, s.duration_s, s.freeze_immune, s.hp) == (
            raw["targets"],
            raw["level_offset"],
            raw["duration_s"],
            raw["freeze_immune"],
            raw["hp"],
        )
    assert (sc["dungeon_boss"].level_offset, sc["raid_boss"].duration_s, sc["dungeon_pack"].targets) == (2, 180, 4)


@pytest.mark.parametrize(("rotation", "pts", "opts"), ROTATIONS)
def test_analytic_close_to_monte_carlo_on_a_single_target(game_data, rotation, pts, opts):
    a = encounter_analytic(game_data, "dungeon_boss", 40, pts, "Orc", rotation, NO_OOM, **opts)
    m = encounter_mc(game_data, "dungeon_boss", 40, pts, "Orc", rotation, 400, seed=1, over=NO_OOM, **opts)
    assert a["dps"] == pytest.approx(m.mean, rel=0.03), (a["dps"], m.mean)
    assert a["duration_s"] == 60 and a["taken"] == 0


def test_monte_carlo_statistics_are_per_fight_dps(game_data):
    m = encounter_mc(game_data, "dungeon_boss", 40, FROST, "Orc", "frost", 20, seed=4)
    rng = random.Random(4)
    fights = [encounter_fight(game_data, "dungeon_boss", 40, FROST, "Orc", "frost", rng) for _ in range(20)]
    assert m.totals == tuple(f["dps"] for f in fights)
    assert m.n == 20 and m.mean == pytest.approx(sum(m.totals) / 20, rel=1e-12)
    assert m == encounter_mc(game_data, "dungeon_boss", 40, FROST, "Orc", "frost", 20, seed=4)


def test_no_damage_once_the_mana_is_gone(game_data):
    log: list[EncounterLog] = []
    r = encounter_fight(game_data, "raid_boss", 40, FROST, "Orc", "frost", random.Random(2), log, over=LOW_MANA)
    assert r["oom_s"] is not None and r["oom_s"] < 180
    assert all(c.start <= r["oom_s"] for c in log)
    assert r["dmg"] == pytest.approx(sum(c.dmg for c in log), rel=1e-12)  # Frostbolt : aucun DoT
    assert r["dps"] == pytest.approx(r["dmg"] / 180, rel=1e-12)
    a = encounter_analytic(game_data, "raid_boss", 40, FROST, "Orc", "frost", over=LOW_MANA)
    full = encounter_analytic(game_data, "raid_boss", 40, FROST, "Orc", "frost", NO_OOM)
    assert a["oom_s"] is not None and a["oom_s"] < 180
    assert a["dmg"] == pytest.approx(full["dps"] * a["oom_s"], rel=1e-9)


def test_casts_fit_inside_the_duration(game_data):
    log: list[EncounterLog] = []
    encounter_fight(game_data, "dungeon_boss", 40, FIRE, "Orc", "fire", random.Random(3), log)
    assert log and all(c.end <= 60 for c in log)


def test_tank_present_no_damage_taken_and_no_pushback(game_data):
    log: list[EncounterLog] = []
    ch = character(game_data, 40, "Orc")
    r = encounter_fight(game_data, "dungeon_boss", 40, FROST, "Orc", "frost", random.Random(5), log)
    assert r["taken"] == 0
    for c in log:
        rank = best_rank(game_data, c.key, 40, FROST)
        assert c.end - c.start == pytest.approx(cast_time(game_data, c.key, rank, FROST, ch), abs=1e-9), c


def test_bosses_cannot_be_frozen(game_data):
    for seed in range(4):
        log: list[EncounterLog] = []
        encounter_fight(game_data, "dungeon_boss", 40, FROST_IL, "Orc", "frost", random.Random(seed), log)
        assert all(c.key != "ice_lance" for c in log)


def test_pack_area_damage_scales_with_the_number_of_targets(game_data):
    """Sans plafond de cibles (C7, angle mort) : 4 cibles valent 4 fois une cible."""
    gd = game_data
    one = dataclasses.replace(gd.build.scenarios["dungeon_pack"], targets=1)
    gd1 = dataclasses.replace(
        gd, build=dataclasses.replace(gd.build, scenarios={**gd.build.scenarios, "dungeon_pack": one})
    )
    four = encounter_analytic(gd, "dungeon_pack", 40, {}, "Orc", "aoe")
    single = encounter_analytic(gd1, "dungeon_pack", 40, {}, "Orc", "aoe")
    assert four["dps"] == pytest.approx(4 * single["dps"], rel=1e-9)
    assert four["duration_s"] == pytest.approx(single["duration_s"], rel=1e-9)
    assert four["duration_s"] <= 40


def test_pack_rotation_uses_area_spells(game_data):
    log: list[EncounterLog] = []
    r = encounter_fight(game_data, "dungeon_pack", 40, {}, "Orc", "aoe", random.Random(1), log)
    assert {c.key for c in log} <= {"arcane_explosion", "blizzard", "flamestrike", "cone_of_cold", "frost_nova"}
    assert r["dmg"] > 0
    for filler in ("arcane_explosion", "blizzard", "flamestrike"):
        f: list[EncounterLog] = []
        encounter_fight(game_data, "dungeon_pack", 40, {}, "Orc", "aoe", random.Random(1), f, aoe_filler=filler)
        assert filler in {c.key for c in f}


def test_arcane_power_at_the_pull_then_at_each_cooldown(game_data):
    on: list[EncounterLog] = []
    off: list[EncounterLog] = []
    opts = {"ab_dump": "arcane_missiles"}
    encounter_fight(game_data, "dungeon_boss", 40, ARC40, "Orc", "arcane", random.Random(6), on, over=NO_OOM, **opts)
    encounter_fight(
        game_data,
        "dungeon_boss",
        40,
        ARC40,
        "Orc",
        "arcane",
        random.Random(6),
        off,
        over=NO_OOM,
        arcane_power="off",
        **opts,
    )
    assert [(c.start, c.key) for c in on] == [(c.start, c.key) for c in off]  # boss sans limite de PV : même suite
    inside = [(a, b) for a, b in zip(on, off, strict=True) if a.end < 15.0]
    after = [(a, b) for a, b in zip(on, off, strict=True) if a.end >= 15.0]
    assert inside and after
    for a, b in inside:
        assert a.cost == pytest.approx(b.cost * 1.30, rel=1e-12) and a.dmg == pytest.approx(b.dmg * 1.30, rel=1e-12)
    for a, b in after:
        assert (a.cost, a.dmg) == (b.cost, b.dmg)
    raid = encounter_analytic(game_data, "raid_boss", 40, ARC40, "Orc", "arcane", **opts)
    raid_off = encounter_analytic(game_data, "raid_boss", 40, ARC40, "Orc", "arcane", arcane_power="off", **opts)
    assert raid["dmg"] > raid_off["dmg"]


@pytest.mark.parametrize(
    ("scenario", "rotation", "opts", "match"),
    [
        ("dungeon_boss", "frost", {"rules": "seed"}, "rules"),
        ("arena", "frost", {}, "scénario"),
        ("dungeon_boss", "shadow", {}, "rotation"),
        ("dungeon_pack", "aoe", {"aoe_filler": "fireball"}, "aoe_filler"),
    ],
)
def test_invalid_encounters_are_refused(game_data, scenario, rotation, opts, match):
    with pytest.raises(ValueError, match=match):
        encounter_analytic(game_data, scenario, 40, FROST, "Orc", rotation, **opts)
    with pytest.raises(ValueError, match=match):
        encounter_fight(game_data, scenario, 40, FROST, "Orc", rotation, random.Random(1), **opts)
