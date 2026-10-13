"""Séance de jeu avec bonus d'XP (T04f, bloc B) : `session_xp` déroule le temps (durée restante des auras, réservoir
de repos consommé) et rend l'XP par heure moyenne et la part de chaque bonus. Valeurs lues dans les données."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.engine.xp import ActiveAura, XpBonusState, session_xp, xp_multiplier

WELL_RESTED = 429959
BASE = 10_000.0  # XP par heure sans bonus : paramètre de test, pas une valeur du jeu


def wr():
    return next(
        a for a in read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")["auras"] if a["spell_id"] == WELL_RESTED
    )


def wr3():
    a = wr()
    return XpBonusState(auras=(ActiveAura(WELL_RESTED, a["max_stacks"], a["duration_ms"] / 1000),))


def test_without_bonus_the_session_is_the_base(game_data):
    s = session_xp(game_data, base_xp_h=BASE, kill_share=1.0, hours=3, state=None, rested_pool=0.0, level=20)
    assert s.xp_h == pytest.approx(BASE, rel=1e-12) and s.total_xp == pytest.approx(BASE * 3, rel=1e-12)
    assert s.by_bonus == {}


def test_bonus_only_lasts_its_remaining_time(game_data):
    duration_h = wr()["duration_ms"] / 3_600_000
    hours = 2 * duration_h
    factor, _ = xp_multiplier(game_data, wr3(), source="kill")
    s = session_xp(game_data, base_xp_h=BASE, kill_share=1.0, hours=hours, state=wr3(), rested_pool=0.0, level=20)
    assert s.total_xp == pytest.approx(BASE * hours + BASE * duration_h * (factor - 1), rel=1e-9)
    assert s.by_bonus[f"xp_bonus.{WELL_RESTED}"] == pytest.approx(BASE * duration_h * (factor - 1), rel=1e-9)


def test_rested_pool_runs_out(game_data):
    pool = BASE * 0.25
    s = session_xp(game_data, base_xp_h=BASE, kill_share=1.0, hours=2, state=None, rested_pool=pool, level=20)
    assert s.rested_used == pytest.approx(pool, rel=1e-9)
    assert s.total_xp == pytest.approx(BASE * 2 + pool, rel=1e-9)
    assert s.by_bonus["xp.rested"] == pytest.approx(pool, rel=1e-9)


def test_quest_share_gets_no_rested(game_data):
    s = session_xp(game_data, base_xp_h=BASE, kill_share=0.0, hours=1, state=None, rested_pool=1e9, level=20)
    assert s.rested_used == 0.0 and s.total_xp == pytest.approx(BASE, rel=1e-12)


@pytest.mark.parametrize("kill_share", [0.0, 0.6, 1.0])
def test_parts_add_up_and_bonus_never_lowers_xp(game_data, kill_share):
    state = XpBonusState(auras=wr3().auras, food=True)
    s = session_xp(game_data, base_xp_h=BASE, kill_share=kill_share, hours=3, state=state, rested_pool=BASE, level=20)
    plain = session_xp(game_data, base_xp_h=BASE, kill_share=kill_share, hours=3, state=None, rested_pool=0.0, level=20)
    assert s.xp_h >= plain.xp_h
    assert BASE * 3 + sum(s.by_bonus.values()) == pytest.approx(s.total_xp, rel=1e-9)
    for t in s.terms:
        assert t.certainty in {"certain", "probable", "suppose"} and t.source
