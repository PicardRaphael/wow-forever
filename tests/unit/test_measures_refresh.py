"""`forever measures refresh` (T04c, bloc E) : relance des mesures, comparaison, écriture après accord seulement.

Monde de test (dossier temporaire) : journaux des fixtures (Durotar, puis les Tarides), carnet de Questie de la fixture
comme SavedVariable, copie des données où `monsters.json` est construit sur le premier journal seul (PNJ 3986 écarté de
l'ajustement, comme `test_monsters_cli.py`). Preuve B1 du registre : n = 50 sur les deux journaux.
Ignite : `synthetic/ignite_pairs.txt` (README des fixtures : part 40 %, critiques de 200 et 150 à 1 s, tics de 70 à
+3 s et +5 s)."""

import dataclasses
import hashlib
import json
import shutil

import pytest
from conftest import COMBATLOG, FIXTURES, LOCAL_VERSION, REAL_LOG, SYNTHETIC_LOGS, FakeHttp, read_json

from forever.cli import main
from forever.engine.damage import predict_ignite_ticks
from forever.manifest import write_manifest
from forever.pipeline.combatlog import read_log
from forever.pipeline.measure import find_mine, ignite_ticks, monster_hp
from forever.pipeline.monsters import build_monsters
from forever.pipeline.questie import read_questie
from forever.pipeline.refresh import collect_sources

SECOND_LOG = COMBATLOG / "WoWCombatLog-092726_150346.anon.txt.gz"
QUESTIE = FIXTURES / "questie" / "11.38.0"
JOURNEY = FIXTURES / "questie" / "journey" / "Questie.lua"
IGNITE_LOG = SYNTHETIC_LOGS / "ignite_pairs.txt"
IGNITE_AURA = 412538  # aura d'Ignite du client (Spell.csv)
EXCLUDE = [3986]


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode() + p.read_bytes())
    return h.hexdigest()


def table_for(*logs):
    observations, conflicts = [], []
    for log in logs:
        found, clash = monster_hp(list(read_log(log)[1]), log=log.name)
        observations += found
        conflicts += clash
    return build_monsters(
        observations,
        read_questie(QUESTIE),
        LOCAL_VERSION,
        conflicts=conflicts,
        logs=[log.name for log in logs],
        fit_exclude=EXCLUDE,
    )


@pytest.fixture
def world(tmp_path, data_copy):
    logs = tmp_path / "Logs"
    logs.mkdir()
    shutil.copy(REAL_LOG, logs)
    shutil.copy(SECOND_LOG, logs)
    sv = tmp_path / "SavedVariables"
    sv.mkdir()
    shutil.copy(JOURNEY, sv / "Questie.lua")
    installed = data_copy / LOCAL_VERSION / "monsters.json"
    installed.write_bytes((json.dumps(table_for(REAL_LOG), ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(data_copy)
    return {"logs": logs, "sv": sv, "data": data_copy}


def refresh(capsys, make_deps, world, *extra, confirm=None, http=None):
    deps = make_deps(http=http or FakeHttp.failing(), data_dir=world["data"])
    deps = dataclasses.replace(deps, confirm=confirm)
    argv = ["measures", "refresh", "--logs", str(world["logs"]), "--sv", str(world["sv"]), "--questie", str(QUESTIE)]
    argv += ["--fit-exclude", "3986", *extra, "--json"]
    code = main(argv, deps)
    return code, json.loads(capsys.readouterr().out), deps


def refuse(prompt):
    return False


def accept(prompt):
    return True


def never(prompt):
    raise AssertionError("confirm ne doit pas être appelé")


def test_collect_sources(world):
    found = collect_sources(world["logs"], world["sv"])
    assert [p.name for p in found.logs] == [REAL_LOG.name, SECOND_LOG.name]
    assert [p.name for p in found.saved_variables] == ["Questie.lua"]


def test_refresh_shows_the_new_log_and_the_changes(capsys, make_deps, world):
    code, out, _ = refresh(capsys, make_deps, world, "--dry-run", confirm=never)
    assert code == 0 and out["status"] == "simulation"
    diff = out["diff"]
    assert diff["logs"]["new"] == [SECOND_LOG.name] and diff["logs"]["gone"] == []
    assert diff["npcs"]["added"]  # PNJ des Tarides
    assert diff["changed"] is True
    b1 = diff["b1"]
    assert b1["measured"]["n"] == b1["registry"]["n"] == 50 and b1["same"] is True
    assert "preuves" in b1["proposed"]
    assert out["written"] == []


def test_refused_confirmation_writes_nothing(capsys, make_deps, world, tmp_path):
    before = tree_sha(world["data"])
    code, out, deps = refresh(capsys, make_deps, world, confirm=refuse)
    assert code == 0 and out["status"] == "refusé" and out["written"] == []
    assert tree_sha(world["data"]) == before
    assert not (deps.cache_dir / "measures" / "last.json").exists()


def test_no_confirmation_callback_means_refusal(capsys, make_deps, world):
    before = tree_sha(world["data"])
    code, out, _ = refresh(capsys, make_deps, world, confirm=None)
    assert code == 0 and out["status"] == "refusé" and tree_sha(world["data"]) == before


def test_accepted_refresh_writes_monsters_manifest_and_snapshot(capsys, make_deps, world):
    http = FakeHttp.failing()
    code, out, deps = refresh(capsys, make_deps, world, confirm=accept, http=http)
    assert code == 0 and out["status"] == "écrit"
    written = {p.replace("\\", "/").rsplit("/", 1)[-1] for p in out["written"]}
    assert written == {"monsters.json", "manifest.json", "last.json"}
    assert read_json(world["data"] / LOCAL_VERSION / "monsters.json") == table_for(REAL_LOG, SECOND_LOG)
    assert main(["manifest", "--check"], deps) == 0
    capsys.readouterr()
    assert (deps.cache_dir / "measures" / "last.json").is_file()
    assert http.calls == []
    code, out, _ = refresh(capsys, make_deps, world, confirm=never)  # relance : même cache
    assert code == 0 and out["status"] == "rien à écrire" and out["diff"]["changed"] is False


def test_yes_writes_without_asking(capsys, make_deps, world):
    code, out, _ = refresh(capsys, make_deps, world, "--yes", confirm=never)
    assert code == 0 and out["status"] == "écrit"


def test_a_vanished_log_keeps_its_npcs(capsys, make_deps, world):
    code, _, _ = refresh(capsys, make_deps, world, "--yes")
    assert code == 0
    first_only = set(table_for(REAL_LOG)["npcs"]) - set(table_for(SECOND_LOG)["npcs"])
    assert first_only
    (world["logs"] / REAL_LOG.name).unlink()
    code, out, _ = refresh(capsys, make_deps, world, "--yes")
    assert code == 0
    assert out["diff"]["logs"]["gone"] == [REAL_LOG.name]
    assert set(out["diff"]["npcs"]["kept"]) >= first_only
    assert first_only <= set(read_json(world["data"] / LOCAL_VERSION / "monsters.json")["npcs"])


def test_missing_logs_dir_is_an_argument_error(capsys, make_deps, world, tmp_path):
    deps = make_deps(data_dir=world["data"])
    code = main(["measures", "refresh", "--logs", str(tmp_path / "absent"), "--json"], deps)
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out["error"]["code"] == "invalid_argument"


# --- Ignite ---------------------------------------------------------------------------------------


def test_ignite_episodes_are_read_from_the_log():
    events = list(read_log(IGNITE_LOG)[1])
    episodes = ignite_ticks(events, find_mine(events), ignite_spell=IGNITE_AURA, window_s=4.0)
    assert [len(e["crits"]) for e in episodes] == [1, 2]
    single, pair = episodes
    assert single["crits"] == [(0.0, 200.0)] and single["ticks"] == [(2.0, 40.0), (4.0, 40.0)]
    assert pair["crits"] == [(0.0, 200.0), (1.0, 150.0)] and pair["ticks"] == [(3.0, 70.0), (5.0, 70.0)]


def test_ignite_prediction_of_both_variants(game_data):
    crits = [(0.0, 200.0), (1.0, 150.0)]
    assert predict_ignite_ticks(game_data, crits, 0.4) == pytest.approx([(3.0, 70.0), (5.0, 70.0)])
    assert predict_ignite_ticks(game_data, crits, 0.4, keep_timer=True) == pytest.approx([(2.0, 70.0), (4.0, 70.0)])
    assert predict_ignite_ticks(game_data, [(0.0, 200.0)], 0.4) == pytest.approx([(2.0, 40.0), (4.0, 40.0)])


def test_refresh_compares_ignite_ticks_with_the_data_rule(capsys, make_deps, world):
    shutil.copy(IGNITE_LOG, world["logs"] / "WoWCombatLog-092726_190000.txt")
    code, out, _ = refresh(capsys, make_deps, world, "--dry-run")
    assert code == 0
    ignite = out["diff"]["ignite"]
    assert len(ignite["episodes"]) == 2
    pair = ignite["episodes"][1]
    assert pair["part"] == pytest.approx(0.4, rel=1e-12)
    assert pair["rolling"]["max_time_gap_s"] == pytest.approx(0.0, abs=1e-9)
    assert pair["keep_timer"]["max_time_gap_s"] == pytest.approx(1.0, rel=1e-9)
    assert ignite["rule"] == "rolling"


def test_real_frost_logs_have_no_ignite(capsys, make_deps, world):
    code, out, _ = refresh(capsys, make_deps, world, "--dry-run")
    assert code == 0 and out["diff"]["ignite"]["episodes"] == []
    assert "aucune mesure" in out["diff"]["ignite"]["note"]
