"""SIM2 : arme compatible avec la rotation du préréglage (diagnostic du 2026-11-08 : l'Assassinat recevait de GearQuest
une hache ou une épée alors que le préréglage de wowsims porte des dagues ; il ne frappait plus qu'en coups blancs).

Aucune règle de jeu codée : quand le type d'arme (`weaponType` de la base des simulateurs) de l'arme proposée diffère
de celui de l'arme du préréglage, la meilleure arme du même type que le préréglage, prise dans la réserve de candidats
au niveau, est essayée par simulation (même graine), main droite puis main gauche ; l'ensemble qui fait le plus de
dégâts est gardé, le choix et l'écart sont dits dans la ligne ; sans arme du bon type au niveau, la ligne le dit.

Préréglage, base d'objets, réserve et simulateur fabriqués (identifiants et dégâts inventés) : aucune valeur de jeu."""

import json
import subprocess
from pathlib import Path

from test_sims_brackets import _setup as brackets_setup
from wowsims_fakes import Sim

from forever.sims.brackets import run_brackets

# Base fabriquée : type 13 = arme, handType 2 = une main, 3 = main gauche ; weaponType 1 = hache, 2 = dague, 9 = épée
# (numéros de l'énumération du proto fabriqué ci-dessous).
DB = [
    {"id": 500, "type": 13, "handType": 2, "weaponType": 2, "reqLvl": 55},  # dague du préréglage (main droite)
    {"id": 501, "type": 13, "handType": 2, "weaponType": 2, "reqLvl": 55},  # dague du préréglage (main gauche)
    {"id": 600, "type": 13, "handType": 2, "weaponType": 1, "reqLvl": 20},  # hache proposée
    {"id": 603, "type": 13, "handType": 2, "weaponType": 9, "reqLvl": 20},  # épée proposée en main gauche
    {"id": 601, "type": 13, "handType": 2, "weaponType": 2, "reqLvl": 20},  # dague au niveau
    {"id": 602, "type": 13, "handType": 2, "weaponType": 2, "reqLvl": 22},  # dague au niveau
    {"id": 604, "type": 13, "handType": 2, "weaponType": 2, "reqLvl": 50},  # dague trop haute pour le niveau 25
    {"id": 700, "type": 5, "reqLvl": 20},  # torse
]
PROTO = (
    "enum WeaponType {\n\tWeaponTypeUnknown = 0;\n\tWeaponTypeAxe = 1;\n\tWeaponTypeDagger = 2;\n"
    "\tWeaponTypeSword = 9;\n}\n"
)
MAIN = {600: 50.0, 601: 120.0, 602: 130.0, 604: 500.0}  # dégâts fabriqués selon la main droite
OFF = {603: 5.0, 601: 10.0, 602: 8.0, 604: 50.0}  # bonus fabriqué selon la main gauche


class WeaponSim(Sim):
    """Dégâts fabriqués selon les armes portées (main droite + main gauche)."""

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        req = json.loads(Path(args[args.index("--infile") + 1]).read_text(encoding="utf-8"))
        self.requests.append(req)
        items = req["raid"]["parties"][0]["players"][0]["equipment"]["items"]
        mh, oh = (items[i].get("id") if len(items) > i else None for i in (14, 15))
        dps = MAIN.get(mh, 0.0) + OFF.get(oh, 0.0)
        res = {"raidMetrics": {"parties": [{"players": [{"dps": {"avg": dps, "stdev": 1.0}}]}]},
               "iterationsDone": req["simOptions"]["iterations"]}  # fmt: skip
        Path(args[args.index("--outfile") + 1]).write_text(json.dumps(res), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def _setup(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    forever = deps.cache_dir / "third_party" / "wowsims" / "forever"
    gear = [{} for _ in range(17)]
    gear[14], gear[15] = {"id": 500}, {"id": 501}
    (forever / "ui" / "specs" / "mage" / "dps" / "gear_sets" / "p1.gear.json").write_text(
        json.dumps({"items": gear}), encoding="utf-8"
    )
    (forever / "proto" / "common.proto").write_text(PROTO, encoding="utf-8")
    database = forever / "assets" / "database"
    database.mkdir(parents=True, exist_ok=True)
    (database / "db.json").write_text(json.dumps({"items": DB}), encoding="utf-8")
    (database / "leftover_db.json").write_text(json.dumps({"items": []}), encoding="utf-8")
    return deps


PICKS = [{"slot": "Chest", "item": 700}, {"slot": "MainHand", "item": 600}, {"slot": "SecondaryHand", "item": 603}]
POOL = [{"item": i, "slot": "MainHand"} for i in (600, 601, 602, 603, 604)] + [{"item": 700, "slot": "Chest"}]


def _run(deps, pool, picks=PICKS):
    sim = WeaponSim()
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="25", steps=[],
                       picks_at=lambda _level: picks, candidates_at=lambda _level: pool, iterations=10,
                       runner=sim)  # fmt: skip
    return out, sim


def test_weapons_of_the_preset_type_are_tried_and_the_best_set_is_kept(make_deps, tmp_path):
    out, _ = _run(_setup(make_deps, tmp_path), POOL)
    row = out["rows"][0]
    # main droite : meilleure dague au niveau (602 ; 604 exige le niveau 50) ; main gauche : meilleure autre dague
    assert row["dps"] == 140.0 and row["equipment"] == [700, 602, 601]
    weapon = row["weapon"]
    assert weapon["choice"] == "type du préréglage"
    assert weapon["reference_type"] == {"MainHand": "Dagger", "OffHand": "Dagger"}
    assert weapon["proposed"] == {"MainHand": 600, "OffHand": 603} and weapon["proposed_dps"] == 55.0
    assert weapon["chosen"] == {"MainHand": 602, "OffHand": 601} and weapon["chosen_dps"] == 140.0
    assert weapon["delta"] == 85.0
    assert any("type d'arme" in a for a in out["provenance"]["assumptions"])


def test_without_a_weapon_of_the_preset_type_at_the_level_the_row_says_so(make_deps, tmp_path):
    pool = [{"item": i, "slot": "MainHand"} for i in (600, 603, 604)]
    out, _ = _run(_setup(make_deps, tmp_path), pool)
    row = out["rows"][0]
    assert row["dps"] == 55.0 and row["equipment"] == [700, 600, 603]
    weapon = row["weapon"]
    assert weapon["choice"] == "proposée"
    assert "Dagger" in weapon["note"] and "25" in weapon["note"]


def test_same_weapon_type_as_the_preset_runs_no_extra_trial(make_deps, tmp_path):
    picks = [{"slot": "MainHand", "item": 601}, {"slot": "SecondaryHand", "item": 602}]
    out, sim = _run(_setup(make_deps, tmp_path), POOL, picks=picks)
    assert "weapon" not in out["rows"][0] and len(sim.requests) == 1
