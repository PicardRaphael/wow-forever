"""SIM2 bloc 8 : optimisation de l'équipement par emplacement au niveau L, par wowsims corrigé (conditions des
tranches : talents du parcours au niveau, solo, cible du niveau) :

- départ : l'équipement porté (emplacement de wowsims -> objet) ;
- chaque candidat (choix de GearQuest au niveau, ou liste donnée) est essayé à sa place, même graine ; une bague ou
  un bijou est essayé sur ses deux emplacements, le meilleur est gardé ; un candidat déjà porté n'est pas essayé ;
- gain sur le départ, seuil de bruit (deux erreurs types de la différence) et verdict « meilleur » ou « non
  départagé » (règle de MS1) ; candidats triés par gain.

Simulateur fabriqué (dégâts = niveau + valeur fabriquée de chaque objet porté) : aucune valeur de jeu."""

import json
import subprocess
from pathlib import Path

import pytest
from test_sims_brackets import FROST_STEPS
from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import Sim

from forever.errors import InvalidArgumentError
from forever.sims.brackets import SLOT_NAMES, optimise_gear

VALUE = {100: 10.0, 101: 30.0, 200: 5.0, 201: 5.0, 300: 2.0, 301: 8.0, 400: 1.0}  # objet -> dégâts (fabriqués)


class GearSim(Sim):
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
        items = req["raid"]["parties"][0]["players"][0]["equipment"]["items"]
        dps = level + sum(VALUE.get(i.get("id"), 0.0) for i in items)
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": dps, "stdev": 1.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


EQUIPPED = {"Head": 100, "Chest": 200, "Finger1": 300, "Finger2": 400}
CANDIDATES = [
    {"slot": "Head", "item": 101},  # meilleur : +20
    {"slot": "Chest", "item": 201},  # égal : non départagé
    {"slot": "Finger", "item": 301},  # meilleur à la place de 400 (+7) qu'à la place de 300 (+6)
    {"slot": "Head", "item": 100},  # déjà porté : pas essayé
]


def test_each_candidate_is_tried_in_its_slot_and_ranked(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    sim = GearSim()
    out = optimise_gear(deps, preset="mage/dps/Fire", race="Human", level=25, equipped=EQUIPPED,
                        candidates=CANDIDATES, steps=FROST_STEPS, iterations=10000, runner=sim)  # fmt: skip
    assert out["base"]["dps"] == pytest.approx(25 + 10 + 5 + 2 + 1, rel=1e-12)
    rows = out["candidates"]
    assert [(r["item"], r["slot"], r["replaces"]) for r in rows] == [
        (101, "Head", 100),
        (301, "Finger2", 400),
        (201, "Chest", 200),
    ]
    assert rows[0]["gain"] == pytest.approx(20.0, rel=1e-12) and rows[0]["verdict"] == "meilleur"
    assert rows[1]["gain"] == pytest.approx(7.0, rel=1e-12) and rows[1]["verdict"] == "meilleur"
    assert rows[2]["gain"] == pytest.approx(0.0, abs=1e-12) and rows[2]["verdict"] == "non départagé"
    assert all(r["threshold"] > 0 for r in rows)
    assert set(sim.levels) == {25}
    first = sim.requests[0]["raid"]["parties"][0]["players"][0]
    assert first["equipment"]["items"][SLOT_NAMES.index("Head")] == {"id": 100}  # départ inchangé
    assert first["talentsString"] == "--0505" and "buffs" not in first
    assert out["provenance"]["certainty"] == "suppose"


def test_unknown_equipped_slot_is_refused(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    with pytest.raises(InvalidArgumentError, match="Tabard"):
        optimise_gear(deps, preset="mage/dps/Fire", race="Human", level=25, equipped={"Tabard": 1}, candidates=[],
                      steps=[], iterations=10, runner=GearSim())  # fmt: skip


def test_equipped_text_is_read_by_simulate(make_deps, tmp_path):
    from forever.sims.brackets import parse_equipped

    assert parse_equipped("Head:100, Finger1:300") == {"Head": 100, "Finger1": 300}
    with pytest.raises(InvalidArgumentError, match="Head"):
        parse_equipped("Head=100")
