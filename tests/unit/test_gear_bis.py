"""CJ1, bloc 4 (décision 276) : liste BiS personnelle. Candidats de Naowh Forever puis de Forever Companion pour chaque
emplacement (bagues et bijoux sur deux emplacements), classés par les poids donnés (nos poids pour le Mage, l'échelle
de Forever Companion pour les autres classes) sur les statistiques de Forever Guide ; un objet sans statistiques
connues garde le rang de l'addon, après les objets chiffrés ; lieu de butin de Naowh joint ; export `!NBIS1!`.

Valeurs : addons fabriqués `tests/fixtures/addons/gear/` ; poids fabriqués ici. Aucun chiffre de jeu ici."""

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
