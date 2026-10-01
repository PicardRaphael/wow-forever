"""`forever addons status` (T08b, bloc D, décision 124) : version du `.toc` et empreinte des fichiers de données de
chaque addon suivi, relevé précédent dans le cache, statut `nouveau`, `inchangé` ou `changé` (même à chaîne de version
identique), différences des agrégats de Questie ; sans `--save`, rien n'est écrit ; aucun réseau.

Dossiers d'addons construits dans le test (fichiers factices, aucune valeur de jeu) ; Questie : fixture
`tests/fixtures/questie/11.38.0/`, dont une copie modifiée."""

import json
import re
import shutil

import pytest
from conftest import FIXTURES

from forever.addons import DATA_ADDONS, STATE_NAME, addons_status
from forever.cli import main

QUESTIE = FIXTURES / "questie" / "11.38.0"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    addons = root / "Interface" / "AddOns"
    write(addons / "AtlasLootClassic" / "AtlasLootClassic.toc", "## Title: AtlasLoot\n## Version: Forever 1.60.1\n")
    write(addons / "AtlasLootClassic_Data" / "data.lua", "local data = { boss = 'A' }\n")
    write(addons / "ForeverLogger" / "ForeverLogger.toc", "## Version: 0.1.0\n")
    write(addons / "ForeverLogger" / "ForeverLogger.lua", "-- addon\n")
    shutil.copytree(QUESTIE, addons / "Questie")
    return root


def by_name(report):
    return {a["name"]: a for a in report["addons"]}


def test_followed_addons_are_named_without_values():
    assert {"Questie", "AtlasLootClassic", "ForeverDungeonJournal", "GearQuestForever", "Auctionator"} <= set(
        DATA_ADDONS
    )


def test_first_scan_is_new_and_writes_nothing_without_save(wow, make_deps):
    deps = make_deps(wow_dir=wow)
    report = addons_status(deps)
    a = by_name(report)
    assert a["AtlasLootClassic"]["status"] == "nouveau" and a["AtlasLootClassic"]["version"] == "Forever 1.60.1"
    assert a["Questie"]["status"] == "nouveau"
    assert a["ForeverDungeonJournal"]["status"] == "absent"
    assert re.fullmatch(r"[0-9a-f]{12}", a["AtlasLootClassic"]["fingerprint"])
    assert not (deps.cache_dir / "addons" / STATE_NAME).exists()


def test_second_scan_after_save_is_unchanged(wow, make_deps):
    deps = make_deps(wow_dir=wow)
    addons_status(deps, save=True)
    assert (deps.cache_dir / "addons" / STATE_NAME).is_file()
    a = by_name(addons_status(deps))
    assert a["AtlasLootClassic"]["status"] == "inchangé" and a["Questie"]["status"] == "inchangé"


def test_data_file_changed_with_same_version_is_changed(wow, make_deps):
    deps = make_deps(wow_dir=wow)
    addons_status(deps, save=True)
    write(
        wow / "Interface" / "AddOns" / "AtlasLootClassic_Data" / "data.lua", "local data = { boss = 'BB' }\n"
    )  # taille différente
    a = by_name(addons_status(deps))["AtlasLootClassic"]
    assert a["status"] == "changé" and a["version"] == "Forever 1.60.1"
    assert a["files"]["modified"] == ["AtlasLootClassic_Data/data.lua"]
    assert "lecteur" in a["reader"]


def test_questie_aggregate_differences_are_listed(wow, make_deps):
    deps = make_deps(wow_dir=wow)
    addons_status(deps, save=True)
    db = wow / "Interface" / "AddOns" / "Questie" / "Database" / "Classic" / "classicNpcDB.lua"
    lines = db.read_text(encoding="utf-8").split("\n")
    k = next(i for i, ln in enumerate(lines) if re.match(r"^\[\d+\] = \{", ln))
    removed = int(re.match(r"^\[(\d+)\]", lines[k]).group(1))
    db.write_bytes("\n".join(lines[:k] + lines[k + 1 :]).encode("utf-8"))
    q = by_name(addons_status(deps))["Questie"]
    assert q["status"] == "changé"
    assert {"kind": "npc_removed", "id": removed} in q["aggregates_diff"]
    assert "monsters.json" in " ".join(q["depends"]) and "forever measures refresh" in q["action"]


def test_cli_json_and_save(wow, make_deps, capsys):
    deps = make_deps(wow_dir=wow)
    assert main(["addons", "status", "--json"], deps) == 0
    data = json.loads(capsys.readouterr()[0])
    assert data["provenance"]["game_version"]
    assert not (deps.cache_dir / "addons" / STATE_NAME).exists()
    assert main(["addons", "status", "--save"], deps) == 0
    assert (deps.cache_dir / "addons" / STATE_NAME).is_file()
