"""SIM2 bloc 3 : dégâts par tranche de niveaux, calculés par wowsims/forever corrigé (décision 305), Mage d'abord.

Pour chaque tranche (10-19, 20-29, 30-39, 40-49, 50-59 et 60 ; un niveau représentatif chacune : 15, 25, 35, 45, 55,
60 ; ou un niveau donné), un combat au niveau L :
- talents : le parcours dans l'ordre (étapes « niveau, clé, rang ») tronqué au niveau L, contrôlé légal au niveau L ;
- équipement : choix par emplacement (GearQuest) placés dans l'ordre `ItemSlot` de wowsims, ou nu ;
- solo : aucun buff, affaiblissement ni consommable ; cible du niveau L ;
- binaire lancé avec `--forever-level=L` ; chaque ligne garde sa source.

Dépôt, proto des talents (`tests/fixtures/sims/wowsims-64b21da`) et simulateur fabriqués : aucun calcul de jeu ici."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import FIXTURES
from wowsims_fakes import ENCOUNTER, Sim, clone

from forever.errors import ForeverError, InvalidArgumentError
from forever.sims.brackets import (
    BRACKETS,
    SLOT_NAMES,
    encounter_at,
    equipment_from_picks,
    parse_brackets,
    run_brackets,
    solo_preset,
    talents_at,
)
from forever.sims.wowsims import read_presets, request_for

# Parcours de Givre fabriqué : Improved Frostbolt 1 à 5 aux niveaux 10 à 14, Ice Shards 1 à 5 aux niveaux 15 à 19.
FROST_STEPS = [{"level": 9 + r, "key": "improvedFrostbolt", "rank": r} for r in range(1, 6)] + [
    {"level": 14 + r, "key": "iceShards", "rank": r} for r in range(1, 6)
]


def test_brackets_are_the_six_asked_with_one_level_each():
    assert BRACKETS == {"10-19": 15, "20-29": 25, "30-39": 35, "40-49": 45, "50-59": 55, "60": 60}
    assert parse_brackets(None) == list(BRACKETS.items())
    assert parse_brackets("all") == list(BRACKETS.items())
    assert parse_brackets("20-29, 60") == [("20-29", 25), ("60", 60)]
    assert parse_brackets("22") == [("22", 22)]
    for bad in ("abc", "0", "61", "15-25"):
        with pytest.raises(InvalidArgumentError):
            parse_brackets(bad)


def test_talents_follow_the_path_up_to_the_level():
    assert talents_at(FROST_STEPS, 9) == {}
    assert talents_at(FROST_STEPS, 12) == {"improvedFrostbolt": 3}
    assert talents_at(FROST_STEPS, 15) == {"improvedFrostbolt": 5, "iceShards": 1}
    assert talents_at(FROST_STEPS, 25) == {"improvedFrostbolt": 5, "iceShards": 5}


def test_gear_picks_fill_the_wowsims_slot_order():
    assert SLOT_NAMES[:5] == ("Head", "Neck", "Shoulder", "Back", "Chest") and len(SLOT_NAMES) == 17
    picks = [
        {"slot": "Back", "item": 6614},
        {"slot": "Finger", "item": 11},
        {"slot": "Finger", "item": 12},
        {"slot": "Trinket", "item": 21},
        {"slot": "MainHand", "item": 31},
        {"slot": "SecondaryHand", "item": 32},
    ]
    items = equipment_from_picks(picks)["items"]
    assert len(items) == 17
    assert items[3] == {"id": 6614} and items[10] == {"id": 11} and items[11] == {"id": 12}
    assert items[12] == {"id": 21} and items[13] == {} and items[14] == {"id": 31} and items[15] == {"id": 32}
    assert items[0] == {} and equipment_from_picks([])["items"] == [{}] * 17
    with pytest.raises(ForeverError, match="Tabard"):
        equipment_from_picks([{"slot": "Tabard", "item": 1}])


def test_solo_case_has_no_buffs_debuffs_or_consumables_and_a_target_of_the_level(tmp_path):
    root = clone(tmp_path)
    fire = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    solo = solo_preset(fire, talents="--0501", equipment={"items": [{}] * 17})
    req = request_for(solo, race="RaceHuman", encounter=encounter_at(ENCOUNTER, 25))
    player = req["raid"]["parties"][0]["players"][0]
    assert player["talentsString"] == "--0501" and player["equipment"] == {"items": [{}] * 17}
    assert "buffs" not in player and "consumables" not in player
    assert "buffs" not in req["raid"] and "debuffs" not in req["raid"] and not req["raid"]["parties"][0]["buffs"]
    target = req["encounter"]["targets"][0]
    assert target["level"] == 25 and target["canCrush"] is False
    assert ENCOUNTER["targets"][0]["level"] != 25  # rencontre d'origine intacte


class LevelSim(Sim):
    """wowsimcli simulé : garde le niveau passé et la requête ; dégâts fabriqués égaux au niveau."""

    def __init__(self):
        super().__init__()
        self.levels = []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        flag = next((a for a in args if a.startswith("--forever-level=")), None)
        level = int(flag.split("=")[1]) if flag else 60
        self.levels.append(level)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": float(level), "stdev": 1.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def _setup(make_deps, tmp_path):
    deps = make_deps()
    root = clone(deps.cache_dir)
    proto = root / "forever" / "proto"
    proto.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "sims" / "wowsims-64b21da" / "proto" / "mage.proto", proto / "mage.proto")
    doc = json.loads((root / "pin.json").read_text(encoding="utf-8"))
    doc["patches"] = {"sha256": "c" * 64, "files": ["0001-level.patch", "0002-ranks.patch"]}
    (root / "pin.json").write_text(json.dumps(doc), encoding="utf-8")
    return deps


def test_each_bracket_is_simulated_at_its_level_with_its_talents_and_gear(make_deps, tmp_path):
    deps = _setup(make_deps, tmp_path)
    sim = LevelSim()
    picks = {15: [{"slot": "Back", "item": 6614}], 25: [{"slot": "Chest", "item": 2800}]}
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="10-19,20-29", steps=FROST_STEPS,
                       picks_at=lambda level: picks[level], iterations=100, runner=sim)  # fmt: skip
    assert sim.levels == [15, 25]
    rows = out["rows"]
    assert [(r["bracket"], r["level"], r["dps"]) for r in rows] == [("10-19", 15, 15.0), ("20-29", 25, 25.0)]
    assert rows[0]["talents"] == {"improvedFrostbolt": 5, "iceShards": 1}
    first = sim.requests[0]["raid"]["parties"][0]["players"][0]
    assert first["talentsString"] == "--0501" and first["equipment"]["items"][3] == {"id": 6614}
    assert sim.requests[1]["raid"]["parties"][0]["players"][0]["equipment"]["items"][4] == {"id": 2800}
    assert sim.requests[0]["encounter"]["targets"][0]["level"] == 15
    assert rows[1]["source"]["level"] == 25 and rows[1]["source"]["patches"] == "c" * 64
    prov = out["provenance"]
    assert prov["certainty"] == "suppose"
    text = " ".join(prov["assumptions"])
    assert "correctifs forever" in text and "attributs de base" in text and "solo" in text


def test_naked_and_without_talents_is_allowed(make_deps, tmp_path):
    deps = _setup(make_deps, tmp_path)
    sim = LevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="60", steps=[], picks_at=None,
                       iterations=100, runner=sim)  # fmt: skip
    player = sim.requests[0]["raid"]["parties"][0]["players"][0]
    assert player["equipment"] == {"items": [{}] * 17} and player["talentsString"] == ""
    assert out["rows"][0]["level"] == 60 and out["rows"][0]["equipment"] == "nu"


def test_a_path_with_too_many_points_for_the_level_is_refused_in_its_row(make_deps, tmp_path):
    deps = _setup(make_deps, tmp_path)
    # dix points pris dès le niveau 11 : illégal au niveau 15 (six points), légal au niveau 25 (seize points)
    steps = [{"level": 10, "key": "improvedFrostbolt", "rank": 5}, {"level": 11, "key": "iceShards", "rank": 5}]
    sim = LevelSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="10-19,20-29", steps=steps,
                       picks_at=None, iterations=100, runner=sim)  # fmt: skip
    assert out["rows"][0]["error"]["code"] == "invalid_argument" and "15" in out["rows"][0]["error"]["message"]
    assert out["rows"][1]["dps"] == 25.0 and sim.levels == [25]
    sim = LevelSim()
    bad = [{"level": 10, "key": "iceShards", "rank": 1}]  # palier 2 sans les cinq points du palier 1
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="10-19", steps=bad, picks_at=None,
                       iterations=100, runner=sim)  # fmt: skip
    assert out["rows"][0]["error"]["code"] == "invalid_argument" and "15" in out["rows"][0]["error"]["message"]
    assert sim.levels == []  # aucun combat lancé pour un build illégal


def test_unknown_preset_or_missing_race_is_refused(make_deps, tmp_path):
    deps = _setup(make_deps, tmp_path)
    with pytest.raises(InvalidArgumentError, match="Préréglage"):
        run_brackets(deps, preset="mage/dps/Nope", race="Human", brackets="60", steps=[], picks_at=None,
                     runner=LevelSim())  # fmt: skip
    with pytest.raises(InvalidArgumentError, match="Race"):
        run_brackets(deps, preset="mage/dps/Fire", race=None, brackets="60", steps=[], picks_at=None,
                     runner=LevelSim())  # fmt: skip
