"""Règle générale des boutons et suites de l'essai du Chasseur réel (décision 243) :

- aucun bouton n'est réservé à une classe, sauf Familiers (classes qui ont un familier) ;
- Familiers : les bêtes apprivoisables dont Forever Bestiary ne connaît pas les rangs enseignés sont rendues aussi,
  avec leur famille et les capacités de leur famille lues dans le client ; positions absentes dites ;
- addons : un passage de `forever update` hors ligne voit un addon dont la version change ; sans inventaire précédent
  (remise à zéro du PC), un addon dont dépend le dépôt est relu (décision 295 : Questie par la veille elle-même,
  sans attente) ;
- banc d'essai : PvP depuis le contexte réel du Chasseur (cible ajoutée au contexte relevé).

Fixtures : `tests/fixtures/bestiary/`, Questie ; aucun chiffre du jeu écrit ici."""

import copy
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json
from mcp import Client  # noqa: F401  (tests MCP : socket local autorisé par conftest)
from test_hunter_p06b import LEVEL, context, hunter_bench, run_calls  # noqa: F401  (fixture importée)

from forever.bridge.buttons import BUTTONS
from forever.bridge.context import resolve
from forever.bridge.plans import button_plan, plan_text
from forever.engine.leveling import level_band
from forever.gamedata import build_game_data
from forever.pets import tame_guide
from forever.pipeline.bestiary import read_bestiary
from forever.store import load_version

PETS = read_json(DATA_DIR / LOCAL_VERSION / "pets.json")
PET_RULES = read_json(DATA_DIR / LOCAL_VERSION / "pet_rules.json")


# --- règle générale ------------------------------------------------------------------------------------------------


def test_no_button_is_reserved_to_a_class_except_pets():
    for b in BUTTONS:
        if b.key == "pets":
            assert b.classes == ("HUNTER",)  # Démoniste (démons) : avec sa tranche de classe
        else:
            assert b.classes is None, b.key


# --- Familiers : bêtes sans rang connu ---------------------------------------------------------------------------


def test_beasts_without_known_ranks_are_listed_with_their_family_abilities(make_deps):
    bestiary = copy.deepcopy(read_bestiary(FIXTURES / "bestiary" / "ForeverBestiary"))
    wolf = next(b for b in bestiary["beasts"] if b.get("family") == "wolf")
    bestiary["beasts"].append(
        {**wolf, "id": 990100, "name": {"en": "Unranked Beast of the Test"}, "taught": [], "coords": {}}
    )
    deps = make_deps()
    band = level_band(build_game_data(load_version(deps)), LEVEL)
    out = tame_guide(PETS, PET_RULES, bestiary, level=LEVEL, zone=wolf["zones"][0], band=band, zone_levels={})
    entry = next(b for z in out["zones"] for b in z["beasts"] if b["id"] == 990100)
    assert entry["taught"] == [] and entry["family"] == "wolf"
    family_abilities = PETS["families"]["wolf"]["abilities"]
    assert entry["family_abilities"] and {a["key"] for a in entry["family_abilities"]} <= set(family_abilities)
    assert entry["coords"] == [] and entry["positions_known"] is False


def test_pets_consigne_names_the_client_as_the_source_of_ranks(hunter_bench):  # noqa: F811
    _, data = hunter_bench
    text = plan_text(button_plan("pets", resolve(data, context("chasseur15")), data.level_cap))
    assert "données du client" in text and "positions" in text


# --- addons relus ------------------------------------------------------------------------------------------------


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    shutil.copytree(FIXTURES / "questie" / "11.38.0", root / "Interface" / "AddOns" / "Questie")
    return root


def addons_pass(deps):
    from forever.update import UpdateOptions, run_update

    return run_update(deps, UpdateOptions(only=frozenset({"addons"}), network=False))


def test_a_pass_without_previous_inventory_rereads_the_addons_the_repo_depends_on(make_deps, wow):
    deps = make_deps(wow_dir=wow)
    report = addons_pass(deps)
    assert [p for p in report["pending"] if p["kind"] == "addon_data"] == []
    step = next(s for s in report["steps"] if s["name"] == "addons")
    assert "Questie relu" in step["detail"]


def test_an_offline_pass_sees_a_version_change(make_deps, wow):
    from forever.addons import addons_status

    deps = make_deps(wow_dir=wow)
    addons_status(deps, save=True)
    toc = wow / "Interface" / "AddOns" / "Questie" / "Questie_Camelot.toc"
    text = toc.read_text(encoding="utf-8")
    toc.write_bytes(
        text.replace("## Version: 11.38.0 Forever-v27", "## Version: 11.39.0 Forever-v28", 1).encode("utf-8")
    )
    report = addons_pass(deps)
    step = next(s for s in report["steps"] if s["name"] == "addons")
    assert step["status"] == "fait", step
    assert [c["name"] for c in step["data"]["changed"]] == ["Questie"]


# --- banc : PvP depuis le contexte réel du Chasseur ------------------------------------------------------------


def test_hunter_pvp_on_the_real_context(hunter_bench):  # noqa: F811
    deps, data = hunter_bench
    ctx = dict(context("chasseur15"))
    target = context("mage19_cible_chaman21_tauren")
    ctx.update({k: v for k, v in target.items() if k.startswith("target")})
    plan = button_plan("pvp", resolve(data, ctx), data.level_cap)
    assert plan is not None and plan.calls[0].args["name"] == "Hunter"
    (sheet,) = run_calls(deps, plan)
    assert sheet.get("threats") or sheet.get("missing")
