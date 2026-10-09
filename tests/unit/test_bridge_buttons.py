"""Boutons de la fenêtre (P06a, bloc B, décision 212 amendée le 2026-10-09) : un bouton n'apparaît que si la tranche
qui le calcule est faite, et pour les classes qu'elle sert ; Talents pour toutes les classes, calculé pour le Mage."""

from forever.bridge.buttons import BUTTONS, DONE_SLICES, button_payload, visible_buttons

CLASSES = ("MAGE", "PALADIN", "WARLOCK", "PRIEST", "HUNTER", "SHAMAN", "WARRIOR", "ROGUE", "DRUID")


def keys(buttons):
    return [b.key for b in buttons]


def test_four_buttons_in_p06a():
    assert keys(visible_buttons()) == ["talents", "leveling", "pets", "pvp"]
    assert {"T04b", "T04c", "T05", "FA1", "CH0", "PV1"} <= DONE_SLICES


def test_buttons_of_unfinished_slices_are_hidden():
    all_keys = keys(BUTTONS)
    assert {"update", "gear", "last_fight"} <= set(all_keys)
    visible = keys(visible_buttons())
    assert "update" not in visible and "gear" not in visible and "last_fight" not in visible
    assert keys(visible_buttons(DONE_SLICES - {"CH0"})) == ["talents", "leveling", "pvp"]


def test_classes_and_questions():
    by_key = {b.key: b for b in visible_buttons()}
    assert by_key["leveling"].classes == ("MAGE",)
    assert by_key["pets"].classes == ("HUNTER",)
    assert by_key["pvp"].classes is None and by_key["pvp"].needs_player_target
    talents = by_key["talents"]
    assert talents.classes is None
    assert talents.question_for("MAGE") == "Quel est mon prochain talent, avec le lien Talents Forever ?"
    for cls in CLASSES[1:]:
        assert "build populaire" in talents.question_for(cls) and "Talents Forever" in talents.question_for(cls)
        assert talents.notice_for(cls) == (
            "Build populaire de Talents Forever (choix de joueurs), pas encore calculé par le moteur de forever."
        )
    assert talents.notice_for("MAGE") is None
    assert by_key["leveling"].question_for("MAGE") == "Quel est mon prochain objectif de leveling ?"
    assert by_key["pets"].question_for("HUNTER") == "Où apprivoiser le prochain rang utile près de moi ?"
    assert by_key["pvp"].question_for("ROGUE") == "Fiche de la classe de ma cible"


def test_payload_for_the_addon():
    payload = button_payload(visible_buttons())
    talents = payload[0]
    assert talents["key"] == "talents" and talents["label"] == "Talents"
    assert talents["questions"]["MAGE"].startswith("Quel est mon prochain talent")
    assert "classes" not in talents
    pets = next(b for b in payload if b["key"] == "pets")
    assert pets["classes"] == ["HUNTER"]
    pvp = next(b for b in payload if b["key"] == "pvp")
    assert pvp["target"] is True
