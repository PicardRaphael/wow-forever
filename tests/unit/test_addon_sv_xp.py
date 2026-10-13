"""T04d, bloc A : lecture des gains d'XP et des quêtes de ForeverLogger 0.4.0 (`forever/pipeline/addon_sv.py`).
Montant lu dans le texte (anglais et français, anciennes entrées comprises), bonus de groupe et de repos séparés,
reste du texte gardé ; nouveaux champs (cible, niveaux vus, état de l'XP, instance, groupe, carte), états de l'XP,
quêtes acceptées et rendues. Valeurs de la fixture `tests/fixtures/addon/ForeverLoggerDB_xp.lua` (inventées)."""

import pytest
from conftest import FIXTURES

from forever.pipeline.addon_sv import ParsedXp, parse_xp_text, read_logger_db

SAMPLE = FIXTURES / "addon" / "ForeverLoggerDB_xp.lua"
OLD = FIXTURES / "addon" / "ForeverLoggerDB.lua"
GUID = "Player-0000-0000BEEF"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Dire Mottled Boar dies, you gain 23 experience.",
            ParsedXp(23, "monster", "Dire Mottled Boar", None, None, ""),
        ),
        (
            "Kolkar Drudge dies, you gain 40 experience. (+4 group bonus)",
            ParsedXp(40, "monster", "Kolkar Drudge", 4, None, "(+4 group bonus)"),
        ),
        ("You gain 450 experience.", ParsedXp(450, "other", None, None, None, "")),
        ("You gain 1,050 experience.", ParsedXp(1050, "other", None, None, None, "")),
        ("You gain 12 experience. (+3 group bonus)", ParsedXp(12, "other", None, 3, None, "(+3 group bonus)")),
        (
            "Sanglier marbré meurt, vous gagnez 23 points d'expérience.",
            ParsedXp(23, "monster", "Sanglier marbré", None, None, ""),
        ),
        ("Vous gagnez 120 points d'expérience.", ParsedXp(120, "other", None, None, None, "")),
        (
            "Ragefire Trogg dies, you gain 67 experience. (+33 exp Rested bonus)",
            ParsedXp(67, "monster", "Ragefire Trogg", None, 33, "(+33 exp Rested bonus)"),
        ),
        (
            "Ragefire Trogg dies, you gain 67 experience. (+30 exp Rested bonus, +4 group bonus)",
            ParsedXp(67, "monster", "Ragefire Trogg", 4, 30, "(+30 exp Rested bonus, +4 group bonus)"),
        ),
        ("You gain 46 experience. (forme inconnue)", ParsedXp(46, "other", None, None, None, "(forme inconnue)")),
        ("Texte sans montant", ParsedXp(None, "unknown", None, None, None, "")),
    ],
)
def test_parse_xp_text(text, expected):
    assert parse_xp_text(text) == expected


def test_old_and_new_gains_are_read_with_their_amount():
    me = read_logger_db(SAMPLE).characters[GUID]
    assert [g.amount for g in me.xp] == [23, 40, 450, 23, 67, 30]
    assert [g.kind for g in me.xp] == ["monster", "monster", "other", "monster", "monster", "monster"]
    assert me.xp[1].group_bonus == 4 and me.xp[1].rested_bonus is None
    assert me.xp[0].seq is None and me.xp[0].target is None and me.xp[0].state == {}  # ancienne entrée
    new = me.xp[4]
    assert new.seq == 12 and new.rested_bonus == 33 and new.monster == "Ragefire Trogg"
    assert new.target == {
        "name": "Ragefire Trogg",
        "level": 13,
        "classification": "normal",
        "npc": 11318,
        "creature_type": "Humanoid",
        "source": "target",
    }
    assert new.state == {"xp": 400, "max": 1000, "rested": 300, "rest_state": 1}
    assert new.resting is False
    assert new.instance == {"inside": True, "type": "party", "name": "Ragefire Chasm", "id": 389}
    assert new.group == {"size": 3, "raid": False, "levels": [14, 17]}
    assert new.map == 213
    seen = me.xp[5]
    assert seen.target is None and seen.seen_levels == [7, 8] and seen.map == 1411


def test_states_and_quests_are_read():
    me = read_logger_db(SAMPLE).characters[GUID]
    assert [(s.seq, s.reason, s.xp, s.rested) for s in me.xp_states] == [
        (11, "connexion", 400, 300),
        (13, "xp", 467, 267),
    ]
    assert me.xp_states[0].max == 1000 and me.xp_states[0].rest_state == 1 and me.xp_states[0].resting is False
    (accepted,) = me.quest_accepts
    assert (accepted.quest_id, accepted.title, accepted.quest_level, accepted.seq) == (
        5761,
        "Slaying the Beast",
        16,
        20,
    )
    (turned,) = me.quest_turnins
    assert (turned.quest_id, turned.xp_reward, turned.money_reward, turned.level) == (5761, 1450, 2500, 15)
    assert turned.state == {"xp": 900, "max": 1000, "rested": 120, "rest_state": 1} and turned.resting is True
    assert turned.map == 1454 and turned.localtime is not None
    snap = me.snapshots[0]
    assert snap.trivial_range == 5 and snap.state["rested"] == 300 and snap.resting is True


def test_schema_one_file_still_reads_without_new_lists():
    db = read_logger_db(OLD)
    assert db.schema == 1
    me = db.characters["Player-0000-00000000"]
    assert me.xp[0].amount == 23 and me.xp[0].kind == "monster"
    assert me.xp_states == [] and me.quest_accepts == [] and me.quest_turnins == []
    assert me.snapshots[0].trivial_range is None and me.snapshots[0].state == {}
