"""Familier du Chasseur comparé à la demande (demande du 2026-11-10 : « tout doit être calculable à la demande ») :
même préréglage, même race, même combat, même graine, seul le familier change (`petType` des options de la spé) ;
familles lues dans le proto épinglé (`enum PetType`, sans `PetNone`). Dépôt et simulateur fabriqués : aucune valeur
de jeu."""

import json
import subprocess
from pathlib import Path

import pytest
from wowsims_fakes import ENCOUNTER, clone

from forever.sims.wowsims import WowsimsError, compare_pets, pet_types, read_presets

PROTO = "enum PetType {\n\tPetNone = 0;\n\tBat = 1;\n\tCat = 6;\n\tWolf = 19;\n}\nPetType pet_type = 3;\n"
BONUS = {"Bat": 1.0, "Cat": 5.0, "Wolf": 3.0}


class PetSim:
    def __init__(self):
        self.requests = []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        pet = req["raid"]["parties"][0]["players"][0]["hunter"]["options"]["classOptions"]["petType"]
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": 100.0 + BONUS[pet], "stdev": 1.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def _hunter(tmp_path):
    root = clone(tmp_path)
    (root / "forever" / "proto").mkdir(parents=True, exist_ok=True)
    (root / "forever" / "proto" / "hunter.proto").write_text(PROTO, encoding="utf-8")
    builds = root / "forever" / "ui" / "specs" / "hunter" / "dps" / "builds"
    builds.mkdir(parents=True)
    build = {"player": {"class": "ClassHunter", "talentsString": "53", "equipment": {"items": [{"id": 1}]},
                        "hunter": {"options": {"classOptions": {"petType": "Raptor"}}},
                        "rotation": {"type": "TypeAPL"}}, "encounter": ENCOUNTER}  # fmt: skip
    (builds / "bm.build.json").write_text(json.dumps(build), encoding="utf-8")
    return root


def test_pet_types_come_from_the_pinned_proto(tmp_path):
    root = _hunter(tmp_path)
    assert pet_types(root / "forever") == ["Bat", "Cat", "Wolf"]


def test_pets_are_compared_with_only_the_pet_changing(tmp_path):
    root = _hunter(tmp_path)
    bm = {p.key: p for p in read_presets(root / "forever")}["hunter/dps/bm"]
    sim = PetSim()
    rows = compare_pets(tmp_path, bm, "RaceOrc", ENCOUNTER, runner=sim)
    assert [r["pet"] for r in rows] == ["Cat", "Wolf", "Bat"]
    assert rows[0]["gap_to_best"] == 0 and rows[-1]["gap_to_best"] < 0
    assert {r["simOptions"]["randomSeed"] for r in sim.requests} == {sim.requests[0]["simOptions"]["randomSeed"]}
    assert bm.spec_options["options"]["classOptions"]["petType"] == "Raptor"  # préréglage d'origine intact
    assert [r["pet"] for r in compare_pets(tmp_path, bm, "RaceOrc", ENCOUNTER, pets=["Wolf"], runner=PetSim())] == [
        "Wolf"
    ]
    mage = {p.key: p for p in read_presets(root / "forever")}["mage/dps/Fire"]
    with pytest.raises(WowsimsError, match="familier"):
        compare_pets(tmp_path, mage, "RaceOrc", ENCOUNTER, runner=PetSim())
