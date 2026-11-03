"""Codes de Talents Forever de générations 9 et 10 (addon 0.38.14 : correctif du Mage du 28 octobre 2026, puis du
Druide et du Paladin du 30 octobre ; 10 est la première génération à deux chiffres). Même format que les générations
6 à 8, lu dans le code de l'addon (`TF.Encode`, `TF.Decode`) : la génération dit sur quelle disposition des arbres le
code est écrit, et forever lit cette disposition dans `Data.lua`. Formats pas encore relus en jeu : certitude
`probable` de l'export.

Addon fabriqué dans `tmp_path` (structure de Talents Forever) ; aucun chiffre de jeu."""

import pytest
from conftest import DATA_DIR, PRE_70450_VERSION
from talents_forever_data import write_addon

from forever.talents_forever import export_build, load_addon, popular_builds
from forever.tf_code import CODE_VERSIONS, TfPlan, decode, encode

CLASSES = DATA_DIR / PRE_70450_VERSION / "classes.json"
PLAN = TfPlan("mage", 20, ((1, 0), (0, 2), (0,)), None)
MAX = ((3, 2), (5, 2), (1,))
NEW = ("9", "10")


def addon_deps(tmp_path, make_deps, generation):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=lambda doc: doc.update(codeVersion=generation))
    return make_deps(wow_dir=root)


@pytest.mark.parametrize("generation", NEW)
def test_generation_is_known(generation):
    assert generation in CODE_VERSIONS


@pytest.mark.parametrize("generation", NEW)
def test_code_written_and_read(generation):
    code = encode(PLAN, generation=generation)
    assert code.endswith(f"-{generation}")
    assert decode(code, MAX, "mage", generation=generation).ranks == PLAN.ranks
    with pytest.raises(ValueError):
        decode(encode(PLAN, generation="8"), MAX, "mage", generation=generation)  # autre disposition des arbres


def test_generation_1_is_not_read_as_generation_10():
    with pytest.raises(ValueError):
        decode(encode(PLAN, generation="10")[:-1], MAX, "mage", generation="10")


@pytest.mark.parametrize("generation", NEW)
def test_addon_is_supported_and_exports_probable_codes(generation, tmp_path, make_deps_at_pre_70450_version):
    addon = load_addon(addon_deps(tmp_path, make_deps_at_pre_70450_version, generation))
    assert addon is not None and addon.supported
    block = export_build(addon, "Mage", 20, {}, None)
    assert block["status"] == "ok" and block["code"].endswith(f"-{generation}")
    assert block["certainty"] == "probable"  # format jamais relu en jeu


@pytest.mark.parametrize("generation", NEW)
def test_popular_builds_are_read(generation, tmp_path, make_deps_at_pre_70450_version):
    deps = addon_deps(tmp_path, make_deps_at_pre_70450_version, generation)
    top = popular_builds(load_addon(deps), deps, "Mage")["classes"]["Mage"]["top"]
    assert top and all(b["legality"] != "illisible" for b in top)
