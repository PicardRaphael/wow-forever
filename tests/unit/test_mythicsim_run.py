"""MythicSim, second simulateur au niveau 60 (MS1, décision 301) : adaptateur mince du binaire épinglé
`forever-engine sim --request … --outfile … --gate` (même `RaidSimRequest` que wowsims).

- requête écrite : un joueur, rotation, options et buffs du fork Go épinglé de MythicSim (jamais ceux du wowsims
  actuel, que son proto refuse), équipement, talents, race et rencontre du cas ;
- sortie lue : dégâts par seconde (moyenne, écart type), combats, identité (la version du client de l'identité est
  celle du contrat, jamais présentée comme la version simulée) ;
- refus rendu tel quel (code 5 de la préparation, code 3 de la porte) : erreur `mythicsim_refused` avec le code et la
  raison du moteur, jamais remplacé par wowsims.

Clone, binaire et exécuteur fabriqués (`tests/mythicsim_fakes.py`) ; aucun réseau, aucun calcul de jeu."""

import pytest
from mythicsim_fakes import GO_REVISION, Engine, install
from wowsims_fakes import ENCOUNTER, clone

from forever.sims import mythicsim
from forever.sims.wowsims import read_presets


def _case(tmp_path):
    root = clone(tmp_path)
    install(tmp_path)
    return next(p for p in read_presets(root / "forever") if p.key == "mage/dps/Fire")


def test_request_takes_the_fork_rotation_and_the_case_gear(tmp_path):
    case = _case(tmp_path)
    preset = mythicsim.preset_for(tmp_path, case, talents="-5", tree_names=["Arcane", "Fire", "Frost"])
    req = mythicsim.request_for(preset, race="RaceGnome", encounter=ENCOUNTER, iterations=300, seed=9)
    player = req["raid"]["parties"][0]["players"][0]
    assert player["talentsString"] == "-5" and player["equipment"] == case.equipment
    assert player["rotation"]["priorityList"][0]["action"]["castSpell"]["spellId"]["otherId"] == "fire"  # arbre Fire
    assert player["mage"]["options"]["classOptions"]["defaultMageArmor"] == "MageArmorMageArmor"  # options du fork
    assert req["simOptions"] == {"iterations": 300, "randomSeed": 9} and req["encounter"] == ENCOUNTER


def test_rotation_can_be_chosen_and_unknown_one_is_refused(tmp_path):
    case = _case(tmp_path)
    preset = mythicsim.preset_for(tmp_path, case, talents="-5", tree_names=None, rotation="Arcane")
    assert preset.rotation["priorityList"][0]["action"]["castSpell"]["spellId"]["otherId"] == "arcane"
    with pytest.raises(mythicsim.MythicsimError, match="Arcane, Fire"):
        mythicsim.preset_for(tmp_path, case, talents="-5", tree_names=None, rotation="Frost")


def test_run_reads_the_result_and_the_identity(tmp_path):
    case = _case(tmp_path)
    preset = mythicsim.preset_for(tmp_path, case, talents="-5", tree_names=["Arcane", "Fire", "Frost"])
    engine = Engine()
    out = mythicsim.run_sim(tmp_path, mythicsim.request_for(preset, race="RaceGnome", encounter=ENCOUNTER),
                            runner=engine)  # fmt: skip
    assert out["dps"] == 200.0 and out["stdev"] == 20.0 and out["iterations"] > 0
    call = engine.calls[0]
    assert call[1] == "sim" and "--request" in call and "--outfile" in call and "--gate" in call
    assert "--go-rules" not in call  # règles de Forever, jamais celles de la référence Go
    src = out["source"]
    assert src["simulator"] == "MythicSim" and src["commit"] == "b" * 40 and src["certainty"] == "suppose"
    assert src["go_reference_revision"] == GO_REVISION and src["contract_client_build"] == "1.60.1.70425"
    assert "game_version" not in src and "client_build" not in src


def test_preparation_refusal_is_returned_as_is(tmp_path):
    case = _case(tmp_path)
    preset = mythicsim.preset_for(tmp_path, case, talents="-5", tree_names=["Arcane", "Fire", "Frost"])
    engine = Engine(refuse=("talents", 'mage talents "-9": Incineration has 5 ranks'))
    with pytest.raises(mythicsim.MythicsimError) as err:
        mythicsim.run_sim(tmp_path, mythicsim.request_for(preset, race="RaceGnome", encounter=ENCOUNTER),
                          runner=engine)  # fmt: skip
    assert err.value.code == "mythicsim_refused"
    assert "talents" in err.value.message and "Incineration has 5 ranks" in err.value.message


def test_gate_refusal_is_returned_as_is(tmp_path):
    case = _case(tmp_path)
    preset = mythicsim.preset_for(tmp_path, case, talents="-5", tree_names=["Arcane", "Fire", "Frost"])
    with pytest.raises(mythicsim.MythicsimError) as err:
        mythicsim.run_sim(tmp_path, mythicsim.request_for(preset, race="RaceGnome", encounter=ENCOUNTER),
                          runner=Engine(gate="unsupported trinket 19959"))  # fmt: skip
    assert err.value.code == "mythicsim_refused" and "unsupported trinket 19959" in err.value.message


def test_changed_binary_and_missing_pin(tmp_path):
    case = _case(tmp_path)
    preset = mythicsim.preset_for(tmp_path, case, talents="-5", tree_names=["Arcane", "Fire", "Frost"])
    req = mythicsim.request_for(preset, race="RaceGnome", encounter=ENCOUNTER)
    (tmp_path / "third_party" / "mythicsim" / "forever-engine-bbbbbbbbbbbb.exe").write_bytes(b"autre")
    with pytest.raises(mythicsim.MythicsimError, match="empreinte"):
        mythicsim.run_sim(tmp_path, req, runner=Engine())
    with pytest.raises(mythicsim.MythicsimError, match="forever sims update"):
        mythicsim.run_sim(tmp_path / "vide", req, runner=Engine())
