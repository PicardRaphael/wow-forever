"""Lecture des journaux de combat (format 22 avancé) : en-tête, événements, unités, bloc avancé, suffixes.

Valeurs tirées de la fixture anonymisée du journal réel du 2026-09-27 (tests/fixtures/combatlog/README.md)."""

from collections import Counter

import pytest
from conftest import COMBATLOG, MINE_GUID, REAL_LOG, SYNTHETIC_LOGS

from forever.errors import DataSchemaError, UnsupportedLogError
from forever.pipeline.combatlog import read_log, scan_logs


def events(path=REAL_LOG):
    _, it = read_log(path)
    return list(it)


def test_header():
    header, _ = read_log(REAL_LOG)
    assert (header.version, header.advanced, header.build, header.project_id) == (22, True, "1.60.1", 18)


def test_event_counts_match_real_log():
    evs = events()
    assert len(evs) == 193
    counts = Counter(e.name for e in evs)
    assert counts["SPELL_AURA_APPLIED"] == 44
    assert counts["SPELL_CAST_SUCCESS"] == 40
    assert counts["SPELL_CAST_START"] == 29
    assert counts["SWING_DAMAGE"] == 12
    assert counts["SPELL_DAMAGE"] == 9
    assert counts["SWING_DAMAGE_LANDED"] == 9
    assert counts["UNIT_DIED"] == 4
    assert counts["DAMAGE_SHIELD"] == 6
    assert counts["ENVIRONMENTAL_DAMAGE"] == 1
    assert [e.line for e in evs[:2]] == [2, 3]


def test_timestamp_parsed():
    first = events()[0]
    assert first.name == "ZONE_CHANGE"
    assert first.time.isoformat() == "2026-09-27T14:53:46.081200"  # heure locale du client, sans fuseau


def test_advanced_block_has_19_fields_and_describes_destination_on_spell_damage():
    frostbolt = next(e for e in events() if e.name == "SPELL_DAMAGE" and e.spell and e.spell[0] == 837)
    adv = frostbolt.advanced
    assert adv is not None and len(adv) == 19
    assert adv.guid == frostbolt.dest.guid
    assert (adv.hp, adv.max_hp, adv.level, adv.ui_map_id) == (64, 120, 6, 1411)
    assert frostbolt.dest.npc_id == 3099 and frostbolt.dest.kind == "Creature"
    assert frostbolt.spell == (837, "Frostbolt", 0x10)
    assert frostbolt.suffix["amount"] == 56 and frostbolt.suffix["critical"] is None
    assert frostbolt.suffix["aoe"] is False


def test_advanced_block_describes_source_on_swing_and_cast_success():
    evs = events()
    swing = next(e for e in evs if e.name == "SWING_DAMAGE")
    assert swing.advanced.guid == swing.source.guid
    landed = next(e for e in evs if e.name == "SWING_DAMAGE_LANDED")
    assert landed.advanced.guid == landed.dest.guid
    cast = next(e for e in evs if e.name == "SPELL_CAST_SUCCESS" and e.source.guid == MINE_GUID)
    assert cast.advanced.guid == MINE_GUID and cast.advanced.power_cost == 50


def test_suffixes_of_other_events():
    evs = events()
    env = next(e for e in evs if e.name == "ENVIRONMENTAL_DAMAGE")
    assert env.source is None and env.suffix["environmental_type"] == "Fire" and env.suffix["amount"] == 14
    crit = next(e for e in evs if e.name == "SPELL_DAMAGE" and e.suffix["critical"])
    assert (crit.suffix["amount"], crit.suffix["base_amount"], crit.spell[0]) == (87, 58, 145)
    energize = next(e for e in evs if e.name == "SPELL_ENERGIZE")
    assert energize.suffix["amount"] == 9 and energize.suffix["power_type"] == 1
    missed = next(e for e in evs if e.name == "SWING_MISSED")
    assert missed.suffix["miss_type"] == "DODGE" and missed.advanced is None
    failed = next(e for e in evs if e.name == "SPELL_CAST_FAILED")
    assert failed.suffix["failed_type"]


def test_single_mine_player():
    mine = {u.guid for e in events() for u in (e.source, e.dest) if u is not None and u.is_mine}
    assert mine == {MINE_GUID}


@pytest.mark.parametrize("name", ["version21.txt", "not_advanced.txt", "empty.txt"])
def test_unsupported_logs(name):
    with pytest.raises(UnsupportedLogError) as exc:
        read_log(SYNTHETIC_LOGS / name)
    assert exc.value.code == "unsupported_log" and exc.value.exit_code == 3


def test_truncated_line_names_file_and_line():
    with pytest.raises(DataSchemaError) as exc:
        events(SYNTHETIC_LOGS / "truncated.txt")
    assert "truncated.txt" in exc.value.message and "ligne 3" in exc.value.message


def test_unknown_event_is_kept_raw():
    evs = events(SYNTHETIC_LOGS / "unknown_event.txt")
    unknown = evs[0]
    assert unknown.name == "FOREVER_NEW_EVENT" and unknown.raw == ("FOREVER_NEW_EVENT", "1", "2", "3")
    assert unknown.source is None and unknown.advanced is None and dict(unknown.suffix) == {}
    assert evs[1].name == "SPELL_DAMAGE"


def test_scan_logs_lists_every_log(tmp_path):
    (tmp_path / "WoWCombatLog-092726_145346.txt").write_bytes(REAL_LOG.read_bytes())
    (tmp_path / "WoWCombatLog-092726_150346.txt").write_bytes(b"")
    (tmp_path / "Hotfix.log").write_bytes(b"x")
    summaries = scan_logs(tmp_path)
    assert [s.name for s in summaries] == ["WoWCombatLog-092726_145346.txt", "WoWCombatLog-092726_150346.txt"]
    real, empty = summaries
    assert real.lines == 194 and real.events == 193 and real.header.build == "1.60.1"
    assert real.start.isoformat() == "2026-09-27T14:53:46.081200" and real.end.minute == 55
    assert real.mine == ["Moi-Royaume"] and real.error is None
    assert empty.lines == 0 and empty.header is None and empty.error


def test_scan_logs_reads_utf8_names_and_ignores_other_files(tmp_path):
    assert scan_logs(SYNTHETIC_LOGS) == []  # seuls les fichiers WoWCombatLog-*.txt sont listés
    (tmp_path / "WoWCombatLog-1.txt").write_bytes((SYNTHETIC_LOGS / "hp_conflict.txt").read_bytes())
    assert scan_logs(tmp_path)[0].mine == ["Élève-Royaume"]
    assert scan_logs(COMBATLOG)[0].mine == ["Moi-Royaume"]
