"""Version candidate : dossier de données complet hors de forever/data/, fichiers hérités tracés, aucun réseau."""

import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70009, FakeHttp, read_json

from forever.errors import CandidateExistsError, CsvMissingError
from forever.gamedata import build_game_data
from forever.manifest import compute_manifest, verify
from forever.pipeline.decode import DECODED_FILES, INHERITED_FILES, decode_version
from forever.pipeline.fetch import wago_dir
from forever.store import VersionData, current_identity, read_sources

EXPECTED_FILES = {*DECODED_FILES, *INHERITED_FILES, "sources.json"}


def version_data(root):
    identity = current_identity(root)
    return VersionData(
        identity.game_version, identity.data_sha, root / LOCAL_VERSION, read_sources(root, LOCAL_VERSION)
    )


def test_candidate_is_a_complete_data_dir(candidate):
    assert candidate.version == LOCAL_VERSION
    assert verify(candidate.root).ok
    names = {p.name for p in (candidate.root / LOCAL_VERSION).iterdir()}
    assert names == EXPECTED_FILES and len(names) == 12  # T04 : monsters.json hérité, spell_scaling.json décodé
    assert "_source_gunba_mage_tree.json" not in names and "confirmed_changes.json" not in names


def test_counts(candidate):
    assert (candidate.talents, candidate.spells, candidate.spell_ranks) == (54, 15, 99)


def test_inherited_files_are_marked(candidate):
    for name in INHERITED_FILES:
        assert read_json(candidate.root / LOCAL_VERSION / name)["inherited_from"] == LOCAL_VERSION, name


def test_sources_describe_every_file(candidate):
    sources = read_json(candidate.root / LOCAL_VERSION / "sources.json")
    assert sources["game_version"] == LOCAL_VERSION
    assert set(sources["files"]) == EXPECTED_FILES - {"sources.json"}
    assert sources["files"]["talents.json"]["certainty"] == "certain"
    assert sources["files"]["spells.json"]["certainty"] == "certain"
    for name in INHERITED_FILES:
        assert f"hérité de {LOCAL_VERSION}" in " ".join(sources["files"][name]["notes"]), name
    local = read_json(DATA_DIR / LOCAL_VERSION / "sources.json")
    assert sources["product"] == local["product"] and sources["version_prefix"] == local["version_prefix"]


def test_engine_accepts_candidate(candidate):
    gd = build_game_data(version_data(candidate.root))
    assert len(gd.talents) == 54 and len(gd.spells) == 15


def test_observations_mention_client_spell_ids(candidate):
    assert any("spellIds" in o for o in candidate.observations)


def test_repository_data_is_untouched(make_deps, tmp_path):
    before = compute_manifest(DATA_DIR)
    decode_version(make_deps(), LOCAL_VERSION, csv_dir=WAGO_70009, out=tmp_path / "c")
    assert compute_manifest(DATA_DIR) == before
    assert verify(DATA_DIR).ok


def test_default_out_and_csv_dir_use_the_cache(make_deps):
    http = FakeHttp.failing()
    deps = make_deps(http=http)
    shutil.copytree(WAGO_70009, wago_dir(deps.cache_dir, LOCAL_VERSION))
    c = decode_version(deps, LOCAL_VERSION)
    assert c.root == deps.cache_dir / "candidates" / LOCAL_VERSION
    assert http.calls == []


def test_existing_candidate_needs_force(make_deps, tmp_path):
    out = tmp_path / "c"
    decode_version(make_deps(), LOCAL_VERSION, csv_dir=WAGO_70009, out=out)
    with pytest.raises(CandidateExistsError) as info:
        decode_version(make_deps(), LOCAL_VERSION, csv_dir=WAGO_70009, out=out)
    assert info.value.exit_code == 2
    assert decode_version(make_deps(), LOCAL_VERSION, csv_dir=WAGO_70009, out=out, force=True).root == out


def test_missing_csv_asks_for_fetch(make_deps, tmp_path):
    with pytest.raises(CsvMissingError) as info:
        decode_version(make_deps(), LOCAL_VERSION, csv_dir=tmp_path / "vide", out=tmp_path / "c")
    assert info.value.exit_code == 4 and "forever fetch" in info.value.action
    assert not (tmp_path / "c").exists()
