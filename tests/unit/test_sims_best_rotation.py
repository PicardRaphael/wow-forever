"""SIM2 bloc 14 : meilleure rotation par tranche (demande du 2026-11-08) : toutes les rotations des préréglages de la
même spécialisation (APL du dépôt de wowsims) sont essayées dans les conditions de la tranche, même graine ; la
meilleure est gardée et nommée, les autres rendues avec leur écart. `rotation="preset"` garde celle du préréglage.
Dépôt et simulateur fabriqués : aucune valeur de jeu."""

import json
import subprocess
from pathlib import Path

from test_sims_brackets import FROST_STEPS
from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import Sim

from forever.sims.brackets import run_brackets


class RotationSim(Sim):
    """Dégâts = 10 × nombre d'entrées de la rotation (fabriqué)."""

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        rot = req["raid"]["parties"][0]["players"][0]["rotation"]
        dps = 10.0 * len(rot.get("priorityList") or [])
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": dps, "stdev": 1.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def _second_mage_build(deps):
    builds = deps.cache_dir / "third_party" / "wowsims" / "forever" / "ui" / "specs" / "mage" / "dps" / "builds"
    builds.mkdir(parents=True, exist_ok=True)
    player = {"class": "ClassMage", "talentsString": "05-23-003", "equipment": {"items": [{"id": 1}]},
              "mage": {"options": {}}, "rotation": {"type": "TypeAPL", "priorityList": [{"a": 1}, {"a": 2}]}}  # fmt: skip
    (builds / "Long.build.json").write_text(json.dumps({"player": player}), encoding="utf-8")


def test_the_best_rotation_of_the_spec_is_kept_and_named(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    _second_mage_build(deps)
    sim = RotationSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=FROST_STEPS, picks_at=None,
                       iterations=10, runner=sim, rotation="best")  # fmt: skip
    row = out["rows"][0]
    assert row["dps"] == 20.0 and row["rotation"] == "mage/dps/Long"
    alts = {a["rotation"]: a["dps"] for a in row["rotations"]}
    assert alts == {"mage/dps/Long": 20.0, "mage/dps/Fire": 0.0}


def test_preset_rotation_is_kept_on_request(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    _second_mage_build(deps)
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=FROST_STEPS, picks_at=None,
                       iterations=10, runner=RotationSim(), rotation="preset")  # fmt: skip
    assert out["rows"][0]["rotation"] == "mage/dps/Fire" and "rotations" not in out["rows"][0]
