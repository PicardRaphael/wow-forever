"""Rangs appris au niveau d'un sort de classe (EX1, relecture du registre : G4), règle unique du moteur utilisée par
les macros et les profils EllesmereUI. Sorts synthétiques (niveaux inventés, aucune valeur du jeu)."""

from forever.engine.spells import learned_class_ranks

PLAIN = {"talent": None, "ranks": [{"rank": 1, "level": 4}, {"rank": 2, "level": 12}, {"rank": 3, "level": 20}]}
UNKNOWN = {"talent": None, "ranks": [{"rank": 1, "level": 0}, {"rank": 2, "level": None}]}
TALENT = {"talent": {"key": "unTalent"}, "ranks": [{"rank": 1, "level": None}, {"rank": 2, "level": 30}]}


def ranks(spell, level, talents=None):
    return [r["rank"] for r in learned_class_ranks(spell, level, talents or {})]


def test_ranks_up_to_the_level():
    assert ranks(PLAIN, 3) == []
    assert ranks(PLAIN, 4) == [1]
    assert ranks(PLAIN, 19) == [1, 2]
    assert ranks(PLAIN, 60) == [1, 2, 3]


def test_unknown_level_is_never_learned():
    assert ranks(UNKNOWN, 60) == []


def test_talent_spell_needs_the_talent_and_its_first_rank_comes_from_it():
    assert ranks(TALENT, 60) == []
    assert ranks(TALENT, 60, {"unTalent": 0}) == []
    assert ranks(TALENT, 20, {"unTalent": 1}) == [1]
    assert ranks(TALENT, 30, {"unTalent": 1}) == [1, 2]
    assert ranks({**TALENT, "talent": "unTalent"}, 20, {"unTalent": 1}) == [1]
