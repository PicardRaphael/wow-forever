"""Sortie texte d'une feuille de route : un rappel répété à chaque recharge de son objet (sac de couchage) tient sur
une ligne, avec le nombre de fois sur la séance, au lieu d'une ligne par recharge. Route fabriquée ; aucun chiffre de
jeu."""

from forever.cli import render_route


def test_a_repeated_reminder_is_one_line_with_its_count():
    doc = {
        "class": "mage", "faction": "alliance", "levels": {"from": 1, "to": 2, "reached": 2}, "hours": 1.0,
        "xp_h": 100.0, "certainty": "suppose", "id": "x", "dungeons": [], "stops": [], "warnings": [],
        "reminders": [{"text": "pose le sac"}, {"text": "pose le sac"}, {"text": "pose le sac"}, {"text": "tente"}],
    }  # fmt: skip
    lines = [line for line in render_route(doc) if "rappel" in line]
    assert lines == ["  rappel : pose le sac (×3 sur la séance)", "  rappel : tente"]
