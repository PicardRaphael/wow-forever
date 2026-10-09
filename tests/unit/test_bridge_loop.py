"""Boucle du pont (P06a, bloc D, décision 212 amendée le 2026-10-09) : capture simulée, accusé publié dès la lecture
de la bande (`working`, pas encore prêt), réponse publiée dans les emplacements que le jeu peut encore charger, file
d'un message à la fois, boîte d'envoi `/reload`, session reprise, mention Talents hors Mage, rafraîchissement
périodique, verrou et arrêt par fichier, journal sans pixel. Aucun jeu, aucun écran, aucun `claude` réel."""

import json
import os
import shutil
from datetime import UTC, datetime

from conftest import FIXTURES
from forever.bridge.journal import Journal
from forever.bridge.loop import Bridge, acquire_lock, release_lock
from forever.bridge.state import BridgeState
from lupa import lua51

from forever.bridge.agent import AgentResult
from forever.bridge.buttons import TALENTS_NOTICE
from forever.bridge.capture import GameWindow, Rect
from forever.bridge.codec import SELFTEST_ID, encode_cells, render_band, selftest_payload
from forever.bridge.image import Image, solid
from forever.bridge.record import Record, build_payload

CLIENT = Rect(100, 50, 1280, 720)
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
PROVENANCE = {"game_version": "1.60.1.70245", "certainty": "probable"}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class FakeCapture:
    """Fenêtre du jeu au premier plan (ou non) dont le coin de la zone client montre `band` (ou rien)."""

    def __init__(self, band: Image | None = None, *, front=True):
        self.band = band
        self.front = front
        self.window = GameWindow(7, 4242, "WowB.exe", "World of Warcraft")
        self.grabs: list[Rect] = []

    def find(self):
        return self.window

    def client(self):
        return CLIENT

    def allowed(self):
        return self.front

    def grab(self, rect):
        if not self.front:
            raise AssertionError("capture hors du premier plan")
        self.grabs.append(rect)
        x, y = rect.left - CLIENT.left, rect.top - CLIENT.top
        if self.band is None:
            return solid(rect.width, rect.height, (0, 0, 0))
        return pad(self.band, 800, 96).crop(x, y, rect.width, rect.height)


def pad(image: Image, width: int, height: int) -> Image:
    """`image` dans le coin haut gauche d'un écran noir de `width` × `height`."""
    rows = []
    for y in range(height):
        line = image.bgra[y * image.width * 4 : (y + 1) * image.width * 4] if y < image.height else b""
        rows.append(line + bytes((0, 0, 0, 255)) * (width - len(line) // 4))
    return Image(width, height, b"".join(rows))


def band_of(record: Record, cell_px=1) -> Image:
    return render_band(encode_cells(record.message_id, build_payload(record)), cell_px)


class FakeAgent:
    def __init__(self, results=None, on_call=None):
        self.calls: list[tuple[str, str | None]] = []
        self.results = list(results or [])
        self.on_call = on_call

    def __call__(self, prompt, session_id):
        self.calls.append((prompt, session_id))
        if self.on_call:
            self.on_call()
        if self.results:
            return self.results.pop(0)
        return AgentResult(text="## Réponse\n- **Frostbolt**", session_id="sess-1", provenances=[PROVENANCE])


def make(tmp_path, capture, agent, *, outbox=None, slots=8):
    addons = tmp_path / "AddOns"
    addons.mkdir(exist_ok=True)
    clock = Clock()
    journal = Journal(tmp_path / "journal", lambda: NOW)
    state = BridgeState.load(tmp_path / "state.json")
    bridge = Bridge(
        addons_dir=addons,
        capture=capture,
        agent=agent,
        journal=journal,
        state=state,
        status=lambda: {"version": "1.60.1.70245", "freshness": "fresh", "line": "Données 1.60.1.70245 · à jour"},
        outbox_files=lambda: [outbox] if outbox else [],
        slots=slots,
        clock=clock,
        epoch=lambda: 1791547200,
        executor=lambda job: job(),
    )
    return bridge, addons, clock


def events(tmp_path):
    out = []
    for path in sorted((tmp_path / "journal").glob("*.jsonl")):
        out += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return out


def slot_table(addons, index):
    lua = lua51.LuaRuntime()
    lua.execute((addons / f"ForeverBridge_S{index:03d}" / "Inbox.lua").read_text(encoding="utf-8"))
    return lua.globals().ForeverBridgeSlot


RECORD = Record("6ac884ce31ab", 3, frozenset(), {"level": "19", "class": "MAGE"}, "Quel talent ?", slot=3)


def test_message_acknowledged_then_answered(tmp_path):
    seen = {}

    def at_agent_time():
        slot = slot_table(addons, 3)
        seen["status"] = slot.replies[1].status

    agent = FakeAgent(on_call=at_agent_time)
    bridge, addons, _ = make(tmp_path, FakeCapture(band_of(RECORD)), agent)
    bridge.step()
    assert seen["status"] == "working"  # accusé publié avant la conversation
    assert len(agent.calls) == 1
    prompt, session = agent.calls[0]
    assert prompt.startswith("Contexte du personnage") and "Quel talent ?" in prompt and session is None
    reply = slot_table(addons, 3).replies[1]
    assert reply.status == "done" and reply.id == 3 and reply.session == "6ac884ce31ab"
    assert reply.text == "## Réponse\n- **Frostbolt**"
    assert reply.provenance == "Données 1.60.1.70245 · probable"
    assert slot_table(addons, 8).replies[1].status == "done"
    assert len(slot_table(addons, 2).replies) == 0  # emplacement déjà dépassé par le jeu : pas réécrit
    assert (addons / "ForeverBridge" / "Inbox.lua").is_file()
    kinds = [e["event"] for e in events(tmp_path)]
    assert kinds.count("message") == 1 and "reply" in kinds and kinds.count("published") >= 2
    message = next(e for e in events(tmp_path) if e["event"] == "message")
    assert message["id"] == 3 and message["via"] == "pixels" and message["context_keys"] == ["level", "class"]


def test_same_band_seen_twice_is_handled_once(tmp_path):
    agent = FakeAgent()
    bridge, _, _ = make(tmp_path, FakeCapture(band_of(RECORD)), agent)
    for _ in range(5):
        bridge.step()
    assert len(agent.calls) == 1


def test_session_is_resumed_unless_new_conversation(tmp_path):
    capture = FakeCapture(band_of(RECORD))
    agent = FakeAgent()
    bridge, _, _ = make(tmp_path, capture, agent)
    bridge.step()
    capture.band = band_of(Record("6ac884ce31ab", 4, frozenset(), {}, "Et ensuite ?", slot=5))
    bridge.step()
    capture.band = band_of(Record("6ac884ce31ab", 5, frozenset({"n"}), {}, "Autre sujet", slot=6))
    bridge.step()
    assert [session for _, session in agent.calls] == [None, "sess-1", None]


def test_no_marker_means_no_full_read_and_nothing_journaled(tmp_path):
    capture = FakeCapture(None)
    bridge, _, _ = make(tmp_path, capture, FakeAgent())
    for _ in range(100):
        bridge.step()
    assert capture.grabs and all(r.width <= 20 and r.height <= 4 for r in capture.grabs)
    assert [e["event"] for e in events(tmp_path)] in ([], ["published"])


def test_nothing_is_read_when_the_game_is_not_in_front(tmp_path):
    capture = FakeCapture(band_of(RECORD), front=False)
    agent = FakeAgent()
    bridge, _, _ = make(tmp_path, capture, agent)
    for _ in range(10):
        bridge.step()
    assert capture.grabs == [] and agent.calls == []


def test_selftest_band_is_ignored(tmp_path):
    band = render_band(encode_cells(SELFTEST_ID, selftest_payload()), 1)
    agent = FakeAgent()
    bridge, _, _ = make(tmp_path, FakeCapture(band), agent)
    bridge.step()
    assert agent.calls == []


def test_outbox_is_processed_once(tmp_path):
    outbox = tmp_path / "ForeverBridge.lua"
    shutil.copy(FIXTURES / "bridge" / "ForeverBridge_outbox.lua", outbox)
    agent = FakeAgent()
    bridge, addons, _ = make(tmp_path, FakeCapture(None), agent, outbox=outbox)
    bridge.step()
    assert len(agent.calls) == 1 and "Quel talent prendre à Westfall ?" in agent.calls[0][0]
    message = next(e for e in events(tmp_path) if e["event"] == "message")
    assert message["via"] == "reload" and message["id"] == 5
    assert slot_table(addons, 4).replies[1].id == 5
    os.utime(outbox, (outbox.stat().st_atime, outbox.stat().st_mtime + 60))
    bridge.step()
    assert len(agent.calls) == 1


def test_agent_error_is_published(tmp_path):
    failed = AgentResult(text="", session_id=None, is_error=True, error="délai dépassé (180 s)")
    bridge, addons, _ = make(tmp_path, FakeCapture(band_of(RECORD)), FakeAgent([failed]))
    bridge.step()
    reply = slot_table(addons, 3).replies[1]
    assert reply.status == "error" and "délai dépassé" in reply.text
    assert any(e["event"] == "error" for e in events(tmp_path))


def test_talents_notice_for_other_classes_only(tmp_path):
    hunter = Record("6ac884ce31ab", 7, frozenset({"b=talents"}), {"class": "HUNTER"}, "Q ?", slot=1)
    bridge, addons, _ = make(tmp_path, FakeCapture(band_of(hunter)), FakeAgent())
    bridge.step()
    assert TALENTS_NOTICE in slot_table(addons, 1).replies[1].text
    mage = Record("6ac884ce31ab", 8, frozenset({"b=talents"}), {"class": "MAGE"}, "Q ?", slot=2)
    bridge.capture.band = band_of(mage)
    bridge.step()
    replies = slot_table(addons, 2).replies
    last = next(replies[i] for i in range(1, len(replies) + 1) if replies[i].id == 8)
    assert TALENTS_NOTICE not in last.text


def test_periodic_refresh_rewrites_status_and_the_whole_reserve(tmp_path):
    bridge, addons, clock = make(tmp_path, FakeCapture(None), FakeAgent())
    bridge.step()
    status = addons / "ForeverBridge" / "Status.lua"
    assert status.is_file() and (addons / "ForeverBridge_S001" / "Inbox.lua").is_file()
    status.unlink()
    clock.t += 599
    bridge.step()
    assert not status.exists()
    clock.t += 2
    bridge.step()
    lua = lua51.LuaRuntime()
    lua.execute(status.read_text(encoding="utf-8"))
    st = lua.globals().ForeverBridgeStatus
    assert st.status.version == "1.60.1.70245" and st.buttons[1].key == "talents"
    assert slot_table(addons, 8).buttons[1].key == "talents"


def test_journal_lines_have_no_pixels(tmp_path):
    bridge, _, _ = make(tmp_path, FakeCapture(band_of(RECORD)), FakeAgent())
    bridge.step()
    for event in events(tmp_path):
        assert "at" in event and "event" in event
        assert not {"pixels", "image", "bgra"} & set(event)


def test_lock(tmp_path):
    alive = {1234: True, 99: False}
    assert acquire_lock(tmp_path, NOW, pid=1234, alive=lambda p: alive.get(p))
    assert not acquire_lock(tmp_path, NOW, pid=5678, alive=lambda p: alive.get(p))
    (tmp_path / "bridge" / "bridge.lock").write_text(json.dumps({"pid": 99, "started_at": "x"}), encoding="utf-8")
    assert acquire_lock(tmp_path, NOW, pid=5678, alive=lambda p: alive.get(p))
    release_lock(tmp_path, pid=5678)
    assert not (tmp_path / "bridge" / "bridge.lock").exists()


def test_run_stops_on_the_stop_file(tmp_path):
    bridge, _, _ = make(tmp_path, FakeCapture(None), FakeAgent())
    stop = tmp_path / "stop"
    steps = []

    def sleep(_):
        steps.append(1)
        if len(steps) == 3:
            stop.write_text("", encoding="utf-8")

    assert bridge.run(stop, sleep=sleep) == 0
    assert not stop.exists()
    kinds = [e["event"] for e in events(tmp_path)]
    assert kinds[0] == "start" and kinds[-1] == "stop"
