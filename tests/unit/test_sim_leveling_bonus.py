"""Simulateur de leveling avec bonus d'XP (T04f, bloc C) : sans bonus, sortie inchangée (parité du seed intacte) ;
avec un bonus, XP par heure multipliée par le facteur de la séance et bonus listés."""

import asyncio

import pytest
from mcp import Client

from forever.engine.xp import session_xp, sleeping_bag_state
from forever.errors import InvalidArgumentError
from forever.gamedata import load_game_data
from forever.leveling import simulate_leveling
from forever.mcp_server import build_server
from forever.xp_bonuses import DEFAULT_SESSION_H

LEVEL, N = 20, 40


def test_without_bonus_the_report_is_unchanged(make_deps):
    deps = make_deps()
    plain = simulate_leveling(deps, LEVEL, n=N)
    explicit = simulate_leveling(deps, LEVEL, n=N, bonus=(), rested=0.0)
    assert "bonuses" not in plain
    assert explicit["analytic"] == plain["analytic"] and explicit["monte_carlo"] == plain["monte_carlo"]


def test_sleeping_bag_multiplies_xp_per_hour(make_deps):
    deps = make_deps()
    plain = simulate_leveling(deps, LEVEL, n=N)
    rep = simulate_leveling(deps, LEVEL, n=N, bonus=["sleeping_bag"])
    gd = load_game_data(deps)
    for side in ("analytic", "monte_carlo"):
        base = plain[side]["xp_h"]
        s = session_xp(
            gd,
            base_xp_h=base,
            kill_share=1.0,
            hours=DEFAULT_SESSION_H,
            state=sleeping_bag_state(gd),
            rested_pool=0.0,
            level=LEVEL,
        )
        assert rep[side]["xp_h"] == pytest.approx(s.xp_h, rel=1e-9)
        assert rep[side]["total"] == plain[side]["total"]  # temps par monstre inchangé
    assert rep["bonuses"]["names"] == ["sleeping_bag"] and rep["bonuses"]["terms"]
    assert rep["bonuses"]["factor"] > 1
    assert any("bonus" in a for a in rep["provenance"]["assumptions"])


def test_unknown_bonus_is_refused(make_deps):
    with pytest.raises(InvalidArgumentError):
        simulate_leveling(make_deps(), LEVEL, n=N, bonus=["discoverers_delight"])


def test_mcp_sim_leveling_with_bonus(make_deps):
    async def go():
        async with Client(build_server(make_deps())) as client:
            return await client.call_tool(
                "forever_sim_leveling", {"level": LEVEL, "n": N, "bonus": ["food"], "rested": 1000.0}
            )

    r = asyncio.run(go())
    assert not r.is_error
    assert r.structured_content["bonuses"]["names"] == ["food"]
