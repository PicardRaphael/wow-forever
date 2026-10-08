"""Codes de test du Chasseur et du Démoniste à importer en jeu (demande de l'utilisateur du 2026-10-08) : builds
fixes de `tests/fixtures/talents_forever/class_witnesses.json`, légaux sur nos données, encodés par notre
exportateur et relus à l'identique. Addon synthétique dans `tmp_path` ; aucun accès au dossier réel du jeu."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION
from talents_forever_data import load_fixture, write_addon

from forever.lookup import check_talents
from forever.talents_forever import decode_code, export_build, load_addon

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"
CASES = load_fixture("class_witnesses.json")["cases"]


@pytest.fixture
def deps(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES)
    return make_deps(wow_dir=root)


@pytest.mark.parametrize("name", sorted(CASES))
def test_class_witness_is_legal_encoded_and_read_back(deps, name):
    case = CASES[name]
    assert set(case["must_include"]) <= set(case["talents"])
    assert check_talents(deps, case["class"], case["talents"], case["level"])["legal"] is True
    addon = load_addon(deps)
    block = export_build(addon, case["class"], case["level"], case["talents"], None)
    assert block["status"] == "ok" and block["code"] == case["expected_code"]
    back = decode_code(addon, deps, case["expected_code"])
    assert back["class"] == case["class"] and back["talents"] == case["talents"] and back["legal"] is True


def test_class_witnesses_verified_in_game():
    """Relevé de l'utilisateur du 2026-10-08 : les deux codes s'affichent en jeu exactement comme prévu."""
    for case in CASES.values():
        assert case["verified_in_game"] == "import"
        assert "relevé en jeu du 2026-10-08" in case["source"]


@pytest.mark.parametrize(
    ("class_name", "verified"), [("Mage", True), ("Hunter", True), ("Warlock", True), ("Rogue", False)]
)
def test_export_says_which_classes_were_read_back_in_game(deps, class_name, verified):
    block = export_build(load_addon(deps), class_name, 20, {}, None)
    assert block["status"] == "ok" and block["certainty"] == "certain"  # format v6 relu en jeu (décision 210)
    prov = block["provenance"]
    assert prov["class_verified_in_game"] is verified
    source = prov["class_verified_in_game_source"]
    assert (source is not None and "2026-10-08" in source) if verified else source is None
