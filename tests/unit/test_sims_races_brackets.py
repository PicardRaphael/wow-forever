"""SIM2 §9 : toutes les races jouables d'une classe comparées par tranche de niveaux (demande du 2026-11-08 : « toute
race… meilleur DPS »).

Pour chaque tranche, un combat par race jouable de la classe (lue dans `races.json` des données de Forever), mêmes
talents, même équipement, même graine (tirages appariés) ; races triées par dégâts par seconde, écart à la meilleure,
« non départagé » quand l'écart est sous deux erreurs types (`forever.sims.builds.decide`).

Dépôt et simulateur fabriqués (dégâts = niveau + écart fabriqué par race) : aucune valeur de jeu."""

import json
import subprocess
from pathlib import Path

import pytest
from test_sims_brackets import FROST_STEPS, LevelSim
from test_sims_brackets import _setup as brackets_setup

from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.provenance import validate_provenance
from forever.sims.races import compare_races_brackets, playable_races
from forever.sims.report import simulate
from forever.sims.wowsims import race_enum
from forever.store import load_version

# écart fabriqué par race (dégâts par seconde) ; sens inversé à partir du niveau 50 pour changer l'ordre par tranche
OFFSET = {"RaceTroll": 5.0, "RaceHighOrderSkyborne": 5.1, "RaceOrc": 3.0, "RaceHuman": 1.0, "RaceGnome": 0.0,
          "RaceUndead": -2.0}  # fmt: skip


class RaceLevelSim(LevelSim):
    """Dégâts = niveau + écart de la race (inversé dès le niveau 50) ; écart type 1."""

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        flag = next((a for a in args if a.startswith("--forever-level=")), None)
        level = int(flag.split("=")[1]) if flag else 60
        self.levels.append(level)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        race = req["raid"]["parties"][0]["players"][0]["race"]
        sign = 1.0 if level < 50 else -1.0
        dps = level + sign * OFFSET.get(race, -10.0)
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": dps, "stdev": 1.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def _mage_races(deps):
    races = load_version(deps).read_json("races.json")["races"]
    return {race_enum(name) for name, r in races.items() if "Mage" in r.get("classes", [])}


def test_playable_races_are_read_from_the_game_data(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    expected = _mage_races(deps)
    assert expected and set(playable_races(deps, "Mage")) == expected
    assert len(playable_races(deps, "Mage")) == len(expected)  # chaque race une fois


def test_every_playable_race_is_ranked_in_each_bracket(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    sim = RaceLevelSim()
    picks = {15: [{"slot": "Back", "item": 6614}], 60: [{"slot": "Chest", "item": 2800}]}
    out = compare_races_brackets(deps, preset="mage/dps/Fire", brackets="10-19,60", steps=FROST_STEPS,
                                 picks_at=lambda level: picks[level], iterations=100, runner=sim)  # fmt: skip
    races = _mage_races(deps)
    assert set(out["races"]) == races and out["preset"] == "mage/dps/Fire" and out["conditions"] == "solo"
    assert [(b["bracket"], b["level"]) for b in out["brackets"]] == [("10-19", 15), ("60", 60)]
    for b in out["brackets"]:
        ranking = b["ranking"]
        assert {r["race"] for r in ranking} == races
        dps = [r["dps"] for r in ranking]
        assert dps == sorted(dps, reverse=True)
        assert ranking[0]["gap_to_best"] == 0.0
        assert all(r["gap_to_best"] == pytest.approx(r["dps"] - dps[0]) for r in ranking)
    low, high = out["brackets"]
    # niveau 15 : Skyborne (+5,1) et Troll (+5) sous le seuil de bruit, Orc (+3) nettement derrière
    assert [r["race"] for r in low["ranking"][:3]] == ["RaceHighOrderSkyborne", "RaceTroll", "RaceOrc"]
    assert low["ranking"][0]["verdict"] == "non départagé" and low["ranking"][1]["verdict"] == "non départagé"
    assert low["ranking"][2]["verdict"] == "derrière" and low["decided"] is False
    assert low["ranking"][1]["threshold"] > 0
    # niveau 60 : ordre inversé, Undead seule devant (+2, rien sous le seuil)
    assert high["ranking"][0]["race"] == "RaceUndead" and high["ranking"][0]["verdict"] == "meilleure"
    assert high["best"] == "RaceUndead" and high["decided"] is True
    assert all(r["verdict"] == "derrière" for r in high["ranking"][1:])
    # mêmes talents, même équipement, même graine pour toutes les races d'une tranche
    by_level = {}
    for req in sim.requests:
        player = req["raid"]["parties"][0]["players"][0]
        level = req["encounter"]["targets"][0]["level"]
        key = (player["talentsString"], json.dumps(player["equipment"]), req["simOptions"]["randomSeed"])
        by_level.setdefault(level, set()).add(key)
    assert set(by_level) == {15, 60} and all(len(keys) == 1 for keys in by_level.values())
    assert len(sim.requests) == 2 * len(races)
    prov = out["provenance"]
    validate_provenance(prov)
    assert prov["certainty"] == "suppose"
    text = " ".join(prov["assumptions"])
    assert "races.json" in text and "même graine" in text and "correctifs forever" in text


def test_a_subset_of_races_can_be_asked_and_an_unplayable_one_is_refused(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    sim = RaceLevelSim()
    out = compare_races_brackets(deps, preset="mage/dps/Fire", brackets="20-29", races=["Human", "Gnome"],
                                 steps=[], picks_at=None, iterations=100, runner=sim)  # fmt: skip
    assert [r["race"] for r in out["brackets"][0]["ranking"]] == ["RaceHuman", "RaceGnome"]
    assert sim.levels == [25, 25]
    with pytest.raises(InvalidArgumentError, match="Tauren"):
        compare_races_brackets(deps, preset="mage/dps/Fire", brackets="25", races=["Tauren"], steps=[],
                               picks_at=None, runner=RaceLevelSim())  # fmt: skip
    with pytest.raises(InvalidArgumentError, match="Préréglage"):
        compare_races_brackets(deps, preset="mage/dps/Nope", brackets="25", steps=[], picks_at=None,
                               runner=RaceLevelSim())  # fmt: skip


def test_an_illegal_bracket_is_reported_once_without_any_fight(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    steps = [{"level": 10, "key": "improvedFrostbolt", "rank": 5}, {"level": 11, "key": "iceShards", "rank": 5}]
    sim = RaceLevelSim()
    out = compare_races_brackets(deps, preset="mage/dps/Fire", brackets="10-19,20-29", races=["Human", "Orc"],
                                 steps=steps, picks_at=None, iterations=100, runner=sim)  # fmt: skip
    low, high = out["brackets"]
    assert low["ranking"] == [] and low["error"]["code"] == "invalid_argument" and "15" in low["error"]["message"]
    assert [r["race"] for r in high["ranking"]] == ["RaceOrc", "RaceHuman"] and set(sim.levels) == {25}


def test_simulate_cli_and_mcp_action(make_deps, tmp_path, monkeypatch, capsys):
    from forever.pipeline import gitops
    from forever.sims.report import ACTIONS

    deps = brackets_setup(make_deps, tmp_path)
    monkeypatch.setattr(gitops, "subprocess_runner", RaceLevelSim())
    assert "race_brackets" in ACTIONS
    out = simulate(deps, "race_brackets", preset="mage/dps/Fire", brackets="25", path="none", gear="none",
                   iterations=100)  # fmt: skip
    assert {r["race"] for r in out["brackets"][0]["ranking"]} == _mage_races(deps)
    assert out["brackets"][0]["best"] == "RaceHighOrderSkyborne"
    assert any("talents : aucun" in a for a in out["provenance"]["assumptions"])
    sub = simulate(deps, "race_brackets", preset="mage/dps/Fire", brackets="25", races="Human,Gnome", path="none",
                   gear="none", iterations=100)  # fmt: skip
    assert [r["race"] for r in sub["brackets"][0]["ranking"]] == ["RaceHuman", "RaceGnome"]
    with pytest.raises(InvalidArgumentError, match="Préréglage"):
        simulate(deps, "race_brackets", brackets="25", path="none", gear="none")
    argv = ["sims", "races-brackets", "--preset", "mage/dps/Fire", "--brackets", "25", "--path", "none", "--gear",
            "none", "--iterations", "100"]  # fmt: skip
    assert main([*argv, "--json"], deps) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["brackets"][0]["ranking"][0]["race"] == "RaceHighOrderSkyborne"
    assert main(argv, deps) == 0
    text = capsys.readouterr().out
    assert "niveau 25" in text and "HighOrderSkyborne" in text and "non départagé" in text


def test_mcp_tool_documents_the_action():
    import inspect

    from forever import mcp_server

    assert "race_brackets" in inspect.getsource(mcp_server)
