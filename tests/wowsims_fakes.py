"""Faux dépôt épinglé de wowsims/forever et faux `wowsimcli` partagés par les tests de l'adaptateur (structure de
wowsims/forever ; aucune valeur de jeu : dégâts et poids fabriqués)."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import ClassVar

PRESETS_TS = """import { SavedTalents } from '@generated/proto/ui';
import fire from './apls/fire.apl.json';
import P1Json from './gear_sets/p1.gear.json';

export const P1Gear = PresetUtils.makePresetGear('P1', P1Json, { devOnly: true });
export const FireApl = PresetUtils.makePresetAPLRotation('Fire', fire);
export const FireTalents = PresetUtils.makePresetTalents('Fire', SavedTalents.create({ talentsString: '05-23-003' }));

export const DefaultOptions = MageOptions.create({
	classOptions: {
		defaultMageArmor: MageArmor.MageArmorMageArmor,
	},
});

export const DefaultRaidBuffs = RaidBuffs.create({
	arcaneBrilliance: true,
});

export const FireBuild = PresetUtils.makePresetBuild('Fire', {
	gear: P1Gear,
	talents: FireTalents,
	rotation: FireApl,
});
"""
ENCOUNTER = {"duration": 180, "durationVariation": 5, "targets": [{"name": "Raid Target", "level": 63}]}
BUILD = {
    "raidBuffs": {"arcaneBrilliance": True},
    "partyBuffs": {},
    "debuffs": {"curseOfElements": True},
    "player": {"race": "RaceDwarf", "class": "ClassShaman", "talentsString": "55-05-05",
               "elementalShaman": {"options": {"classOptions": {}}}, "rotation": {"type": "TypeAPL"},
               "equipment": {"items": [{"id": 1}]}},
    "encounter": ENCOUNTER,
}  # fmt: skip


def clone(tmp_path):
    root = tmp_path / "third_party" / "wowsims"
    specs = root / "forever" / "ui" / "specs"
    mage = specs / "mage" / "dps"
    (mage / "apls").mkdir(parents=True)
    (mage / "gear_sets").mkdir()
    (mage / "presets.ts").write_text(PRESETS_TS, encoding="utf-8")
    (mage / "apls" / "fire.apl.json").write_text(json.dumps({"type": "TypeAPL", "priorityList": []}), encoding="utf-8")
    (mage / "gear_sets" / "p1.gear.json").write_text(json.dumps({"items": [{"id": 16686}]}), encoding="utf-8")
    ele = specs / "shaman" / "elemental" / "builds"
    ele.mkdir(parents=True)
    (ele / "testing.build.json").write_text(json.dumps(BUILD), encoding="utf-8")
    binary = root / "wowsimcli-aaaaaaaaaaaa.exe"
    binary.write_bytes(b"binaire")
    pin = {"commit": "a" * 40, "committed_at": "2026-10-21T12:00:00+02:00", "binary": binary.name,
           "sha256": hashlib.sha256(b"binaire").hexdigest(), "go": "go1.27.0", "protoc": "36.0"}  # fmt: skip
    (root / "pin.json").write_text(json.dumps(pin), encoding="utf-8")
    return root


class Sim:
    """wowsimcli simulé : lit la requête, écrit un résultat dont les dégâts dépendent de la race (fabriqués)."""

    DPS: ClassVar[dict[str, float]] = {
        "RaceHuman": 100.0,
        "RaceGnome": 101.0,
        "RaceHighOrderSkyborne": 103.0,
        "RaceDwarf": 90.0,
    }

    def __init__(self):
        self.requests = []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        race = req["raid"]["parties"][0]["players"][0]["race"]
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": self.DPS[race], "stdev": 10.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


PROTO_STATS = "enum Stat {\n\t// x\n\tStatStrength = 0;\n\tStatIntellect = 1;\n\tStatSpellDamage = 2;\n}\n"


class WeightSim(Sim):
    """wowsimcli simulé : dégâts de base + poids fabriqués × statistiques ajoutées (`bonusStats`)."""

    WEIGHTS: ClassVar[list[float]] = [0.0, 0.4, 0.8]

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        bonus = req["raid"]["parties"][0]["players"][0].get("bonusStats", {}).get("stats", [])
        dps = 500.0 + sum(w * b for w, b in zip(self.WEIGHTS, bonus, strict=False))
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": dps, "stdev": 10.0}}]}]}, "iterationsDone": 10}
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")
