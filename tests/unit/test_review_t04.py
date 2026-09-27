"""Corrections de relecture de T04a : ratés avant le bloc avancé, types de raté, journal illisible, rang invalide."""

import pytest
from conftest import SYNTHETIC_LOGS

from forever.engine.spells import rank_values_at_level
from forever.pipeline.combatlog import read_log, scan_logs
from forever.pipeline.measure import hit_tally


def test_miss_before_the_target_is_described_counts_at_its_level():
    _, events = read_log(SYNTHETIC_LOGS / "missed_first.txt")
    tally = hit_tally(list(events), "Player-0000-00000000", 14)
    (count,) = tally.counts.values()
    assert list(tally.counts) == [("frost", -8)]
    assert (count["hits"], count["misses"]) == (1, 1)  # RESIST compte, IMMUNE non
    assert count["by_type"] == {"RESIST": 1, "IMMUNE": 1}
    assert tally.assumptions == []


def test_scan_lists_an_unreadable_log_instead_of_failing(tmp_path):
    (tmp_path / "WoWCombatLog-1.txt").write_bytes((SYNTHETIC_LOGS / "hp_conflict.txt").read_bytes())
    (tmp_path / "WoWCombatLog-2.txt").write_bytes(b"9/27/2026 10:00:00.0000  COMBAT_LOG_VERSION,22\n\xc3")
    ok, bad = scan_logs(tmp_path)
    assert ok.error is None and bad.error and "UTF-8" in bad.error


def test_rank_out_of_range_is_refused(game_data):
    with pytest.raises(ValueError, match="rang 0"):
        rank_values_at_level(game_data, "frostbolt", 0, 20)
