"""FR1 : `forever rxp traduire` (simulation, JSON avec bloc `provenance`, écriture avec sauvegarde, annulation,
manquants, import d'une session de traduction).

Valeurs : mini-addon inventé pour le test (`tests/fixtures/rxp_fr/`)."""

import json
import shutil
from pathlib import Path

from forever.rxp_fr.build import MARKER
from forever.rxp_fr.memory import Memory, memory_path

from forever.cli import main

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "rxp_fr"
REL = Path("Interface/AddOns/RXPGuides/lang/Guides-frFR/forever/Test-Isle.lua")


def _setup(make_deps, tmp_path):
    wow = tmp_path / "wow"
    shutil.copytree(FIX / "AddOns", wow / "Interface" / "AddOns")
    shutil.copytree(FIX / "wago", tmp_path / "cache" / "wago" / "1.0.0.1")
    return make_deps(wow_dir=wow), wow


def test_simulation_writes_nothing_and_reports_with_provenance(make_deps, tmp_path, capsys):
    deps, wow = _setup(make_deps, tmp_path)
    before = (wow / REL).read_bytes()
    assert main(["rxp", "traduire", "--simulation", "--json"], deps) == 0
    doc = json.loads(capsys.readouterr().out)
    assert (wow / REL).read_bytes() == before
    assert doc["written"] == []
    (row,) = doc["files"]
    assert row["file"] == "Test-Isle.lua" and row["generated"] == 2 and row["copied"] == 1
    assert doc["phrases"]["anglais"] >= 1
    prov = doc["provenance"]
    for key in ("game_version", "data_sha", "generated_at", "freshness", "certainty", "assumptions"):
        assert key in prov


def test_write_then_cancel_restores_the_restedxp_file(make_deps, tmp_path, capsys):
    deps, wow = _setup(make_deps, tmp_path)
    original = (wow / REL).read_bytes()
    assert main(["rxp", "traduire", "--json"], deps) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["written"] == ["Test-Isle.lua"]
    assert MARKER in (wow / REL).read_bytes().decode("utf-8")
    assert memory_path(deps).is_file()  # mémoire hors dépôt, à côté du profil
    assert main(["rxp", "traduire", "--annuler", "--json"], deps) == 0
    assert (wow / REL).read_bytes() == original


def test_missing_lists_phrases_left_in_english(make_deps, tmp_path, capsys):
    deps, _ = _setup(make_deps, tmp_path)
    assert main(["rxp", "traduire", "--manquants", "--json"], deps) == 0
    doc = json.loads(capsys.readouterr().out)
    assert "|cRXP_WARN_Wait for the boat at the dock|r" in doc["missing_phrases"]
    assert {"kind": "npc", "name": "Marsh Lurkers"} in doc["missing_names"]


def test_import_records_session_translations(make_deps, tmp_path, capsys):
    deps, wow = _setup(make_deps, tmp_path)
    data = tmp_path / "lot.json"
    data.write_text(
        json.dumps(
            {
                "|cRXP_WARN_Wait for the boat at the dock|r": "|cRXP_WARN_Attendez le bateau au quai|r",
                "Kill {1} and {2}": "Tuez {1}",  # jeton perdu : refusé
            }
        ),
        encoding="utf-8",
    )
    assert main(["rxp", "traduire", "--importer", str(data), "--json"], deps) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["imported"] == {"accepted": 1, "refused": 1}
    mem = Memory.load(memory_path(deps))
    assert mem.get("|cRXP_WARN_Wait for the boat at the dock|r").origin == "traduit"
    assert "*|cRXP_WARN_Attendez le bateau au quai|r" in (wow / REL).read_bytes().decode("utf-8")


def test_a_missing_addon_says_what_to_do(make_deps, tmp_path, capsys):
    deps = make_deps(wow_dir=tmp_path / "nowow")
    assert main(["rxp", "traduire", "--json"], deps) != 0
