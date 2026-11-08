"""SIM2 : familiers au niveau du personnage dans wowsims corrigé (correctif 0006-pets, décision 305).

- Les familiers de wowsims (Chasseur, faucons, démons) tirent PV, armure, puissance d'attaque et dégâts des valeurs de
  créature du client (`ExpectedStat`) au niveau 60. Le correctif les lit dans le fichier donné par
  `--forever-pet-stats=<fichier>` ; sans l'option, les valeurs du 60 restent. Il ne porte aucune valeur de jeu.
- Les valeurs par niveau viennent du client : `forever decode` les range dans `character_scaling.json` (bloc
  `creature`, colonnes CreatureHealth, CreatureArmor, CreatureAutoAttackDps d'ExpectedStat).
- forever ne passe le fichier que sous le niveau 60, si l'épinglage porte le correctif et si les données ont le bloc
  `creature` ; sinon les familiers gardent les valeurs du 60 et la ligne le dit.

Valeurs attendues lues dans les fixtures du client (`tests/fixtures/wago/1.60.1.70124/`) ou arbitraires (fichier de
passage) ; simulateur fabriqué."""

import csv
import json
from pathlib import Path

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, WAGO_70124, read_json
from test_sims_base_stats import FileSim, _pin
from test_sims_brackets import FROST_STEPS
from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import ENCOUNTER, clone

from forever.pipeline.character_scaling import decode_character_scaling, load_character_tables, load_gametables
from forever.pipeline.wowsims_build import PATCHES_DIR
from forever.sims.base_stats import PETS_PATCH, base_stats_doc, client_pet_stats, pet_stats_at
from forever.sims.brackets import run_brackets
from forever.sims.wowsims import WowsimsError, read_presets, request_for, run_sim

RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
CAP = RULES["levels"]["level_cap"]
ALL_PATCHES = ["0001-level.patch", "0002-ranks.patch", "0003-base-stats.patch", "0006-pets.patch"]
PETS = {"creature_health": 1.5, "creature_armor": 2.5, "creature_auto_attack_dps": 3.5}  # arbitraires


def test_repository_patch_reads_creature_values_from_a_file():
    text = (PATCHES_DIR / PETS_PATCH).read_text(encoding="utf-8")
    assert "--forever-pet-stats=" in text and "forever (SIM2)" in text
    touched = {line.split(" b/", 1)[1] for line in text.splitlines() if line.startswith("diff --git ")}
    assert {"sim/core/forever_pet_stats.go", "sim/hunter/pets.go", "sim/hunter/summon_hawk.go",
            "sim/warlock/pets.go", "cmd/wowsimcli/cmd/basic_sim.go"} <= touched  # fmt: skip
    assert "sim/core/base_stats_auto_gen.go" not in touched  # fichier généré par wowsims, laissé tel quel
    for key in ("creature_health", "creature_armor", "creature_auto_attack_dps"):
        assert f'json:"{key}"' in text


def test_creature_values_are_decoded_per_level_from_expected_stat():
    tables = load_character_tables(WAGO_70124, RULES)
    doc = decode_character_scaling(tables, RULES, load_gametables(WAGO_70124 / "gametables", RULES), LOCAL_VERSION)
    with (WAGO_70124 / "enUS" / "ExpectedStat.csv").open(encoding="utf-8", newline="") as f:
        rows = {int(r["Lvl"]): r for r in csv.DictReader(f) if r["ExpansionID"] == "-2" and r["ContentSetID"] == "0"}
    creature = doc["creature"]
    for key, column in (("health", "CreatureHealth"), ("armor", "CreatureArmor"),
                        ("auto_attack_dps", "CreatureAutoAttackDps")):  # fmt: skip
        assert creature[key] == [float(rows[lv][column]) for lv in range(1, CAP + 1)], key


def test_pet_stats_at_a_level_or_none_without_the_data():
    scaling = {"creature": {"health": [10.0, 20.0], "armor": [1.0, 2.0], "auto_attack_dps": [0.5, 0.75]}}
    assert pet_stats_at(scaling, 2) == {"creature_health": 20.0, "creature_armor": 2.0,
                                        "creature_auto_attack_dps": 0.75}  # fmt: skip
    assert pet_stats_at({}, 2) is None  # données d'avant le bloc creature : rien d'inventé


def test_client_pet_stats_read_the_installed_data(make_deps):
    scaling = read_json(DATA_DIR / LOCAL_VERSION / "character_scaling.json")
    assert client_pet_stats(make_deps(), 25) == pet_stats_at(scaling, 25)


def test_pet_stats_file_is_passed_apart_then_removed(tmp_path):
    root = clone(tmp_path)
    _pin(root, ALL_PATCHES)
    fire = next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")
    doc = base_stats_doc("ClassMage", {"mana": 1.0}, [], pets=PETS)
    sim = PetSim()
    out = run_sim(tmp_path, request_for(fire, race="RaceHuman", encounter=ENCOUNTER), runner=sim, level=25,
                  base_stats=doc)  # fmt: skip
    assert sim.pets == [PETS] and "pets" not in sim.base_stats[0] and out["source"]["pet_stats"] is True
    path = next(a for a in sim.args[0] if a.startswith("--forever-pet-stats=")).split("=", 1)[1]
    assert not Path(path).exists()  # fichier de passage retiré
    _pin(root, ALL_PATCHES[:3])
    with pytest.raises(WowsimsError, match="0006-pets"):
        run_sim(tmp_path, request_for(fire, race="RaceHuman", encounter=ENCOUNTER), runner=PetSim(), level=25,
                base_stats=doc)  # fmt: skip


def test_brackets_say_pets_keep_level_60_values_without_client_data(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    _pin(deps.cache_dir / "third_party" / "wowsims", ALL_PATCHES)
    sim = PetSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="20-29", steps=FROST_STEPS,
                       picks_at=None, iterations=10, runner=sim)  # fmt: skip
    expected = client_pet_stats(deps, 25)
    assert sim.pets == [expected]
    note = out["rows"][0]["pets"]
    assert ("niveau 60" in note) == (expected is None)


class PetSim(FileSim):
    """wowsimcli simulé : lit aussi le fichier des valeurs de créature pendant le lancement."""

    def __init__(self):
        super().__init__()
        self.pets = []

    def __call__(self, args, cwd, timeout=None):
        flag = next((a for a in args if a.startswith("--forever-pet-stats=")), None)
        self.pets.append(json.loads(Path(flag.split("=", 1)[1]).read_text(encoding="utf-8")) if flag else None)
        return super().__call__(args, cwd, timeout)
