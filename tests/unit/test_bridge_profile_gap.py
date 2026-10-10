"""Écart entre le jeu et le profil (P06b, bloc C, décision 122 et 235), sur le contexte réel `contexts/mage19.txt` :
comparaison de la classe, de la race, de la faction, du niveau, des talents et de l'équipement ; empreinte stable ;
carte de proposition, ou de création quand le personnage manque. Rien n'est écrit ici."""

import pytest
from conftest import FIXTURES

from forever.bridge.context import load_context_data, resolve
from forever.bridge.profile_gap import Gap, game_fields, gap_card, gap_fingerprint, profile_gaps

REAL = FIXTURES / "bridge" / "contexts" / "mage19.txt"


def context():
    return dict(line.split("=", 1) for line in REAL.read_text(encoding="utf-8").split("\n") if "=" in line)


@pytest.fixture
def resolved(make_deps):
    return resolve(load_context_data(make_deps()), context())


def same_profile(resolved):
    return {"name": "Jen", "realm": "Classic Beta PvE 2", **game_fields(resolved)}


def test_identical_profile_has_no_gap(resolved):
    fields = game_fields(resolved)
    assert fields["class"] == "Mage" and fields["level"] == 19 and fields["faction"] == "Horde"
    assert fields["talents"] == resolved.current and fields["talents"]
    assert fields["gear"]["16"]["item"] == 15444
    assert profile_gaps(resolved, same_profile(resolved)) == []


def test_level_gap(resolved):
    assert profile_gaps(resolved, {**same_profile(resolved), "level": 18}) == [Gap("level", 18, 19)]


def test_missing_talents_and_gear(resolved):
    gaps = profile_gaps(resolved, {**same_profile(resolved), "talents": {}, "gear": {}})
    assert [g.field for g in gaps] == ["talents", "gear"]
    assert gaps[0].game == resolved.current


def test_faction_case_is_not_a_gap(resolved):
    assert profile_gaps(resolved, {**same_profile(resolved), "faction": "horde"}) == []


def test_fingerprint_is_stable_and_follows_the_game(resolved):
    a = [Gap("level", 18, 19), Gap("talents", {}, {"x": 5, "y": 1})]
    b = [Gap("talents", {}, {"y": 1, "x": 5}), Gap("level", 18, 19)]
    assert gap_fingerprint(a) == gap_fingerprint(b)
    assert gap_fingerprint([Gap("level", 18, 20)]) != gap_fingerprint([Gap("level", 18, 19)])


def test_cards():
    gaps = [Gap("level", 18, 19), Gap("talents", {}, {"x": 5})]
    card = gap_card("Jen", "Royaume", gaps, create=False)
    assert card["kind"] == "profile" and card["id"] == "profile-" + gap_fingerprint(gaps)
    assert card["title"] == "Écart avec ton profil : Jen"
    assert card["lines"][0] == "niveau : 18 au profil, 19 en jeu"
    assert [b["key"] for b in card["buttons"]] == ["apply", "dismiss"]
    assert card["buttons"][0]["action"] == f"profile_apply:{card['id']}" and card["buttons"][0]["label"] == (
        "Mettre à jour le profil"
    )
    assert card["buttons"][1]["action"] == f"profile_dismiss:{card['id']}" and card["buttons"][1]["label"] == "Ignorer"
    created = gap_card("Jen", "Royaume", gaps, create=True)
    assert created["title"] == "Créer le personnage Jen au profil"


def test_no_profile_means_every_field_is_a_gap(resolved):
    fields = [g.field for g in profile_gaps(resolved, None)]
    assert fields == ["class", "race", "faction", "level", "talents", "gear"]
