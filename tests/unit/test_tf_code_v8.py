"""Codes de Talents Forever de génération 8 (addon 0.38.10 et suivants : correctif du serveur du 20 octobre 2026 sur
l'arbre Givre du Mage). Même format que les générations 6 et 7, lu dans le code de l'addon (`TF.Encode`, `TF.Decode`) :
la génération dit sur quelle disposition des arbres le code est écrit, et forever lit cette disposition dans
`Data.lua`. Format v8 pas encore relu en jeu : certitude `probable` de l'export.

Addon fabriqué dans `tmp_path` (structure de Talents Forever) ; aucun chiffre de jeu."""

import pytest
from conftest import DATA_DIR, PRE_70450_VERSION
from talents_forever_data import write_addon

from forever.talents_forever import export_build, load_addon, popular_builds
from forever.tf_code import CODE_VERSIONS, TfPlan, decode, encode

CLASSES = DATA_DIR / PRE_70450_VERSION / "classes.json"
PLAN = TfPlan("mage", 20, ((1, 0), (0, 2), (0,)), None)
MAX = ((3, 2), (5, 2), (1,))


@pytest.fixture
def deps(tmp_path, make_deps_at_pre_70450_version):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=lambda doc: doc.update(codeVersion="8"))
    return make_deps_at_pre_70450_version(wow_dir=root)


def test_generation_8_is_known():
    assert "8" in CODE_VERSIONS


def test_code_written_and_read_in_generation_8():
    code = encode(PLAN, generation="8")
    assert code.endswith("-8")
    assert decode(code, MAX, "mage", generation="8").ranks == PLAN.ranks
    with pytest.raises(ValueError):
        decode(encode(PLAN, generation="7"), MAX, "mage", generation="8")  # autre disposition des arbres


def test_a_generation_8_addon_is_supported_and_exports_probable_codes(deps):
    addon = load_addon(deps)
    assert addon is not None and addon.supported
    block = export_build(addon, "Mage", 20, {}, None)
    assert block["status"] == "ok" and block["code"].endswith("-8")
    assert block["certainty"] == "probable"  # format v8 jamais relu en jeu


def test_popular_builds_of_a_generation_8_addon_are_read(deps):
    top = popular_builds(load_addon(deps), deps, "Mage")["classes"]["Mage"]["top"]
    assert top and all(b["legality"] != "illisible" for b in top)
