"""Origine déclarée de chaque valeur (T08b, bloc H, D4) : `forever/data/<version>/origins.json` et son contrôle.

Les cas d'échec modifient une copie des données (`data_copy`) ; les clés visées sont lues dans `origins.json` et
`mechanics.json` de la copie, jamais écrites dans le test."""

import json
from pathlib import Path
from typing import Any

from conftest import DATA_DIR, LOCAL_VERSION, PREVIOUS_VERSION

from forever.origins import ORIGINS, ORIGINS_NAME, check_all, check_version


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, doc: Any) -> None:
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def kinds(report) -> set[str]:
    return {i.kind for i in report.issues}


def manual_rule(origins: dict[str, Any], file: str = "mechanics.json") -> dict[str, Any]:
    return next(r for r in origins["rules"] if r["origin"] == "manuel" and r["file"] == file)


def test_seven_origins():
    """T08c : septième origine, `correctif_serveur` (valeur appliquée depuis DBCache.bin, poussée et date vue)."""
    assert ORIGINS == ("client", "journal", "addon", "manuel", "copie_figee", "parametre", "correctif_serveur")


def test_installed_versions_pass():
    report = check_all(DATA_DIR)
    assert report.versions == [PREVIOUS_VERSION, "1.60.1.70124", LOCAL_VERSION]  # 70170 installée le 2026-10-02
    assert report.issues == [], [f"{i.version} {i.file} {i.path} : {i.message}" for i in report.issues[:10]]
    assert report.leaves[LOCAL_VERSION] > 0 and report.leaves[PREVIOUS_VERSION] > 0


def test_every_installed_data_file_has_a_rule():
    for version in (PREVIOUS_VERSION, LOCAL_VERSION):
        origins = load(DATA_DIR / version / ORIGINS_NAME)
        named = {r["file"] for r in origins["rules"]} | {m["file"] for m in origins["not_game_values"]}
        present = {p.name for p in (DATA_DIR / version).glob("*.json")} - {ORIGINS_NAME}
        assert present <= named, version


def test_leaf_added_without_rule_fails(data_copy):
    path = data_copy / LOCAL_VERSION / "mechanics.json"
    doc = load(path)
    doc["values"]["t08b.cle_nouvelle"] = {"value": 1, "certainty": "suppose", "source": "test"}
    dump(path, doc)
    report = check_version(data_copy, LOCAL_VERSION)
    assert [(i.kind, i.file, i.path) for i in report.issues] == [
        ("non_couverte", "mechanics.json", "/values/t08b.cle_nouvelle/value")
    ]


def test_leaf_added_in_a_decoded_file_is_covered_by_its_pattern(data_copy):
    path = data_copy / LOCAL_VERSION / "spell_scaling.json"
    doc = load(path)
    first = next(iter(doc["spells"]))
    doc["spells"][first][0]["t08b_champ_nouveau"] = 1
    dump(path, doc)
    assert check_version(data_copy, LOCAL_VERSION).ok


def test_metadata_keys_are_not_values(data_copy):
    path = data_copy / LOCAL_VERSION / "mechanics.json"
    doc = load(path)
    key = next(iter(doc["values"]))
    doc["values"][key]["note"] = "note ajoutée par le test"
    dump(path, doc)
    assert check_version(data_copy, LOCAL_VERSION).ok


def test_manual_rule_without_reason_fails(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    rule = manual_rule(origins)
    rule.pop("reason")
    dump(path, origins)
    assert "raison_absente" in kinds(check_version(data_copy, LOCAL_VERSION))


def test_manual_rule_cannot_be_certain(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    manual_rule(origins)["certainty"] = "certain"
    dump(path, origins)
    assert "certitude_plafond" in kinds(check_version(data_copy, LOCAL_VERSION))


def test_pattern_on_manual_rule_is_refused(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    rule = manual_rule(origins)
    rule["paths"] = ["/values/*"]
    dump(path, origins)
    assert "motif_interdit" in kinds(check_version(data_copy, LOCAL_VERSION))


def test_entry_more_certain_than_its_rule_fails(data_copy):
    origins = load(data_copy / LOCAL_VERSION / ORIGINS_NAME)
    pending = {p["path"] for p in origins["pending"]}
    rule = next(
        r
        for r in origins["rules"]
        if r["origin"] == "manuel" and r["file"] == "mechanics.json" and r["certainty"] == "suppose"
    )
    target = next(p for p in rule["paths"] if p not in pending)
    key = target.split("/")[2]
    path = data_copy / LOCAL_VERSION / "mechanics.json"
    doc = load(path)
    doc["values"][key]["certainty"] = "probable"
    dump(path, doc)
    report = check_version(data_copy, LOCAL_VERSION)
    assert {(i.kind, i.file) for i in report.issues} == {("certitude_superieure", "mechanics.json")}
    assert all(i.path.startswith(f"/values/{key}/") or i.path == f"/values/{key}/value" for i in report.issues)


def test_pending_lowering_is_tolerated_and_listed(data_copy):
    path = data_copy / PREVIOUS_VERSION / ORIGINS_NAME
    origins = load(path)
    assert origins["pending"], "abaissements prévus en révision 4 déclarés"
    for entry in origins["pending"]:
        assert entry["until"] and entry["reason"] and entry["declared"] == "certain"
    origins["pending"] = origins["pending"][1:]
    dump(path, origins)
    assert "certitude_superieure" in kinds(check_version(data_copy, PREVIOUS_VERSION))


def test_pending_without_object_fails(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    rule = next(
        r
        for r in origins["rules"]
        if r["origin"] == "manuel" and r["file"] == "mechanics.json" and r["certainty"] == "suppose"
    )
    pending = {p["path"] for p in origins["pending"]}
    target = next(p for p in rule["paths"] if p not in pending)
    origins["pending"].append(
        {
            "file": "mechanics.json",
            "path": target,
            "declared": "certain",
            "target": "suppose",
            "reason": "test",
            "until": "test",
        }
    )
    dump(path, origins)
    assert "attente_sans_objet" in kinds(check_version(data_copy, LOCAL_VERSION))


def test_frozen_copy_is_file_level(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    frozen = [r for r in origins["rules"] if r["origin"] == "copie_figee"]
    assert {r["file"] for r in frozen} >= {"_seed_spells.json", "_seed_talents.json", "_seed_racials.json"}
    assert all(r["paths"] == ["**"] for r in frozen)
    frozen[0]["paths"] = ["/spells"]
    dump(path, origins)
    assert "copie_figee_partielle" in kinds(check_version(data_copy, LOCAL_VERSION))


def test_rule_for_absent_file_fails_unless_retired(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    base = {"origin": "client", "paths": ["**"], "source": "test", "certainty": "certain"}
    origins["rules"].append({"file": "racials.json", **base})  # retiré en PV1 (decode_rules.json, retired_files)
    dump(path, origins)
    assert check_version(data_copy, LOCAL_VERSION).ok
    origins["rules"].append({"file": "absent.json", **base})
    dump(path, origins)
    assert kinds(check_version(data_copy, LOCAL_VERSION)) == {"fichier_absent"}


def test_rule_without_effect_fails(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    rule = manual_rule(origins)
    rule["paths"] = [*rule["paths"], "/values/t08b.cle_absente"]
    dump(path, origins)
    report = check_version(data_copy, LOCAL_VERSION)
    assert [(i.kind, i.path) for i in report.issues] == [("regle_sans_effet", "/values/t08b.cle_absente")]


def test_unknown_origin_fails(data_copy):
    path = data_copy / LOCAL_VERSION / ORIGINS_NAME
    origins = load(path)
    manual_rule(origins)["origin"] = "memoire"
    dump(path, origins)
    assert "schema" in kinds(check_version(data_copy, LOCAL_VERSION))


def test_missing_origins_file_fails(data_copy):
    (data_copy / PREVIOUS_VERSION / ORIGINS_NAME).unlink()
    report = check_all(data_copy)
    assert [(i.kind, i.version) for i in report.issues] == [("schema", PREVIOUS_VERSION)]
