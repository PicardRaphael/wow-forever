"""Vérification passive des bonus d'XP (T04f, bloc F, décision 247) : `forever xp check` compare le facteur prédit
aux gains relevés avec leurs auras (ForeverLogger 0.5.0, schéma 3) ; par règle (Well-Rested, nourriture, cumul,
repos Legacy) « vérifié » ou « à vérifier », jamais d'échec. Fixture synthétique
`tests/fixtures/addon/ForeverLoggerDB_xpcheck_bonus.lua` (voir le README du dossier)."""

from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, read_json

from forever.pipeline.addon_sv import read_logger_db
from forever.xp_check import RULES, check_records

SV = FIXTURES / "addon" / "ForeverLoggerDB_xpcheck_bonus.lua"
OLD = FIXTURES / "addon" / "ForeverLoggerDB_xpcheck.lua"
BONUS_RULES = {
    "xp.sleeping_bag": "LVL12",
    "xp.food_bonus": "LVL13",
    "xp.bonus_stacking": "LVL12",
    "xp.legacy_rested": "LVL10",
}


def params():
    return read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["measures.xp_check"]["value"]


def check(game_data, *paths):
    p = params()
    return check_records(
        game_data, None, [read_logger_db(path) for path in paths], tolerance=p["tolerance"], min_cases=p["min_cases"]
    )


def rule(report, key):
    return next(r for r in report["rules"] if r["rule"] == key)


def test_bonus_rules_are_reported_with_their_question():
    for key, question in BONUS_RULES.items():
        assert RULES[key][1] == question


def test_each_bonus_gain_goes_to_its_rule(game_data):
    report = check(game_data, SV)
    for key in ("xp.sleeping_bag", "xp.food_bonus", "xp.bonus_stacking"):
        r = rule(report, key)
        assert r["cases"] == 1 and r["outside"] == 0, key
        assert r["verdict"] in ("vérifié", "à vérifier")
    assert rule(report, "kill_xp")["cases"] == 1  # l'aura sans rapport ne change rien


def test_legacy_rested_stays_to_verify(game_data):
    r = rule(check(game_data, SV), "xp.legacy_rested")
    assert r["cases"] == 0 and r["verdict"] == "à vérifier"


def test_gains_without_auras_are_unchanged(game_data):
    report = check(game_data, OLD)
    for key in BONUS_RULES:
        assert rule(report, key)["cases"] == 0
    assert rule(report, "kill_xp")["cases"] == 4


def test_never_raises_without_records(game_data):
    empty = check(game_data)
    assert all(r["verdict"] == "à vérifier" for r in empty["rules"])
