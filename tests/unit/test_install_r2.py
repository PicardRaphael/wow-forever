"""Révision 2 de 1.60.1.70124 (PV1, bloc B4 ; décision 106 ; D5) : fichiers des 9 classes décodés et installés,
`racials.json` retiré (déclaré dans `decode_rules.json`, `retired_files`), copie figée `_seed_racials.json` pour le
mode seed, moteur et consommateurs branchés sur `races.json` et `classes.json`.

Fixtures : `tests/fixtures/wago/1.60.1.70124/` (candidate des 9 classes) et `tests/fixtures/wago/1.60.1.70009/`
(candidate sans les tables des classes, fixture de session `candidate`). Les tests d'installation partent d'une copie
des données ramenée à l'état d'avant la révision 2 (`rewind_classes`)."""

import json
import shutil

import pytest
from conftest import (
    CLASS_FIXTURE_VERSION,
    DATA_DIR,
    LOCAL_VERSION,
    PREVIOUS_VERSION,
    WAGO_70124,
    isolated_deps,
    read_json,
    rewind_to,
)

from forever.cli import main
from forever.errors import CsvMissingError, DataSchemaError, InvalidArgumentError
from forever.gamedata import build_game_data
from forever.manifest import write_manifest
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install, plan_install
from forever.profile import CLASSES, set_character
from forever.profile_import import class_spell_index
from forever.store import ensure_integrity, load_version

CLASS_FILES = ("classes.json", "races.json", "pvp_items.json")


def content(path):
    """Contenu d'un fichier JSON, sa marque d'origine mise à part (`inherited_from`, écrite par forever decode)."""
    doc = read_json(path)
    return {k: v for k, v in doc.items() if k != "inherited_from"} if isinstance(doc, dict) else doc


@pytest.fixture(scope="module")
def class_candidate(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("classes")
    return decode_version(isolated_deps(tmp), CLASS_FIXTURE_VERSION, csv_dir=WAGO_70124, out=tmp / "candidate")


def rewind_classes(data):
    """État d'avant la révision 2 sur une copie des données : fichiers des classes et copie figée retirés,
    `racials.json` remis (contenu du relevé, hérité de 1.60.1.70009), leurs entrées de `sources.json` ajustées.
    Copie ramenée d'abord à la version des extraits (1.60.1.70124), que la candidate révise."""
    rewind_to(data, CLASS_FIXTURE_VERSION)
    v = data / CLASS_FIXTURE_VERSION
    for name in (*CLASS_FILES, "_seed_racials.json"):
        (v / name).unlink(missing_ok=True)
    record = {**read_json(data / PREVIOUS_VERSION / "racials.json"), "inherited_from": PREVIOUS_VERSION}
    (v / "racials.json").write_bytes(json.dumps(record, ensure_ascii=False, indent=1).encode("utf-8"))
    sources = read_json(v / "sources.json")
    for name in (*CLASS_FILES, "_seed_racials.json"):
        sources["files"].pop(name, None)
    sources["files"]["racials.json"] = {"source": "relevé communautaire", "certainty": "suppose", "notes": []}
    (v / "sources.json").write_bytes(json.dumps(sources, ensure_ascii=False, indent=2).encode("utf-8"))
    write_manifest(data)


@pytest.fixture
def before_r2(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    rewind_classes(data)
    return isolated_deps(tmp_path, data)


# --- Décodage de la candidate ---------------------------------------------------------------------------------


def test_candidate_from_class_tables_decodes_the_nine_classes(class_candidate):
    v = class_candidate.root / CLASS_FIXTURE_VERSION
    for name in CLASS_FILES:
        assert "inherited_from" not in read_json(v / name), name
    assert set(read_json(v / "classes.json")["classes"]) == set(CLASSES)
    sources = read_json(v / "sources.json")
    for name in CLASS_FILES:
        assert sources["files"][name]["certainty"] == "certain", name
    assert sources["retired_files"]["racials.json"]["replaced_by"] == "races.json"
    assert "racials.json" not in {p.name for p in v.iterdir()}


def test_unresolved_spells_listed_in_report(class_candidate):
    doc = read_json(class_candidate.root / CLASS_FIXTURE_VERSION / "classes.json")
    text = "\n".join(class_candidate.observations)
    listed = 0
    for c in doc["classes"].values():
        for u in c["unresolved_nodes"]:
            assert u["key"] in text
            listed += 1
        for u in c["unresolved_spells"]:
            assert u["name"] in text
            listed += 1
    assert listed >= 3  # prémisses : nœuds du Paladin et du Démoniste, pièges et totems


def test_partial_class_tables_are_refused(tmp_path):
    copy = tmp_path / "csv"
    shutil.copytree(WAGO_70124, copy)
    (copy / "enUS" / "SpellRange.csv").unlink()
    with pytest.raises(CsvMissingError) as info:
        decode_version(isolated_deps(tmp_path), LOCAL_VERSION, csv_dir=copy, out=tmp_path / "c")
    assert "SpellRange" in info.value.message


def test_candidate_without_class_tables_inherits_them(candidate):
    v = candidate.root / PREVIOUS_VERSION
    for name in CLASS_FILES:
        assert read_json(v / name)["inherited_from"] == LOCAL_VERSION, name
    assert any("classes.json" in o and "hérit" in o for o in candidate.observations)


def test_seed_racials_is_a_frozen_copy_of_the_community_record():
    assert content(DATA_DIR / LOCAL_VERSION / "_seed_racials.json") == content(
        DATA_DIR / PREVIOUS_VERSION / "racials.json"
    )
    assert not (DATA_DIR / LOCAL_VERSION / "racials.json").exists()
    assert (DATA_DIR / PREVIOUS_VERSION / "racials.json").is_file()  # l'ancienne version garde son relevé


# --- Installation ---------------------------------------------------------------------------------------------


def test_install_adds_the_class_files_and_retires_racials(before_r2, class_candidate):
    plan = plan_install(before_r2, str(class_candidate.root))
    assert plan["refused"] == []
    rules = {(c["file"], c["rule"]) for c in plan["changes"]}
    for name in (*CLASS_FILES, "_seed_racials.json"):
        assert (name, "added_file") in rules, name
    assert ("racials.json", "retired_file") in rules
    rev = apply_install(before_r2, str(class_candidate.root), motif="test", date="2026-09-30")
    ensure_integrity(before_r2.data_dir)
    v = before_r2.data_dir / CLASS_FIXTURE_VERSION
    assert all((v / name).is_file() for name in CLASS_FILES)
    assert not (v / "racials.json").exists()
    assert content(v / "_seed_racials.json") == content(DATA_DIR / PREVIOUS_VERSION / "racials.json")
    sources = read_json(v / "sources.json")
    assert "racials.json" not in sources["files"] and all(n in sources["files"] for n in CLASS_FILES)
    assert {c["rule"] for c in rev["changes"]} >= {"added_file", "retired_file"}
    assert main(["verify", "--json"], before_r2) == 0


def test_inherited_class_files_are_never_installed(tmp_path, candidate):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    rewind_to(data, PREVIOUS_VERSION)  # 1.60.1.70009 redevient la version courante
    plan = plan_install(isolated_deps(tmp_path, data), str(candidate.root))
    files = {c["file"] for c in plan["changes"] if c["rule"] in ("added_file", "replaced_file", "retired_file")}
    assert not files  # fichiers des classes hérités d'une autre version : ni installés, ni racials.json retiré


# --- Moteur et consommateurs ----------------------------------------------------------------------------------


def test_mage_races_come_from_races_json(make_deps):
    races = read_json(DATA_DIR / LOCAL_VERSION / "races.json")["races"]
    deps = make_deps()
    mage = [name for name, r in races.items() if "Mage" in r["classes"]]
    other = [name for name, r in races.items() if "Mage" not in r["classes"]]
    assert mage and other
    for i, race in enumerate(mage):
        set_character(deps, f"M{i}", cls="Mage", race=race, level=10)
    with pytest.raises(InvalidArgumentError) as info:
        set_character(deps, "Autre", cls="Mage", race=other[0], level=10)
    assert "races.json" in info.value.action


def test_class_spell_index_uses_classes_json(make_deps):
    doc = read_json(DATA_DIR / LOCAL_VERSION / "classes.json")
    owners: dict[int, set[str]] = {}
    for cls, c in doc["classes"].items():
        for spells in (c["spells"], c.get("pet_spells", {})):
            for spell in spells.values():
                for r in spell["ranks"]:
                    owners.setdefault(r["spell_id"], set()).add(cls)
    index = class_spell_index(load_version(make_deps()))
    assert set(index.values()) == set(CLASSES)
    for spell_id, classes in owners.items():
        if len(classes) == 1:
            assert index[spell_id] == next(iter(classes))
        else:
            assert spell_id not in index  # sort de plusieurs classes : n'indique aucune classe
    frostbolt = read_json(DATA_DIR / LOCAL_VERSION / "spells.json")["spells"]["frostbolt"]["source"]["rank_spell_ids"]
    assert {index[i] for i in frostbolt} == {"Mage"}


def test_verify_rejects_a_broken_classes_json(tmp_path, make_deps):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    path = data / LOCAL_VERSION / "classes.json"
    doc = read_json(path)
    del doc["classes"]["Rogue"]["trees"]
    path.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    write_manifest(data)
    assert main(["verify", "--json"], make_deps(data_dir=data)) != 0
    deps = make_deps(data_dir=data)
    gd = build_game_data(load_version(deps))
    with pytest.raises(DataSchemaError):  # la classe cassée n'est jamais rendue à moitié
        _ = gd.classes["Rogue"]


def test_no_retirement_without_its_declaration(before_r2, class_candidate, tmp_path):
    """Relecture de PV1 : sans `retired_files` dans la candidate, racials.json n'est jamais retiré."""
    copy = tmp_path / "cand"
    shutil.copytree(class_candidate.root, copy)
    sources = copy / CLASS_FIXTURE_VERSION / "sources.json"
    doc = read_json(sources)
    doc.pop("retired_files")
    sources.write_bytes(json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"))
    write_manifest(copy)
    plan = plan_install(before_r2, str(copy))
    assert "racials.json" not in {c["file"] for c in plan["changes"] if c["rule"] == "retired_file"}


def test_imported_mage_race_token_is_accepted(make_deps):
    races = read_json(DATA_DIR / LOCAL_VERSION / "races.json")["races"]
    token = next(r["client_file"] for n, r in races.items() if "Mage" in r["classes"] and r["client_file"] != n)
    deps = make_deps()
    set_character(deps, "Jeton", cls="Mage", race=token, level=10)  # jeton du client écrit par ForeverLogger
    frozen = read_json(DATA_DIR / LOCAL_VERSION / "_seed_racials.json")["races"]
    old = next(n for n in frozen if n not in races)  # nom de l'ancien relevé communautaire
    set_character(deps, "Ancien", cls="Mage", race=old, level=10)  # profil saisi avant PV1 : toujours accepté
