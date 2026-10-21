"""Adaptateur mince de wowsims/forever au niveau 60 (décisions 293 et 294 ; plan des simulateurs §7, étape 2) :

- préréglages lus dans le clone épinglé, sans exécuter de code : builds complets (`ui/specs/<classe>/<spé>/builds/*.build.json`)
  et builds de `presets.ts` (`makePresetBuild` : équipement, talents, rotation APL, options de la spé, buffs) ;
- requête de combat (`RaidSimRequest`) : un joueur, le combat de référence du dépôt, graine fixe ;
- lancement du binaire épinglé (vérifié par son empreinte), lecture du résultat (dégâts par seconde, écart type) ;
- comparaisons appariées : même préréglage, même graine, seule la race change.

Clone et binaire fabriqués dans `tmp_path` (structure de wowsims/forever) ; exécuteur simulé, aucun calcul de jeu."""

import json

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


HUNTER_TS = """import WeaveAPL from './apls/default.apl.json';
import P1GearJson from './gear_sets/p1.gear.json';

export const P1Gear = PresetUtils.makePresetGear('P1', P1GearJson, { devOnly: true });
export const WeaveAPLRotation = PresetUtils.makePresetAPLRotation('Melee Weave', WeaveAPL);
const talents = (name: string, talentsString: string) => ({ name, data: SavedTalents.create({ talentsString }) });
export const SurvivalWeaveTalents = talents('SV Weave', '-0053-5502');
export const NoPetOptions = HunterOptions.create({ classOptions: { petType: PetType.PetNone } });

const build = (name, gear, talentPreset, rotation, options, distanceFromTarget) =>
	PresetUtils.makePresetBuild(name, { gear, talents: talentPreset, rotation, settings: { name } });

export const Builds = [
	build('SV Weave', P1Gear, SurvivalWeaveTalents, WeaveAPLRotation, NoPetOptions, 12),
];
"""
ROGUE_TS = """import P1MutiGear from './gear_sets/p1_muti.gear.json';

export const TALENTS_MUTILATE_ASN = {
	name: 'Asn Muti',
	data: SavedTalents.create({
		talentsString: '0053-3023',
	}),
};
export const DEFAULT_SIMPLE_ROTATION = RogueRotation.create({ useBackstab: false, useExposeArmor: false });
export const SIMPLE_ROTATION = PresetUtils.makePresetSimpleRotation('Configurable', Spec.SpecRogue, DEFAULT_SIMPLE_ROTATION);
export const P1_MUTI_GEAR = PresetUtils.makePresetGear('Mutilate', P1MutiGear, { devOnly: true });

export const PRESET_BUILD_MUTILATE_ASN = PresetUtils.makePresetBuild('Asn Muti', {
	talents: TALENTS_MUTILATE_ASN,
	rotation: SIMPLE_ROTATION,
	gear: P1_MUTI_GEAR,
});
"""


def test_hunter_build_helper_and_rogue_simple_rotation_are_read(tmp_path):
    """Formes des préréglages du Chasseur (fonction `build(nom, équipement, talents, rotation, options, distance)`,
    talents par `talents(nom, chaîne)`) et du Voleur (talents en objet ; rotation « simple » : le moteur ne la joue
    pas, seule l'interface web la convertit en APL : le build prend l'APL par défaut de la spé)."""
    root = clone(tmp_path) / "forever" / "ui" / "specs"
    hunter = root / "hunter" / "dps"
    (hunter / "apls").mkdir(parents=True)
    (hunter / "gear_sets").mkdir()
    (hunter / "presets.ts").write_text(HUNTER_TS, encoding="utf-8")
    (hunter / "apls" / "default.apl.json").write_text(json.dumps({"type": "TypeAPL"}), encoding="utf-8")
    (hunter / "gear_sets" / "p1.gear.json").write_text(json.dumps({"items": [{"id": 1}]}), encoding="utf-8")
    rogue = root / "rogue" / "dps"
    (rogue / "gear_sets").mkdir(parents=True)
    (rogue / "presets.ts").write_text(ROGUE_TS, encoding="utf-8")
    (rogue / "gear_sets" / "p1_muti.gear.json").write_text(json.dumps({"items": [{"id": 2}]}), encoding="utf-8")
    (rogue / "apls").mkdir()
    (rogue / "apls" / "default.apl.json").write_text(json.dumps({"type": "TypeAPL", "x": 1}), encoding="utf-8")
    (rogue / "presets.ts").write_text(
        "import DefaultAPL from './apls/default.apl.json';\n"
        "export const ROTATION = PresetUtils.makePresetAPLRotation('Default', DefaultAPL);\n" + ROGUE_TS,
        encoding="utf-8",
    )
    presets = {p.key: p for p in read_presets(root.parent.parent)}
    sv = presets["hunter/dps/SV Weave"]
    assert sv.talents == "-0053-5502" and sv.rotation == {"type": "TypeAPL"}
    assert sv.spec_options == {"options": {"classOptions": {"petType": "PetNone"}}}
    assert sv.distance == 12
    asn = presets["rogue/dps/Asn Muti"]
    assert asn.talents == "0053-3023"
    assert asn.rotation == {"type": "TypeAPL", "x": 1}  # APL par défaut de la spé, jamais TypeSimple
    req = request_for(sv, race="RaceDwarf", encounter=ENCOUNTER)
    assert req["raid"]["parties"][0]["players"][0]["distanceFromTarget"] == 12


def test_consumables_are_resolved_from_the_generated_table(tmp_path):
    from forever.sims.wowsims import ts_literal

    text = "{ flaskId: Consumables.FlaskOfTest.id, elixirIds: [Consumables.ElixirOfTest.id], foodId: Consumables.Unknown.id }"
    value, _ = ts_literal(text, 0, {"FlaskOfTest": 900001, "ElixirOfTest": 900002})
    assert value == {"flaskId": 900001, "elixirIds": [900002]}


def test_local_objects_are_spread_and_aliases_followed():
    """`...classOptions` (objet local) étalé dans les options, `DefaultOptions = NoPetOptions` suivi : sans eux, le
    Chasseur partait sans munitions et le moteur plantait."""
    from forever.sims.wowsims import _from_presets_ts

    assert _from_presets_ts is not None
    from forever.sims.wowsims import ts_literal

    refs = {"classOptions": {"ammo": "ThoriumHeadedArrow", "petUptime": 1}}
    value, _ = ts_literal("{ classOptions: { ...classOptions, petType: PetType.PetNone } }", 0, None, refs)
    assert value == {"classOptions": {"ammo": "ThoriumHeadedArrow", "petUptime": 1, "petType": "PetNone"}}
