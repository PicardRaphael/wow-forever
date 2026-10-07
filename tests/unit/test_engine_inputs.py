"""Preuve d'entrées identiques par moteur et rejeu ciblé (T08d, bloc B).

Modifications faites par le test sur une copie de la version installée ; aucune valeur de jeu n'est affirmée : les
tests changent une valeur existante et vérifient quels moteurs la voient."""

import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, mount_warrior, read_json

from forever.engine_inputs import (
    ENGINES,
    PROVENANCE_FILES,
    EngineDeclarationError,
    EngineSpec,
    canonical_sha,
    capture_reads,
    cases_to_replay,
    check_engines,
    compare_inputs,
    covered,
    metadata_keys,
    targeted_replay,
)

MAGE = ("mage_build", "mage_leveling")


@pytest.fixture
def pair(tmp_path):
    before = tmp_path / "avant" / LOCAL_VERSION
    shutil.copytree(DATA_DIR / LOCAL_VERSION, before)
    after = tmp_path / "après" / LOCAL_VERSION
    shutil.copytree(before, after)
    return before, after


def edit(path, change):
    doc = read_json(path)
    change(doc)
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def different(diffs):
    return {name for name, d in diffs.items() if not d.identical}


def test_engines_are_declared():
    assert set(ENGINES) == {"mage_build", "mage_leveling", "pvp_dr"}
    for name, spec in ENGINES.items():
        assert spec.name == name
        assert spec.files
        assert bool(spec.cases) == (spec.mode == "calcule")  # un moteur qui recopie n'a pas de cas de rejeu
        assert not set(spec.files) & PROVENANCE_FILES


def test_engines_declare_their_mode():
    assert {n: s.mode for n, s in ENGINES.items()} == {
        "mage_build": "calcule",
        "mage_leveling": "calcule",
        "pvp_dr": "recopie",
    }
    assert ENGINES["pvp_dr"].cases == ()
    check_engines(ENGINES)


def test_an_engine_without_mode_cannot_be_built():
    with pytest.raises(TypeError):
        EngineSpec("sans_mode", ("spells.json",), {}, ())  # type: ignore[call-arg]


def test_an_unknown_mode_is_refused():
    spec = ENGINES["pvp_dr"]._replace(name="autre", mode="autre")
    with pytest.raises(EngineDeclarationError, match="autre"):
        check_engines({**ENGINES, "autre": spec})


def test_changed_items_carry_their_leaves_and_origins(tmp_path):
    """Cas réel : 70245 r1 (sans correctifs) puis r3 (refonte du Guerrier par les correctifs), fixtures de T08e."""
    before = mount_warrior(tmp_path / "avant", "70245-r1", None)
    after = mount_warrior(tmp_path / "après", "70245-r3", "70245-r3")
    diffs = compare_inputs(before, after)
    assert different(diffs) == {"pvp_dr"}
    changed = [i for i in diffs["pvp_dr"].items if i["status"] == "différent"]
    assert [(i["file"], i["pointer"]) for i in changed] == [("classes.json", "/classes/Warrior")]
    item = changed[0]
    assert len(item["changes"]) == item["leaves"] == 297
    origins = {c.origin_before for c in item["changes"]} | {c.origin_after for c in item["changes"]}
    assert origins <= {"client", "correctif_serveur"}
    assert sum(item["origins"].values()) == 297 and set(item["origins"]) <= {"client", "correctif_serveur"}
    hit = next(c for c in item["changes"] if c.pointer == "/classes/Warrior/spells/berserkerRage/ranks/0/level")
    assert (hit.file, hit.before, hit.after) == ("classes.json", 32, 30)
    assert (hit.origin_before, hit.origin_after) == ("client", "correctif_serveur")
    assert all("changes" not in i for i in diffs["pvp_dr"].items if i["status"] == "identique")


def test_same_data_is_identical(pair):
    diffs = compare_inputs(*pair)
    assert set(diffs) == set(ENGINES)
    assert different(diffs) == set()
    for d in diffs.values():
        assert d.items and all(i["status"] == "identique" for i in d.items)


def test_metadata_changes_are_ignored(pair):
    _, after = pair

    def carried(doc):
        doc["game_state"]["beta_level_cap"]["carried_from"] = "révision du test"

    def read_at(doc):
        doc["trees"][0]["talents"][0]["source"]["read_at"] = "2099-01-01T00:00:00Z"

    edit(after / "meta.json", carried)
    edit(after / "talents.json", read_at)
    assert different(compare_inputs(*pair)) == set()


def test_a_scaling_value_touches_the_mage_engines_only(pair):
    _, after = pair

    def bump(doc):
        doc["spells"]["frostbolt"][0]["components"][0]["base_points"] += 1

    edit(after / "spell_scaling.json", bump)
    diffs = compare_inputs(*pair)
    assert different(diffs) == set(MAGE)
    for name in MAGE:
        [item] = [i for i in diffs[name].items if i["status"] == "différent"]
        assert item["file"] == "spell_scaling.json" and item["leaves"] == 1
        assert item["before"] != item["after"]


def test_classes_file_is_compared_by_pointer(pair):
    _, after = pair

    def warrior(doc):
        spell = next(iter(doc["classes"]["Warrior"]["spells"].values()))
        spell["ranks"][0]["level"] += 1

    edit(after / "classes.json", warrior)
    diffs = compare_inputs(*pair)
    assert not set(MAGE) & different(diffs)
    assert "pvp_dr" in different(diffs)  # la fiche d'affrontement lit toutes les classes

    def mage(doc):
        doc["classes"]["Mage"]["spells"]["frostbolt"]["ranks"][0]["level"] += 1

    edit(after / "classes.json", mage)
    assert set(MAGE) <= different(compare_inputs(*pair))


def test_pvp_rules_touch_the_pvp_engine_only(pair):
    _, after = pair

    def steps(doc):
        doc["diminishing_returns"]["steps"]["value"][1] += 0.1

    edit(after / "pvp_rules.json", steps)
    assert different(compare_inputs(*pair)) == {"pvp_dr"}


def test_canonical_sha_ignores_key_order_and_metadata():
    meta = frozenset({"source"})
    a = {"x": 1, "y": {"z": 2, "source": "a"}}
    b = {"y": {"source": "b", "z": 2}, "x": 1}
    assert canonical_sha(a, None, meta) == canonical_sha(b, None, meta)
    assert canonical_sha(a, None, meta) != canonical_sha({"x": 2, "y": {"z": 2}}, None, meta)
    assert canonical_sha(a, ["/y"], meta) == canonical_sha({"y": {"z": 2}, "x": 9}, ["/y"], meta)


def test_metadata_keys_include_origins_and_carried_fields():
    keys = metadata_keys(DATA_DIR / LOCAL_VERSION)
    origins = read_json(DATA_DIR / LOCAL_VERSION / "origins.json")["metadata_keys"]
    assert set(origins) <= keys
    assert {"source", "carried_from", "carried_to", "read_at", "hotfix"} <= keys


def assert_covered(name, reads):
    spec = ENGINES[name]
    assert reads, "aucune lecture relevée"
    missing = sorted(r for r in reads if r[0] not in PROVENANCE_FILES and not covered(spec, r))
    assert missing == [], f"{name} lit des entrées non déclarées : {missing}"


@pytest.mark.slow
def test_completeness_of_the_mage_build_engine(make_deps):
    from forever.build import build_report

    deps = make_deps()
    reads = capture_reads(lambda: build_report(deps, "leveling", 20, preset="rapide", sensitivity=False))
    assert ("classes.json", "/classes/Mage/spells") in reads
    assert_covered("mage_build", reads)


def test_completeness_of_the_mage_leveling_engine(make_deps):
    from forever.leveling import simulate_leveling

    deps = make_deps()
    reads = capture_reads(lambda: simulate_leveling(deps, 20, n=20))
    assert_covered("mage_leveling", reads)


def test_completeness_of_the_pvp_engine(make_deps):
    from forever.pvp import pvp_report

    deps = make_deps()
    reads = capture_reads(lambda: pvp_report(deps, "Mage", opponent="Warlock", level=20))
    assert ("classes.json", "/classes/Warlock") in reads
    assert ("classes.json", None) not in reads
    assert_covered("pvp_dr", reads)


def test_an_undeclared_read_is_caught():
    spec = ENGINES["mage_build"]
    assert not covered(spec, ("pvp_rules.json", None))
    assert not covered(spec, ("classes.json", "/classes/Warrior"))
    assert not covered(spec, ("classes.json", None))
    assert covered(spec, ("spells.json", None))
    assert covered(ENGINES["pvp_dr"], ("classes.json", "/classes/Druid"))


def test_targeted_replay_runs_only_touched_engines(pair):
    _, after = pair

    def bump(doc):
        doc["spells"]["frostbolt"][0]["components"][0]["base_points"] += 1

    edit(after / "spell_scaling.json", bump)
    diffs = compare_inputs(*pair)
    diffs = {k: v for k, v in diffs.items() if k != "mage_leveling"} | {
        "mage_leveling": diffs["mage_leveling"]._replace(identical=True)
    }
    chosen = cases_to_replay(diffs)
    assert chosen and {e for e, _ in chosen} == {"mage_build"}
    assert {c for _, c in chosen} == set(ENGINES["mage_build"].cases)
    calls = []
    result = targeted_replay(diffs, lambda engine, case: calls.append((engine, case)) or f"{engine}:{case}")
    assert calls == chosen
    assert set(result) == {"mage_build"}
    assert not any(e == "pvp_dr" for e, _ in calls)


def test_targeted_replay_skips_copying_engines(pair):
    _, after = pair

    def warrior(doc):
        spell = next(iter(doc["classes"]["Warrior"]["spells"].values()))
        spell["ranks"][0]["level"] += 1

    edit(after / "classes.json", warrior)
    diffs = compare_inputs(*pair)
    assert different(diffs) == {"pvp_dr"}
    assert cases_to_replay(diffs) == []
    assert targeted_replay(diffs, lambda engine, case: pytest.fail(f"rejeu de {engine} {case}")) == {}


def test_nothing_to_replay_when_identical(pair):
    assert cases_to_replay(compare_inputs(*pair)) == []
