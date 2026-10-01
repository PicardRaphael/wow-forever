"""`forever diff` compare les valeurs de `spell_scaling.json` et de `character_scaling.json` (T08b, bloc C) : une
ligne par valeur changée (sort, rang, composant, avant, après), plus de simple « fichier remplacé ».

Copies modifiées des données installées ; valeurs avant et après lues dans la copie, jamais écrites ici."""

import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.pipeline.diff import compare_data
from forever.pipeline.report import render_report
from forever.store import VersionData

SCALING = "spell_scaling.json"


def version(path, name=LOCAL_VERSION):
    return VersionData(name, "0" * 12, path, read_json(path / "sources.json"))


@pytest.fixture
def pair(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    shutil.copytree(DATA_DIR / LOCAL_VERSION, a)
    shutil.copytree(DATA_DIR / LOCAL_VERSION, b)
    return a, b


def edit(path, mutate):
    doc = read_json(path)
    mutate(doc)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def test_identical_copies_have_no_value_change(pair):
    a, b = pair
    assert [c for c in compare_data(version(a), version(b)) if c["kind"] in ("scaling", "character")] == []


def test_four_scaling_changes_named_by_spell_rank_and_component(pair):
    a, b = pair
    doc = read_json(a / SCALING)
    fireball = doc["spells"]["fireball"][0]
    direct = fireball["components"][0]
    dot = next(c for c in fireball["components"] if c["period_ms"])
    talent = next(iter(doc["talent_cooldowns"]))

    def mutate(d):
        comps = d["spells"]["fireball"][0]["components"]
        comps[0]["bonus_coefficient"] = direct["bonus_coefficient"] * 2
        comps[0]["points_per_level"] = direct["points_per_level"] + 1
        comps[dot["index"]]["period_ms"] = dot["period_ms"] * 2
        d["talent_cooldowns"][talent]["cooldown_ms"] = doc["talent_cooldowns"][talent]["cooldown_ms"] * 2

    edit(b / SCALING, mutate)
    changes = [c for c in compare_data(version(a), version(b)) if c["kind"] == "scaling"]
    got = {(c["key"], c["field"], c["old"], c["new"]) for c in changes}
    rank = f"fireball r{fireball['rank']}"
    assert got == {
        (rank, "composant 0 bonus_coefficient", direct["bonus_coefficient"], direct["bonus_coefficient"] * 2),
        (rank, "composant 0 points_per_level", direct["points_per_level"], direct["points_per_level"] + 1),
        (rank, f"composant {dot['index']} period_ms", dot["period_ms"], dot["period_ms"] * 2),
        (
            f"talent_cooldowns {talent}",
            "cooldown_ms",
            doc["talent_cooldowns"][talent]["cooldown_ms"],
            doc["talent_cooldowns"][talent]["cooldown_ms"] * 2,
        ),
    }
    assert all(c["change"] == "modified" for c in changes)


def test_level_cap_change_is_listed(pair):
    a, b = pair
    cap = read_json(a / SCALING)["level_cap"]
    edit(b / SCALING, lambda d: d.update(level_cap=cap + 1))
    changes = [c for c in compare_data(version(a), version(b)) if c["kind"] == "scaling"]
    assert [(c["key"], c["old"], c["new"]) for c in changes] == [("level_cap", cap, cap + 1)]


def test_character_scaling_changes_are_listed(pair, tmp_path):
    a, b = pair
    doc = {
        "schema_version": 1,
        "level_cap": 2,
        "classes": {"Mage": {"base_mana": [1.0, 2.0]}},
        "xp_to_next": [3],
        "armor_constant": [4.0, 5.0],
    }  # document de test (structure du fichier décodé, valeurs inventées)
    for d in (a, b):
        (d / "character_scaling.json").write_bytes(json.dumps(doc).encode("utf-8"))
    edit(b / "character_scaling.json", lambda d: d["classes"]["Mage"]["base_mana"].__setitem__(1, 9.0))
    changes = [c for c in compare_data(version(a), version(b)) if c["kind"] == "character"]
    assert [(c["key"], c["field"], c["old"], c["new"]) for c in changes] == [("Mage niveau 2", "base_mana", 2.0, 9.0)]


def test_report_has_a_values_section(pair, make_deps):
    a, b = pair
    cap = read_json(a / SCALING)["level_cap"]
    edit(b / SCALING, lambda d: d.update(level_cap=cap + 1))
    changes = compare_data(version(a), version(b))
    diff = {
        "a": "A",
        "b": "B",
        "changes": changes,
        "counts": {
            k: sum(1 for c in changes if c["kind"] == k) for k in ("talent", "spell", "file", "scaling", "character")
        },
        "provenance": {
            "game_version": LOCAL_VERSION,
            "data_sha": "0" * 12,
            "data_revision": 0,
            "registry_coverage": "0/0",
            "generated_at": "2026-10-01T00:00:00Z",
            "freshness": "fresh",
            "certainty": "certain",
            "assumptions": [],
        },
    }
    text = render_report(diff)
    assert "## Valeurs de spell_scaling.json" in text and "level_cap" in text
