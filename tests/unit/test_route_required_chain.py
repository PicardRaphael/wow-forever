"""Bloc 4d, essai sur le contexte réel du 2026-10-20 (Gnome Mage parti de Coldridge Valley) : Mage-tastic
Gizmonitor, imposée par la route d'équipement, n'était jamais placée : sa quête préalable ne valait pas le détour pour
l'optimiseur, la quête imposée ne s'ouvrait donc jamais. Une quête imposée impose sa chaîne : préalables obligatoires
(`prereq_all`), un des préalables au choix (`prereq_any`) et l'étape précédente de sa chaîne (`after`), sauf ce que
le personnage a déjà fait ; un choix va à une quête de son camp, la plus basse. Une quête imposée qui reste hors de la
route garde sa raison, dite par la réponse d'équipement.

Quêtes, chaînes et plan fabriqués ici ; aucun chiffre de jeu."""

from forever.route import required_chain


def quest(qid, *, level=10, faction="both", prereq_all=(), prereq_any=(), after=()):
    fields = {
        "level": level,
        "faction": faction,
        "prereq_all": list(prereq_all),
        "prereq_any": list(prereq_any),
        "chain": {"after": list(after)} if after else None,
    }
    return {"id": qid, "name": f"Fixture {qid}", "fields": {k: {"value": v} for k, v in fields.items()}}


BOOK = {
    1: quest(1, prereq_all=(2,)),  # imposée : préalable obligatoire 2
    2: quest(2, after=(3,)),  # 2 vient après 3 dans sa chaîne
    3: quest(3, level=5),
    4: quest(4, prereq_any=(5, 6, 7)),  # un des trois au choix
    5: quest(5, level=12, faction="alliance"),
    6: quest(6, level=8, faction="horde"),  # autre camp : jamais choisie
    7: quest(7, level=9, faction="alliance"),  # la plus basse de mon camp
    8: quest(8, prereq_any=(5, 7)),
}


def test_imposed_quest_brings_its_chain():
    assert required_chain(BOOK, (1,), done=frozenset(), faction="alliance") == frozenset({1, 2, 3})


def test_quests_already_done_are_not_imposed():
    assert required_chain(BOOK, (1,), done=frozenset({3}), faction="alliance") == frozenset({1, 2})


def test_one_prerequisite_of_my_faction_is_chosen_the_lowest():
    assert required_chain(BOOK, (4,), done=frozenset(), faction="alliance") == frozenset({4, 7})


def test_a_prerequisite_already_done_satisfies_the_choice():
    assert required_chain(BOOK, (8,), done=frozenset({5}), faction="alliance") == frozenset({8})


def test_unknown_quests_are_ignored():
    assert required_chain(BOOK, (99,), done=frozenset(), faction="alliance") == frozenset()


def test_gear_reply_says_why_an_imposed_quest_is_not_in_the_route(monkeypatch, make_deps):
    from test_gear_route_4d import DOC, WHO

    from forever.bridge import gear_level

    plan = {"id": "g", "class": "mage", "levels": {"from": 4, "to": 10}, "hours": 1.0, "xp_h": 100.0,
            "certainty": "suppose", "stops": [], "rewards": [], "reminders": [], "warnings": [],
            "required_missing": {"980101": "quêtes d'un donjon hors de la route"},
            "request": {"character": "Go", "purpose": "équipement"}, "basis": {"kind": "calcul"}, "provenance": {}}  # fmt: skip
    monkeypatch.setattr(gear_level, "plan_route", lambda deps_, request, **_k: plan)
    monkeypatch.setattr(gear_level, "_leveling", lambda deps_, context, level, to_level=None: dict(DOC))
    monkeypatch.setattr(gear_level, "_who", lambda deps_, context: dict(WHO))
    monkeypatch.setattr(gear_level, "_drops", lambda deps_: lambda item: [])
    text, _ = gear_level.gear_route_reply(make_deps(offline=True), {}, 10)
    gloves = next(line for line in text.splitlines() if "Quest Gloves" in line)
    assert "pas dans cette route" in gloves and "donjon hors de la route" in gloves
