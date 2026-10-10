"""Boucle du pont en P06b (bloc A, décision 235) : parties réassemblées (publication des parties reçues, aucun agent
avant le message complet), contexte complet au journal, actions `a=` interceptées avant la file (carte de test de
`selftest --card` : action notée, rien de lancé ; tout le reste refusé ; jamais d'agent), export SimulationCraft
`k=simc` reçu sans le modèle et gardé anonymisé, cartes publiées dans les emplacements et `Status.lua`. Aucun jeu,
aucun écran, aucun `claude` réel."""

import json
import time

import pytest
from conftest import FIXTURES
from test_bridge_loop import FakeAgent, FakeCapture, band_of, events, make, slot_table

from forever.bridge.cards import CardSource, read_selftest_cards, write_selftest_card
from forever.bridge.codec import encode_cells, render_band
from forever.bridge.fragments import split_payload
from forever.bridge.record import Record, build_payload

SESSION = "6ac884ce31ab"
CONTEXT = {"level": "19", "class": "MAGE", "zone": "The Barrens"}
EXPORT = (FIXTURES / "simc" / "constructed_mage.txt").read_text(encoding="utf-8")


class RefusingAgent(FakeAgent):
    def __call__(self, prompt, session_id):
        raise AssertionError(f"agent appelé pour : {prompt[-80:]!r}")


def part_bands(record):
    parts = split_payload(build_payload(record), session=record.session, message_id=record.message_id)
    return [render_band(encode_cells(record.message_id, part), 1) for part in parts]


def replies(addons, index=1):
    slot = slot_table(addons, index)
    return [slot.replies[i] for i in range(1, len(slot.replies) + 1)]


# --- Parties --------------------------------------------------------------------------------------------------------


def test_parts_in_any_order_make_one_message(tmp_path):
    record = Record(SESSION, 4, frozenset(), CONTEXT, "é" * 2500, slot=2)
    bands = part_bands(record)
    assert len(bands) == 3
    capture = FakeCapture()
    agent = FakeAgent()
    bridge, addons, _ = make(tmp_path, capture, agent)
    got = []
    for index in (3, 3, 1):
        capture.band = bands[index - 1]
        bridge.step()
        (reply,) = replies(addons)
        assert reply.status == "parts"
        got.append(sorted(reply.got[i] for i in range(1, len(reply.got) + 1)))
    assert got == [[3], [3], [1, 3]]
    assert agent.calls == []
    parts = [e for e in events(tmp_path) if e["event"] == "parts"]
    assert [(e["id"], e["index"], e["total"]) for e in parts] == [(4, 3, 3), (4, 1, 3)]
    capture.band = bands[1]
    bridge.step()
    assert len(agent.calls) == 1 and record.text in agent.calls[0][0]
    messages = [e for e in events(tmp_path) if e["event"] == "message"]
    assert len(messages) == 1 and messages[0]["parts"] == 3
    capture.band = bands[0]
    bridge.step()
    assert len(agent.calls) == 1 and replies(addons, 2)[-1].status == "done"


def test_a_missing_part_never_reaches_the_agent(tmp_path):
    record = Record(SESSION, 5, frozenset(), CONTEXT, "é" * 2500, slot=2)
    bands = part_bands(record)
    capture = FakeCapture()
    bridge, _, _ = make(tmp_path, capture, RefusingAgent())
    for band in bands[:2]:
        capture.band = band
        bridge.step()
    assert not any(e["event"] == "message" for e in events(tmp_path))


def test_malformed_part_is_rejected(tmp_path):
    payload = b"F\x1f" + SESSION.encode() + b"\x1f9\x1fx\x1f3\x1fabc"
    capture = FakeCapture(render_band(encode_cells(9, payload), 1))
    bridge, _, _ = make(tmp_path, capture, RefusingAgent())
    bridge.step()
    assert [e["reason"] for e in events(tmp_path) if e["event"] == "band_rejected"] == ["partie"]


# --- Contexte au journal --------------------------------------------------------------------------------------------


def test_message_event_keeps_the_whole_context(tmp_path):
    context = {**CONTEXT, "gear": "16=7909:1883:0:0:0:0:-12:1234567=Sword of the Bear"}
    record = Record(SESSION, 6, frozenset(), context, "Quel talent ?", slot=1)
    bridge, _, _ = make(tmp_path, FakeCapture(band_of(record)), FakeAgent())
    bridge.step()
    (message,) = [e for e in events(tmp_path) if e["event"] == "message"]
    assert message["context"] == context and message["context_keys"] == list(context)
    for event in events(tmp_path):
        assert not {"pixels", "image", "bgra"} & set(event)


# --- Actions --------------------------------------------------------------------------------------------------------


def action(tmp_path, flag, *, card=True, message_id=7):
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, RefusingAgent())
    bridge.cards = CardSource(tmp_path)
    stamp = None
    if card:
        stamp = write_selftest_card(tmp_path, stamp="20261010T120000Z", now=time.time())["id"]
        bridge.step()
    flag = flag.replace("<carte>", stamp or "")
    capture.band = band_of(Record(SESSION, message_id, frozenset({flag}), CONTEXT, "", slot=2))
    bridge.step()
    return bridge, addons, replies(addons, 2)[-1], [e for e in events(tmp_path) if e["event"] == "action"]


def test_selftest_card_is_published(tmp_path):
    bridge, addons, _ = make(tmp_path, FakeCapture(), RefusingAgent())
    bridge.cards = CardSource(tmp_path)
    card = write_selftest_card(tmp_path, stamp="20261010T120000Z", now=time.time())
    bridge.step()
    slot = slot_table(addons, 1)
    assert slot.cards[1].id == card["id"] == "selftest-20261010T120000Z"
    keys = [slot.cards[1].buttons[i].key for i in range(1, len(slot.cards[1].buttons) + 1)]
    assert keys == ["approve", "reject"]
    status = (addons / "ForeverBridge" / "Status.lua").read_text(encoding="utf-8")
    assert "selftest-20261010T120000Z" in status


def test_selftest_card_action_is_noted_and_nothing_runs(tmp_path):
    bridge, addons, reply, noted = action(tmp_path, "a=approve:<carte>")
    assert reply.status == "done" and "rien n'est lancé" in reply.text
    assert [(e["action"], e["target"], e["result"]) for e in noted] == [
        ("approve", "selftest-20261010T120000Z", "carte de test")
    ]
    assert read_selftest_cards(tmp_path, now=time.time()) == []
    bridge.step()
    assert len(slot_table(addons, 1).cards or {}) == 0


@pytest.mark.parametrize(
    "flag",
    ["a=approve:inconnu", "a=approve:../x", "a=explain:<carte>", "a=autre", "a=approve", "a=reject:<carte>x"],
)
def test_unknown_actions_are_refused_without_the_agent(tmp_path, flag):
    _, _, reply, noted = action(tmp_path, flag)
    assert reply.status == "done" and reply.text.startswith("Action refusée")
    assert [e["result"] for e in noted] == ["refusée"]
    assert read_selftest_cards(tmp_path, now=time.time()) != []


def test_actions_from_the_outbox_never_reach_the_agent(tmp_path):
    outbox = tmp_path / "ForeverBridge.lua"
    outbox.write_text(
        'ForeverBridgeDB = { session = "6ac884ce31ab", outbox = { { id = 8, text = "", flags = "a=approve:x", '
        'slot = 1, context = "level=19" } } }\n',
        encoding="utf-8",
    )
    bridge, _, _ = make(tmp_path, FakeCapture(), RefusingAgent(), outbox=outbox)
    bridge.step()
    assert [e["result"] for e in events(tmp_path) if e["event"] == "action"] == ["refusée"]


# --- Export SimulationCraft -----------------------------------------------------------------------------------------


def test_simc_export_is_received_without_the_agent_and_kept_anonymized(tmp_path):
    context = {"name": "Jen", "realm": "Classic Beta PvE 2", **CONTEXT}
    record = Record(SESSION, 9, frozenset({"k=simc"}), context, EXPORT, slot=1)
    capture = FakeCapture(band_of(record))
    bridge, addons, _ = make(tmp_path, capture, RefusingAgent())
    bridge.step()
    reply = replies(addons)[-1]
    assert reply.status == "done" and "Export SimulationCraft reçu" in reply.text
    assert "somme de contrôle juste" in reply.text
    (kept,) = [e for e in events(tmp_path) if e["event"] == "simc_export"]
    assert kept["id"] == 9 and kept["checksum_ok"] is True and kept["anonymized"] is True
    assert 'mage="Personnage"' in kept["text"] and "server=royaume" in kept["text"]
    from forever.simc import checksum_ok

    assert checksum_ok(kept["text"]) is True
    journal = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "journal").glob("*.jsonl"))
    assert 'mage=\\"Jen\\"' not in journal and "classic_beta_pve_2" not in journal


def test_modified_simc_export_is_reported(tmp_path):
    record = Record(SESSION, 10, frozenset({"k=simc"}), CONTEXT, EXPORT.replace("level=19", "level=18"), slot=1)
    bridge, addons, _ = make(tmp_path, FakeCapture(band_of(record)), RefusingAgent())
    bridge.step()
    reply = replies(addons)[-1]
    assert "export incomplet ou modifié : recopiez /simc" in reply.text
    (kept,) = [e for e in events(tmp_path) if e["event"] == "simc_export"]
    assert kept["checksum_ok"] is False


def test_simc_export_in_parts(tmp_path):
    talents = ",".join(f"{105000 + i}:3" for i in range(51))
    record = Record(SESSION, 11, frozenset({"k=simc"}), {**CONTEXT, "talents": talents}, EXPORT * 3, slot=1)
    bands = part_bands(record)
    assert len(bands) >= 3
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, RefusingAgent())
    for band in bands:
        capture.band = band
        bridge.step()
    assert "Export SimulationCraft reçu" in replies(addons)[-1].text
    (kept,) = [e for e in events(tmp_path) if e["event"] == "simc_export"]
    assert kept["parts"] == len(bands)


def test_contexts_export_writes_contexts_and_exports(tmp_path, capsys, make_deps):
    from forever.cli import main

    deps = make_deps()
    from forever.bridge.journal import Journal

    journal = Journal(deps.cache_dir / "bridge" / "journal", deps.now)
    context = {"name": "Jen", "level": "19", "class": "MAGE", "gear": "16=7909:1883=Sword"}
    for message_id in (1, 2):
        journal.write("message", session=SESSION, id=message_id, context=context, context_keys=list(context))
    journal.write("message", session=SESSION, id=3, context={**context, "level": "20"}, context_keys=list(context))
    journal.write("simc_export", session=SESSION, id=4, text='mage="Personnage"\n', checksum_ok=True)
    out = tmp_path / "relevés"
    assert main(["bridge", "contexts", "export", str(out), "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["contexts"] == 2 and payload["exports"] == 1
    files = sorted(p.name for p in out.iterdir())
    assert len(files) == 3 and sum(name.startswith("simc_") for name in files) == 1
    texts = [p.read_bytes() for p in sorted(out.iterdir()) if not p.name.startswith("simc_")]
    assert b"name=Jen\nlevel=19\nclass=MAGE\ngear=16=7909:1883=Sword\n" in texts
    assert all(b"\r\n" not in t for t in texts)
    assert main(["bridge", "contexts", "last"], deps) == 0
    shown = capsys.readouterr()[0]
    assert "level=20" in shown and "Sword" in shown and "enchantement 1883" in shown


def test_selftest_card_command_writes_the_card(tmp_path, capsys, make_deps):
    from forever.cli import main

    deps = make_deps()
    assert main(["bridge", "selftest", "--card", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["card"]["id"].startswith("selftest-")
    (card,) = read_selftest_cards(deps.cache_dir, now=time.time())
    assert card["id"] == payload["card"]["id"]
