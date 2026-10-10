"""Rejeu des builds du Mage plus rapide (décision 230, point 2) : résultat de chaque cas gardé en cache par version,
empreinte des données et empreinte du code du calcul (un cas déjà calculé n'est jamais recalculé, un code changé l'est
toujours) ; cas répartis sur les cœurs, les plus longs d'abord ; faisceaux du leveling en parallèle quand il reste des
cœurs. Calcul simulé, sauf les tests `slow` qui comparent le parallèle au séquentiel sur de vrais cas."""

import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION

from forever import replay
from forever.manifest import write_manifest
from forever.update import _default_replay, replay_label


@pytest.fixture
def data(tmp_path):
    folder = tmp_path / "data"
    shutil.copytree(DATA_DIR, folder, ignore=shutil.ignore_patterns("__pycache__"))
    return folder


class Compute:
    def __init__(self):
        self.calls = []

    def __call__(self, case, data_dir):
        self.calls.append((case, data_dir))
        return {"talents": {"case": case}, "choices": {}, "alternative": {"better": False}, "provenance": {}}


def test_a_computed_case_is_written_with_its_code_and_parameters(tmp_path, data):
    compute = Compute()
    out = replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=compute)
    result = out["leveling-20", data]
    assert result["cached"] is False and result["advice"]["talents"] == {"case": "leveling-20"}
    path = tmp_path / "cache" / "builds" / replay_label(data) / "leveling-20.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["code"] == replay.code_fingerprint()
    assert doc["params"] == {"race": replay.RACE, "preset": replay.PRESET, "seed": replay.SEED}


def test_the_same_case_on_the_same_data_and_code_is_never_computed_again(tmp_path, data):
    replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=Compute())
    compute = Compute()
    out = replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=compute)
    assert compute.calls == [] and out["leveling-20", data]["cached"] is True
    assert out["leveling-20", data]["advice"]["talents"] == {"case": "leveling-20"}


def test_a_code_change_computes_again(tmp_path, data, monkeypatch):
    replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=Compute())
    monkeypatch.setattr(replay, "code_fingerprint", lambda: "autre-code")
    compute = Compute()
    replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=compute)
    assert compute.calls == [("leveling-20", data)]


def test_other_data_compute_again(tmp_path, data):
    replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=Compute())
    path = data / LOCAL_VERSION / "monsters.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["note_de_test"] = 1
    path.write_text(json.dumps(doc), encoding="utf-8")
    write_manifest(data)
    compute = Compute()
    replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=compute)
    assert compute.calls == [("leveling-20", data)]


def test_an_old_case_without_code_is_computed_again(tmp_path, data):
    folder = tmp_path / "cache" / "builds" / replay_label(data)
    folder.mkdir(parents=True)
    (folder / "leveling-20.json").write_text(json.dumps({"report": {"talents": {}}, "duration_s": 1}), "utf-8")
    compute = Compute()
    replay.replay_cases([("leveling-20", data)], tmp_path / "cache", compute=compute)
    assert compute.calls == [("leveling-20", data)]


def test_the_longest_cases_go_first():
    cases = ["pvp-bg-20", "leveling-20", "raid-60", "leveling-60", "dungeon-40"]
    assert replay.longest_first(cases)[:2] == ["leveling-60", "leveling-20"]
    assert replay.longest_first(cases)[2] == "raid-60"


@pytest.mark.parametrize(("cases", "cpus"), [(["leveling-60", "leveling-40", "dungeon-60"], 20), (["raid-20"] * 30, 8)])
def test_the_worker_budget_never_exceeds_the_cores(cases, cpus):
    outer, inner = replay.worker_budget(cases, cpus)
    assert 1 <= outer <= min(len(cases), cpus) and 1 <= inner <= replay.MAX_BEAM_WORKERS
    assert outer * inner <= max(cpus, outer)


def test_leveling_cases_get_parallel_beams_when_cores_are_free():
    outer, inner = replay.worker_budget(["leveling-60", "leveling-40"], 20)
    assert outer == 2 and inner == replay.MAX_BEAM_WORKERS


def test_the_update_replay_prefetches_in_parallel(make_deps):
    rep = _default_replay(make_deps())
    assert callable(getattr(rep, "prefetch", None))


def test_a_listing_replay_prefetches_nothing(make_deps):
    rep = _default_replay(make_deps(), listing=True)
    assert rep.prefetch([("mage_build", "leveling-20", DATA_DIR)]) == 0


@pytest.mark.slow
def test_parallel_cases_give_the_sequential_advice(tmp_path):
    """Deux vrais cas courts calculés dans deux processus, puis en séquentiel dans ce processus : mêmes conseils."""
    jobs = [("pvp-bg-20", DATA_DIR), ("raid-20", DATA_DIR)]
    parallel = replay.replay_cases(jobs, tmp_path / "par", workers=2)
    sequential = replay.replay_cases(jobs, tmp_path / "seq", workers=1)
    for job in jobs:
        assert parallel[job]["cached"] is False
        assert parallel[job]["advice"] == sequential[job]["advice"]


def test_the_package_entry_point_is_guarded():
    """Un processus de calcul réimporte le module principal sous un autre nom (Windows) : `python -m forever` ne doit
    alors rien lancer."""
    import runpy

    runpy.run_module("forever.__main__", run_name="__mp_main__")  # aucune sortie de la CLI, aucun SystemExit
