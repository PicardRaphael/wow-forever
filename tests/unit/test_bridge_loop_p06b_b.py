"""Boucle du pont en P06b, bloc B (décision 235) : « Mettre à jour », Valider et Refuser traités par le pont sans le
modèle. Commandes fixées lancées par un faux `spawn` (rien n'est exécuté), identifiant apparié exactement à une
attente approuvable de `list_pending`, refus de tout le reste ; hors ligne, aucune mise à jour ; « Expliquer » passe
par la file ; fin d'un passage publiée aussitôt ; cartes des attentes publiées. Aucun jeu, aucun `claude` réel."""

import json
import os
import sys
from datetime import UTC, datetime

import pytest
from test_bridge_loop import FakeAgent, FakeCapture, band_of, events, make, slot_table
from test_bridge_loop_p06b import CONTEXT, SESSION, RefusingAgent, replies

from forever.bridge.actions import ActionHandler, update_argv
from forever.bridge.cards import CardSource
from forever.bridge.record import Record
from forever.bridge.updater import UpdateWatch
from forever.update import record_pending, update_dir

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
VERSION = "1.60.1.70338"
PYTHON = [sys.executable, "-u", "-m", "forever"]


class FakeSpawn:
    def __init__(self):
        self.calls: list[tuple[list[str], str]] = []

    def __call__(self, argv, log):
        self.calls.append((list(argv), str(log)))


def pending(cache, kind, ident, *, state="en_attente", action="attente"):
    record_pending(cache, {"id": ident, "kind": kind, "action": action, "version": VERSION, "revision": None,
                           "reasons": ["raison"], "commands": [], "created_at": "2026-10-10T08:00:00Z"})  # fmt: skip
    if state != "en_attente":
        path = update_dir(cache) / "pending" / f"{ident}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**doc, "state": state}), encoding="utf-8")


def bridge_with_actions(tmp_path, agent=None, *, offline=False):
    cache = tmp_path / "cache"
    spawn = FakeSpawn()
    capture = FakeCapture()
    bridge, addons, clock = make(tmp_path, capture, agent or RefusingAgent())
    bridge.actions = ActionHandler(cache_dir=cache, now=lambda: NOW, offline=offline, spawn=spawn)
    bridge.cards = CardSource(cache)
    return bridge, addons, capture, spawn, cache, clock


def send(bridge, capture, flags, message_id, text=""):
    capture.band = band_of(Record(SESSION, message_id, frozenset(flags), CONTEXT, text, slot=1))
    bridge.step()


def test_update_argv():
    assert update_argv("update") == [*PYTHON, "update", "--auto", "--json"]
    assert update_argv("approve", "m-1") == [*PYTHON, "update", "approve", "m-1", "--json"]
    assert update_argv("reject", "m-1") == [*PYTHON, "update", "reject", "m-1", "--reason", "refusé en jeu", "--json"]


def test_update_button_launches_one_fixed_pass(tmp_path):
    bridge, addons, capture, spawn, _, _ = bridge_with_actions(tmp_path)
    send(bridge, capture, {"a=update"}, 1)
    ((argv, log),) = spawn.calls
    assert argv == [*PYTHON, "update", "--auto", "--json"]
    assert os.path.basename(log).startswith("run-") and log.endswith(".log")
    reply = replies(addons)[-1]
    assert reply.status == "done" and reply.text.startswith("Mise à jour lancée")
    (noted,) = [e for e in events(tmp_path) if e["event"] == "action"]
    assert (noted["action"], noted["result"]) == ("update", "lancée")


def test_update_during_a_pass_launches_nothing(tmp_path):
    bridge, addons, capture, spawn, cache, _ = bridge_with_actions(tmp_path)
    lock = update_dir(cache) / "lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "started_at": "2026-10-10T11:59:00Z", "step": "clone"}),
                    encoding="utf-8")  # fmt: skip
    send(bridge, capture, {"a=update"}, 2)
    assert spawn.calls == []
    assert "Une mise à jour est déjà en cours (préparation)" in replies(addons)[-1].text


def test_update_is_refused_offline(tmp_path):
    bridge, addons, capture, spawn, _, _ = bridge_with_actions(tmp_path, offline=True)
    send(bridge, capture, {"a=update"}, 3)
    assert spawn.calls == [] and "Mise à jour impossible : le pont tourne hors ligne" in replies(addons)[-1].text


def test_approve_and_reject_an_approvable_entry(tmp_path):
    bridge, addons, capture, spawn, cache, _ = bridge_with_actions(tmp_path)
    ident = f"measures-{VERSION}-abc"
    pending(cache, "measures", ident)
    send(bridge, capture, {f"a=approve:{ident}"}, 4)
    assert [argv for argv, _ in spawn.calls] == [[*PYTHON, "update", "approve", ident, "--json"]]
    assert replies(addons)[-1].text.startswith("Validé : ")
    send(bridge, capture, {f"a=reject:{ident}"}, 5)
    assert spawn.calls[-1][0] == [*PYTHON, "update", "reject", ident, "--reason", "refusé en jeu", "--json"]
    assert len(spawn.calls) == 2


@pytest.mark.parametrize(
    ("flag", "why"),
    [
        (f"a=approve:network-{VERSION}", "ne se valide pas en jeu"),
        ("a=approve:../x", "action inconnue"),
        ("a=approve:inconnu", "cette carte n'existe plus"),
        (f"a=reject:measures-{VERSION}-faite", "ne se valide pas en jeu"),
        ("a=explain:x", "action inconnue"),
        ("a=autre", "action inconnue"),
    ],
)
def test_other_actions_are_refused(tmp_path, flag, why):
    bridge, addons, capture, spawn, cache, _ = bridge_with_actions(tmp_path)
    pending(cache, "network", f"network-{VERSION}")
    pending(cache, "measures", f"measures-{VERSION}-faite", state="faite")
    send(bridge, capture, {flag}, 6)
    assert spawn.calls == []
    text = replies(addons)[-1].text
    assert text.startswith("Action refusée") and why in text


def test_explain_goes_to_the_conversation(tmp_path):
    agent = FakeAgent()
    bridge, _, capture, spawn, _, _ = bridge_with_actions(tmp_path, agent)
    question = "Explique cette mise à jour en attente, simplement.\nMesures à valider\nPNJ changés : Hogger"
    send(bridge, capture, {"b=explain"}, 7, question)
    assert len(agent.calls) == 1 and "PNJ changés : Hogger" in agent.calls[0][0]
    assert spawn.calls == []


def test_pending_cards_are_published(tmp_path):
    bridge, addons, _, _, cache, _ = bridge_with_actions(tmp_path)
    pending(cache, "measures", f"measures-{VERSION}-abc")
    pending(cache, "network", f"network-{VERSION}")
    bridge.step()
    slot = slot_table(addons, 1)
    ids = [slot.cards[i].id for i in range(1, len(slot.cards) + 1)]
    assert ids == [f"measures-{VERSION}-abc", f"network-{VERSION}"]


def test_end_of_a_pass_is_published_at_once(tmp_path):
    bridge, _, _, _, cache, clock = bridge_with_actions(tmp_path)
    bridge.update_watch = UpdateWatch(cache)
    bridge.step()
    before = len([e for e in events(tmp_path) if e["event"] == "published" and e["reason"] == "rafraîchissement"])
    last = update_dir(cache) / "last.json"
    last.parent.mkdir(parents=True, exist_ok=True)
    last.write_text(json.dumps({"finished_at": "2026-10-10T12:05:00Z", "written": []}), encoding="utf-8")
    clock.t += 5.0
    bridge.step()
    after = len([e for e in events(tmp_path) if e["event"] == "published" and e["reason"] == "rafraîchissement"])
    assert after == before + 1
    clock.t += 5.0
    bridge.step()
    assert (
        len([e for e in events(tmp_path) if e["event"] == "published" and e["reason"] == "rafraîchissement"]) == after
    )
