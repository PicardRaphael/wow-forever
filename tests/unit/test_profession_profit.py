"""Métiers rentables et hôtel des ventes (AMI7a, `tasks/AMI7a-plan.md` ; décisions 272, 288, 300).

Pour un métier et un rang (ou les métiers du profil) : recettes faisables classées par profit à l'hôtel des ventes
(dernier minimum d'Auctionator du produit moins coût des réactifs, le moins cher entre marchand et hôtel des ventes),
prix manquants nommés, taxe de l'hôtel des ventes dite absente ; objets des sacs et de la banque à vendre (Forever
Companion). Fixtures inventées : `tests/fixtures/professions/` (SkillUp Forever, Forever Companion) et
`tests/fixtures/addon/Auctionator.lua` (prix du royaume « Royaume » : 1001 = 120, 1002 = 10, 1003 = 45000, 1004 = 34,
jour 2463)."""

import json
import shutil
from datetime import timedelta

import mcp  # noqa: F401 : boucle asyncio du client MCP sous Windows (tests/conftest.py, piège T06b)
import pytest
from conftest import FIXTURES

from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.pipeline.auctionator import DAY_EPOCH
from forever.pipeline.skillup import read_crafting
from forever.profile import set_character
from forever.provenance import validate_provenance

PROF = FIXTURES / "professions"
DAY = (DAY_EPOCH + timedelta(days=2463)).isoformat()


def make_wow(root, *, companion=True, beta_realm=False):
    """Dossier du jeu fabriqué : addon SkillUp Forever et SavedVariables d'un compte."""
    wow = root / "wow"
    shutil.copytree(PROF / "AddOns", wow / "Interface" / "AddOns")
    sv = wow / "WTF" / "Account" / "TEST" / "SavedVariables"
    sv.mkdir(parents=True)
    raw = (FIXTURES / "addon" / "Auctionator.lua").read_bytes()
    if beta_realm:  # le second royaume devient un royaume de la bêta (décision 300)
        raw = raw.replace(b'["AutreRoyaume"]', b'["ClassicBetaRoyaume"]')
    (sv / "Auctionator.lua").write_bytes(raw)
    if companion:
        shutil.copy(PROF / "SavedVariables" / "ForeverCompanion.lua", sv / "ForeverCompanion.lua")
    return wow


@pytest.fixture
def wow(tmp_path):
    return make_wow(tmp_path)


def test_crafting_data_is_read_from_skillup():
    c = read_crafting(PROF / "AddOns")
    assert c["recipes"][920002]["reagents"] == [(1002, 3), (1006, 1)]
    assert c["recipes"][920002]["output"] == (1004, 2)
    assert c["recipes"][920005]["output"] == (1008, 1.5)  # rendement moyen
    assert c["recipes"][920006]["output"] is False  # aucun objet produit
    assert c["recipes"][920007]["reagents"] == []
    assert c["vendor_prices"] == {1002: 8, 1006: 5}
    assert c["vendor_names"][1006] == "Fil Test"
    assert c["sell_prices"] == {1001: 30, 1008: 7}  # une valeur non entière est ignorée


def test_recipes_ranked_by_profit(make_deps, wow):
    from forever.professions import profession_profit

    out = profession_profit(make_deps(wow_dir=wow), profession="Tailoring", skill=50, realm="Royaume")
    assert validate_provenance(out["provenance"]) == []
    assert out["provenance"]["certainty"] == "suppose"
    assert out["realm"] == "Royaume"
    (prof,) = out["professions"]
    assert prof["profession"] == "Tailoring" and prof["skill"] == 50
    ids = [r["spell_id"] for r in prof["recipes"]]
    # chiffrées par profit décroissant, puis profit inconnu ; trop haute et sans objet produit écartées
    assert ids == [920001, 920002, 920003, 920005, 920004, 920007]
    assert prof["without_output"] == 1 and prof["too_high"] == 1
    best = prof["recipes"][0]
    assert best["name"] == "Recette Rentable" and best["color"] == "vert"
    assert best["cost"] == 240 and best["sale"] == 45000 and best["profit"] == 44760
    assert best["output"]["unit_price"] == 45000 and best["output"]["date"] == DAY
    assert best["reagents"][0] == {
        "item_id": 1001,
        "name": None,
        "quantity": 2,
        "unit_price": 120,
        "source": "auctionator",
        "date": DAY,
    }


def test_cheapest_source_for_reagents(make_deps, wow):
    from forever.professions import profession_profit

    out = profession_profit(make_deps(wow_dir=wow), profession="Tailoring", skill=50, realm="Royaume")
    mid = next(r for r in out["professions"][0]["recipes"] if r["spell_id"] == 920002)
    by_id = {r["item_id"]: r for r in mid["reagents"]}
    assert by_id[1002]["unit_price"] == 8 and by_id[1002]["source"] == "marchand"  # 8 au marchand < 10 à l'HV
    assert by_id[1006]["unit_price"] == 5 and by_id[1006]["name"] == "Fil Test"
    assert mid["cost"] == 29 and mid["sale"] == 68 and mid["profit"] == 39
    loss = next(r for r in out["professions"][0]["recipes"] if r["spell_id"] == 920003)
    assert loss["profit"] == -44880


def test_missing_prices_are_named(make_deps, wow):
    from forever.professions import profession_profit

    out = profession_profit(make_deps(wow_dir=wow), profession="Tailoring", skill=50, realm="Royaume")
    rows = {r["spell_id"]: r for r in out["professions"][0]["recipes"]}
    assert rows[920004]["profit"] is None and rows[920004]["missing"] == [1007]
    assert rows[920005]["profit"] is None and rows[920005]["missing"] == [1008]
    assert rows[920005]["output"]["vendor_sell"] == 7  # vente au marchand donnée à côté
    assert rows[920007]["profit"] is None and rows[920007]["reagents_unknown"] is True


def test_auction_house_cut_is_said_absent(make_deps, wow):
    from forever.professions import profession_profit

    out = profession_profit(make_deps(wow_dir=wow), profession="Tailoring", skill=50, realm="Royaume")
    assert out["auction_cut"] is None
    assert any("taxe" in a and "absente" in a for a in out["provenance"]["assumptions"])


def test_items_to_sell_from_bags_and_bank(make_deps, wow):
    from forever.professions import profession_profit

    out = profession_profit(make_deps(wow_dir=wow), profession="Tailoring", skill=50, realm="Royaume")
    sell = out["to_sell"]
    assert sell["available"] is True
    assert [(i["item_id"], i["count"], i["total"]) for i in sell["items"]] == [
        (1003, 2, 90000),
        (1001, 5, 600),
        (1004, 10, 340),
    ]
    assert sell["items"][2]["where"] == [{"character": "Moi", "realm": "Royaume", "place": "banque", "count": 10}]
    assert sell["missing"] == [1009]
    assert "Ancien" not in json.dumps(sell)  # personnage d'un royaume de la bêta ignoré ; équipement porté non compté


def test_items_to_sell_without_companion(make_deps, tmp_path):
    from forever.professions import profession_profit

    wow = make_wow(tmp_path, companion=False)
    out = profession_profit(make_deps(wow_dir=wow), profession="Tailoring", skill=50, realm="Royaume")
    assert out["to_sell"]["available"] is False and out["to_sell"]["items"] == []
    assert "Forever Companion" in out["to_sell"]["reason"]


def test_realm_choice(make_deps, tmp_path):
    from forever.professions import profession_profit

    with pytest.raises(InvalidArgumentError):  # deux royaumes de prix : --realm exigé
        profession_profit(make_deps(wow_dir=make_wow(tmp_path / "a")), profession="Tailoring", skill=50)
    out = profession_profit(
        make_deps(wow_dir=make_wow(tmp_path / "b", beta_realm=True)), profession="Tailoring", skill=50
    )
    assert out["realm"] == "Royaume" and out["ignored_realms"] == ["ClassicBetaRoyaume"]


def test_professions_of_the_profile(make_deps, wow):
    from forever.professions import profession_profit

    deps = make_deps(wow_dir=wow)
    set_character(deps, "Moi", cls="Mage", professions={"Tailoring": 50, "Cooking": 50, "Herboristerie": 10})
    out = profession_profit(deps, realm="Royaume")
    assert [(p["profession"], p["skill"]) for p in out["professions"]] == [("Cooking", 50), ("Tailoring", 50)]
    dish = out["professions"][0]["recipes"][0]
    assert dish["name"] == "Plat Test" and dish["color"] == "gris" and dish["profit"] == 26
    assert out["uncovered"] == ["Herboristerie"]


def test_skill_required_without_profile(make_deps, wow):
    from forever.professions import profession_profit

    with pytest.raises(InvalidArgumentError):
        profession_profit(make_deps(wow_dir=wow), profession="Tailoring", realm="Royaume")


def test_cli_professions_profit(make_deps, wow, capsys):
    deps = make_deps(wow_dir=wow)
    argv = ["professions", "profit", "--profession", "Tailoring", "--skill", "50", "--realm", "Royaume"]
    assert main([*argv, "--json"], deps=deps) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["professions"][0]["recipes"][0]["profit"] == 44760
    assert main(argv, deps=deps) == 0
    text = capsys.readouterr().out
    assert "Recette Rentable" in text and "1007" in text and "Objets à vendre" in text


def test_mcp_profession_profit(make_deps, wow):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(make_deps(wow_dir=wow))) as client:
            args = {"kind": "profession_profit", "name": "Tailoring", "level": 50, "realm": "Royaume"}
            return await client.call_tool("forever_lookup", args)

    result = asyncio.run(go())
    assert not result.is_error
    out = result.structured_content
    assert out["professions"][0]["recipes"][0]["spell_id"] == 920001
    assert validate_provenance(out["provenance"]) == []
