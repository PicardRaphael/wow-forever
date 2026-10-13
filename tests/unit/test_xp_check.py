"""Vérification passive du modèle d'XP (T04d, bloc G, décision 247) : `forever xp check`.

Fixture : `tests/fixtures/addon/ForeverLoggerDB_xpcheck.lua` (synthétique, voir le README du dossier) : Chasseur de
niveau 15 : trois gains de même niveau égaux à `kill_xp` du niveau 15 (`character_scaling.json`), un gain d'un
monstre de niveau 13 volontairement faux, un gain reposé, un ancien gain sans cible ; un rendu de la quête 5725 ;
Mage de niveau 1 : un ancien gain sur « Hare » (niveau fixe 1 dans la fixture de Questie). Paramètres : `mechanics.json`
de la version du dépôt (`measures.xp_check`)."""

import json
import shutil

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.cli import main
from forever.pipeline.addon_sv import read_logger_db
from forever.provenance import validate_provenance
from forever.xp_check import RULES, check_records

SV = FIXTURES / "addon" / "ForeverLoggerDB_xpcheck.lua"
QUESTIE = FIXTURES / "questie" / "11.38.0"


def params():
    return read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["measures.xp_check"]["value"]


@pytest.fixture(scope="module")
def report(game_data):
    p = params()
    rewards = read_json(DATA_DIR / LOCAL_VERSION / "quest_rewards.json")
    from forever.pipeline.questie import read_questie

    npcs = read_questie(QUESTIE).npcs()
    fixed = {n.name: n.min_level for n in npcs.values() if n.min_level == n.max_level}
    return check_records(
        game_data,
        rewards,
        [read_logger_db(SV)],
        tolerance=p["tolerance"],
        min_cases=p["min_cases"],
        questie_levels=fixed,
    )


def rule(report, key):
    return next(r for r in report["rules"] if r["rule"] == key)


def test_every_rule_is_reported(report):
    assert {r["rule"] for r in report["rules"]} == set(RULES)


def test_same_level_gains_verify_the_client_per_kill(report):
    r = rule(report, "kill_xp")
    assert r["cases"] == 5  # trois gains, le gain reposé (base) et le lièvre de niveau fixe (Questie)
    assert r["outside"] == 0 and r["median_gap"] == pytest.approx(0.0)
    assert r["verdict"] == "vérifié" if r["cases"] >= params()["min_cases"] else "à vérifier"


def test_level_difference_gap_is_reported(report):
    r = rule(report, "xp.mob_level_difference")
    assert r["cases"] == 1 and r["outside"] == 1 and r["verdict"] == "écart"


def test_old_gain_without_monster_level_is_skipped_and_counted(report):
    assert report["skipped"]["sans niveau de monstre"] == 1


def test_rested_and_seen_quest_are_compared(report):
    rested = rule(report, "xp.rested")
    assert rested["cases"] == 1 and rested["outside"] == 0
    quest = rule(report, "quest_xp")
    assert quest["cases"] == 1 and quest["outside"] == 0


def test_rules_without_records_stay_to_verify_with_their_question(report):
    for key in ("xp.elite_factor", "xp.dungeon_kill_bonus", "xp.group"):
        r = rule(report, key)
        assert r["cases"] == 0 and r["verdict"] == "à vérifier"
        assert r["question"] == RULES[key][1]
    labels = {t["rule"] for t in report["to_verify"]}
    assert {"xp.elite_factor", "xp.dungeon_kill_bonus", "xp.group"} <= labels


def run(capsys, args, tmp_path, monkeypatch):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FOREVER_WOW_DIR", str(tmp_path / "wow"))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    code = main(args)
    return code, capsys.readouterr().out


def test_cli_is_passive_without_any_record(capsys, tmp_path, monkeypatch):
    empty = tmp_path / "sv"
    empty.mkdir()
    code, out = run(capsys, ["xp", "check", "--sv", str(empty), "--json"], tmp_path, monkeypatch)
    assert code == 0
    doc = json.loads(out)
    assert all(r["verdict"] == "à vérifier" for r in doc["rules"])
    assert validate_provenance(doc["provenance"]) == []


def test_cli_reads_the_logger_file(capsys, tmp_path, monkeypatch):
    sv = tmp_path / "sv"
    sv.mkdir()
    shutil.copyfile(SV, sv / "ForeverLogger.lua")
    code, out = run(capsys, ["xp", "check", "--sv", str(sv)], tmp_path, monkeypatch)
    assert code == 0 and "écart" in out and "à vérifier" in out and "Provenance" in out
