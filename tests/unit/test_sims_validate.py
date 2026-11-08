"""SIM2, plan 3e (mesure et recoupement) : DPS mesuré dans les journaux de combat comparé au calcul de la même
tranche.

Fixtures : `tests/fixtures/combatlog/synthetic/validate_hunter.txt` (Chasseur et familier ; cinq combats de 10 s au
niveau 15 pour 300, 320, 280, 300 et 300 points, coups au contact écrits deux fois comme dans le journal réel ; deux
combats de 10 s au niveau 22 pour 500 et 600 points ; un monstre tué par un autre joueur) et
`tests/fixtures/addon/ForeverLoggerDB_validate.lua` (niveau 15 puis 22 à 10:30, Orc). Seuil « assez de combats » :
`measures.kill_time.min_samples` de `mechanics.json` de la version du dépôt. Simulation injectée et fabriquée : aucune
valeur de jeu."""

import json
import math

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.cli import main
from forever.errors import ForeverError, InvalidArgumentError
from forever.pipeline.addon_sv import read_logger_db
from forever.sims.validate import SimRequest, measure_character, validate_character

LOG = FIXTURES / "combatlog" / "synthetic" / "validate_hunter.txt"
SV = FIXTURES / "addon" / "ForeverLoggerDB_validate.lua"
MINE = "Player-0000-00000000"


def loggers():
    return [read_logger_db(SV)]


def min_samples():
    return int(
        read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["measures.kill_time"]["value"]["min_samples"]
    )


class FakeSim:
    """Simulation fabriquée : DPS par niveau, requêtes gardées ; un niveau absent lève une erreur de l'outil."""

    def __init__(self, by_level):
        self.by_level = by_level
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if request.level not in self.by_level:
            raise InvalidArgumentError(f"pas de calcul au niveau {request.level}", "rien")
        dps, stdev = self.by_level[request.level]
        return {"dps": dps, "stdev": stdev, "iterations": 2000, "preset": "hunter/dps/fabrique"}


def test_fights_are_measured_by_level_with_pet_and_without_duplicates():
    found = measure_character("Traqueur", logs=[LOG], loggers=loggers())
    assert found.guid == MINE and found.class_name == "Hunter" and found.race == "Orc"
    dps = {level: sorted(f.dps for f in fights) for level, fights in found.by_level.items()}
    # familier compté (300 au premier combat), doublon `_DAMAGE_LANDED` écarté (320, pas 480)
    assert dps == {15: [28.0, 30.0, 30.0, 30.0, 32.0], 22: [50.0, 60.0]}
    assert found.unattributed == 0


def test_character_by_guid_or_name_and_unknown_refused():
    assert measure_character(MINE, logs=[LOG], loggers=loggers()).name == "Traqueur"
    assert measure_character("traqueur-royaume", logs=[LOG], loggers=loggers()).guid == MINE
    with pytest.raises(InvalidArgumentError):
        measure_character("Personne", logs=[LOG], loggers=loggers())


def test_brackets_compared_to_the_simulation(make_deps):
    sim = FakeSim({15: (30.5, 50.0), 22: (80.0, 50.0)})
    doc = validate_character(make_deps(), "Traqueur", logs=[LOG], loggers=loggers(), simulate=sim)
    assert [r.level for r in sim.requests] == [15, 22]
    assert all(isinstance(r, SimRequest) and (r.class_name, r.race) == ("Hunter", "Orc") for r in sim.requests)
    rows = {r["bracket"]: r for r in doc["rows"]}
    assert set(rows) == {"10-19", "20-29"}

    low = rows["10-19"]
    assert low["levels"] == [15] and low["sim_level"] == 15
    m = low["measured"]
    assert m["fights"] == 5 and m["seconds"] == pytest.approx(50.0)
    assert m["dps"] == pytest.approx(30.0) and m["stdev"] == pytest.approx(math.sqrt(2))
    assert low["simulated"]["dps"] == 30.5
    assert low["gap"]["relative"] == pytest.approx((30.0 - 30.5) / 30.5)
    assert low["gap"]["verdict"] == "non départagé"
    assert m["fights"] >= min_samples() and low["certainty"] == "probable"  # tranche recoupée

    high = rows["20-29"]
    assert high["measured"]["fights"] == 2 and high["measured"]["dps"] == pytest.approx(55.0)
    assert high["gap"]["relative"] == pytest.approx((55.0 - 80.0) / 80.0)
    assert high["gap"]["verdict"] != "non départagé" and high["gap"]["threshold"] < 25.0
    assert high["certainty"] == "suppose"  # trop peu de combats pour recouper

    prov = doc["provenance"]
    assert prov["certainty"] == "suppose" and prov["assumptions"]
    assert doc["character"]["name"] == "Traqueur"


def test_by_level_and_simulation_error_kept_in_its_row(make_deps):
    sim = FakeSim({15: (30.0, 50.0)})
    doc = validate_character(make_deps(), MINE, logs=[LOG], loggers=loggers(), simulate=sim, group="level")
    rows = {r["level"]: r for r in doc["rows"]}
    assert rows[15]["gap"]["verdict"] == "non départagé"
    assert "error" in rows[22]["simulated"] and rows[22]["gap"] is None and rows[22]["certainty"] == "suppose"


def test_cli_and_mcp_action(make_deps, monkeypatch, capsys):
    sim = FakeSim({15: (30.5, 50.0), 22: (80.0, 50.0)})
    monkeypatch.setattr("forever.sims.validate.default_simulate", lambda deps, preset=None: sim)
    deps = make_deps()
    assert main(["sims", "validate", "--character", "Traqueur", "--log", str(LOG), "--sv", str(SV), "--json"],
                deps) == 0  # fmt: skip
    out = json.loads(capsys.readouterr().out)
    assert [r["bracket"] for r in out["rows"]] == ["10-19", "20-29"] and "provenance" in out
    assert main(["sims", "validate", "--character", "Traqueur", "--log", str(LOG), "--sv", str(SV)], deps) == 0
    assert "non départagé" in capsys.readouterr().out

    from forever.sims.report import simulate

    doc = simulate(deps, "validate", character="Traqueur", log=str(LOG), sv=str(SV))
    assert doc["rows"][0]["gap"]["verdict"] == "non départagé"


def test_simulation_failure_is_a_tool_error(make_deps):
    def broken(request):
        raise ForeverError("sim", "calcul impossible", "rien")

    doc = validate_character(make_deps(), "Traqueur", logs=[LOG], loggers=loggers(), simulate=broken)
    assert all("error" in r["simulated"] for r in doc["rows"])
