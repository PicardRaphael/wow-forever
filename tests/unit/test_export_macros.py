"""Macros par classe vers Naowh Forever (EX1, bloc D, décisions 195 et 267) : chaîne `!NFM1!`.

Valeurs : sorts, noms anglais et niveaux des rangs lus dans `classes.json` des données installées ; catalogue
`forever/exports/macros.yaml` (clés de sorts) ; bornes du format relevées dans Naowh Forever 1.1.12
(`NaowhForever_Macros/Constants.lua` : nom de 1 à 16 octets, corps d'au plus 255) ; aucune commande hors de
`/cast`, `/use`, `/stopcasting`, `/startattack` et `#showtooltip`."""

import asyncio
import json
from importlib import resources

import pytest
import yaml
from conftest import DATA_DIR, LOCAL_VERSION
from lua_oracle import lua_unpack, runtime
from mcp import Client

from forever.cli import main
from forever.exports.codec import ExportFormatError, pack
from forever.exports.macros import ALLOWED_COMMANDS, TEMPLATES, class_macros, macro_violations, macros_export
from forever.exports.naowh import MACRO_PREFIX, naowh_macros, read_naowh_macros
from forever.gamedata import build_game_data
from forever.mcp_server import build_server
from forever.provenance import validate_provenance
from forever.store import load_version

CLASSES = json.loads((DATA_DIR / LOCAL_VERSION / "classes.json").read_text(encoding="utf-8"))["classes"]
CATALOGUE = yaml.safe_load(resources.files("forever.exports").joinpath("macros.yaml").read_text(encoding="utf-8"))


def first_level(cls: str, key: str) -> int | None:
    levels = [r["level"] for r in CLASSES[cls]["spells"][key]["ranks"] if r.get("level") is not None]
    return min(levels) if levels else None


def levels_of(cls: str) -> list[int]:
    """Niveaux d'essai lus dans les données : premier niveau de chaque sort du catalogue, un de moins, et le plus haut
    niveau de rang de la classe."""
    out = set()
    for entry in CATALOGUE[cls]:
        lv = first_level(cls, entry["spell"])
        if lv:
            out |= {lv, max(1, lv - 1)}
    top = max(r["level"] for s in CLASSES[cls]["spells"].values() for r in s["ranks"] if r.get("level") is not None)
    return sorted(out | {1, top})


@pytest.fixture
def deps(make_deps):
    return make_deps()


@pytest.fixture
def data(deps):
    return build_game_data(load_version(deps))


# --- catalogue ------------------------------------------------------------------------------------------------------


def test_catalogue_covers_every_class_with_known_spells():
    assert set(CATALOGUE) == set(CLASSES)
    for cls, entries in CATALOGUE.items():
        assert entries, cls
        for entry in entries:
            assert entry["template"] in TEMPLATES, (cls, entry)
            assert entry["spell"] in CLASSES[cls]["spells"], (cls, entry)


# --- macros générées ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("cls", sorted(CLASSES))
def test_generated_macros_respect_the_rules_at_every_level(data, cls):
    for level in levels_of(cls):
        macros = class_macros(data, cls, level)
        for m in macros:
            assert macro_violations(m.body) == [], (cls, level, m)
            assert 1 <= len(m.name.encode("utf-8")) <= 16, m.name
            assert len(m.body.encode("utf-8")) <= 255, m.body
            spell = CLASSES[cls]["spells"][m.spell]
            assert spell["talent"] is None, m
            learned = first_level(cls, m.spell)
            assert learned is not None and 1 <= learned <= level, (cls, level, m)
            assert spell["name"] in m.body and "Rank" not in m.body
            assert m.body.splitlines()[0] == "#showtooltip"
        assert len({m.name for m in macros}) == len(macros)
        assert not any(cmd in m.body for m in macros for cmd in ("/run", "/script", "/dump"))


@pytest.mark.parametrize("cls", sorted(CLASSES))
def test_a_macro_appears_at_the_level_its_spell_is_learned(data, cls):
    for entry in CATALOGUE[cls]:
        spell = CLASSES[cls]["spells"][entry["spell"]]
        level = first_level(cls, entry["spell"])
        if spell["talent"] is not None or not level:
            continue
        assert entry["spell"] in [m.spell for m in class_macros(data, cls, level)], (cls, entry)
        if level > 1:
            assert entry["spell"] not in [m.spell for m in class_macros(data, cls, level - 1)], (cls, entry)


def test_macro_bodies_follow_the_templates(data):
    by_spell = {m.spell: m for m in class_macros(data, "Mage", 60)}
    name = CLASSES["Mage"]["spells"]["polymorph"]["name"]
    assert by_spell["polymorph"].body == f"#showtooltip\n/cast [@focus,harm,nodead][] {name}"
    assert by_spell["polymorph"].template == "focus"
    assert by_spell["counterspell"].body.splitlines()[1] == "/stopcasting"


def test_macro_violations():
    assert macro_violations("#showtooltip\n/cast [@mouseover,help,nodead][] Renew") == []
    assert macro_violations("/startattack\n/cast Sinister Strike") == []
    assert macro_violations("/use Hearthstone") == []
    for bad in ("/run print(1)", "/script x()", "/dump GetTime()", "/focus", "/nf", "#show"):
        assert macro_violations(f"#showtooltip\n{bad}") == [bad], bad
    assert set(ALLOWED_COMMANDS) == {"/cast", "/use", "/stopcasting", "/startattack"}


# --- format !NFM1! --------------------------------------------------------------------------------------------------


def test_macro_string_round_trip_python_and_lua(data):
    macros = [(m.name, m.body) for m in class_macros(data, "Priest", 60)]
    text = naowh_macros(macros)
    assert text.startswith(MACRO_PREFIX)
    assert read_naowh_macros(text) == macros
    table = lua_unpack(runtime(), text[len(MACRO_PREFIX) :].encode())
    assert table == {"v": 1, "macros": [{"name": n, "body": b} for n, b in macros]}


def test_one_invalid_macro_refuses_the_whole_string():
    with pytest.raises(ExportFormatError):
        naowh_macros([("a" * 17, "/cast X")])
    with pytest.raises(ExportFormatError):
        naowh_macros([("ok", "x" * 256)])
    with pytest.raises(ExportFormatError):
        naowh_macros([("ok", "/cast X"), ("", "/cast Y")])
    with pytest.raises(ExportFormatError):
        naowh_macros([])
    with pytest.raises(ExportFormatError):
        naowh_macros([("ok", "/run x()")])
    assert read_naowh_macros(naowh_macros([("é" * 8, "/cast X")])) == [("é" * 8, "/cast X")]


def test_read_refuses_other_shapes():
    with pytest.raises(ExportFormatError):
        read_naowh_macros(pack(MACRO_PREFIX, {"v": 2, "macros": [{"name": "a", "body": "b"}]}))
    with pytest.raises(ExportFormatError):
        read_naowh_macros(pack(MACRO_PREFIX, {"v": 1, "macros": [{"name": "a" * 17, "body": "b"}]}))
    with pytest.raises(ExportFormatError):
        read_naowh_macros(pack(MACRO_PREFIX, {"v": 1, "macros": []}))


# --- export, CLI et MCP ---------------------------------------------------------------------------------------------


def test_macros_export_block(deps, data):
    out = macros_export(deps, "Mage", 20)
    assert out["kind"] == "naowh_macros" and out["code"].startswith(MACRO_PREFIX)
    assert [(m["name"], m["body"]) for m in out["macros"]] == read_naowh_macros(out["code"])
    assert out["certainty"] == "suppose"
    assert validate_provenance(out["provenance"]) == []
    assert all(m["body"] in out["text"] for m in out["macros"])
    assert out["macros"] == [
        {"name": m.name, "body": m.body, "spell": m.spell, "template": m.template}
        for m in class_macros(data, "Mage", 20)
    ]


def test_macros_export_with_nothing_learned(deps):
    out = macros_export(deps, "Mage", 1)
    learned = [e for e in CATALOGUE["Mage"] if (first_level("Mage", e["spell"]) or 99) <= 1]
    assert (out["code"] is None) == (not learned)


def test_cli_naowh_macros(deps, capsys):
    assert main(["export", "naowh-macros", "--class", "Mage", "--level", "20", "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["code"].startswith(MACRO_PREFIX) and validate_provenance(data["provenance"]) == []
    assert main(["export", "naowh-macros", "--class", "Mage", "--level", "20"], deps) == 0
    out = capsys.readouterr().out
    assert data["code"] in out and "#showtooltip" in out
    assert out.rstrip("\n").splitlines()[-1].startswith("Provenance")
    assert main(["export", "read", data["code"], "--json"], deps) == 0
    back = json.loads(capsys.readouterr().out)
    assert back["kind"] == "naowh_macros" and back["macros"] == [
        {"name": m["name"], "body": m["body"]} for m in data["macros"]
    ]


def test_mcp_lookup_naowh_macros(deps):
    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool(
                "forever_lookup", {"kind": "export", "name": "naowh_macros", "class_name": "Priest", "level": 30}
            )

    r = asyncio.run(go())
    assert not r.is_error
    assert r.structured_content["code"].startswith(MACRO_PREFIX)
    assert validate_provenance(r.structured_content["provenance"]) == []
