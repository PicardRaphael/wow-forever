"""SIM2 bloc 7 : poids des statistiques par tranche de niveaux, calculés par wowsims corrigé dans les conditions de
chaque tranche (niveau, talents du parcours, équipement, solo, cible du niveau), par tirages appariés comme au niveau
60 (`stat_weights`) : un combat sans bonus, puis un par statistique avec quelques points de plus, même graine.

Simulateur fabriqué (dégâts = niveau + gains fabriqués par statistique) : aucune valeur de jeu."""

import json
import subprocess
from pathlib import Path

import pytest
from test_sims_brackets import FROST_STEPS
from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import PROTO_STATS, Sim

from forever.errors import ForeverError
from forever.sims.brackets import run_brackets
from forever.sims.wowsims import STAT_DELTA

GAIN = {1: 2.0, 2: 0.5}  # indice du proto fabriqué (Intellect, SpellDamage) -> dégâts par point (fabriqués)


class WeightLevelSim(Sim):
    """Dégâts = niveau + somme(gain × bonus) ; garde le niveau de chaque combat."""

    def __init__(self):
        super().__init__()
        self.levels = []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        flag = next((a for a in args if a.startswith("--forever-level=")), None)
        level = int(flag.split("=")[1]) if flag else 60
        self.levels.append(level)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        bonus = ((req["raid"]["parties"][0]["players"][0].get("bonusStats") or {}).get("stats")) or []
        dps = level + sum(GAIN.get(i, 0.0) * v for i, v in enumerate(bonus))
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": dps, "stdev": 1.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def _deps(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    proto = deps.cache_dir / "third_party" / "wowsims" / "forever" / "proto"
    (proto / "common.proto").write_text(PROTO_STATS, encoding="utf-8")
    return deps


def test_each_bracket_has_its_weights_at_its_level(make_deps, tmp_path):
    deps = _deps(make_deps, tmp_path)
    sim = WeightLevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="10-19,20-29", steps=FROST_STEPS,
                       picks_at=None, iterations=10, runner=sim, stats=["StatIntellect", "StatSpellDamage"],
                       reference="StatSpellDamage")  # fmt: skip
    for row, level in zip(out["rows"], (15, 25), strict=True):
        w = row["weights"]
        assert w["per_point"] == pytest.approx({"StatIntellect": 2.0, "StatSpellDamage": 0.5}, rel=1e-12)
        assert w["normalised"] == pytest.approx({"StatIntellect": 4.0, "StatSpellDamage": 1.0}, rel=1e-12)
        assert w["reference"] == "StatSpellDamage" and w["delta"] == STAT_DELTA and w["base_dps"] == level
    assert set(sim.levels) == {15, 25}  # chaque combat des poids au niveau de sa tranche
    bonus = [r["raid"]["parties"][0]["players"][0].get("bonusStats") for r in sim.requests]
    assert any(b and b["stats"][1] == STAT_DELTA for b in bonus)  # un combat avec le bonus d'Intelligence
    assert any("poids" in a for a in out["provenance"]["assumptions"])


def test_without_stats_no_weights_are_computed(make_deps, tmp_path):
    deps = _deps(make_deps, tmp_path)
    sim = WeightLevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=FROST_STEPS, picks_at=None,
                       iterations=10, runner=sim)  # fmt: skip
    assert "weights" not in out["rows"][0] and len(sim.requests) == 1


def test_unknown_stat_is_refused_in_its_row(make_deps, tmp_path):
    deps = _deps(make_deps, tmp_path)
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=FROST_STEPS, picks_at=None,
                       iterations=10, runner=WeightLevelSim(), stats=["StatNope"])  # fmt: skip
    assert "StatNope" in out["rows"][0]["weights_error"]["message"]


def test_stats_are_read_from_the_simulate_parameter(make_deps, tmp_path):
    from forever.sims.report import simulate

    with pytest.raises(ForeverError, match="reference"):
        simulate(_deps(make_deps, tmp_path), "brackets", preset="mage/dps/Fire", race="Human", brackets="25",
                 path="none", gear="none", stats="Intellect,SpellDamage", reference="Nope")  # fmt: skip
