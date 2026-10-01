"""Plafond de niveau de la bêta, fait d'installation (T08b, bloc B, D2) : `forever install --beta-level-cap N
--beta-level-cap-source S` l'écrit dans `meta.json` (`game_state`) et dans la révision, avec sa source, sa date et
sa certitude ; sans option, la valeur précédente est reportée et le rapport le dit ; `GameData` lit `game_state`, et
l'ancienne clé `mechanics.json` `build.beta_level_cap` est retirée par l'installation puis refusée.

Candidate décodée des fixtures 1.60.1.70124 ; installation sur une copie des données. La valeur de test est la valeur
installée plus un écart arbitraire, jamais un chiffre de jeu écrit ici."""

import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, isolated_deps, read_json

from forever.cli import main
from forever.errors import DataSchemaError
from forever.gamedata import build_game_data
from forever.manifest import write_manifest
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install, plan_install, render_install_report
from forever.store import load_version

OLD_KEY = "build.beta_level_cap"
CURRENT = read_json(DATA_DIR / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]["value"]
TEST_CAP = CURRENT + 10  # valeur de test arbitraire
NOTE = "https://us.forums.blizzard.com/en/wow/t/exemple/1"


@pytest.fixture(scope="module")
def cand(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("gs")
    return decode_version(isolated_deps(tmp), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp / "candidate")


def revision_of(data):
    return read_json(data / LOCAL_VERSION / "sources.json")["revision"]


def test_option_writes_cap_source_and_certainty(data_copy, cand, make_deps):
    deps = make_deps(data_dir=data_copy)
    before = revision_of(data_copy)
    plan = plan_install(deps, str(cand.root), beta_level_cap=TEST_CAP, beta_level_cap_source=NOTE)
    assert next(c for c in plan["changes"] if c["rule"] == "game_state")["after"] == TEST_CAP
    apply_install(deps, str(cand.root), motif="test", beta_level_cap=TEST_CAP, beta_level_cap_source=NOTE)
    state = read_json(data_copy / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]
    assert state["value"] == TEST_CAP and state["source"] == NOTE
    assert state["certainty"] == "probable" and state["revision"] == before + 1
    last = read_json(data_copy / LOCAL_VERSION / "revisions.json")["revisions"][-1]
    assert last["game_state"]["beta_level_cap"]["value"] == TEST_CAP
    assert OLD_KEY not in read_json(data_copy / LOCAL_VERSION / "mechanics.json")["values"]
    gd = build_game_data(load_version(deps))
    assert gd.build.beta_level_cap == TEST_CAP


def test_observation_is_certain(data_copy, cand, make_deps):
    deps = make_deps(data_dir=data_copy)
    apply_install(deps, str(cand.root), motif="test", beta_level_cap=TEST_CAP, beta_level_cap_source="observation")
    state = read_json(data_copy / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]
    assert state["certainty"] == "certain"


def test_without_option_the_value_is_carried_and_said(data_copy, cand, make_deps):
    deps = make_deps(data_dir=data_copy)
    before = revision_of(data_copy)
    plan = plan_install(deps, str(cand.root))
    assert plan["game_state"]["beta_level_cap"]["carried"] is True
    assert "reporté" in render_install_report(plan)
    apply_install(deps, str(cand.root), motif="test")
    state = read_json(data_copy / LOCAL_VERSION / "meta.json")["game_state"]["beta_level_cap"]
    assert state["value"] == CURRENT
    assert state["carried_from"] == f"révision {before}"
    assert build_game_data(load_version(deps)).build.beta_level_cap == CURRENT


def test_source_is_required_with_the_cap(data_copy, cand, make_deps, capsys):
    code = main(
        ["install", str(cand.root), "--beta-level-cap", str(TEST_CAP), "--dry-run"], make_deps(data_dir=data_copy)
    )
    assert code == 2


def test_cli_dry_run_shows_the_cap(data_copy, cand, make_deps, capsys):
    argv = ["install", str(cand.root), "--beta-level-cap", str(TEST_CAP), "--beta-level-cap-source", NOTE, "--dry-run"]
    code = main(argv, make_deps(data_dir=data_copy))
    out, _ = capsys.readouterr()
    assert code == 0 and "plafond de la bêta" in out and NOTE in out


def test_old_key_is_refused_once_game_state_exists(data_copy, cand, make_deps):
    deps = make_deps(data_dir=data_copy)
    apply_install(deps, str(cand.root), motif="test", beta_level_cap=TEST_CAP, beta_level_cap_source=NOTE)
    path = data_copy / LOCAL_VERSION / "mechanics.json"
    doc = read_json(path)
    doc["values"][OLD_KEY] = {"value": CURRENT, "certainty": "probable", "source": "test"}
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    write_manifest(data_copy)
    with pytest.raises(DataSchemaError):
        build_game_data(load_version(deps))
