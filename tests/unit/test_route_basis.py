"""CJ1, blocs 1c et 1f (décisions 277 et 279, registre I18) : sur les niveaux couverts par le parcours gratuit de la
race et de la classe, la route livrée est celle qui est acceptée : notre calcul s'il ressemble au parcours, sinon la
base adaptée, avec l'attribution à RestedXP dans le guide (licence CC BY-NC-SA 4.0, usage personnel) ; au-delà, notre
calcul reprend depuis la fin de la base adaptée.

Valeurs : addons fabriqués (`tests/fixtures/addons/dungeons`, `tests/fixtures/rxp_guides`) ; données du dépôt."""

import shutil

import pytest
from conftest import FIXTURES

from forever.route import RouteRequest, plan_route
from forever.rxp import encode_guide


@pytest.fixture
def deps(make_deps, tmp_path):
    root = tmp_path / "wow"
    shutil.copytree(FIXTURES / "addons" / "dungeons", root)
    shutil.copytree(FIXTURES / "rxp_guides" / "RXPGuides", root / "Interface" / "AddOns" / "RXPGuides")
    return make_deps(wow_dir=root, offline=True)


def test_plan_says_which_route_is_delivered_and_why(deps):
    plan = plan_route(deps, RouteRequest("mage", "horde", 1, 5, race="Orc"))
    basis = plan["basis"]
    assert basis["kind"] in ("calcul", "parcours adapté")
    assert basis["verdict"] and basis["guides"]
    if basis["kind"] == "calcul":
        assert basis["accepted"]
    text = encode_guide(plan, name="Forever · Bob · 1-5", group="Forever Routes")
    if basis["kind"] == "parcours adapté":
        assert "CC BY-NC-SA 4.0" in text and "RestedXP" in text
    assert "objective one" not in text and "Secret" not in text  # aucun texte de guide recopié


def test_without_race_the_route_is_our_calculation(deps):
    plan = plan_route(deps, RouteRequest("mage", "horde", 1, 5))
    assert plan["basis"]["kind"] == "calcul" and plan["basis"]["guides"] == []


def test_mid_route_farm_targets_its_own_level():
    plan = {
        "id": "x",
        "class": "mage",
        "faction": "horde",
        "levels": {"from": 1, "to": 9},
        "stops": [{"kind": "grind", "ref": 4, "name": None, "map": None, "x": None, "y": None}],
    }
    text = encode_guide(plan, name="n", group="g")
    assert ".xp 4 " in text
