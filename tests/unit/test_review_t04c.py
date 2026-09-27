"""Corrections de relecture de T04c (relecteur et auditeur des mécaniques).

Valeurs : talent `arcaneBlast` (talents.json : 4 cumuls, 8 s) recoupé avec l'aura 400573 des fixtures wago
(SpellAuraOptions.CumulativeAura, SpellMisc.DurationIndex -> SpellDuration) ; mondes de test de
test_measures_refresh.py."""

import dataclasses
import json
import shutil
from types import SimpleNamespace

import pytest
from conftest import FIXTURES, LOCAL_VERSION, REAL_LOG, read_json
from test_measures_refresh import JOURNEY, QUESTIE, SECOND_LOG, refresh, world  # noqa: F401 (fixture)

from forever.cli import main
from forever.engine.buffs import ArcaneBlastAura, arcane_blast_after_spell
from forever.engine.leveling import gray_level
from forever.engine.mana import clearcast_cost_factor
from forever.engine.talents import talent_value
from forever.pipeline.questie import QuestieQuest, zones_for_level
from forever.pipeline.refresh import compare

ARCANE_BLAST_AURA = 400573  # aura d'Arcane Blast du client (Spell.csv)
B20 = {"arcaneFocus": 5, "arcaneSubtlety": 2, "magicAbsorption": 2, "arcaneResilience": 1, "arcaneBlast": 1}
MS = 1000  # conversion d'unité


# --- Audit des mécaniques -------------------------------------------------------------------------


def test_arcane_blast_talent_matches_the_client_aura(game_data, client_tables):
    aura = next(r for r in client_tables["SpellAuraOptions"] if r["SpellID"] == ARCANE_BLAST_AURA)
    misc = next(r for r in client_tables["SpellMisc"] if r["SpellID"] == ARCANE_BLAST_AURA)
    duration = next(r["Duration"] for r in client_tables["SpellDuration"] if r["ID"] == misc["DurationIndex"])
    assert talent_value(game_data, B20, "arcaneBlast", 4) == aura["CumulativeAura"]
    assert talent_value(game_data, B20, "arcaneBlast", 5) == duration / MS


def test_any_other_damage_spell_consumes_the_arcane_blast_aura(game_data):
    aura = ArcaneBlastAura(3, 10.0)
    assert arcane_blast_after_spell(game_data, B20, aura, 5.0, "frostbolt") is None
    assert arcane_blast_after_spell(game_data, B20, aura, 5.0, "arcane_blast") == ArcaneBlastAura(4, 13.0)


def test_clearcast_factor_lives_in_the_engine(game_data):
    pts = {"arcaneConcentration": 5}
    chance = talent_value(game_data, pts, "arcaneConcentration") / 100
    assert clearcast_cost_factor(game_data, pts, 0.9) == pytest.approx(1 - 0.9 * chance, rel=1e-12)
    assert clearcast_cost_factor(game_data, {}, 0.9) == 1.0


def test_every_gray_row_of_the_data(game_data):
    for up_to, minus, per in game_data.leveling.quest_band.gray_rows:
        expected = 0 if minus is None else up_to - minus - (up_to // per if per else 0)
        assert gray_level(game_data, up_to) == expected, up_to


# --- Relecture : measures refresh -----------------------------------------------------------------


def test_empty_logs_dir_is_refused(capsys, make_deps, world, tmp_path):  # noqa: F811
    empty = tmp_path / "vide"
    empty.mkdir()
    deps = make_deps(data_dir=world["data"])
    code = main(["measures", "refresh", "--logs", str(empty), "--yes", "--json"], deps)
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out["error"]["code"] == "invalid_argument"


def test_vanished_logs_stay_listed(capsys, make_deps, world):  # noqa: F811
    """Un journal sans aucun relevé de PV (synthetic/multi_power.txt) reste listé après sa disparition du dossier."""
    no_hp = world["logs"] / "WoWCombatLog-092726_120000.txt"
    shutil.copy(FIXTURES / "combatlog" / "synthetic" / "multi_power.txt", no_hp)
    assert refresh(capsys, make_deps, world, "--yes")[0] == 0
    assert no_hp.name in read_json(world["data"] / LOCAL_VERSION / "monsters.json")["logs"]
    no_hp.unlink()
    assert refresh(capsys, make_deps, world, "--yes")[0] == 0
    assert no_hp.name in read_json(world["data"] / LOCAL_VERSION / "monsters.json")["logs"]


def test_removed_npcs_are_shown_before_writing():
    entry = {"name": "Leurre", "zone_id": None, "rank": None, "levels": {"5": {"max_hp": 1, "source": "autre"}}}
    installed = {"logs": [], "npcs": {"99999": entry}, "hp_by_level": {}}
    new = {
        "sources": {"logs": {}, "saved_variables": {}},
        "monsters": {"logs": [], "npcs": {}, "hp_by_level": {}},
        "kept_npcs": [],
        "gone_logs": [],
    }
    assert compare(installed, [], None, new)["npcs"]["removed"] == ["99999"]


def test_written_refresh_updates_the_monsters_source(capsys, make_deps, world):  # noqa: F811
    code, _, deps = refresh(capsys, make_deps, world, "--yes")
    assert code == 0
    entry = read_json(world["data"] / LOCAL_VERSION / "sources.json")["files"]["monsters.json"]
    assert REAL_LOG.name in entry["source"] and SECOND_LOG.name in entry["source"]
    assert "measures refresh" in entry["source"] and "3986" in entry["source"]
    assert main(["manifest", "--check"], deps) == 0


def test_corrupt_snapshot_is_reported(capsys, make_deps, world):  # noqa: F811
    deps = make_deps(data_dir=world["data"])
    (deps.cache_dir / "measures").mkdir(parents=True)
    (deps.cache_dir / "measures" / "last.json").write_text("{pas du json", encoding="utf-8")
    argv = ["measures", "refresh", "--logs", str(world["logs"]), "--questie", str(QUESTIE), "--dry-run", "--json"]
    assert main(argv, dataclasses.replace(deps, confirm=None)) == 0
    out = json.loads(capsys.readouterr().out)
    assert any("instantané illisible" in a for a in out["provenance"]["assumptions"])


# --- Relecture : provenance et détails ------------------------------------------------------------


def test_seed_rules_do_not_claim_the_client_armor(capsys, make_deps):
    argv = ["sim", "leveling", "--level", "12", "--n", "5", "--rules", "seed", "--json"]
    assert main(argv, make_deps()) == 0
    notes = json.loads(capsys.readouterr().out)["provenance"]["assumptions"]
    assert any("Frost Armor" in a and "seed" in a for a in notes)
    assert not any("lue dans le client" in a for a in notes)


def test_chart_provenance_cites_rules_and_armor(capsys, make_deps, tmp_path):
    argv = ["chart", "leveling", "--out", str(tmp_path / "c.png"), "--from", "12", "--to", "12", "--n", "3", "--json"]
    assert main(argv, make_deps()) == 0
    notes = json.loads(capsys.readouterr().out)["provenance"]["assumptions"]
    assert any("rules forever" in a and "armor auto" in a for a in notes)


def test_quest_following_the_player_level_is_not_gray(game_data):
    """Questie : `questLevel` -1 = quête au niveau du joueur (jaune), exclue des plages de niveau de la zone."""
    quests = {1: QuestieQuest(1, "q", 1, -1, 0, 0, 17), 2: QuestieQuest(2, "r", 1, 12, 0, 0, 17)}
    db = SimpleNamespace(
        quests=lambda: quests,
        dungeons=dict,
        zone_names=lambda: {17: "The Barrens"},
        npcs=dict,
        battlegrounds=lambda: frozenset(),
        certainty="suppose",
        source="fixture",
    )
    zone = zones_for_level(db, game_data, 30, faction="horde")["zones"][0]  # type: ignore[arg-type]
    assert zone["by_color"]["yellow"] == 1 and zone["quest_levels"] == [12, 12]


def test_mcp_lookup_spell_needs_a_name(make_deps):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(make_deps())) as client:
            return await client.call_tool("forever_lookup", {"kind": "spell"})

    r = asyncio.run(go())
    assert r.is_error and r.structured_content["error"]["code"] == "invalid_argument"


test_mcp_lookup_spell_needs_a_name = pytest.mark.allow_hosts(["127.0.0.1"])(test_mcp_lookup_spell_needs_a_name)
_ = JOURNEY
