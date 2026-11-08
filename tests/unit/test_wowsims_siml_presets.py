"""SIM2 bloc 9 : spécialisations manquantes lues dans le dépôt épinglé de wowsims.

- Builds au format SIML (`ui/specs/<classe>/<spé>/builds/*.siml` : Chasseur, Paladin Vindicte) : lus par le binaire
  épinglé lui-même (`wowsimcli siml parse -json <fichier>`, lecture locale), jamais par un analyseur recopié ; un
  fichier illisible est écarté sans arrêter les autres.
- Rotation déclarée dans un objet (`export const X = { ...PresetUtils.makePresetAPLRotation('nom', apl), … }`,
  Druide félin) : reconnue comme les autres.
Dépôt et binaire fabriqués dans `tmp_path` : aucune valeur de jeu."""

import json
import subprocess

from wowsims_fakes import clone

from forever.sims.wowsims import read_presets

PLAYER = {
    "class": "ClassHunter",
    "equipment": {"items": [{"id": 1}]},
    "hunter": {"options": {"classOptions": {"petType": "Raptor"}}},
    "talentsString": "53-005",
    "rotation": {"type": "TypeAPL", "priorityList": []},
}


class SimlRunner:
    """`wowsimcli siml parse -json <fichier>` simulé : rend le joueur fabriqué, ou échoue pour `casse.siml`."""

    def __init__(self):
        self.calls = []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        self.calls.append(args)
        if args[-1].endswith("casse.siml"):
            return subprocess.CompletedProcess(args, 1, "", "erreur de lecture simulée")
        return subprocess.CompletedProcess(args, 0, json.dumps({"player": PLAYER}), "")


def test_siml_builds_are_read_by_the_pinned_binary(tmp_path):
    root = clone(tmp_path)
    builds = root / "forever" / "ui" / "specs" / "hunter" / "dps" / "builds"
    builds.mkdir(parents=True)
    (builds / "bm.siml").write_text("siml 1\n", encoding="utf-8")
    (builds / "casse.siml").write_text("siml 1\n", encoding="utf-8")
    runner = SimlRunner()
    presets = {p.key: p for p in read_presets(root / "forever", runner=runner)}
    bm = presets["hunter/dps/bm"]
    assert bm.class_token == "ClassHunter" and bm.spec_field == "hunter" and bm.talents == "53-005"
    assert bm.spec_options == PLAYER["hunter"] and bm.rotation == PLAYER["rotation"] and bm.items == 1
    assert "hunter/dps/casse" not in presets  # illisible : écarté
    parse = [c for c in runner.calls if c[1:4] == ["siml", "parse", "-json"]]
    assert len(parse) == 2 and parse[0][0].endswith("wowsimcli-aaaaaaaaaaaa.exe")


def test_without_siml_builds_the_binary_is_not_called(tmp_path):
    root = clone(tmp_path)
    runner = SimlRunner()
    read_presets(root / "forever", runner=runner)
    assert runner.calls == []


CAT_TS = """import AdaptiveApl from './apls/adaptive.apl.json';
import Level60GearJson from './gear_sets/default.gear.json';
export const Level60Gear = PresetUtils.makePresetGear('Level 60', Level60GearJson, {});
export const JVMES_APL = {
\t...PresetUtils.makePresetAPLRotation('Adaptive Cat', AdaptiveApl),
\ttooltip: 'x',
};
export const CatTalents = PresetUtils.makePresetTalents('Cat', SavedTalents.create({ talentsString: '050022-532' }));
"""


def test_rotation_declared_inside_an_object_is_read(tmp_path):
    root = clone(tmp_path)
    spec = root / "forever" / "ui" / "specs" / "druid" / "feralcat"
    (spec / "apls").mkdir(parents=True)
    (spec / "gear_sets").mkdir()
    (spec / "presets.ts").write_text(CAT_TS, encoding="utf-8")
    (spec / "apls" / "adaptive.apl.json").write_text(json.dumps({"type": "TypeAPL", "priorityList": [1]}), "utf-8")
    (spec / "gear_sets" / "default.gear.json").write_text(json.dumps({"items": [{"id": 7}]}), "utf-8")
    presets = {p.key: p for p in read_presets(root / "forever", runner=SimlRunner())}
    cat = presets["druid/feralcat/défaut"]
    assert cat.rotation == {"type": "TypeAPL", "priorityList": [1]} and cat.talents == "050022-532"
    assert cat.spec_field == "feralCatDruid"
