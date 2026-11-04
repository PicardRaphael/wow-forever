"""Faux MythicSim épinglé (binaire Rust `forever-engine` et clone de son fork Go) partagés par les tests de MS1
(décision 301 ; structure des deux dépôts, aucune valeur de jeu : dégâts fabriqués). Les extraits réels lus pour la
conversion des talents viennent de `tests/fixtures/sims/` (révisions dans son README)."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import ClassVar

FIXTURES = Path(__file__).parent / "fixtures" / "sims"
GO_REVISION = "f" * 40
PRESETS_TS = """import { SavedTalents } from '@generated/proto/ui';
import BlankAPL from './apls/default.apl.json';
import ArcaneApl from './apls/arcane.apl.json';
import FireApl from './apls/fire.apl.json';
import P0BisGear from './gear_sets/p0.bis.gear.json';

export const BLANK_APL = PresetUtils.makePresetAPLRotation('Blank', BlankAPL);
export const ROTATION_PRESET_ARCANE = PresetUtils.makePresetAPLRotation('Arcane', ArcaneApl);
export const ROTATION_PRESET_FIRE = PresetUtils.makePresetAPLRotation('Fire', FireApl);
export const TalentsP1Fire = PresetUtils.makePresetTalents('Fire DPS', SavedTalents.create({ talentsString: '-5' }));

export const DefaultOptions = MageOptions.create({
	classOptions: {
		defaultMageArmor: MageArmor.MageArmorMageArmor,
	},
});

export const DefaultRaidBuffs = RaidBuffs.create({
	arcaneBrilliance: true,
});

export const GEAR_P0_BIS = PresetUtils.makePresetGear('Pre-BiS', P0BisGear);
"""


def install(tmp_path, wowsims_proto=True):
    """Épinglage, binaire et fork Go de MythicSim dans `<tmp>/third_party/mythicsim` ; avec `wowsims_proto`, le
    message des talents du Mage dans le faux clone de wowsims (à créer avant par `wowsims_fakes.clone`)."""
    root = tmp_path / "third_party" / "mythicsim"
    spec = root / "go" / "ui" / "specs" / "mage" / "dps"
    (spec / "apls").mkdir(parents=True)
    (spec / "gear_sets").mkdir()
    (spec / "presets.ts").write_text(PRESETS_TS, encoding="utf-8")
    for name in ("default", "arcane", "fire"):
        apl = {"type": "TypeAPL", "priorityList": [{"action": {"castSpell": {"spellId": {"otherId": name}}}}]}
        (spec / "apls" / f"{name}.apl.json").write_text(json.dumps(apl), encoding="utf-8")
    (spec / "gear_sets" / "p0.bis.gear.json").write_text(json.dumps({"items": [{"id": 1}]}), encoding="utf-8")
    trees = root / "go" / "ui" / "sim" / "talents" / "trees"
    trees.mkdir(parents=True)
    shutil.copy(FIXTURES / "mythicsim" / "go" / "ui" / "sim" / "talents" / "trees" / "mage.json", trees)
    mage = root / "engine" / "src" / "classes" / "mage"
    mage.mkdir(parents=True)
    shutil.copy(FIXTURES / "mythicsim" / "engine" / "src" / "classes" / "mage" / "prepare.rs", mage)
    binary = root / "forever-engine-bbbbbbbbbbbb.exe"
    binary.write_bytes(b"moteur")
    pin = {"repo": "https://github.com/sage3648/mythicsim-forever-engine.git", "commit": "b" * 40,
           "committed_at": "2026-11-04T15:39:27+11:00", "binary": binary.name,
           "sha256": hashlib.sha256(b"moteur").hexdigest(), "toolchain": "1.99.1",
           "go_repo": "https://github.com/sage3648/mythicsim-forever-engine-go.git", "go_revision": GO_REVISION,
           "built_at": "2026-11-04T10:00:00Z", "status": "compilé"}  # fmt: skip
    (root / "pin.json").write_text(json.dumps(pin), encoding="utf-8")
    if wowsims_proto:
        proto = tmp_path / "third_party" / "wowsims" / "forever" / "proto"
        proto.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURES / "wowsims" / "proto" / "mage.proto", proto)
    return root


class Engine:
    """`forever-engine sim --request … --outfile … --gate` simulé : dégâts fabriqués par race ; `refuse` donne le
    refus de préparation (code 5), `gate` celui de la porte (code 3)."""

    DPS: ClassVar[dict[str, float]] = {"RaceGnome": 200.0, "RaceHuman": 198.0, "RaceDwarf": 150.0}

    def __init__(self, refuse=None, gate=None):
        self.requests, self.calls, self.refuse, self.gate = [], [], refuse, gate

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        self.calls.append(args)
        req = json.loads(Path(args[args.index("--request") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        if self.refuse:
            out = json.dumps({"prepared": False, "refusal": {"code": self.refuse[0], "reason": self.refuse[1]}})
            return subprocess.CompletedProcess(args, 5, out, "")
        if self.gate:
            report = {"scenario_id": "rust", "supported": False, "reasons": [self.gate], "refusals": []}
            return subprocess.CompletedProcess(args, 3, json.dumps(report), "")
        race = req["raid"]["parties"][0]["players"][0]["race"]
        res = {
            "identity": {"engine": "forever-engine", "go_reference_revision": GO_REVISION,
                         "client_build": "1.60.1.70425"},
            "result": {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": self.DPS.get(race, 199.0), "stdev": 20.0}}]}]},
                       "iterationsDone": req["simOptions"]["iterations"]},
        }  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


class Both:
    """Exécuteur unique des deux moteurs simulés : `wowsimcli` (wowsims_fakes.Sim) ou `forever-engine`."""

    def __init__(self, wowsims, engine):
        self.wowsims, self.engine = wowsims, engine

    def __call__(self, args, cwd, timeout=None):
        if "forever-engine" in Path(args[0]).name:
            return self.engine(args, cwd, timeout)
        return self.wowsims(args, cwd, timeout)
