"""Relevé du familier par ForeverLogger et sa lecture hors ligne (CH0, bloc F) : instantanés du familier et du
Chasseur, fenêtre Beast Training ; `forever pets measure` compare les coûts et niveaux observés à `pets.json`, le
régime observé au client, et forme les rapports PV du familier / Endurance du Chasseur par paire d'instantanés,
avec `n` ; rien n'est écrit dans les données.

Fixture synthétique `tests/fixtures/addon/ForeverLoggerDB_pets.lua` (noms inventés, structure écrite par l'addon) ;
valeurs du client lues dans `pets.json` installé."""

import json

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.cli import main
from forever.manifest import compute_manifest
from forever.pets import measure_pets
from forever.pipeline.addon_sv import read_logger_db
from forever.provenance import validate_provenance

SV = FIXTURES / "addon" / "ForeverLoggerDB_pets.lua"
PETS = read_json(DATA_DIR / LOCAL_VERSION / "pets.json")
PET_RULES = read_json(DATA_DIR / LOCAL_VERSION / "pet_rules.json")


@pytest.fixture(scope="module")
def db():
    return read_logger_db(SV)


@pytest.fixture(scope="module")
def report(db):
    return measure_pets(PETS, PET_RULES, db)


def hunter(db):
    (c,) = db.characters.values()
    return c


def test_pet_snapshots_and_training_are_read(db):
    c = hunter(db)
    assert len(c.pet_snapshots) == 3 and len(c.training) == 1
    first = c.pet_snapshots[0]
    assert first.pet["family"] == "Wolf" and first.pet["health_max"] == 300
    assert first.hunter["stamina"] == {1: 40, 2: 40, 3: 0, 4: 0}
    window = c.training[0]
    assert window.family == "Wolf" and [e["name"] for e in window.entries] == ["Bite", "Dash", "Growl"]


def test_old_files_without_pet_lists_still_read():
    db = read_logger_db(FIXTURES / "addon" / "ForeverLoggerDB.lua")
    assert all(c.pet_snapshots == [] and c.training == [] for c in db.characters.values())


def test_training_cost_and_level_compared_to_pets_json(db, report):
    rows = {(r["ability"], r["rank"]): r for r in report["training"]}
    window = hunter(db).training[0]
    for entry in window.entries:
        key = entry["name"].lower()
        rank = int(entry["rank"].split()[-1])
        if "cost" not in entry:
            assert (key, rank) not in rows or rows[(key, rank)]["status"] == "incomplet"
            continue
        fam = PETS["families"]["wolf"]
        expected_cost = fam["training_costs"][key][rank - 1]
        expected_level = next(r["level"] for r in PETS["abilities"][key]["ranks"] if r["rank"] == rank)
        row = rows[(key, rank)]
        assert row["observed"] == {"cost": entry["cost"], "level": entry["level"]}
        assert row["client"] == {"cost": expected_cost, "level": expected_level}
        same = expected_cost == entry["cost"] and expected_level == entry["level"]
        assert row["status"] == ("concorde" if same else "ecart")
    assert {r["status"] for r in report["training"]} >= {"concorde", "ecart"}  # la fixture porte les deux cas


def test_diet_observed_compared_to_the_client(report):
    rows = {r["family"]: r for r in report["diet"]}
    for fam in ("wolf", "cat"):
        client = sorted(d["en"] for d in PETS["families"][fam]["diet"])
        assert rows[fam]["client"] == client
        assert rows[fam]["status"] == ("concorde" if rows[fam]["observed"] == client else "ecart")


def test_health_per_stamina_from_pairs_with_n(db, report):
    snaps = [s for s in hunter(db).pet_snapshots if s.pet.get("family") == "Wolf"]
    a, b = snaps[0], snaps[1]
    expected = (b.pet["health_max"] - a.pet["health_max"]) / (b.hunter["stamina"][2] - a.hunter["stamina"][2])
    inh = report["inheritance"]["health_per_stamina"]
    assert inh["n"] == 1 and inh["values"] == [pytest.approx(expected)]
    assert inh["rule"] == PET_RULES["rules"]["inheritance.health_per_stamina"]["value"]
    assert inh["certainty"] == "probable"


def test_attack_speed_grouped_by_family_with_n(db, report):
    speeds = report["attack_speed"]
    for fam in ("wolf", "cat"):
        observed = [s.pet["attack_speed"] for s in hunter(db).pet_snapshots if s.pet.get("family", "").lower() == fam]
        assert speeds[fam]["n"] == len(observed) and speeds[fam]["values"] == sorted(set(observed))
    assert report["rules"]["attack_speed.base_s"] == PET_RULES["rules"]["attack_speed.base_s"]["value"]


def test_nothing_is_written_to_the_data(make_deps, capsys):
    before = compute_manifest(DATA_DIR)
    assert main(["pets", "measure", "--addon-sv", str(SV), "--json"], make_deps()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert validate_provenance(payload["provenance"]) == [] and payload["training"]
    assert compute_manifest(DATA_DIR) == before
    assert any("rien n'est écrit" in a for a in payload["provenance"]["assumptions"])
    assert main(["pets", "measure", "--addon-sv", str(SV)], make_deps()) == 0
    assert capsys.readouterr().out.rstrip().splitlines()[-1].startswith("Provenance")
