"""Bloc 6b, PvP actionnable (décision 281, idées du chat du 2026-10-15, point 2 ; amende la consigne resserrée de la
décision 237) : la réponse du bouton PvP commence par « Comment jouer contre lui », trois à cinq consignes concrètes
dans l'ordre du combat, adaptées à ma classe et à mes sorts, tirées des menaces et réponses de
`forever_lookup(kind="pvp")` (aucune règle inventée) ; puis le détail en mots de joueur (chaque sort nommé avec ce
qu'il fait, « rendement décroissant » expliqué en une phrase) ; certitude affichée.

Contexte réel relevé en jeu (`tests/fixtures/bridge/contexts/mage19_cible_chaman21_tauren.txt`). Aucun chiffre de
jeu ici."""

from conftest import FIXTURES

from forever.bridge.context import load_context_data, resolve
from forever.bridge.plans import button_plan


def guide(make_deps):
    data = load_context_data(make_deps())
    text = (FIXTURES / "bridge" / "contexts" / "mage19_cible_chaman21_tauren.txt").read_text(encoding="utf-8")
    ctx = dict(line.split("=", 1) for line in text.split("\n") if "=" in line)
    plan = button_plan("pvp", resolve(data, ctx), data.level_cap)
    return " ".join(plan.read)


def test_reply_starts_with_how_to_play_against_him(make_deps):
    text = guide(make_deps)
    assert "« Comment jouer contre lui »" in text and "trois à cinq consignes" in text
    assert "ordre du combat" in text and "tes sorts" in text
    assert text.index("Comment jouer contre lui") < text.index("détail")


def test_advice_only_from_the_tool(make_deps):
    text = guide(make_deps)
    for key in ("threats", "answers", "their_answers", "windows", "missing"):
        assert f"`{key}`" in text
    assert "aucune règle inventée" in text


def test_detail_in_player_words_with_certainty(make_deps):
    text = guide(make_deps)
    assert "ce qu'il fait" in text and "rendement décroissant" in text and "une phrase" in text
    assert "certitude" in text
