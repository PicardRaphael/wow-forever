"""SIM2 : combat de zone (plusieurs cibles), demande du 2026-11-08 (« AoE, single »).

`targets` (défaut 1) : la rencontre porte N cibles identiques (copies de la cible de la rencontre de référence de
wowsims, chacune au niveau voulu ; le proto de wowsims porte une liste `repeated Target targets` et son simulateur
crée une cible par entrée) ; `targets` est rendu dans le résultat et dit dans la provenance ; transmis par
`forever sims brackets --targets N` et `forever_simulate(action="brackets", targets=N)`.
Dépôt et simulateur fabriqués : aucune valeur de jeu."""

import pytest
from test_sims_brackets import LevelSim
from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import ENCOUNTER

from forever.errors import InvalidArgumentError
from forever.sims.brackets import encounter_at, run_brackets


def test_encounter_copies_the_reference_target_n_times_at_the_level():
    out = encounter_at(ENCOUNTER, 25, targets=3)
    assert len(out["targets"]) == 3
    assert all(t["level"] == 25 and t["name"] == ENCOUNTER["targets"][0]["name"] for t in out["targets"])
    out["targets"][0]["level"] = 1
    assert out["targets"][1]["level"] == 25  # copies indépendantes
    assert len(ENCOUNTER["targets"]) == 1 and ENCOUNTER["targets"][0]["level"] == 63  # rencontre d'origine intacte
    assert len(encounter_at(ENCOUNTER, 25)["targets"]) == 1


def test_brackets_fight_n_targets_and_say_so(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    sim = LevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=[], picks_at=None,
                       iterations=10, runner=sim, targets=5)  # fmt: skip
    targets = sim.requests[0]["encounter"]["targets"]
    assert len(targets) == 5 and {t["level"] for t in targets} == {25}
    assert out["targets"] == 5
    assert any("5 cibles" in a for a in out["provenance"]["assumptions"])


def test_single_target_is_the_default_and_zero_is_refused(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    sim = LevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=[], picks_at=None,
                       iterations=10, runner=sim)  # fmt: skip
    assert out["targets"] == 1 and len(sim.requests[0]["encounter"]["targets"]) == 1
    with pytest.raises(InvalidArgumentError, match="cible"):
        run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=[], picks_at=None,
                     iterations=10, runner=sim, targets=0)  # fmt: skip


def test_targets_reach_the_calculation_from_the_tool(make_deps, monkeypatch):
    from forever.sims import brackets
    from forever.sims.report import simulate

    seen = {}

    def fake(deps, **kw):
        seen.update(kw)
        return {"rows": []}

    monkeypatch.setattr(brackets, "run_from_sources", fake)
    simulate(make_deps(), "brackets", preset="mage/dps/Fire", race="Human", targets=5)
    assert seen["targets"] == 5
    simulate(make_deps(), "brackets", preset="mage/dps/Fire", race="Human")
    assert seen["targets"] == 1


def test_cli_and_mcp_take_targets(make_deps, monkeypatch):
    import asyncio

    from mcp import Client

    from forever.cli import build_parser
    from forever.mcp_server import build_server
    from forever.sims import report

    args = build_parser().parse_args(["sims", "brackets", "--preset", "mage/dps/Fire", "--race", "Human",
                                      "--targets", "5"])  # fmt: skip
    assert args.targets == 5
    assert build_parser().parse_args(["sims", "brackets", "--preset", "p", "--race", "Human"]).targets == 1
    seen = {}

    def fake(deps, action, **kw):
        seen.update(kw)
        return {"rows": []}

    monkeypatch.setattr(report, "simulate", fake)

    async def go():
        async with Client(build_server(make_deps())) as client:
            await client.call_tool("forever_simulate", {"action": "brackets", "preset": "p", "targets": 3})

    asyncio.run(go())
    assert seen["targets"] == 3
