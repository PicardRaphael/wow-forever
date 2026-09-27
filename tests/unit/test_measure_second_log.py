"""Seconde fixture de journal (décision 1 du plan T04b) : journal réel du 2026-09-27 15:03:46 (les Tarides), filtré aux
événements utiles aux mesures, anonymisé et compressé (voir tests/fixtures/combatlog/README.md).

Valeurs relevées sur le journal complet puis contrôlées sur la fixture (mêmes mesures) : 47 intervalles entre sorts
sous recharge globale (98 sans filtre), 29 relevés de PV, 281 sorts directs du Mage sur des créatures, aucun raté de
table ; niveau du lanceur : carnet de Questie de la fixture (14, puis 15 à 15:17:26 heure locale)."""

import gzip
import json
import statistics
from datetime import timedelta

import pytest
from conftest import COMBATLOG, FIXTURES, MINE_GUID, REAL_LOG, REGISTRY_PATH

from forever.cli import main
from forever.pipeline.combatlog import read_log, scan_logs
from forever.pipeline.levels import CasterLevels, from_questie_journey
from forever.pipeline.measure import (
    find_mine,
    gcd_intervals,
    hit_tally,
    log_spell_sets,
    monster_hp,
    spell_costs,
)
from forever.registry import find_entry, load

SECOND_LOG = COMBATLOG / "WoWCombatLog-092726_150346.anon.txt.gz"
JOURNEY = FIXTURES / "questie" / "journey" / "Questie.lua"
UTC_OFFSET = timedelta(hours=2)  # instantané ForeverLogger du 2026-09-27 : time 1790523688 = localtime 17:41:28
MAX_GAP_S = 3.0  # fenêtre d'enchaînement (paramètre de mesure, comme tests/unit/test_measure.py)


@pytest.fixture(scope="module")
def second():
    header, it = read_log(SECOND_LOG)
    return header, list(it)


def events(path):
    return list(read_log(path)[1])


def test_second_fixture_header_and_events(second):
    header, evs = second
    assert (header.version, header.advanced, header.build, header.project_id) == (22, True, "1.60.1", 18)
    assert len(evs) == 3329


def test_gz_log_reads_like_the_plain_text(second, tmp_path):
    plain = tmp_path / "WoWCombatLog-plain.txt"
    plain.write_bytes(gzip.decompress(SECOND_LOG.read_bytes()))
    header, it = read_log(plain)
    assert header == second[0]
    assert [(e.time, e.name, e.raw) for e in it] == [(e.time, e.name, e.raw) for e in second[1]]


def test_scan_lists_gz_logs():
    names = [s.name for s in scan_logs(COMBATLOG)]
    assert names == [REAL_LOG.name, SECOND_LOG.name]


def test_single_mine_player(second):
    _, evs = second
    mine = {u.guid for e in evs for u in (e.source, e.dest) if u is not None and u.is_mine and u.kind == "Player"}
    assert mine == {MINE_GUID} and find_mine(evs) == MINE_GUID


def test_spell_sets_come_from_the_data(game_data):
    sets = log_spell_sets(game_data)
    assert {116, 205, 837, 122, 145, 1449, 2137} <= sets.gcd
    assert 5019 not in sets.known and 6136 not in sets.known  # baguette (Shoot), Chilled (Frost Armor)
    assert sets.gcd <= sets.known


def test_gcd_intervals_filtered_to_gcd_spells(second, game_data):
    _, evs = second
    intervals = gcd_intervals(evs, MINE_GUID, max_gap_s=MAX_GAP_S, gcd_spells=log_spell_sets(game_data).gcd)
    assert len(intervals) == 47
    assert min(intervals) == pytest.approx(1.414, abs=1e-3)
    assert statistics.median(intervals) == pytest.approx(1.51, abs=1e-3)


def test_gcd_intervals_without_filter_keep_off_gcd_spells(second):
    _, evs = second
    intervals = gcd_intervals(evs, MINE_GUID, max_gap_s=MAX_GAP_S)
    assert len(intervals) == 98 and min(intervals) == pytest.approx(0.001, abs=1e-6)


def test_monsters_and_costs(second):
    _, evs = second
    observations, conflicts = monster_hp(evs, log=SECOND_LOG.name)
    assert len(observations) == 29 and conflicts == []
    costs = spell_costs(evs, MINE_GUID)
    assert {k: costs[k] for k in (837, 145, 1449, 2137, 122)} == {
        837: {50},
        145: {65},
        1449: {75},
        2137: {75},
        122: {55},
    }


def test_hit_tally_with_the_questie_journey(second, game_data):
    _, evs = second
    levels = CasterLevels((from_questie_journey(JOURNEY, MINE_GUID, utc_offset=UTC_OFFSET),))
    tally = hit_tally(evs, MINE_GUID, levels, known_spells=log_spell_sets(game_data).known)
    counts = tally.counts
    assert sum(c["hits"] for c in counts.values()) == 281
    assert sum(c["misses"] for c in counts.values()) == 0
    assert all(not c["by_type"] for c in counts.values())  # Chilled (effet de Frost Armor) exclu
    assert {school for school, _ in counts} == {"arcane", "fire", "frost"}  # baguette (physique) exclue
    assert {diff for _, diff in counts} == {-8, -7, -5, -4, -3, -2}
    assert (counts[("frost", -4)]["hits"], counts[("frost", -3)]["hits"]) == (43, 50)  # 14 puis 15


def test_b1_proof_matches_the_registry(game_data, second):
    """Preuve B1 de deux journaux (décision 2) : effectif et écarts à la recharge globale des données, recalculés."""
    gcd = log_spell_sets(game_data).gcd
    intervals = gcd_intervals(events(REAL_LOG), MINE_GUID, max_gap_s=MAX_GAP_S, gcd_spells=gcd)
    intervals += gcd_intervals(second[1], MINE_GUID, max_gap_s=MAX_GAP_S, gcd_spells=gcd)
    (proof,) = find_entry(load(REGISTRY_PATH), "B1").proofs
    assert proof["journal"] == [
        "tests/fixtures/combatlog/WoWCombatLog-092726_145346.anon.txt",
        "tests/fixtures/combatlog/WoWCombatLog-092726_150346.anon.txt.gz",
    ]
    assert proof["n"] == len(intervals) == 50
    gcd_s = game_data.rules.gcd_s
    assert proof["ecart_median_s"] == pytest.approx(abs(statistics.median(intervals) - gcd_s), abs=5e-4)
    # 10e percentile (statistics.quantiles, méthode par défaut) : 1,4569 s ; minimum 1,414 s non contrôlé
    assert proof["ecart_p10_s"] == pytest.approx(gcd_s - statistics.quantiles(intervals, n=10)[0], abs=5e-5)


def test_logs_measure_on_the_gz_fixture_with_the_journey(capsys, make_deps):
    argv = ["logs", "measure", str(SECOND_LOG), "--questie-sv", str(JOURNEY), "--utc-offset", "2", "--json"]
    assert main(argv, make_deps()) == 0
    payload = json.loads(capsys.readouterr().out)
    (log,) = payload["logs"]
    assert log["gcd_intervals"]["n"] == 47 and len(log["monsters"]) == 29
    assert sum(h["hits"] for h in log["hit_tally"]) == 281
    assert log["caster_level"] == 14
    assert log["caster_level_changes"] == [{"time": "2026-09-27T15:17:26", "level": 15, "source": "questie"}]
    assert payload["provenance"]["game_version"]


def test_logs_measure_directory_reads_both_fixtures(capsys, make_deps):
    assert main(["logs", "measure", str(COMBATLOG), "--caster-level", "15", "--json"], make_deps()) == 0
    logs = json.loads(capsys.readouterr().out)["logs"]
    assert [m["name"] for m in logs] == [REAL_LOG.name, SECOND_LOG.name]
    assert [m["caster_level"] for m in logs] == [15, 15]
