"""SIM2 §10 (demande du 2026-11-10 : « les builds sont au DPS, pas au leveling : assez de mana, assez de vie ») :
objectif leveling en solo.

- Sortie de wowsims lue en entier : mana dépensée (gains de mana négatifs), mana gagnée, dégâts subis, temps avant
  la panne de mana (`tto`), secondes sans mana, chance de mort, par combat (moyennes par itération).
- Rencontre de leveling : une cible normale du niveau (PV des journaux, armure et DPS d'attaque d'ExpectedStat), qui
  frappe le joueur (déclaré tank), coups sans écart ni puissance d'attaque, durée = temps pour tuer (deux passes).
- Sonde de repos : un tirage d'une itération, rotation vide, journal de débogage : mana et vie maximales
  (« of N total »), régénération hors incantation (tics `{OtherID: 2, Tag: 2}`).
- Cycle : combat, course, repos (boisson et repas du niveau, régénération) ; XP par heure avec repos ; classement des
  rotations à l'XP par heure, le DPS restant affiché.
- Valeurs de créature absentes : combat de référence gardé, raison dite (rien d'inventé).

Dépôt et simulateur fabriqués (valeurs arbitraires) ; données de jeu lues par les fonctions du moteur."""

import json
import subprocess
from pathlib import Path

import pytest
from test_sims_best_rotation import _second_mage_build
from test_sims_brackets import FROST_STEPS
from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import ENCOUNTER, Sim

from forever.engine.dungeon import SECONDS_PER_HOUR
from forever.engine.mana import consumables
from forever.engine.monsters import grind_xp_per_hour_rested, kills_per_bar, rest_per_kill
from forever.engine.xp import mob_kill_xp
from forever.gamedata import build_game_data
from forever.sims import leveling
from forever.sims.brackets import run_brackets
from forever.sims.wowsims import fight_metrics
from forever.store import load_version

MOB = {"hp": 300.0, "armor": 100.0, "auto_attack_dps": 4.0, "certainty": "certain", "source": "fabriqué"}
POOL_MANA, POOL_HP, TICK = 1000.0, 500.0, 2.0  # sonde fabriquée : tics de 2 de mana toutes les 0,1 s
TAKEN_PER_S = 5.0


def _probe_logs() -> str:
    lines = [f"[{t / 10:.2f}] [x (#1)] Gained {TICK:.3f} mana from {{OtherID: 2, Tag: 2}} "
             f"({POOL_MANA:.3f} --> {POOL_MANA:.3f}) of {POOL_MANA:.0f} total." for t in range(1, 6)]  # fmt: skip
    lines.append(f"[1.49] [x (#1)] Spent 10.000 health from {{OtherID: 9}} ({POOL_HP:.3f} --> 490.000) of "
                 f"{POOL_HP:.0f} total.")  # fmt: skip
    return "\n".join(lines)


class LevelingSim(Sim):
    """Combat : DPS = 10 + 10 × entrées de la rotation ; mana dépensée par seconde = 1e6 × entrées ; dégâts subis
    5 par seconde. Sonde (débogage) : journal fabriqué, aucun dégât."""

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        n = req["simOptions"]["iterations"]
        if req["simOptions"].get("debugFirstIteration"):
            res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": 0.0, "stdev": 0.0}}]}]},
                   "iterationsDone": n, "logs": _probe_logs()}  # fmt: skip
        else:
            entries = len(req["raid"]["parties"][0]["players"][0]["rotation"].get("priorityList") or [])
            dur = float(req["encounter"]["duration"])
            spent = 1e6 * entries * dur
            player = {
                "dps": {"avg": 10.0 + 10.0 * entries, "stdev": 1.0},
                "tto": {"avg": 7.0}, "secondsOomAvg": 0.5, "chanceOfDeath": 0.0,
                "resources": [
                    {"id": {"spellId": 1}, "type": "ResourceTypeMana", "gain": -spent * n},
                    {"id": {"otherId": "OtherActionManaRegen", "tag": 1}, "type": "ResourceTypeMana", "gain": 3.0 * n},
                    {"id": {"otherId": "OtherActionDamageTaken"}, "type": "ResourceTypeHealth",
                     "gain": -TAKEN_PER_S * dur * n},
                ],
            }  # fmt: skip
            res = {"raidMetrics": {"parties": [{"players": [player]}]}, "iterationsDone": n}
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def test_fight_metrics_read_mana_spent_gained_damage_taken_and_oom_per_iteration():
    player = {"tto": {"avg": 42.0}, "secondsOomAvg": 3.0, "chanceOfDeath": 0.25, "resources": [
        {"id": {"spellId": 7}, "type": "ResourceTypeMana", "gain": -400.0},
        {"id": {"spellId": 8}, "type": "ResourceTypeMana", "gain": -200.0},
        {"id": {"otherId": "OtherActionManaRegen", "tag": 1}, "type": "ResourceTypeMana", "gain": 100.0},
        {"id": {"otherId": "OtherActionDamageTaken"}, "type": "ResourceTypeHealth", "gain": -80.0},
        {"id": {"spellId": 9}, "type": "ResourceTypeRage", "gain": -50.0},
    ]}  # fmt: skip
    m = fight_metrics(player, 2)
    assert m == {"mana_spent": 300.0, "mana_gained": 50.0, "damage_taken": 40.0, "tto_s": 42.0, "oom_s": 3.0,
                 "death_chance": 0.25}  # fmt: skip
    assert fight_metrics({}, 1) == {"mana_spent": 0.0, "mana_gained": 0.0, "damage_taken": 0.0, "tto_s": None,
                                    "oom_s": 0.0, "death_chance": 0.0}  # fmt: skip


def test_probe_logs_give_the_pools_and_the_regen_while_not_casting():
    pools = leveling.pools_from_logs(_probe_logs())
    assert pools == {"max_mana": POOL_MANA, "max_hp": POOL_HP, "rest_mana_per_s": pytest.approx(TICK / 0.1)}
    assert leveling.pools_from_logs("") == {"max_mana": None, "max_hp": None, "rest_mana_per_s": 0.0}


def test_leveling_encounter_is_one_normal_mob_of_the_level_that_hits_the_player():
    enc = leveling.leveling_encounter(ENCOUNTER, 25, MOB, duration=12.5)
    assert enc["duration"] == 12.5 and enc["durationVariation"] == 0
    assert enc["executeProportion20"] == pytest.approx(0.2) and enc["executeProportion35"] == pytest.approx(0.35)
    (t,) = enc["targets"]
    assert t["level"] == 25 and t["canCrush"] is False and t["damageSpread"] == 0
    swing = float(ENCOUNTER["targets"][0].get("swingSpeed") or leveling.DEFAULT_SWING_S)
    assert t["swingSpeed"] == swing and t["minBaseDamage"] == pytest.approx(MOB["auto_attack_dps"] * swing)
    stats = t["stats"]
    assert stats[leveling.STAT_ARMOR] == MOB["armor"] and stats[leveling.STAT_HEALTH] == MOB["hp"]
    assert sum(stats) == MOB["armor"] + MOB["hp"]  # ni puissance d'attaque ni autre statistique de boss


def test_cycle_counts_the_rest_needed_after_the_run_between_mobs():
    # 100 de mana nets par monstre, 2 par seconde de régénération en courant 10 s : 80 à boire à 40 par seconde
    rest, limiter = rest_per_kill(mana_net=100.0, mana_regen=2.0, mana_rest_rate=40.0, hp_lost=10.0, hp_regen=1.0,
                                  hp_rest_rate=5.0, between=10.0)  # fmt: skip
    assert rest == pytest.approx(2.0) and limiter == "mana"
    rest, limiter = rest_per_kill(mana_net=0.0, mana_regen=0.0, mana_rest_rate=0.0, hp_lost=60.0, hp_regen=1.0,
                                  hp_rest_rate=5.0, between=10.0)  # fmt: skip
    assert rest == pytest.approx(10.0) and limiter == "vie"
    assert rest_per_kill(mana_net=5.0, mana_regen=1.0, mana_rest_rate=1.0, hp_lost=0.0, hp_regen=0.0,
                         hp_rest_rate=1.0, between=10.0) == (0.0, None)  # fmt: skip
    assert grind_xp_per_hour_rested(50.0, 10.0, 8.0, 2.0) == pytest.approx(50.0 * SECONDS_PER_HOUR / 20.0)
    assert kills_per_bar(1000.0, 250.0) == pytest.approx(4.0) and kills_per_bar(1000.0, 0.0) is None


def _leveling(make_deps, tmp_path, mob=MOB):
    deps = brackets_setup(make_deps, tmp_path)
    _second_mage_build(deps)
    sim = LevelingSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=FROST_STEPS, picks_at=None,
                       iterations=10, runner=sim, objective="leveling", mob_at=lambda level: mob)  # fmt: skip
    return deps, sim, out


def test_leveling_fight_lasts_the_time_to_kill_and_the_mob_hits_the_player(make_deps, tmp_path):
    _, sim, _ = _leveling(make_deps, tmp_path)
    fights = [r for r in sim.requests if not r["simOptions"].get("debugFirstIteration")]
    for req in fights:
        assert req["raid"]["tanks"] == [{"type": "Player", "index": 0}]
        assert req["encounter"]["targets"][0]["stats"][leveling.STAT_HEALTH] == MOB["hp"]
    # deux passes par rotation : amorce, puis durée = PV / DPS de l'amorce
    durations = sorted(float(r["encounter"]["duration"]) for r in fights)
    assert durations == sorted([leveling.PRIME_S, leveling.PRIME_S, MOB["hp"] / 10.0, MOB["hp"] / 30.0])
    probes = [r for r in sim.requests if r["simOptions"].get("debugFirstIteration")]
    assert len(probes) == 1 and probes[0]["simOptions"]["iterations"] == 1
    assert not probes[0]["raid"]["parties"][0]["players"][0]["rotation"].get("priorityList")


def test_rotations_are_ranked_by_xp_per_hour_with_rest_not_by_dps(make_deps, tmp_path):
    deps, _, out = _leveling(make_deps, tmp_path)
    row = out["rows"][0]
    # « Long » fait trois fois les dégâts mais vide la barre de mana : la rotation du préréglage gagne au leveling
    assert row["rotation"] == "mage/dps/Fire" and row["objective"] == "leveling"
    by_name = {a["rotation"]: a for a in row["rotations"]}
    assert by_name["mage/dps/Long"]["dps"] > by_name["mage/dps/Fire"]["dps"]
    assert by_name["mage/dps/Long"]["xp_per_hour"] < by_name["mage/dps/Fire"]["xp_per_hour"]
    gd = build_game_data(load_version(deps))
    lv = row["leveling"]
    ttk = MOB["hp"] / 10.0
    assert row["ttk_s"] == pytest.approx(ttk)
    assert lv["max_mana"] == POOL_MANA and lv["max_hp"] == POOL_HP
    assert lv["damage_taken"] == pytest.approx(TAKEN_PER_S * ttk) and lv["mana_spent"] == 0.0
    water, food = consumables(gd, 25)
    between = gd.leveling.default_run_between_s
    hp_regen = gd.leveling.rest_hp_regen_fraction * POOL_HP
    rest, limiter = rest_per_kill(mana_net=0.0, mana_regen=TICK / 0.1, mana_rest_rate=water + TICK / 0.1,
                                  hp_lost=TAKEN_PER_S * ttk, hp_regen=hp_regen, hp_rest_rate=food + hp_regen,
                                  between=between)  # fmt: skip
    assert lv["rest_s"] == pytest.approx(rest) and lv["limited_by"] == limiter
    xp = mob_kill_xp(gd, 25, 25).xp
    assert row["xp_per_hour"] == pytest.approx(grind_xp_per_hour_rested(xp, ttk, between, rest))
    assert row["xp_per_hour_no_rest"] >= row["xp_per_hour"]
    assert lv["tto_s"] == 7.0 and lv["oom_s"] == 0.5 and lv["death_chance"] == 0.0
    text = " ".join(out["provenance"]["assumptions"])
    assert "leveling" in text and "ExpectedStat" in text and "boisson" in text and "XP par heure" in text


def test_missing_creature_values_keep_the_reference_fight_and_say_why(make_deps, tmp_path):
    _, sim, out = _leveling(make_deps, tmp_path, mob=None)
    row = out["rows"][0]
    assert "leveling" not in row and row["objective"] == "dps"
    assert "ExpectedStat" in row["leveling_missing"] or "créature" in row["leveling_missing"]
    assert all("tanks" not in r["raid"] for r in sim.requests)


def test_default_mob_reads_hit_points_from_monsters_and_the_rest_from_expected_stat(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    gd = build_game_data(load_version(deps))
    scaling = {"creature": {"health": [1.0] * 60, "armor": [float(i) for i in range(60)],
                            "auto_attack_dps": [0.5 * i for i in range(60)]}}  # fmt: skip
    mob = leveling.mob_from(gd, scaling, 25)
    from forever.engine.monsters import mob_hp

    hp = mob_hp(gd, 25)
    assert mob["hp"] == hp.value and mob["certainty"] == hp.certainty
    assert mob["armor"] == 24.0 and mob["auto_attack_dps"] == 12.0
    assert leveling.mob_from(gd, {}, 25) is None


def test_analysis_key_names_the_objective_model(make_deps, tmp_path):
    from forever.sims.analysis import analysis_path

    deps = brackets_setup(make_deps, tmp_path)
    assert leveling.MODEL in str(analysis_path(deps, "mage/dps/Fire", "Human"))


GEAR_DPS = {501: 2.0, 502: 1.0}  # objet -> dégâts ajoutés (fabriqués)
GEAR_TAKEN = {502: 0.0}  # objet -> dégâts subis par seconde (fabriqués ; 50 sinon)


class GearLevelingSim(LevelingSim):
    """Leveling avec équipement : DPS = 10 + valeur des objets portés ; dégâts subis 50 par seconde, 0 avec 502."""

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        if req["simOptions"].get("debugFirstIteration"):
            return super().__call__(args, cwd, timeout)
        self.requests.append(req)
        n = req["simOptions"]["iterations"]
        ids = [i.get("id") for i in req["raid"]["parties"][0]["players"][0]["equipment"]["items"]]
        taken = min([GEAR_TAKEN[i] for i in ids if i in GEAR_TAKEN] or [50.0])
        dur = float(req["encounter"]["duration"])
        player = {"dps": {"avg": 10.0 + sum(GEAR_DPS.get(i, 0.0) for i in ids), "stdev": 0.01},
                  "tto": {"avg": 99.0}, "secondsOomAvg": 0.0, "chanceOfDeath": 0.0,
                  "resources": [{"id": {"otherId": "OtherActionDamageTaken"}, "type": "ResourceTypeHealth",
                                 "gain": -taken * dur * n}]}  # fmt: skip
        res = {"raidMetrics": {"parties": [{"players": [player]}]}, "iterationsDone": n}
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def test_gear_is_ranked_by_xp_per_hour_with_rest_when_leveling(make_deps, tmp_path):
    """Équipement au leveling (demande du 2026-11-11 : « temps d'arrêt… réfléchis ») : chaque objet essayé dans le
    cycle de leveling (monstre du niveau qui frappe, repos) et classé à l'XP par heure ; l'objet qui supprime les
    dégâts subis (pas de repos) passe devant celui qui donne plus de DPS. À l'objectif DPS, l'inverse."""
    from forever.sims.brackets import optimise_gear

    deps = brackets_setup(make_deps, tmp_path)
    cands = [{"slot": "Head", "item": 501}, {"slot": "Chest", "item": 502}]
    kw = {
        "preset": "mage/dps/Fire",
        "race": "Human",
        "level": 25,
        "equipped": {},
        "candidates": cands,
        "steps": FROST_STEPS,
        "iterations": 10,
    }
    lev = optimise_gear(deps, **kw, runner=GearLevelingSim(), objective="leveling", mob_at=lambda level: MOB)
    assert [r["item"] for r in lev["candidates"]] == [502, 501]
    assert lev["objective"] == "leveling" and lev["base"]["xp_per_hour"] > 0
    assert all("xp_per_hour" in r and "xp_gain" in r for r in lev["candidates"])
    assert lev["candidates"][0]["xp_gain"] > lev["candidates"][1]["xp_gain"] > 0
    dps = optimise_gear(deps, **kw, runner=GearLevelingSim())
    assert [r["item"] for r in dps["candidates"]] == [501, 502] and dps["objective"] == "dps"
