"""SIM2 bloc 3, sources réelles du calcul par tranche : objets absents de la base de wowsims écartés et nommés (jamais
remplacés), options inconnues refusées, erreur du simulateur rendue sans sa trace Go.

Dépôt, base d'objets et simulateur fabriqués (`wowsims_fakes`) : aucun calcul de jeu ici."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import FIXTURES
from wowsims_fakes import ENCOUNTER, Sim, clone

from forever.errors import InvalidArgumentError
from forever.sims.brackets import known_items, run_brackets, run_from_sources
from forever.sims.wowsims import WowsimsError, read_presets, request_for, run_sim


def _setup(make_deps):
    deps = make_deps()
    root = clone(deps.cache_dir)
    proto = root / "forever" / "proto"
    proto.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "sims" / "wowsims-64b21da" / "proto" / "mage.proto", proto / "mage.proto")
    doc = json.loads((root / "pin.json").read_text(encoding="utf-8"))
    doc["patches"] = {"sha256": "c" * 64, "files": ["0001-level.patch"]}
    (root / "pin.json").write_text(json.dumps(doc), encoding="utf-8")
    return deps, root


def _database(root, main, leftover):
    folder = root / "forever" / "assets" / "database"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "db.json").write_text(json.dumps({"items": [{"id": i} for i in main]}), encoding="utf-8")
    (folder / "leftover_db.json").write_text(json.dumps({"items": [{"id": i} for i in leftover]}), encoding="utf-8")


def test_known_items_read_both_databases(make_deps):
    _, root = _setup(make_deps)
    assert known_items(root / "forever") is None  # clone sans base : aucun filtre
    _database(root, [2800], [6614])
    assert known_items(root / "forever") == {2800, 6614}


def test_unknown_items_are_left_out_and_named(make_deps):
    deps, root = _setup(make_deps)
    _database(root, [2800], [6614])
    sim = Sim()
    picks = [{"slot": "Back", "item": 6614}, {"slot": "Chest", "item": 2800}, {"slot": "Head", "item": 999999}]
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=[],
                       picks_at=lambda _level: picks, iterations=10, runner=sim)  # fmt: skip
    row = out["rows"][0]
    assert row["unknown_items"] == [999999] and row["equipment"] == [6614, 2800]
    items = sim.requests[0]["raid"]["parties"][0]["players"][0]["equipment"]["items"]
    assert items[0] == {} and items[3] == {"id": 6614} and items[4] == {"id": 2800}
    assert any("absents de la base de wowsims" in a for a in out["provenance"]["assumptions"])


def test_unknown_path_or_gear_option_is_refused(make_deps):
    deps, _ = _setup(make_deps)
    with pytest.raises(InvalidArgumentError, match="Parcours"):
        run_from_sources(deps, preset="mage/dps/Fire", race="Human", brackets="25", path="maxroll")
    with pytest.raises(InvalidArgumentError, match="Équipement"):
        run_from_sources(deps, preset="mage/dps/Fire", race="Human", brackets="25", path="none", gear="bis")


class ErrorSim(Sim):
    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        err = {"type": "ErrorOutcomeError", "message": "No item with id: 1769\nStack Trace:\ngoroutine 58 [running]:"}
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps({"error": err}), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def test_simulator_error_is_named_without_its_go_trace(make_deps):
    deps, root = _setup(make_deps)
    fire = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    with pytest.raises(WowsimsError) as caught:
        run_sim(deps.cache_dir, request_for(fire, race="RaceHuman", encounter=ENCOUNTER), runner=ErrorSim())
    assert caught.value.message == "wowsims : No item with id: 1769"
