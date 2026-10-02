"""Une révision installe `pets.json` décodé du client (CH0, bloc C, révision 5) : `added_file` quand le dépôt ne l'a
pas, `replaced_file` quand il change, rien quand il est identique ; jamais un `pets.json` absent de la candidate.

Candidate décodée des fixtures 1.60.1.70124 ; installation sur une copie des données."""

import shutil

import pytest
from conftest import CLASS_FIXTURE_VERSION as LOCAL_VERSION  # version des extraits, pas la version installée
from conftest import WAGO_70124, isolated_deps, read_json

from forever.manifest import write_manifest
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install, plan_install

PETS = "pets.json"


@pytest.fixture
def data_copy(data_at_class_fixture_version):
    """Copie des données ramenée à la version des extraits (1.60.1.70124) : la candidate des fixtures la révise
    (1.60.1.70170 installée le 2026-10-02 porte d'autres talents que ces extraits)."""
    return data_at_class_fixture_version


@pytest.fixture(scope="module")
def decoded(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pets")
    return decode_version(isolated_deps(tmp), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp / "candidate")


def pets_changes(plan):
    return [c for c in plan["changes"] if c["file"] == PETS]


def test_pets_json_is_added_when_the_repository_has_none(data_copy, decoded, make_deps):
    (data_copy / LOCAL_VERSION / PETS).unlink(missing_ok=True)
    write_manifest(data_copy)
    plan = plan_install(make_deps(data_dir=data_copy), str(decoded.root))
    assert [c["rule"] for c in pets_changes(plan)] == ["added_file"] and not plan["refused"]


def test_pets_json_is_installed_and_described(data_copy, decoded, make_deps):
    (data_copy / LOCAL_VERSION / PETS).unlink(missing_ok=True)
    write_manifest(data_copy)
    apply_install(make_deps(data_dir=data_copy), str(decoded.root), motif="test")
    vdir = data_copy / LOCAL_VERSION
    assert read_json(vdir / PETS) == read_json(decoded.root / LOCAL_VERSION / PETS)
    assert read_json(vdir / "sources.json")["files"][PETS]["certainty"] == "certain"


def test_identical_pets_json_gives_no_change(data_copy, decoded, make_deps):
    shutil.copyfile(decoded.root / LOCAL_VERSION / PETS, data_copy / LOCAL_VERSION / PETS)
    write_manifest(data_copy)
    assert pets_changes(plan_install(make_deps(data_dir=data_copy), str(decoded.root))) == []


def test_candidate_without_pets_json_never_removes_it(data_copy, decoded, make_deps, tmp_path):
    cand = tmp_path / "cand"
    shutil.copytree(decoded.root, cand)
    (cand / LOCAL_VERSION / PETS).unlink()
    write_manifest(cand)
    assert pets_changes(plan_install(make_deps(data_dir=data_copy), str(cand))) == []
