"""Coefficients de puissance des sorts lus dans le client (T04e, registre G4).

Sources : tests/fixtures/wago/1.60.1.70009/enUS/SpellEffect.csv (EffectBonusCoefficient, DifficultyID 0) ; niveaux
des rangs : forever/data/1.60.1.70009/spells.json ; pénalité des sorts de bas niveau : mechanics.json
(`coefficient.low_level`, `coefficient.low_level_default`). Personnage de référence du seed : niveau 60, Orc, 500 de
puissance des sorts, 10 % de critique (seed/forever-mage/tests/run_all.py)."""

import csv
import json

import pytest
from conftest import COMBATLOG, LOCAL_VERSION, WAGO_70009

from forever.engine import character, coefficient, expected_cast
from forever.engine.damage import dot_tick_damage, dot_tick_period_s, dot_tick_times, roll_base_damage
from forever.engine.spells import dot_coefficient, dot_ticks
from forever.gamedata import load_game_data
from forever.manifest import write_manifest
from forever.pipeline.combatlog import read_log
from forever.sim.leveling_mc import mc

SPELLS = (
    "frostbolt",
    "fireball",
    "fire_blast",
    "scorch",
    "pyroblast",
    "frostfire_bolt",
    "ice_lance",
    "arcane_blast",
    "arcane_missiles",
    "arcane_explosion",
    "frost_nova",
    "cone_of_cold",
    "blast_wave",
    "blizzard",
    "flamestrike",
)


def approx(x):
    return pytest.approx(x, rel=1e-12, abs=1e-15)


def client_coefficients():
    """(sort, indice d'effet) -> EffectBonusCoefficient, lu directement dans la fixture du client."""
    with open(WAGO_70009 / "enUS" / "SpellEffect.csv", encoding="utf-8", newline="") as f:
        return {
            (int(r["SpellID"]), int(r["EffectIndex"])): float(r["EffectBonusCoefficient"])
            for r in csv.DictReader(f)
            if r["DifficultyID"] == "0"
        }


@pytest.fixture
def ch(game_data):
    return character(game_data, 60, "Orc", {"sp": 500, "spell_crit": 0.10})


def edit_version_file(data_dir, name, change):
    path = data_dir / LOCAL_VERSION / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    write_manifest(data_dir)  # modification voulue : l'intégrité reste valide


def test_coefficient_matches_client_table(game_data):
    """Pour chaque rang des 15 sorts : coups directs + éclairs canalisés × tics, coefficients lus dans SpellEffect.csv
    (Frost Nova 0,029 ; Cone of Cold et Blast Wave 0,129 ; Ice Lance 0 ; Blizzard 8 × 0,042 ; Arcane Missiles r8
    5 × 0,286), sans pénalité des sorts de bas niveau."""
    table = client_coefficients()
    checked = 0
    for key in SPELLS:
        for rank, scaling in zip(game_data.spells[key].ranks, game_data.scaling[key], strict=True):
            expected = sum(
                table[(c.spell_id, c.index)] * (c.ticks if c.kind == "channel" else 1)
                for c in scaling.components
                if c.kind in ("direct", "channel")
            )
            assert coefficient(game_data, key, rank, low_level_penalty=False) == approx(expected), (key, rank.position)
            checked += 1
    assert checked == 99
    last = {key: game_data.spells[key].ranks[-1] for key in SPELLS}
    assert coefficient(game_data, "frost_nova", last["frost_nova"]) == 0.02899999917
    assert coefficient(game_data, "cone_of_cold", last["cone_of_cold"]) == 0.12899999321
    assert coefficient(game_data, "blast_wave", last["blast_wave"]) == 0.12899999321
    assert coefficient(game_data, "blizzard", last["blizzard"]) == approx(8 * 0.04199999943)
    assert coefficient(game_data, "arcane_missiles", last["arcane_missiles"]) == approx(5 * 0.28600001335)


def test_low_level_penalty_applies_to_client_coefficient(game_data):
    """Frostbolt r1 (niveau 4) : 0,407 × (1 - 0,0375 × (20 - 4)) par défaut (clé des données à vrai), 0,407 sans
    pénalité ; à partir du rang 4 (niveau 20), la pénalité est sans effet."""
    ranks = game_data.spells["frostbolt"].ranks
    assert coefficient(game_data, "frostbolt", ranks[0]) == approx(0.40700000525 * (1 - 0.0375 * 16))
    assert coefficient(game_data, "frostbolt", ranks[0], low_level_penalty=True) == approx(0.1628000021)
    assert coefficient(game_data, "frostbolt", ranks[0], low_level_penalty=False) == 0.40700000525
    for r in ranks[3:]:
        assert coefficient(game_data, "frostbolt", r) == coefficient(game_data, "frostbolt", r, low_level_penalty=False)


def test_low_level_default_comes_from_data(make_deps, data_copy):
    edit_version_file(
        data_copy, "mechanics.json", lambda d: d["values"]["coefficient.low_level_default"].update(value=False)
    )
    gd = load_game_data(make_deps(data_dir=data_copy))
    assert coefficient(gd, "frostbolt", gd.spells["frostbolt"].ranks[0]) == 0.40700000525


def test_client_coefficient_reads_data(make_deps, data_copy):
    """Preuve que le coefficient vient de spell_scaling.json : le changer change le coefficient."""
    edit_version_file(
        data_copy,
        "spell_scaling.json",
        lambda d: d["spells"]["frostbolt"][10]["components"][0].update(bonus_coefficient=0.5),
    )
    gd = load_game_data(make_deps(data_dir=data_copy))
    assert coefficient(gd, "frostbolt", gd.spells["frostbolt"].ranks[10]) == 0.5


def test_ice_lance_coefficient(game_data):
    """Ice Lance : 0 dans le client (six rangs, probable, test en jeu E4) ; 0,1429 en mode seed (estimation)."""
    for r in game_data.spells["ice_lance"].ranks:
        assert coefficient(game_data, "ice_lance", r) == 0.0
    assert coefficient(game_data, "ice_lance", game_data.spells["ice_lance"].ranks[-1], rules="seed") == 0.1429


def test_seed_rules_keep_the_seed_formula(game_data):
    ranks = game_data.spells["frostbolt"].ranks
    assert coefficient(game_data, "frostbolt", ranks[1], rules="seed") == approx(0.26871428571428574)
    assert coefficient(game_data, "frostbolt", ranks[10], rules="seed") == approx(0.8142857142857142)


def test_unknown_rules_and_seed_without_penalty_are_refused(game_data):
    rank = game_data.spells["frostbolt"].ranks[0]
    with pytest.raises(ValueError, match="rules"):
        coefficient(game_data, "frostbolt", rank, rules="classic")
    with pytest.raises(ValueError, match="low_level_penalty"):
        coefficient(game_data, "frostbolt", rank, rules="seed", low_level_penalty=False)
    assert coefficient(game_data, "frostbolt", rank, rules="seed", low_level_penalty=True) == coefficient(
        game_data, "frostbolt", rank, rules="seed"
    )


def test_frostbolt_forever_values(game_data, ch):
    """Frostbolt r11 (457-493) à 500 de puissance des sorts : (475 + 0,814 × 500) × (1 + 0,1 × 0,5), toucher 0,96."""
    e = expected_cast(game_data, "frostbolt", 60, {}, ch)
    assert e["direct_per_hit"] == approx((475 + 0.81400001049 * 500) * 1.05)
    assert e["direct_per_hit"] == approx(926.1000055072501)
    assert e["dmg"] == approx(889.05600528696)
    seed = expected_cast(game_data, "frostbolt", 60, {}, ch, rules="seed")
    assert seed["direct_per_hit"] == approx(926.25)


def test_fireball_rank12_is_the_same_in_both_modes(game_data, ch):
    """Fireball r12 : coefficient 1 dans le client comme dans la formule (3,5 s / 3,5), DoT sans puissance."""
    assert expected_cast(game_data, "fireball", 60, {}, ch) == expected_cast(
        game_data, "fireball", 60, {}, ch, rules="seed"
    )


def test_roll_base_damage_uses_the_rules(game_data, ch):
    r = game_data.spells["frostbolt"].ranks[10]
    assert roll_base_damage(game_data, "frostbolt", r, ch, 0.0) == approx(457 + 0.81400001049 * 500)
    assert roll_base_damage(game_data, "frostbolt", r, ch, 0.0, rules="seed") == approx(457 + 0.8142857142857142 * 500)


# --- DoT : puissance des sorts par tic et période du client (registre A17) ---------------------------------------
# Fixture SpellEffect.csv : Pyroblast r8 (18809) effet 1 aura 3, 0.15000000596 par tic, 3000 ms ; Flamestrike r6 : sort
# déclenché 1279990, 0.03200000152 par tic, période 2000 ms de l'aura 226 de 10216 ; Frostfire Bolt r3 (1237313) : 0,
# 3000 ms ; Fireball : 0, 2000 ms. Rangs (spells.json) : Pyroblast r1 44 sur 12 s, r8 212 sur 12 s ; Flamestrike r6
# 332 sur 8 s.


@pytest.fixture
def ch534(game_data):
    return character(game_data, 60, "Orc", {"sp": 534, "spell_crit": 0.0})


def rank_of(gd, key, n):
    return gd.spells[key].ranks[n - 1]


def test_dot_coefficient_per_tick(game_data):
    gd = game_data
    assert dot_coefficient(gd, "pyroblast", rank_of(gd, "pyroblast", 8)) == 0.15000000596
    assert dot_coefficient(gd, "flamestrike", rank_of(gd, "flamestrike", 6)) == 0.03200000152
    assert dot_coefficient(gd, "frostfire_bolt", rank_of(gd, "frostfire_bolt", 3)) == 0.0
    assert dot_coefficient(gd, "fireball", rank_of(gd, "fireball", 12)) == 0.0
    assert dot_coefficient(gd, "frostbolt", rank_of(gd, "frostbolt", 11)) == 0.0  # pas de DoT
    assert dot_coefficient(gd, "pyroblast", rank_of(gd, "pyroblast", 8), rules="seed") == 0.0


def test_low_level_penalty_applies_to_tick_coefficient(game_data):
    """Flamestrike r1 (niveau 16) : pénalité des sorts de bas niveau aussi sur le tic (décision 2, suppose)."""
    table = client_coefficients()
    r1 = game_data.spells["flamestrike"].ranks[0]
    assert r1.level == 16
    (dot,) = [c for c in game_data.scaling["flamestrike"][0].components if c.kind == "dot"]
    raw = table[(dot.spell_id, dot.index)]
    assert raw > 0
    assert dot_coefficient(game_data, "flamestrike", r1, low_level_penalty=False) == raw
    assert dot_coefficient(game_data, "flamestrike", r1) == approx(raw * (1 - 0.0375 * 4))


def test_dot_ticks(game_data):
    gd = game_data
    assert dot_ticks(gd, "pyroblast", rank_of(gd, "pyroblast", 8)) == 4
    assert dot_ticks(gd, "pyroblast", rank_of(gd, "pyroblast", 8), rules="seed") == 6
    assert dot_ticks(gd, "frostfire_bolt", rank_of(gd, "frostfire_bolt", 3)) == 3
    assert dot_ticks(gd, "fireball", rank_of(gd, "fireball", 12)) == 4
    assert dot_ticks(gd, "fireball", rank_of(gd, "fireball", 12), rules="seed") == 4
    assert dot_ticks(gd, "frostbolt", rank_of(gd, "frostbolt", 11)) == 0


def test_dot_ticks_follow_client_period(game_data):
    def times(key, n, **kw):
        r = rank_of(game_data, key, n)
        return dot_tick_times(game_data, r.dot_duration_s, dot_tick_period_s(game_data, key, r, **kw))

    assert times("pyroblast", 8) == [3, 6, 9, 12]
    assert times("frostfire_bolt", 3) == [3, 6, 9]
    assert times("fireball", 12) == [2, 4, 6, 8]
    assert times("pyroblast", 8, rules="seed") == [2, 4, 6, 8, 10, 12]
    assert dot_tick_times(game_data, 8) == [2, 4, 6, 8]  # sans période : leveling.dot_tick_s, inchangé
    assert dot_tick_damage(game_data, 12, 1.1, 4) == approx(3.3)


def test_tick_times_match_tick_count_for_every_dot(game_data):
    """Le Monte Carlo pose len(dot_tick_times) tics : en forever, c'est le nombre de tics du composant du client."""
    checked = 0
    for key, spell in game_data.spells.items():
        for r in spell.ranks:
            if not r.dot_total:
                continue
            t = dot_tick_times(game_data, r.dot_duration_s, dot_tick_period_s(game_data, key, r))
            assert len(t) == dot_ticks(game_data, key, r), (key, r.position)
            checked += 1
    assert checked > 20


def test_pyroblast_dot_scales_with_spell_power(game_data, ch534):
    """Pyroblast r8 à 534 de puissance des sorts, sans critique : 4 × (53 + 0,15 × 534) ; seed : 212 sans puissance."""
    pts = {"pyroblast": 1}
    e = expected_cast(game_data, "pyroblast", 60, pts, ch534)
    assert e["crit"] == 0.0 and e["dmg_mult"] == 1.0
    assert e["dot"] == approx(4 * (53 + 0.15000000596 * 534))
    assert e["dot"] == approx(532.40001273056)
    assert expected_cast(game_data, "pyroblast", 60, pts, ch534, rules="seed")["dot"] == 212


def test_flamestrike_dot_scales_with_spell_power(game_data, ch534):
    e = expected_cast(game_data, "flamestrike", 60, {}, ch534)
    assert e["dot"] == approx(4 * (83 + 0.03200000152 * 534))
    assert e["dot"] == approx(400.35200324672)


def test_pyroblast_r1_tick(game_data):
    """Prédiction du test en jeu E3 : tic de Pyroblast r1 à 20 de puissance des sorts = 11 + 0,15 × 20, sans talent."""
    r1 = game_data.spells["pyroblast"].ranks[0]
    ticks = dot_ticks(game_data, "pyroblast", r1)
    per_tick = dot_coefficient(game_data, "pyroblast", r1) * 20
    tick = dot_tick_damage(game_data, r1.dot_total, 1.0, ticks, sp_per_tick=per_tick)
    assert tick == approx(11 + 0.15000000596 * 20)
    assert tick == approx(14.0000001192)


def test_fireball_dot_has_no_spell_power_in_log(game_data):
    """Journal WoWCombatLog-092726_150346 : Fireball r3 (sort 145) lancé à 13 de puissance des sorts (bloc avancé de
    SPELL_CAST_SUCCESS) ; ses trois tics valent 2. Le tic du moteur (coefficient du client, 0) donne 2 ; un
    coefficient de 0,15 par tic, comme Pyroblast, en donnerait près de 4 : une seule hypothèse tient."""
    _, events = read_log(COMBATLOG / "WoWCombatLog-092726_150346.anon.txt.gz")
    events = [e for e in events if e.spell and e.spell[0] == 145]
    (cast,) = [e for e in events if e.name == "SPELL_CAST_SUCCESS"]
    sp = cast.advanced.spell_power
    ticks = [e.suffix["amount"] for e in events if e.name == "SPELL_PERIODIC_DAMAGE"]
    assert sp == 13 and ticks == [2, 2, 2]
    r3 = game_data.spells["fireball"].ranks[2]
    n = dot_ticks(game_data, "fireball", r3)
    ours = dot_tick_damage(game_data, r3.dot_total, 1.0, n, sp_per_tick=dot_coefficient(game_data, "fireball", r3) * sp)
    alternative = dot_tick_damage(game_data, r3.dot_total, 1.0, n, sp_per_tick=0.15 * sp)
    assert round(ours) == 2
    assert round(alternative) >= 4


def test_monte_carlo_uses_the_client_dot_period(make_deps, data_copy):
    """Fireball : période du client portée à 4 s (2 tics) dans une copie des données : le Monte Carlo forever change,
    le mode seed (période leveling.dot_tick_s) non."""

    def slow_dot(doc):
        for r in doc["spells"]["fireball"]:
            for c in r["components"]:
                if c["kind"] == "dot":
                    c.update(period_ms=4000, ticks=2)

    base = load_game_data(make_deps(data_dir=data_copy))
    edit_version_file(data_copy, "spell_scaling.json", slow_dot)
    gd = load_game_data(make_deps(data_dir=data_copy))
    seed_mode = {"mob_source": "seed", "spell_level": "rank", "rules": "seed"}
    args = (20, {}, "Orc", "fire", 40)
    assert mc(gd, *args, seed=3, spell_level="rank") != mc(base, *args, seed=3, spell_level="rank")
    assert mc(gd, *args, seed=3, **seed_mode) == mc(base, *args, seed=3, **seed_mode)
