"""Builds populaires de Talents Forever (FA1, bloc D) : lecture du bloc `popular` (parts, date, fenêtre), légalité sur
le client, certitude `suppose` (choix de joueurs, décision 127), build populaire le plus proche de la même
spécialisation (classé par nos points absents du sien, puis l'écart total, puis le rang), `forever talents tf
popular`, `forever_lookup(kind="tf_popular")`, bloc `closest_popular` de l'export du Mage.

Addon synthétique écrit dans `tmp_path` (`tests/talents_forever_data.py`, agrégats de
`tests/fixtures/talents_forever/popular.json`) ; aucun accès au dossier réel du jeu."""

import asyncio
import json

import pytest
from conftest import DATA_DIR, LOCAL_VERSION
from mcp import Client
from talents_forever_data import load_fixture, write_addon

from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.mcp_server import build_server
from forever.talents_forever import attach_export, closest_popular, load_addon, popular_builds

CLASSES = DATA_DIR / LOCAL_VERSION / "classes.json"
CASES = load_fixture("mage_builds.json")["cases"]


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


@pytest.fixture
def popular(addon, deps):
    return popular_builds(addon, deps)


def test_nine_classes_five_builds_each(popular):
    assert popular["kind"] == "tf_popular"
    assert len(popular["classes"]) == 9
    assert all(len(c["top"]) == 5 for c in popular["classes"].values())


def test_mage_shares_date_and_count(popular):
    mage = popular["classes"]["Mage"]
    assert [(s["name"], s["pct"]) for s in mage["spec"]] == [("Fire", 44), ("Frost", 34), ("Arcane", 22)]
    assert mage["asOf"] == "2026-10-04" and mage["builds"] == 41203 and mage["window"]
    top = mage["top"][0]
    assert top["rank"] == 1 and top["spec"] == "Fire" and top["tree_index"] == 1
    assert top["link"] == "https://talentsforever.com/" + top["code"]
    assert top["import"] == "/tf import " + top["code"]
    assert top["points_by_tree"] == [0, 29, 22]


def test_certainty_and_provenance(popular):
    assert popular["certainty"] == "suppose"
    assert popular["addon"]["version"] == "0.37.1"
    notes = " ".join(popular["provenance"]["assumptions"])
    assert "0.37.1" in notes and "2026-10-04" in notes and "choix de joueurs" in notes


def test_legality_on_the_client(popular):
    builds = [b for c in popular["classes"].values() for b in c["top"]]
    assert sum(1 for b in builds if b["legality"] == "légal") == 45
    odd = [(name, b["rank"]) for name, c in popular["classes"].items() for b in c["top"] if b["legality"] != "légal"]
    assert odd == []


def test_shadow_and_elemental_leads_matched_by_tree_index(popular):
    shadow = [b for b in popular["classes"]["Priest"]["top"] if b["spec"] == "Shadow"]
    assert shadow and all(b["tree_index"] == 2 for b in shadow)
    elemental = [b for b in popular["classes"]["Shaman"]["top"] if b["spec"] == "Elemental"]
    assert elemental and all(b["tree_index"] == 0 for b in elemental)


def test_one_class_by_french_or_english_name(addon, deps):
    assert list(popular_builds(addon, deps, "Voleur")["classes"]) == ["Rogue"]
    assert list(popular_builds(addon, deps, "Rogue")["classes"]) == ["Rogue"]


@pytest.mark.parametrize(
    ("name", "rank", "spec", "missing", "total"),
    [
        ("leveling-20", 3, "Frost", 0, 40),
        ("leveling-30", 3, "Frost", 0, 30),
        ("dungeon-20", 4, "Arcane", 0, 40),
    ],
)
def test_closest_popular_of_our_mage_builds(addon, popular, name, rank, spec, missing, total):
    closest = closest_popular(addon, popular, "Mage", CASES[name]["talents"])
    assert closest["rank"] == rank and closest["spec"] == spec and closest["same_spec"] is True
    assert closest["missing_points"] == missing and closest["total_gap"] == total
    assert closest["points_to_add"] == total - missing
    diffs = closest["differences"]
    assert sum(abs(d["theirs"] - d["ours"]) for d in diffs) == total
    assert diffs == sorted(diffs, key=lambda d: (-abs(d["theirs"] - d["ours"]), d["key"]))
    assert closest["certainty"] == "suppose" and closest["asOf"] == "2026-10-04"


def test_closest_is_deterministic(addon, popular):
    talents = CASES["leveling-30"]["talents"]
    assert closest_popular(addon, popular, "Mage", talents) == closest_popular(addon, popular, "Mage", talents)


def test_export_of_the_mage_carries_the_closest_popular(deps):
    case = CASES["leveling-30"]
    report = {"level": case["level"], "talents": case["talents"], "order": [{"talent": k} for k in case["order"]]}
    block = attach_export(deps, report)["export"]["talents_forever"]
    assert block["status"] == "ok"
    assert block["closest_popular"]["rank"] == 3 and block["closest_popular"]["missing_points"] == 0


def test_without_popular_block(tmp_path, make_deps):
    root = tmp_path / "wow"
    write_addon(root, CLASSES, with_popular=False)
    deps = make_deps(wow_dir=root)
    loaded = load_addon(deps)
    with pytest.raises(InvalidArgumentError, match="populaires"):
        popular_builds(loaded, deps)
    case = CASES["leveling-20"]
    report = {"level": case["level"], "talents": case["talents"], "order": [{"talent": k} for k in case["order"]]}
    block = attach_export(deps, report)["export"]["talents_forever"]
    assert block["status"] == "ok" and block["closest_popular"] is None


def test_cli_popular(deps, capsys):
    assert main(["talents", "tf", "popular", "--class", "Mage", "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert list(data["classes"]) == ["Mage"] and data["provenance"]["certainty"] == "suppose"
    assert main(["talents", "tf", "popular", "--class", "Mage"], deps) == 0
    out = capsys.readouterr().out
    assert "talentsforever.com/mage/60/" in out and "2026-10-04" in out and "suppose" in out


def test_mcp_lookup_tf_popular(deps):
    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_lookup", {"kind": "tf_popular", "name": "Rogue"})

    r = asyncio.run(go())
    assert not r.is_error
    data = r.structured_content
    rogue = data["classes"]["Rogue"]
    assert len(rogue["top"]) == 5 and all(
        b["link"].startswith("https://talentsforever.com/rogue/") for b in rogue["top"]
    )
    assert data["certainty"] == "suppose"
