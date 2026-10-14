"""Boucle du pont en P06b, bloc C (décision 122 et 235) : écart entre le jeu et le profil à chaque message (ligne fixe
dans le message à la conversation, mention dans la réponse, carte « Mettre à jour le profil »), écriture par le pont
seulement au clic (`profile_apply`, source `jeu`), « Ignorer » qui fait taire le même écart, création proposée quand
le personnage manque. Contexte réel `contexts/mage19.txt` ; aucun `claude` réel."""

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from test_bridge_loop import FakeAgent, FakeCapture, band_of, make, slot_table
from test_bridge_loop_p06b import SESSION, replies
from test_bridge_profile_gap import context

from forever.bridge.cards import CardSource
from forever.bridge.context import load_context_data, resolve
from forever.bridge.profile_gap import ProfileWatch
from forever.bridge.record import Record
from forever.profile import read_profile, set_character

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
GAP_LINE = "Écart avec le profil"
MENTION = "Écart avec ton profil : voir À valider"


@pytest.fixture
def setup(tmp_path, make_deps):
    deps = replace(make_deps(), profile_path=tmp_path / "profil" / "profile.json")
    data = load_context_data(deps)
    agent = FakeAgent()
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, agent)
    watch = ProfileWatch(data=data, deps=deps, store=tmp_path / "cache" / "bridge" / "profile_gaps.json",
                         now=lambda: NOW)  # fmt: skip
    bridge.profile = watch
    bridge.cards = CardSource(tmp_path / "cache", profile=watch)
    state = {"id": 0}

    def send(ctx=None, flags=(), text="Quel talent ?"):
        state["id"] += 1
        capture.band = band_of(Record(SESSION, state["id"], frozenset(flags), ctx or context(), text, slot=1))
        bridge.step()
        return replies(addons)[-1]

    def cards():
        bridge.step()
        slot = slot_table(addons, 1)
        return [slot.cards[i] for i in range(1, len(slot.cards or {}) + 1)]

    return deps, data, agent, send, cards


def test_gap_is_told_proposed_and_applied_on_click(setup):
    deps, data, agent, send, cards = setup
    set_character(deps, "Jen", cls="Mage", race="Orc", faction="Horde", level=18)
    reply = send()
    assert GAP_LINE in agent.calls[-1][0] and "Le jeu l'emporte pour cette réponse" in agent.calls[-1][0]
    assert reply.text.endswith(MENTION)
    (card,) = cards()
    assert card.kind == "profile" and card.title == "Écart avec ton profil : Jen"
    assert read_profile(deps)["character"]["level"] == 18  # rien d'écrit avant le clic
    reply = send(flags={f"a=profile_apply:{card.id}"}, text="")
    assert reply.text.startswith("Profil mis à jour")
    c = read_profile(deps)["character"]
    assert c["level"] == 19 and c["fields"]["level"]["source"] == "jeu"
    assert c["talents"] == resolve(data, context()).current and c["gear"]["16"]["item"] == 15444
    assert cards() == []
    calls = len(agent.calls)
    reply = send()
    assert len(agent.calls) == calls + 1 and GAP_LINE not in agent.calls[-1][0]
    assert not reply.text.endswith(MENTION) and cards() == []


def test_dismiss_silences_the_same_gap_only(setup):
    deps, _, _, send, cards = setup
    set_character(deps, "Jen", cls="Mage", race="Orc", faction="Horde", level=18)
    send()
    (card,) = cards()
    reply = send(flags={f"a=profile_dismiss:{card.id}"}, text="")
    assert reply.text.startswith("Écart ignoré")
    send()
    assert cards() == []
    assert read_profile(deps)["character"]["level"] == 18
    send(ctx={**context(), "level": "20"})
    (again,) = cards()
    assert again.id != card.id


def test_missing_character_is_proposed_for_creation(setup):
    deps, _, _, send, cards = setup
    send()
    (card,) = cards()
    assert card.title == "Créer le personnage Jen au profil"
    assert not deps.profile_path.exists()
    send(flags={f"a=profile_apply:{card.id}"}, text="")
    doc = json.loads(deps.profile_path.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 4 and doc["active"] == "Jen"  # schéma 4 depuis LN1
    c = read_profile(deps)["character"]
    assert (c["class"], c["race"], c["level"], c["realm"]) == ("Mage", "Orc", 19, "Classic Beta PvE 2")


def test_unknown_profile_card_is_refused(setup):
    _, _, _, send, _ = setup
    reply = send(flags={"a=profile_apply:profile-inconnu"}, text="")
    assert reply.text.startswith("Action refusée")
