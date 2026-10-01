"""Consultation des familiers par le MCP (`forever_lookup(kind="pets")`) et le service (CH0, bloc D) : règles,
famille (nom français et anglais), capacité, bête, guide ; candidats listés ; `kind` inconnu ; sans addon, fiches
du client seules et guide refusé ; provenance avec l'addon ; aucun réseau.

Données : version installée (`pets.json`, `pet_rules.json`) ; dossier du jeu construit dans le test avec les
fixtures `tests/fixtures/bestiary/` et `tests/fixtures/questie/11.38.0`."""

import json
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.pets_lookup import lookup_pets, pets_crosscheck, pets_mine
from forever.pipeline.bestiary import read_bestiary
from forever.provenance import validate_provenance

PETS = read_json(DATA_DIR / LOCAL_VERSION / "pets.json")
PET_RULES = read_json(DATA_DIR / LOCAL_VERSION / "pet_rules.json")
INFO = read_bestiary(FIXTURES / "bestiary" / "ForeverBestiary")["info"]


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    addons = root / "Interface" / "AddOns"
    shutil.copytree(FIXTURES / "bestiary" / "ForeverBestiary", addons / "ForeverBestiary")
    shutil.copytree(FIXTURES / "questie" / "11.38.0", addons / "Questie")
    sv = root / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    shutil.copyfile(FIXTURES / "bestiary" / "ForeverBestiary.lua", sv / "ForeverBestiary.lua")
    return root


def call_lookup(deps, arguments):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_lookup", arguments)

    return asyncio.run(go())


def test_rules_without_name(make_deps, wow):
    out = lookup_pets(make_deps(wow_dir=wow))
    assert out["kind"] == "pets_rules" and [r["key"] for r in out["rules"]] == list(PET_RULES["rules"])
    assert validate_provenance(out["provenance"]) == []


def test_family_by_french_and_english_name(make_deps, wow):
    deps = make_deps(wow_dir=wow)
    wolf = PETS["families"]["wolf"]
    fr = lookup_pets(deps, wolf["name"]["fr"])
    en = lookup_pets(deps, "Wolf")
    assert fr["kind"] == en["kind"] == "pets_family" and fr["key"] == en["key"] == "wolf"
    assert fr["bonus"] == wolf["bonus"]
    text = json.dumps(fr["provenance"], ensure_ascii=False)
    assert f"Forever Bestiary {INFO['version']}" in text


def test_ability_and_beast(make_deps, wow):
    deps = make_deps(wow_dir=wow)
    bite = lookup_pets(deps, PETS["abilities"]["bite"]["name"]["fr"], rank=3, detail=True)
    assert bite["kind"] == "pets_ability" and [r["rank"] for r in bite["ranks"]] == [3]
    beast = lookup_pets(deps, "Prowler of the Test")
    assert beast["kind"] == "pets_beast" and beast["family"]["key"] == "wolf"


def test_guide_with_zone_and_level_and_its_provenance(make_deps, wow):
    deps = make_deps(wow_dir=wow)
    out = lookup_pets(deps, "Bite", rank=3, zone="Les Tarides", level=10)
    assert out["kind"] == "pets_guide" and out["zones"][0]["name"]["en"] == "The Barrens"
    prov = out["provenance"]
    assert validate_provenance(prov) == [] and prov["game_version"] == LOCAL_VERSION
    text = json.dumps(prov, ensure_ascii=False)
    for needle in (f"Forever Bestiary {INFO['version']}", INFO["date"], INFO["community_date"], "carte communautaire"):
        assert needle in text, needle
    assert (
        out["addon"]["fingerprint"] == INFO["fingerprint"] and out["addon"]["community_date"] == INFO["community_date"]
    )


def test_guide_refuses_a_missing_level(make_deps, wow):
    with pytest.raises(InvalidArgumentError):
        lookup_pets(make_deps(wow_dir=wow), "Bite", rank=3, zone="Les Tarides")


def test_without_addon_client_sheets_still_rendered_and_guide_refused(make_deps, tmp_path):
    deps = make_deps(wow_dir=tmp_path / "vide")
    fam = lookup_pets(deps, "Wolf")
    assert fam["kind"] == "pets_family" and any(
        "Forever Bestiary absent" in a for a in fam["provenance"]["assumptions"]
    )
    with pytest.raises(InvalidArgumentError) as exc:
        lookup_pets(deps, "Bite", rank=3, zone="Les Tarides", level=10)
    assert "Forever Bestiary" in exc.value.message


def test_crosscheck_and_mine_with_provenance(make_deps, wow):
    deps = make_deps(wow_dir=wow)
    report = pets_crosscheck(deps)
    assert report["gaps"] and validate_provenance(report["provenance"]) == []
    mine = pets_mine(deps)
    assert mine["pets"] and "JoueurTiersInvente" not in json.dumps(mine, ensure_ascii=False)


# --- MCP -------------------------------------------------------------------------------------------------


def test_mcp_pets_kind(make_deps, wow):
    deps = make_deps(wow_dir=wow)
    r = call_lookup(deps, {"kind": "pets"})
    assert not r.is_error and r.structured_content["kind"] == "pets_rules"
    fam = call_lookup(deps, {"kind": "pets", "name": "Loup"})
    assert not fam.is_error and fam.structured_content["key"] == "wolf"
    g = call_lookup(deps, {"kind": "pets", "name": "Bite", "rank": 3, "zone": "Les Tarides", "level": 10})
    assert not g.is_error and g.structured_content["kind"] == "pets_guide"


def test_mcp_ambiguous_name_lists_candidates(make_deps, wow):
    data = wow / "Interface" / "AddOns" / "ForeverBestiary" / "Data" / "Data.lua"
    text = data.read_text(encoding="utf-8").replace('en = "Prowler of the Test"', 'en = "Wolf"', 1)
    data.write_bytes(text.encode("utf-8"))
    r = call_lookup(make_deps(wow_dir=wow), {"kind": "pets", "name": "Wolf"})
    assert r.is_error
    err = r.structured_content["error"]
    assert err["code"] == "invalid_argument" and len(err["suggestions"]) >= 2


def test_unknown_kind_lists_pets(make_deps, capsys):
    r = call_lookup(make_deps(), {"kind": "objet", "name": "x"})
    assert r.is_error and "pets" in r.structured_content["error"]["suggestions"]
    capsys.readouterr()
    assert main(["lookup", "objet", "x", "--json"], make_deps()) != 0
    assert "pets" in json.loads(capsys.readouterr().out)["error"]["suggestions"]
