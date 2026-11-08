"""SIM2 bloc 10 : réserve de candidats de l'optimisation d'équipement, réunie depuis toutes les sources installées
(choix de GearQuest au niveau, listes BiS de Naowh Forever et de Forever Companion…), puis filtrée par la base
d'objets des simulateurs (wowsims et MythicSim : `reqLvl`, `type`, `handType`, `classAllowlist`) :

- emplacement de wowsims déduit du type de l'objet (bague et bijou : `Finger`/`Trinket`, essayés sur leurs deux
  emplacements ; arme : `MainHand`, main gauche : `OffHand` ; à distance : `Ranged`) ;
- niveau requis au plus celui de la tranche ; classe permise si l'objet en restreint ;
- un objet inconnu des deux bases est écarté et nommé ; chaque candidat garde ses sources.
Base et listes fabriquées : aucune valeur de jeu."""

from forever.sims.brackets import candidate_pool

DB = {
    1: {"type": 1, "reqLvl": 20},  # tête
    2: {"type": 11, "reqLvl": 22},  # bague
    3: {"type": 13, "handType": 2, "reqLvl": 18},  # arme à une main
    4: {"type": 13, "handType": 3, "reqLvl": 10},  # main gauche
    5: {"type": 14, "reqLvl": 25},  # à distance
    6: {"type": 5, "reqLvl": 40},  # torse trop haut pour le niveau 25
    7: {"type": 4, "reqLvl": 12, "classAllowlist": [1]},  # cape réservée au Guerrier (classe 1)
    8: {"type": 12},  # bijou sans niveau requis
}


def test_pool_merges_sources_and_filters_by_level_class_and_base():
    sources = [("GearQuest", [1, 3]), ("Naowh", [1, 2, 6, 99]), ("Companion", [4, 5, 7, 8])]
    pool, skipped = candidate_pool(DB, sources, level=25, class_id=8)
    by_item = {c["item"]: c for c in pool}
    assert set(by_item) == {1, 2, 3, 4, 5, 8}
    assert by_item[1] == {"item": 1, "slot": "Head", "sources": ["GearQuest", "Naowh"]}
    assert by_item[2]["slot"] == "Finger" and by_item[8]["slot"] == "Trinket"
    assert by_item[3]["slot"] == "MainHand" and by_item[4]["slot"] == "OffHand" and by_item[5]["slot"] == "Ranged"
    assert {s["item"]: s["reason"] for s in skipped} == {
        6: "niveau requis 40",
        7: "réservé à d'autres classes",
        99: "absent des bases de wowsims et de MythicSim",
    }


def test_two_hand_weapon_goes_to_the_main_hand():
    pool, _ = candidate_pool({9: {"type": 13, "handType": 4, "reqLvl": 20}}, [("Naowh", [9])], level=30, class_id=8)
    assert pool == [{"item": 9, "slot": "MainHand", "sources": ["Naowh"]}]
