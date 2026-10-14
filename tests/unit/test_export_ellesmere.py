"""Profils EllesmereUI par personnage et par rôle (EX1, bloc F, décision 267) : chaîne `!EUI_`.

Valeurs : sauvegarde synthétique `tests/fixtures/exports/ellesmere_base.lua` (forme relevée dans EllesmereUI 9.5.4),
rôles de `tests/fixtures/exports/roles.json` (repris de `docs/SPEC.md`), sorts et niveaux de `classes.json` ;
catalogue `forever/exports/roles.yaml` (clés de sorts). Le sérialiseur d'EllesmereUI n'est jamais exécuté ni recopié :
le format est contrôlé sur sa description (chaînes `s<octets>:`, nombres `n…;`, `T`, `F`, `N`, tables)."""

import asyncio
import copy
import json
import shutil
from importlib import resources

import pytest
import yaml
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION
from lua_oracle import runtime
from mcp import Client

from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.exports.codec import decode_for_print, deflate, encode_for_print, inflate
from forever.exports.ellesmere import (
    PREFIX,
    ROLE_LABELS,
    base_from_string,
    ellesmere_deserialize,
    ellesmere_export,
    ellesmere_serialize,
    read_base_profile,
    read_ellesmere,
    role_spells,
)
from forever.gamedata import build_game_data
from forever.mcp_server import build_server
from forever.pipeline.lua_table import parse_lua_assignments
from forever.provenance import validate_provenance
from forever.store import load_version

BASE = FIXTURES / "exports" / "ellesmere_base.lua"
ROLES = json.loads((FIXTURES / "exports" / "roles.json").read_text(encoding="utf-8"))["roles"]
CLASSES = json.loads((DATA_DIR / LOCAL_VERSION / "classes.json").read_text(encoding="utf-8"))["classes"]
CATALOGUE = yaml.safe_load(resources.files("forever.exports").joinpath("roles.yaml").read_text(encoding="utf-8"))
DB = parse_lua_assignments(BASE.read_text(encoding="utf-8"))["EllesmereUIDB"]


def learned_ids(cls: str, level: int) -> set[int]:
    return {
        r["spell_id"]
        for s in CLASSES[cls]["spells"].values()
        if s["talent"] is None
        for r in s["ranks"]
        if r.get("level") and r["level"] <= level
    }


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    sv = root / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    shutil.copy(BASE, sv / "EllesmereUI.lua")
    return root


@pytest.fixture
def deps(wow, make_deps):
    return make_deps(wow_dir=wow)


@pytest.fixture
def gd(deps):
    return build_game_data(load_version(deps))


# --- sérialiseur ----------------------------------------------------------------------------------------------------


def test_serializer_known_bytes():
    assert ellesmere_serialize({"a": 1}) == b"{Ks1:an1;}"
    assert ellesmere_serialize([True, False, "x"]) == b"{TFs1:x}"
    assert ellesmere_serialize("é") == "s2:é".encode()
    assert ellesmere_serialize(None) == b"N"
    assert ellesmere_serialize(0.5) == b"n0.5;"


SYNTHETIC = {
    "texte": "a:b}c{d;K",
    "accents": "Éclair de givre",
    "vide": "",
    "nombres": [1, -2, 0.25, 123456789, -0.5],
    "booléens": [True, False],
    "imbriqué": {"x": {"y": {"z": ["fond"]}}},
    "mixte": {1: "a", 2: "b", "k": "v"},
    7: "clé entière hors tableau",
}


def test_serializer_round_trip_and_determinism():
    assert ellesmere_deserialize(ellesmere_serialize(SYNTHETIC)) == SYNTHETIC
    shuffled = dict(reversed(list(SYNTHETIC.items())))
    assert ellesmere_serialize(shuffled) == ellesmere_serialize(SYNTHETIC)


def test_serializer_refuses_unknown_types():
    for bad in ({1, 2}, object(), b"octets", float("nan")):
        with pytest.raises((TypeError, ValueError)):
            ellesmere_serialize(bad)


def test_envelope_is_read_by_libdeflate():
    payload = {"version": 3, "type": "full", "data": {"fonts": {"global": "x"}}, "client": "forever"}
    text = PREFIX + encode_for_print(deflate(ellesmere_serialize(payload)))
    lua = runtime()
    raw = lua.eval(b"function(s) return (LD:DecompressDeflate(LD:DecodeForPrint(s))) end")(text[len(PREFIX) :].encode())
    assert ellesmere_deserialize(raw) == payload
    assert read_ellesmere(text) == payload
    assert inflate(decode_for_print(text[len(PREFIX) :]), 1 << 20) == ellesmere_serialize(payload)


def test_read_refuses_other_versions_and_prefixes():
    for version in (2, 4):
        bad = PREFIX + encode_for_print(deflate(ellesmere_serialize({"version": version, "type": "full"})))
        with pytest.raises(ValueError):
            read_ellesmere(bad)
    with pytest.raises(ValueError):
        read_ellesmere("!NFB1!abc")


# --- profil de base -------------------------------------------------------------------------------------------------


def test_base_profile_is_read_locally_never_written(wow):
    path = next(wow.rglob("EllesmereUI.lua"))
    before = path.read_bytes()
    base = read_base_profile(wow, "Jen - Forever")
    assert base.name == DB["activeProfile"] and base.spec_key == "9001"
    assert base.data == DB["profiles"]["Base"]
    assert base.cdm == DB["spellAssignments"]["profiles"]["Base"]["specProfiles"]
    assert read_base_profile(wow, "Jen - Forever", "Autre").name == "Autre"
    assert path.read_bytes() == before
    with pytest.raises(InvalidArgumentError):
        read_base_profile(wow, "Jen - Forever", "Absent")


# --- profil rendu ---------------------------------------------------------------------------------------------------


def without_ours(data):
    rest = copy.deepcopy(dict(data))
    rest.pop("cdmSpells", None)
    rest["addons"]["EllesmereUIAuraBuffReminders"]["forever"].pop("customIDs")
    return rest


def test_profile_keeps_the_base_and_fills_only_cdm_and_buffs(deps):
    out = ellesmere_export(deps, "Jen", "Forever", "Mage", 20, "dps")
    assert out["profile_name"] == f"Jen - {ROLE_LABELS['dps']}"
    assert out["code"].startswith(PREFIX)
    payload = read_ellesmere(out["code"])
    assert payload["version"] == 3 and payload["type"] == "full" and payload["client"] == "forever"
    data = payload["data"]
    base = copy.deepcopy(DB["profiles"]["Base"])
    base["addons"]["EllesmereUIAuraBuffReminders"]["forever"].pop("customIDs")
    assert without_ours(data) == base
    assert list(data["cdmSpells"]) == ["9001"]
    spec = data["cdmSpells"]["9001"]
    assert "__ghost_cd" not in spec["barSpells"] and "_barFilterModelV6" not in spec
    assert (
        spec["barSpells"]["buffs"]
        == DB["spellAssignments"]["profiles"]["Base"]["specProfiles"]["9001"]["barSpells"]["buffs"]
    )
    ids = learned_ids("Mage", 20)
    for bar in ("cooldowns", "utility"):
        assert spec["barSpells"][bar]["assignedSpells"], bar
        assert set(spec["barSpells"][bar]["assignedSpells"]) <= ids, bar
    custom = data["addons"]["EllesmereUIAuraBuffReminders"]["forever"]["customIDs"]
    assert custom and set(custom) <= ids
    assert out["certainty"] == "suppose" and validate_provenance(out["provenance"]) == []


def test_spells_are_learned_at_the_level_and_follow_the_catalogue(gd):
    for cls, roles in ROLES.items():
        for role in roles:
            for level in (10, 30, 60):
                got = role_spells(gd, cls, role, level)
                keys = CATALOGUE[cls][role]
                ids = learned_ids(cls, level)
                for bar in ("cooldowns", "utility"):
                    allowed = {r["spell_id"] for k in keys[bar] for r in CLASSES[cls]["spells"][k]["ranks"]}
                    assert set(got[bar]) <= ids & allowed, (cls, role, level, bar)
                buffs = {r["spell_id"] for k in keys["buffs"] for r in CLASSES[cls]["spells"][k]["ranks"]}
                assert set(got["buffs"]) <= ids & buffs, (cls, role, level)


def test_cooldown_bars_hold_only_spells_with_a_cooldown(gd):
    by_id = {r["spell_id"]: r for s in CLASSES["Mage"]["spells"].values() for r in s["ranks"]}
    got = role_spells(gd, "Mage", "dps", 60)
    for bar in ("cooldowns", "utility"):
        for sid in got[bar]:
            rank = by_id[sid]
            assert rank["cooldown_s"] and rank["cooldown_s"] > (rank["gcd_s"] or 0), sid


def test_talent_spells_only_when_the_talent_is_taken(gd):
    talent = next(k for k in CATALOGUE["Mage"]["dps"]["utility"] if CLASSES["Mage"]["spells"][k]["talent"])
    talent_key = CLASSES["Mage"]["spells"][talent]["talent"]["key"]
    ids = {r["spell_id"] for r in CLASSES["Mage"]["spells"][talent]["ranks"]}
    assert not ids & set(role_spells(gd, "Mage", "dps", 60)["utility"])
    assert ids & set(role_spells(gd, "Mage", "dps", 60, {talent_key: 1})["utility"])


def test_role_not_held_by_the_class_is_refused(deps):
    for cls, roles in ROLES.items():
        for role in ROLE_LABELS:
            if role not in roles:
                with pytest.raises(InvalidArgumentError):
                    ellesmere_export(deps, "Jen", "Forever", cls, 20, role)
    assert set(CATALOGUE) == set(ROLES)
    assert {c: sorted(r) for c, r in CATALOGUE.items()} == {c: sorted(r) for c, r in ROLES.items()}


def test_catalogue_keys_exist():
    for cls, roles in CATALOGUE.items():
        for groups in roles.values():
            assert set(groups) == {"cooldowns", "utility", "buffs"}
            for keys in groups.values():
                for key in keys:
                    assert key in CLASSES[cls]["spells"], (cls, key)


def test_spec_key_from_the_spells_when_ellesmere_kept_none(deps):
    out = ellesmere_export(deps, "Inconnu", "Forever", "Paladin", 20, "dps")
    assert list(read_ellesmere(out["code"])["data"]["cdmSpells"]) == ["9002"]
    out = ellesmere_export(deps, "Inconnu", "Forever", "Mage", 20, "dps", spec_key="9001")
    assert list(read_ellesmere(out["code"])["data"]["cdmSpells"]) == ["9001"]
    with pytest.raises(InvalidArgumentError):
        ellesmere_export(deps, "Inconnu", "Forever", "Warlock", 20, "dps")


def test_pasted_string_is_a_base_too(deps, make_deps, tmp_path):
    first = ellesmere_export(deps, "Jen", "Forever", "Mage", 20, "dps")
    base = base_from_string(first["code"], "Jen - Forever")
    assert base.source == "chaîne collée" and base.spec_key is None
    alone = make_deps(wow_dir=tmp_path / "vide")
    again = ellesmere_export(alone, "Jen", "Forever", "Mage", 30, "dps", paste=first["code"])
    data = read_ellesmere(again["code"])["data"]
    assert list(data["cdmSpells"]) == ["9001"]
    assert set(data["cdmSpells"]["9001"]["barSpells"]["cooldowns"]["assignedSpells"]) <= learned_ids("Mage", 30)


def test_no_base_profile_says_so(make_deps, tmp_path):
    with pytest.raises(InvalidArgumentError, match="profil de base"):
        ellesmere_export(make_deps(wow_dir=tmp_path / "vide"), "Jen", "Forever", "Mage", 20, "dps")


# --- CLI et MCP -----------------------------------------------------------------------------------------------------


def test_cli_ellesmere(deps, capsys):
    argv = ["export", "ellesmere", "Jen", "--realm", "Forever", "--class", "Mage", "--level", "20", "--role", "dps"]
    assert main([*argv, "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["code"].startswith(PREFIX) and validate_provenance(data["provenance"]) == []
    assert main(argv, deps) == 0
    out = capsys.readouterr().out
    assert data["profile_name"] in out and data["code"] in out
    assert main(["export", "read", data["code"], "--json"], deps) == 0
    back = json.loads(capsys.readouterr().out)
    assert back["kind"] == "ellesmere" and back["version"] == 3 and back["client"] == "forever"
    assert main([*argv[:-1], "tank", "--json"], deps) == 2


def test_mcp_lookup_ellesmere(deps):
    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool(
                "forever_lookup",
                {
                    "kind": "export",
                    "name": "ellesmere",
                    "character": "Jen",
                    "realm": "Forever",
                    "class_name": "Mage",
                    "level": 20,
                    "role": "dps",
                },
            )

    r = asyncio.run(go())
    assert not r.is_error and r.structured_content["code"].startswith(PREFIX)
