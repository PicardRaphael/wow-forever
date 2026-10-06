"""Report des changements faits à la main (T08d, bloc C).

Version A : copie de la version installée (règle `manuel` sur `pet_rules.json` `/official_fixes`, valeurs `journal`
de `monsters.json`, changements à la main de la révision 3) ; version B construite par le test dans un autre dossier
de données. Aucune valeur de jeu n'est affirmée : les tests déplacent ou modifient des valeurs existantes."""

import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.carry import carry_apply, carry_check, manual_values
from forever.manifest import verify, write_manifest

FIXES = ("pet_rules.json", "/official_fixes")
NPCS = ("monsters.json", "/npcs")


@pytest.fixture
def versions(tmp_path):
    a = tmp_path / "a" / LOCAL_VERSION
    shutil.copytree(DATA_DIR / LOCAL_VERSION, a)
    b_data = tmp_path / "b"
    b = b_data / LOCAL_VERSION
    shutil.copytree(a, b)
    write_manifest(b_data)
    return a, b


def edit(path, change):
    doc = read_json(path)
    change(doc)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def mark(version_dir, file, inherited):
    def change(doc):
        entry = doc["files"][file]
        if inherited:
            entry["inherited_from"] = "1.60.1.70124"
        else:
            entry.pop("inherited_from", None)

    edit(version_dir / "sources.json", change)


def keys(values):
    return {(v.file, v.pointer) for v in values}


def test_manual_values_cover_rules_and_game_state(versions):
    a, _ = versions
    values = manual_values(a)
    found = keys(values)
    assert FIXES in found and NPCS in found
    assert ("meta.json", "/game_state") in found
    assert {v.origin for v in values} <= {"manuel", "journal"}
    fixes = next(v for v in values if (v.file, v.pointer) == FIXES)
    assert fixes.value == read_json(a / "pet_rules.json")["official_fixes"]


def test_manual_changes_are_included_without_origin_rule(versions):
    a, _ = versions

    def drop(doc):
        doc["rules"] = [r for r in doc["rules"] if r["paths"] != ["/official_fixes"]]

    edit(a / "origins.json", drop)
    values = manual_values(a)
    fixes = [v for v in values if (v.file, v.pointer) == FIXES]
    assert fixes and fixes[0].revision == 3
    # chemin pointé de la révision 3 (« coefficient.low_level_default.certainty ») retrouvé sous /values
    low = [v for v in values if v.file == "mechanics.json" and v.revision == 3]
    assert ("/values/coefficient.low_level_default/certainty") in {v.pointer for v in low}
    # les fichiers de provenance ne sont jamais reportés
    assert not {v.file for v in values} & {"origins.json", "sources.json", "revisions.json"}


def test_identical_version_keeps_everything(versions):
    report = carry_check(*versions)
    assert report.reapplied == [] and report.superseded == [] and report.lost == []
    assert FIXES in keys(report.kept) and NPCS in keys(report.kept)


def test_metadata_only_change_is_kept(versions):
    _, b = versions

    def carried(doc):
        doc["game_state"]["beta_level_cap"]["carried_to"] = 99

    edit(b / "meta.json", carried)
    report = carry_check(*versions)
    assert ("meta.json", "/game_state") in keys(report.kept)


def test_value_missing_from_inherited_file_is_reapplied(versions):
    a, b = versions
    mark(b, "pet_rules.json", inherited=True)
    edit(b / "pet_rules.json", lambda doc: doc.pop("official_fixes"))
    report = carry_check(a, b)
    assert FIXES in keys(report.reapplied)
    assert report.lost == [] and report.superseded == []
    written = carry_apply(a, b, report)
    assert b / "pet_rules.json" in written
    assert (b / "pet_rules.json").read_bytes() == (a / "pet_rules.json").read_bytes()
    assert verify(b.parent).ok
    assert carry_check(a, b).reapplied == []


def test_other_value_in_decoded_file_is_superseded(versions):
    a, b = versions
    mark(b, "monsters.json", inherited=False)
    npcs = read_json(a / "monsters.json")["npcs"]
    first = next(iter(npcs))

    def change(doc):
        doc["npcs"][first] = {"changed_by_test": True}

    edit(b / "monsters.json", change)
    report = carry_check(a, b)
    [(value, after)] = [(v, n) for v, n in report.superseded if (v.file, v.pointer) == NPCS]
    assert value.value == npcs
    assert after[first] == {"changed_by_test": True}
    assert NPCS not in keys(report.lost) and NPCS not in keys(report.reapplied)


def test_value_absent_from_decoded_file_is_lost(versions):
    a, b = versions
    mark(b, "monsters.json", inherited=False)
    edit(b / "monsters.json", lambda doc: doc.pop("npcs"))
    report = carry_check(a, b)
    assert NPCS in keys(report.lost)
    assert NPCS not in keys(report.reapplied)


def test_missing_file_is_lost(versions):
    a, b = versions
    (b / "pet_rules.json").unlink()
    assert FIXES in keys(carry_check(a, b).lost)


def test_apply_writes_nothing_without_reapplied_values(versions):
    a, b = versions
    before = {p.name: p.read_bytes() for p in b.iterdir() if p.is_file()}
    assert carry_apply(a, b, carry_check(a, b)) == []
    assert {p.name: p.read_bytes() for p in b.iterdir() if p.is_file()} == before
