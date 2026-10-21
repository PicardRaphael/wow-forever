"""Adaptateur mince de wowsims/forever au niveau 60 (décisions 293 et 294 ; plan des simulateurs §7, étape 2) :

- préréglages lus dans le clone épinglé, sans exécuter de code : builds complets (`ui/specs/<classe>/<spé>/builds/*.build.json`)
  et builds de `presets.ts` (`makePresetBuild` : équipement, talents, rotation APL, options de la spé, buffs) ;
- requête de combat (`RaidSimRequest`) : un joueur, le combat de référence du dépôt, graine fixe ;
- lancement du binaire épinglé (vérifié par son empreinte), lecture du résultat (dégâts par seconde, écart type) ;
- comparaisons appariées : même préréglage, même graine, seule la race change.

Clone et binaire fabriqués dans `tmp_path` (structure de wowsims/forever) ; exécuteur simulé, aucun calcul de jeu."""

import pytest
from wowsims_fakes import ENCOUNTER, PROTO_STATS, Sim, WeightSim, clone

from forever.sims.wowsims import (
    WowsimsError,
    compare_races,
    read_presets,
    request_for,
    run_sim,
)


def test_presets_are_read_from_builds_and_presets_ts(tmp_path):
    presets = {p.key: p for p in read_presets(clone(tmp_path) / "forever")}
    fire = presets["mage/dps/Fire"]
    assert fire.class_token == "ClassMage" and fire.talents == "05-23-003"
    assert fire.rotation == {"type": "TypeAPL", "priorityList": []} and fire.equipment == {"items": [{"id": 16686}]}
    assert fire.spec_field == "mage"
    assert fire.spec_options == {"options": {"classOptions": {"defaultMageArmor": "MageArmorMageArmor"}}}
    assert fire.raid_buffs == {"arcaneBrilliance": True}
    ele = presets["shaman/elemental/testing"]
    assert ele.class_token == "ClassShaman" and ele.race == "RaceDwarf" and ele.debuffs == {"curseOfElements": True}


def test_request_has_one_player_the_reference_encounter_and_a_fixed_seed(tmp_path):
    root = clone(tmp_path)
    presets = {p.key: p for p in read_presets(root / "forever")}
    req = request_for(presets["mage/dps/Fire"], race="RaceGnome", encounter=ENCOUNTER, iterations=500, seed=7)
    player = req["raid"]["parties"][0]["players"][0]
    assert player["race"] == "RaceGnome" and player["class"] == "ClassMage" and player["talentsString"] == "05-23-003"
    assert player["mage"]["options"]["classOptions"]["defaultMageArmor"] == "MageArmorMageArmor"
    assert req["encounter"] == ENCOUNTER and req["simOptions"] == {"iterations": 500, "randomSeed": 7}
    assert req["raid"]["buffs"] == {"arcaneBrilliance": True} and req["type"] == "SimTypeIndividual"


def test_run_checks_the_pinned_binary_and_reads_the_result(tmp_path):
    root = clone(tmp_path)
    preset = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    out = run_sim(tmp_path, request_for(preset, race="RaceHuman", encounter=ENCOUNTER), runner=Sim())
    assert out["dps"] == 100.0 and out["stdev"] == 10.0 and out["iterations"] > 0
    assert out["source"]["commit"] == "a" * 40 and out["source"]["sha256"]
    (root / "wowsimcli-aaaaaaaaaaaa.exe").write_bytes(b"autre")  # binaire changé depuis l'épinglage : refus
    with pytest.raises(WowsimsError, match="empreinte"):
        run_sim(tmp_path, request_for(preset, race="RaceHuman", encounter=ENCOUNTER), runner=Sim())


def test_race_comparison_is_paired(tmp_path):
    root = clone(tmp_path)
    preset = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    sim = Sim()
    rows = compare_races(tmp_path, preset, ["RaceHuman", "RaceGnome", "RaceHighOrderSkyborne"], ENCOUNTER, runner=sim)
    assert [r["race"] for r in rows] == ["RaceHighOrderSkyborne", "RaceGnome", "RaceHuman"]  # du meilleur au moins bon
    assert rows[0]["gap_to_best"] == 0.0 and rows[-1]["gap_to_best"] == pytest.approx(-3.0)
    seeds = {r["simOptions"]["randomSeed"] for r in sim.requests}
    assert len(seeds) == 1  # même graine pour toutes les races
    talents = {r["raid"]["parties"][0]["players"][0]["talentsString"] for r in sim.requests}
    assert talents == {"05-23-003"}  # seule la race change


def test_missing_pin_says_how_to_build(tmp_path):
    with pytest.raises(WowsimsError, match="forever sims update"):
        run_sim(tmp_path, {"raid": {}}, runner=Sim())


def test_stat_weights_are_paired_and_normalised(tmp_path):
    from forever.sims.wowsims import stat_names, stat_weights

    root = clone(tmp_path)
    (root / "forever" / "proto").mkdir(parents=True, exist_ok=True)
    (root / "forever" / "proto" / "common.proto").write_text(PROTO_STATS, encoding="utf-8")
    assert stat_names(root / "forever") == ["StatStrength", "StatIntellect", "StatSpellDamage"]
    preset = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    sim = WeightSim()
    out = stat_weights(tmp_path, preset, ["StatIntellect", "StatSpellDamage"], reference="StatSpellDamage", runner=sim)
    assert out["per_point"]["StatIntellect"] == pytest.approx(0.4) and out["per_point"][
        "StatSpellDamage"
    ] == pytest.approx(0.8)
    assert out["normalised"] == {"StatIntellect": pytest.approx(0.5), "StatSpellDamage": pytest.approx(1.0)}
    assert len({r["simOptions"]["randomSeed"] for r in sim.requests}) == 1  # tirages appariés
    lengths = {
        len(r["raid"]["parties"][0]["players"][0].get("bonusStats", {}).get("stats", [0, 0, 0])) for r in sim.requests
    }
    assert lengths == {3}  # tableau complet du proto épinglé
