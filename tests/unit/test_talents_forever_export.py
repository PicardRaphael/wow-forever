"""Export de nos builds vers Talents Forever (FA1, bloc C) : code v6 et lien des trois builds du Mage de la fixture
(`tests/fixtures/talents_forever/mage_builds.json`, points et ordre figés de 1.60.1.70245), relus sur les mêmes points
et le même ordre ; blocages (talent sans correspondance, addon absent, ordre incohérent, autre génération) ;
provenance ; `forever talents tf decode` ; bloc `export` de `forever build` (CLI) et de l'outil MCP `forever_build`.

Addon synthétique écrit dans `tmp_path` (`tests/talents_forever_data.py`) ; aucun accès au dossier réel du jeu."""

import asyncio
import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION
from mcp import Client
from talents_forever_data import load_fixture, write_addon

from forever.build import build_report
from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.mcp_server import build_server
from forever.talents_forever import attach_export, decode_code, export_build, load_addon

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"
CASES = load_fixture("mage_builds.json")["cases"]
NO_ORDER = "ordre non calculé pour ce contexte"


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    write_addon(root, CLASSES)
    return root


@pytest.fixture
def deps(wow, make_deps):
    return make_deps(wow_dir=wow)


@pytest.fixture
def addon(deps):
    loaded = load_addon(deps)
    assert loaded is not None
    return loaded


def export_case(addon, name, **kw):
    case = CASES[name]
    order = case["order"] or None
    return export_build(addon, "Mage", case["level"], case["talents"], order, **kw)


@pytest.mark.parametrize("name", ["leveling-20", "leveling-30", "dungeon-20"])
def test_mage_builds_give_the_expected_codes_and_read_back(addon, deps, name):
    case = CASES[name]
    block = export_case(addon, name)
    assert block["status"] == "ok"
    assert block["code"] == case["expected_code"]
    assert block["link"] == "https://talentsforever.com/" + case["expected_code"]
    assert block["import"] == "/tf import " + case["expected_code"]
    assert block["level"] == case["level"]
    back = decode_code(addon, deps, block["code"])
    assert back["class"] == "Mage" and back["level"] == case["level"]
    assert back["talents"] == case["talents"]
    assert back["order"] == (case["order"] or None)
    assert back["legal"] is True


def test_expected_codes_of_the_plan():
    assert CASES["leveling-20"]["expected_code"] == "mage/20/--0530002001-klps-6"
    assert CASES["leveling-30"]["expected_code"] == "mage/30/--05300033210003001-klp2sr1prq1w2q1wqz-6"
    assert CASES["dungeon-20"]["expected_code"] == "mage/20/0500050001---6"


def test_order_flags(addon):
    leveling = export_case(addon, "leveling-30")
    assert leveling["order_included"] is True and leveling["order_note"] is None
    dungeon = export_case(addon, "dungeon-20")
    assert dungeon["order_included"] is False
    assert NO_ORDER in dungeon["order_note"] and "arbre par arbre" in dungeon["order_note"]


def test_provenance_and_certainty(addon):
    block = export_case(addon, "leveling-20")
    assert block["certainty"] == "probable"
    prov = block["provenance"]
    assert prov["format"] == "v6"
    assert prov["version"] == "0.37.1"
    assert prov["build"] == "1.60.1.70170" and prov["generated"] == "2026-10-04" and prov["codeVersion"] == "6"
    assert len(prov["fingerprint"]) == 12
    assert prov["talented_note"] is None


def test_talented_bonus_keeps_the_build_level_and_adds_a_note(addon):
    case = CASES["leveling-20"]
    block = export_build(addon, "Mage", case["level"], case["talents"], case["order"], talented_bonus=1)
    assert block["level"] == case["level"] and block["code"].startswith(f"mage/{case['level']}/")
    assert "Talented" in block["provenance"]["talented_note"]


def test_unmatched_mage_talent_blocks_and_names_it(tmp_path, make_deps):
    def move_ice_lance(doc):
        for tree in doc["classes"]["MAGE"]["trees"]:
            for t in tree["talents"]:
                if t["name"] == "Ice Lance":
                    t["spell"] = t["spell"] + 1  # position de l'addon qui ne correspond plus à notre talent

    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=move_ice_lance)
    loaded = load_addon(make_deps(wow_dir=root))
    block = export_case(loaded, "leveling-20")
    assert block["status"] == "bloque"
    assert "iceLance" in block["reason"] and block["code"] is None and block["link"] is None


def test_absent_addon_is_reported_never_guessed():
    case = CASES["leveling-20"]
    block = export_build(None, "Mage", case["level"], case["talents"], case["order"])
    assert block["status"] == "absent" and block["code"] is None
    assert "Talents Forever" in block["reason"]


def test_incoherent_order_is_reported(addon):
    block = export_build(addon, "Mage", 20, {"iceLance": 1}, ["iceLance", "iceLance"])
    assert block["status"] == "ordre_incoherent" and block["code"] is None


def test_other_generation_is_not_supported(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, mutate=lambda doc: doc.update(codeVersion="7"))
    loaded = load_addon(make_deps(wow_dir=root))
    block = export_case(loaded, "leveling-20")
    assert block["status"] == "format_non_pris_en_charge" and block["code"] is None


def test_hunter_export_is_blocked_with_the_missing_talent(addon):
    block = export_build(addon, "Hunter", 20, {}, None)
    assert block["status"] == "bloque" and "improvedSerpentSting" in block["reason"]


def test_decode_refusals(addon, deps):
    with pytest.raises(InvalidArgumentError, match="classe inconnue"):
        decode_code(addon, deps, "deathknight/60/--05-6")
    with pytest.raises(InvalidArgumentError, match="génération"):
        decode_code(addon, deps, "mage/60/--0555323331321331251-5")


def test_cli_decode(deps, capsys):
    code = CASES["leveling-30"]["expected_code"]
    assert main(["talents", "tf", "decode", "https://talentsforever.com/" + code + "?a", "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["talents"] == CASES["leveling-30"]["talents"]
    assert data["order"] == CASES["leveling-30"]["order"]
    assert data["legal"] is True and data["provenance"]["game_version"] == LOCAL_VERSION
    assert main(["talents", "tf", "decode", code], deps) == 0
    out = capsys.readouterr().out
    assert "légal" in out and "improvedFrostbolt" in out


# --- forever build et forever_build (slow : optimiseur réel) ---------------------------------------------------


def read_back(addon, deps, block):
    back = decode_code(addon, deps, block["code"])
    return back["talents"], back["order"]


@pytest.mark.slow
def test_build_report_export_reads_back_the_report(addon, deps):
    rep = attach_export(deps, build_report(deps, "leveling", 20, preset="rapide", sensitivity=False))
    block = rep["export"]["talents_forever"]
    assert block["status"] == "ok" and block["code"].startswith("mage/20/")
    talents, order = read_back(addon, deps, block)
    assert talents == {k: v for k, v in rep["talents"].items() if v}
    assert order == [s["talent"] for s in rep["order"] if s["talent"]]


@pytest.mark.slow
def test_mcp_build_carries_the_export(addon, deps):
    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool(
                "forever_build", {"context": "leveling", "level": 20, "preset": "rapide", "sensitivity": False}
            )

    r = asyncio.run(go())
    assert not r.is_error
    data = r.structured_content
    block = data["export"]["talents_forever"]
    assert block["status"] == "ok" and block["certainty"] == "probable"
    talents, order = read_back(addon, deps, block)
    assert talents == {k: v for k, v in data["talents"].items() if v}
    assert order == [s["talent"] for s in data["order"] if s["talent"]]


@pytest.mark.slow
def test_cli_build_text_has_a_talents_forever_line(deps, capsys):
    argv = ["build", "leveling", "--level", "20", "--preset", "rapide", "--sensitivity", "off"]
    assert main(argv, deps) == 0
    out = capsys.readouterr().out
    line = next(ln for ln in out.splitlines() if ln.startswith("Talents Forever"))
    assert "https://talentsforever.com/mage/20/" in line and "/tf import mage/20/" in line
