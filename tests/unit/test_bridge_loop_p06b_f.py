"""Boucle du pont en P06b, bloc F (décision 235) : un message de l'onglet « Addons » (`c=addons`) va à la conversation
« addons » (consignes et session à part de la conversation « jeu ») ; le pont sauvegarde le dossier avant le tour et
committe en local après ; la réponse publiée porte la ligne du commit. Faux agents, faux git ; aucun `claude` réel."""

import json

from test_bridge_addons import FakeGit, addon
from test_bridge_loop import FakeAgent, FakeCapture, band_of, make
from test_bridge_loop_p06b import CONTEXT, SESSION, replies

from forever.bridge.addons import AddonsConfig, AddonsTurn
from forever.bridge.record import Record


class Recorder:
    def __init__(self, order, name, session="sess-addons"):
        self.order = order
        self.name = name
        self.calls = []
        self.session = session

    def __call__(self, prompt, session_id):
        from forever.bridge.agent import AgentResult

        self.order.append(self.name)
        self.calls.append((prompt, session_id))
        return AgentResult(text="Corrigé : Core.lua. Tapez /reload pour essayer.", session_id=self.session)


def setup(tmp_path):
    order: list[str] = []
    folder = addon(tmp_path)
    game = FakeAgent()
    capture = FakeCapture()
    bridge, addons_dir, _ = make(tmp_path, capture, game)
    fake_git = FakeGit()
    agent = Recorder(order, "agent")

    def snap(config, cache_dir, stamp):
        order.append("sauvegarde")
        return cache_dir / stamp

    def git(argv, **kwargs):
        order.append("git " + next(a for a in argv[3:] if not a.startswith("-") and "=" not in a))
        return fake_git(argv, **kwargs)

    bridge.addons = AddonsTurn(config=AddonsConfig(folder), cache_dir=tmp_path / "cache", agent=agent,
                               snapshot=snap, run=git, now=lambda: "20261010T120000Z")  # fmt: skip
    return bridge, capture, addons_dir, game, agent, order


def test_addons_message_goes_to_the_addons_conversation(tmp_path):
    bridge, capture, addons_dir, game, agent, order = setup(tmp_path)
    capture.band = band_of(Record(SESSION, 1, frozenset({"c=addons"}), CONTEXT, "Corrige le chargement", slot=1))
    bridge.step()
    assert game.calls == [] and len(agent.calls) == 1
    prompt, session = agent.calls[0]
    assert prompt.startswith("Conversation « addons »") and "Corrige le chargement" in prompt and session is None
    assert order[0] == "sauvegarde" and order[1] == "agent" and "git commit" in order[2:]
    reply = replies(addons_dir)[-1]
    assert reply.status == "done" and reply.text.startswith("Corrigé : Core.lua")
    assert reply.text.splitlines()[-1] == "abc1234 · 2 fichier(s)"
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["sessions"]["addons"] == "sess-addons" and state["session"] is None


def test_sessions_stay_apart(tmp_path):
    bridge, capture, _, game, agent, _ = setup(tmp_path)
    capture.band = band_of(Record(SESSION, 1, frozenset({"c=addons"}), CONTEXT, "Un", slot=1))
    bridge.step()
    capture.band = band_of(Record(SESSION, 2, frozenset(), CONTEXT, "Question du jeu", slot=1))
    bridge.step()
    capture.band = band_of(Record(SESSION, 3, frozenset({"c=addons"}), CONTEXT, "Deux", slot=1))
    bridge.step()
    assert [s for _, s in agent.calls] == [None, "sess-addons"]
    assert [s for _, s in game.calls] == [None]
    capture.band = band_of(Record(SESSION, 4, frozenset({"c=addons", "n"}), CONTEXT, "Trois", slot=1))
    bridge.step()
    assert agent.calls[-1][1] is None


def test_without_configuration_the_addons_tab_is_refused(tmp_path):
    bridge, capture, addons_dir, game, _, _ = setup(tmp_path)
    bridge.addons = None
    capture.band = band_of(Record(SESSION, 5, frozenset({"c=addons"}), CONTEXT, "Corrige", slot=1))
    bridge.step()
    assert game.calls == []
    assert "conversation « addons » non configurée" in replies(addons_dir)[-1].text


def test_addons_status_is_published(tmp_path):
    bridge, _, addons_dir, _, _, _ = setup(tmp_path)
    bridge.step()
    text = (addons_dir / "ForeverBridge" / "Status.lua").read_text(encoding="utf-8")
    assert "addons = {" in text and '"RaphCompletionist"' in text
