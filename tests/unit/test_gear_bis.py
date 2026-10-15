"""CJ1, bloc 4 (décision 276) : liste BiS personnelle. Candidats de Naowh Forever puis de Forever Companion pour chaque
emplacement (bagues et bijoux sur deux emplacements), classés par les poids donnés (nos poids pour le Mage, l'échelle
de Forever Companion pour les autres classes) sur les statistiques de Forever Guide ; un objet sans statistiques
connues garde le rang de l'addon, après les objets chiffrés ; lieu de butin de Naowh joint ; export `!NBIS1!`.

Valeurs : addons fabriqués `tests/fixtures/addons/gear/` ; poids fabriqués ici. Aucun chiffre de jeu ici."""

import shutil

from conftest import FIXTURES

from forever.exports.naowh import read_naowh_bis as decode_nbis
from forever.gear import companion_weights, personal_bis

ADDONS = FIXTURES / "addons" / "gear"
WEIGHTS = {"int": 1.0, "sp": 2.0, "scrit": 20.0, "shit": 30.0}  # clés de Forever Guide


def test_best_item_per_slot_by_weights():
    bis = personal_bis(ADDONS, spec_key="fire-mage", weights=WEIGHTS, name="Forever · Bob · Feu")
    assert bis["slots"][1] == 900001  # 10 Int + 6 SP×2 bat 12 Int
    assert bis["slots"][11] == 900003 and bis["slots"][12] == 900004  # deux bagues distinctes
    assert bis["slots"][13] == 900005 and 14 not in bis["slots"]
    assert 900007 in bis["extra"][11]  # stats inconnues : gardé en repli, après les objets chiffrés


def test_items_carry_score_source_and_origin():
    bis = personal_bis(ADDONS, spec_key="fire-mage", weights=WEIGHTS, name="n")
    head = next(i for i in bis["items"] if i["slot"] == 1)
    assert head["item"] == 900001 and head["score"] > 0 and head["source"].startswith("Boss Fixture")
    assert set(head["lists"]) == {"Naowh Forever", "Forever Companion"}
    unknown = next(i for i in bis["items"] if i["item"] == 900007)
    assert unknown["score"] is None


def test_export_reads_back():
    bis = personal_bis(ADDONS, spec_key="fire-mage", weights=WEIGHTS, name="Forever · Bob · Feu")
    decoded = decode_nbis(bis["export"])
    assert decoded.spec == "fire-mage" and decoded.slots == bis["slots"]


def test_companion_scale_weights_for_other_classes():
    weights = companion_weights(ADDONS, "WARRIOR")
    assert weights == {"str": 2.0, "sta": 1.0}
    bis = personal_bis(ADDONS, spec_key="fury-warrior", weights=weights, name="n")
    assert bis["slots"][5] == 900006


def test_unknown_spec_has_no_list():
    bis = personal_bis(ADDONS, spec_key="arcane-mage", weights=WEIGHTS, name="n")
    assert bis["slots"] == {} and bis["export"] is None


def test_items_of_the_other_faction_are_left_out():
    # 900003 : « Quest (Alliance) » chez Naowh (fixture) : écarté pour la Horde, gardé pour l'Alliance
    horde = personal_bis(ADDONS, spec_key="fire-mage", weights=WEIGHTS, name="n", faction="horde")
    assert 900003 not in horde["slots"].values() and all(i["item"] != 900003 for i in horde["items"])
    alliance = personal_bis(ADDONS, spec_key="fire-mage", weights=WEIGHTS, name="n", faction="alliance")
    assert alliance["slots"][11] == 900003


def _camp_fixture(tmp_path):
    """Copie de la fixture : origines de GearQuest (900001 récompense de quête, 900002 marchand) et 900008, fabriqué,
    choisi pour l'Alliance seulement et candidat de Naowh (emplacement 13)."""
    addons = tmp_path / "gear"
    shutil.copytree(ADDONS, addons)
    data = addons / "GearQuestForever_MAGE" / "Data.Mage.generated.lua"
    text = data.read_text(encoding="utf-8").replace('sourceType="quest"', 'sourceType="quest_reward"')
    facts = '\n    [900002]={name="Fixture Cap",quality=2,sourceType="vendor"},'
    facts += '\n    [900008]={name="Fixture Charm",quality=3,sourceType="profession"},'
    text = text.replace("GQ.Data.mageItemFacts = {", "GQ.Data.mageItemFacts = {" + facts)
    pick = '\n    {900008,"Trinket",20,25,1,"fire","Alliance",1.0},'
    text = text.replace("GQ.Data.magePicks = {", "GQ.Data.magePicks = {" + pick)
    data.write_text(text, encoding="utf-8")
    bis = addons / "NaowhForever_BiS" / "BiS" / "Data" / "BiS.lua"
    bis.write_text(bis.read_text(encoding="utf-8").replace("[13] = { 900005 }", "[13] = { 900005, 900008 }"), "utf-8")
    return addons


def test_items_listed_only_for_the_other_faction_by_gearquest_are_left_out(tmp_path):
    # GearQuest tient une liste de choix par camp ; un objet choisi pour l'Alliance seulement est écarté pour la Horde
    # quand son origine dépend du camp (récompense de quête, marchand : 900001, 900002), gardé sinon (900008 :
    # fabriqué) ; la mention de Naowh prime (900003 : « (Alliance) » chez Naowh, choix Horde chez GearQuest)
    addons = _camp_fixture(tmp_path)
    horde = personal_bis(addons, spec_key="fire-mage", weights=WEIGHTS, name="n", faction="horde")
    assert not {900001, 900002} & set(horde["slots"].values())
    assert any(i["item"] == 900008 for i in horde["items"])
    alliance = personal_bis(addons, spec_key="fire-mage", weights=WEIGHTS, name="n", faction="alliance")
    assert alliance["slots"][1] in {900001, 900002} and alliance["slots"][11] == 900003
