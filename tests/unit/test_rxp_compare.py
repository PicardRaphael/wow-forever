"""Nos routes face aux parcours gratuits en clair de RestedXP (RX1c, décision 268) : lecture locale des seuls guides
en clair de `Guides/Forever` (bloc chiffré compté et ignoré, rien d'autre ouvert), filtres de classe, de race et de
camp, chaîne `#next` et couverture, rejeu par notre simulation (conditions `.xp`, `.isOnQuest`, `#xprate`, étapes de
donjon écartées, étapes de farm), commande `forever route rxp-compare` sans aucun texte de guide dans la sortie.

Valeurs : guides fabriqués `tests/fixtures/rxp_guides/` (syntaxe seulement, quêtes de
`tests/fixtures/route/route.json`)."""

import json
import shutil

import pytest
from conftest import FIXTURES
from forever.rxp_guides import Who, applies, coverage, guide_chain, read_rxp_guides
from test_engine_route import CAP, make_world, start_state

from forever.cli import main
from forever.compare import replay_rxp
from forever.errors import InvalidArgumentError
from forever.provenance import validate_provenance

ADDONS = FIXTURES / "rxp_guides"
ORC_MAGE = Who("Mage", "Orc", "Horde")
ORC_HUNTER = Who("Hunter", "Orc", "Horde")


@pytest.fixture(scope="module")
def library():
    return read_rxp_guides(ADDONS)


def test_reads_only_clear_forever_guides(library):
    names = [g.name for g in library.guides]
    assert names == ["1-4 Fixture Meadow", "4-7 Fixture Coast", "1-3 Fixture Vale", "3-5 Fixture Hills"]
    assert library.refused == 1  # bloc qui n'est pas un guide en clair : compté, jamais décodé
    assert all("Decoy" not in g.file and "dungeon" not in g.file for g in library.guides)
    with_dungeons = read_rxp_guides(ADDONS, dungeon_guides=True)
    assert any(g.dungeon for g in with_dungeons.guides)


def test_missing_addon_is_refused(tmp_path):
    with pytest.raises(InvalidArgumentError):
        read_rxp_guides(tmp_path)


def test_guide_headers(library):
    vale = next(g for g in library.guides if g.name == "1-3 Fixture Vale")
    assert (vale.group, vale.defaultfor, vale.filter) == ("Fixture Guide (H)", "Orc/Troll", "Horde")
    assert vale.next == (("3-5 Fixture Hills", "!Hunter"), ("3-5 Fixture Hunter Hills", "Hunter"))
    assert vale.levels == (1, 3)


@pytest.mark.parametrize(
    ("expr", "who", "expected"),
    [
        ("Horde", ORC_MAGE, True),
        ("Alliance", ORC_MAGE, False),
        ("Orc/Troll", ORC_MAGE, True),
        ("Orc Hunter/Troll Hunter", ORC_MAGE, False),
        ("Orc Hunter/Troll Hunter", ORC_HUNTER, True),
        ("!Tauren", ORC_MAGE, True),
        ("!Hunter !Shaman", ORC_HUNTER, False),
        ("Horde Mage", ORC_MAGE, True),
        ("skip", ORC_MAGE, False),
        ("sod", ORC_MAGE, False),
        (None, ORC_MAGE, True),
    ],
)
def test_filters(expr, who, expected):
    assert applies(expr, who) is expected


def test_chain_follows_next_with_filters(library):
    chain = guide_chain(library, ORC_MAGE)
    assert [g.name for g in chain.guides] == ["1-3 Fixture Vale", "3-5 Fixture Hills"]
    assert chain.missing == ("5-12 Fixture Paid Lands",)
    hunter = guide_chain(library, ORC_HUNTER)
    assert [g.name for g in hunter.guides] == ["1-3 Fixture Vale"] and hunter.missing == ("3-5 Fixture Hunter Hills",)
    alliance = guide_chain(library, Who("Mage", "Human", "Alliance"))
    assert [g.name for g in alliance.guides] == ["1-4 Fixture Meadow", "4-7 Fixture Coast"]  # « ; » : le premier connu
    assert guide_chain(library, ORC_MAGE, start="Fixture Hills").guides[0].name == "3-5 Fixture Hills"


def test_coverage_says_how_far_the_clear_guides_go(library):
    rows = {(r["faction"], r["defaultfor"]): r for r in coverage(library)}
    horde = rows[("Horde", "Orc/Troll")]
    assert horde["max_level"] == 5 and horde["missing"] == ["5-12 Fixture Paid Lands"]
    assert rows[("Alliance", "Human")]["max_level"] == 7


def test_replay_follows_the_guide_logic(library, game_data):
    world, _ = make_world(game_data)
    chain = guide_chain(library, ORC_MAGE)
    replay = replay_rxp(game_data, world, chain.guides, ORC_MAGE, start_state(), end_level=5, cap=CAP)
    kinds = [(s.kind, s.ref) for s in replay.stops]
    turned = [ref for kind, ref in kinds if kind == "turnin"]
    assert turned[:2] == [101, 102]
    assert kinds.index(("objective", 101)) < kinds.index(("turnin", 101))
    assert sum(1 for k in kinds if k == ("objective", 101)) == 1  # deux lignes .complete : un seul arrêt
    assert ("accept", 103) in kinds and ("accept", 104) not in kinds  # filtre de race sur la ligne
    assert any(kind == "grind" and ref == 3 for kind, ref in kinds)  # .xp 3 : farm jusqu'au niveau 3
    attempted = {ref for _, ref in kinds} | {s["quest"] for s in replay.skipped}
    assert not attempted & {105, 106, 111, 999, 110}  # Tauren, skip, donjon, .xp <9,1, #xprate >1.99
    assert replay.result.feasible and replay.result.reached


def test_replay_starts_in_the_guide_of_the_start_level(library, game_data):
    world, _ = make_world(game_data)
    chain = guide_chain(library, ORC_MAGE)
    replay = replay_rxp(game_data, world, chain.guides, ORC_MAGE, start_state(level=3), end_level=5, cap=CAP)
    assert ("accept", 101) not in [(s.kind, s.ref) for s in replay.stops]  # guide 1-3 passé


def _wow(tmp_path):
    root = tmp_path / "wow"
    shutil.copytree(FIXTURES / "addons" / "dungeons", root)
    shutil.copytree(ADDONS / "RXPGuides", root / "Interface" / "AddOns" / "RXPGuides")
    return root


def test_rxp_compare_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(_wow(tmp_path)))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    argv = [
        "route",
        "rxp-compare",
        "--class",
        "Mage",
        "--race",
        "Orc",
        "--faction",
        "horde",
        "--from",
        "1",
        "--to",
        "5",
    ]
    assert main([*argv, "--json"]) == 0
    raw = capsys.readouterr().out
    doc = json.loads(raw)
    assert validate_provenance(doc["provenance"]) == []
    assert doc["request"] == {"class": "mage", "race": "Orc", "faction": "horde", "from": 1, "to": 5}
    assert doc["guides"] == {"count": 2, "missing": ["5-12 Fixture Paid Lands"], "max_level": 5, "refused": 1}
    for side in ("ours", "theirs"):
        assert {"hours", "xp_h", "quests", "travel_hours", "objective_hours", "grind_hours", "zones"} <= set(doc[side])
    assert {"skipped", "skip_reasons"} <= set(doc["theirs"])
    assert set(doc) >= {"common", "only_ours", "only_theirs"}
    assert "Secret" not in raw and "objective one" not in raw  # aucun texte de guide recopié
    assert main(argv) == 0
    assert "RestedXP" in capsys.readouterr().out


def test_rxp_coverage_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(_wow(tmp_path)))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    assert main(["route", "rxp-coverage", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert validate_provenance(doc["provenance"]) == []
    assert {r["max_level"] for r in doc["chains"]} == {5, 7} and doc["refused"] == 1
