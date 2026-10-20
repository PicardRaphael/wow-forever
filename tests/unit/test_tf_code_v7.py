"""1.60.1.70450, bloc D (`tasks/70450-plan.md`) : codes de Talents Forever de génération 7 (addon 0.38.9, arbres du
build 70425, gardés par 70450). Même format que la génération 6 (lu dans le code de l'addon : la génération dit sur
quelle disposition des arbres le code est écrit) : forever lit et écrit la génération que l'addon installé annonce,
sur sa disposition ; un code d'une autre génération que celle de l'addon, ou d'une génération inconnue, reste refusé.
Format v7 pas encore relu en jeu : certitude `probable` de l'export.

Addon fabriqué dans `tmp_path` (structure de Talents Forever) ; aucun chiffre de jeu."""

import pytest
from conftest import DATA_DIR, PRE_70450_VERSION
from talents_forever_data import write_addon

from forever.talents_forever import export_build, load_addon
from forever.tf_code import CODE_VERSIONS, TfPlan, decode, encode


@pytest.fixture
def make_deps(make_deps_at_pre_70450_version):
    """Données de PRE_70450_VERSION : les arbres de l'addon fabriqué sont ceux de layout.json (conftest)."""
    return make_deps_at_pre_70450_version

CLASSES = DATA_DIR / PRE_70450_VERSION / "classes.json"
PLAN = TfPlan("mage", 20, ((1, 0), (0, 2), (0,)), None)  # une position par talent de la disposition MAX
MAX = ((3, 2), (5, 2), (1,))


def test_both_generations_are_known():
    assert set(CODE_VERSIONS) >= {"6", "7"}


def test_code_written_and_read_in_the_addon_generation():
    code = encode(PLAN, generation="7")
    assert code.endswith("-7")
    assert decode(code, MAX, "mage", generation="7").ranks == PLAN.ranks


def test_code_of_another_generation_is_refused():
    with pytest.raises(ValueError):
        decode(encode(PLAN, generation="6"), MAX, "mage", generation="7")  # autre disposition des arbres
    with pytest.raises(ValueError):
        decode("mage/20/1-02--8", MAX, "mage")  # génération inconnue


def test_export_follows_a_generation_7_addon(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=lambda doc: doc.update(codeVersion="7"))
    addon = load_addon(make_deps(wow_dir=root))
    assert addon is not None and addon.supported
    block = export_build(addon, "Mage", 20, {}, None)
    assert block["status"] == "ok" and block["code"].endswith("-7")
