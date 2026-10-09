"""Boucle du pont (P06a, bloc D, décision 212 amendée le 2026-10-09). À chaque pas (un quart de seconde) : sonde du
marqueur dans la fenêtre du jeu au premier plan, bande lue seulement si le marqueur est là ; message nouveau →
accusé publié aussitôt (`working`, « pas encore prêt ») puis mis en file ; boîte d'envoi `/reload` relue quand la
sauvegarde change ; un message à la fois confié à la conversation « jeu », sur un fil à part pour que la capture et
les accusés continuent ; réponse publiée (texte mis en forme, mention Talents hors Mage, ligne de provenance, lien).
Chaque publication écrit le même `Inbox.lua` dans les emplacements que le jeu peut encore charger ; toutes les
10 minutes, toute la réserve et `Status.lua` (rattrape un `/reload` que le pont ne voit pas). Un pont à la fois
(verrou), arrêt par fichier. Rien de la sonde n'est gardé ni journalisé.

Au repos (décision 226 : le pont démarre avec la session Windows) : jeu fermé, la fenêtre est cherchée toutes les
`FIND_EVERY_S` secondes et le pont ne se réveille que toutes les `IDLE_INTERVAL_S` secondes ; jeu en arrière-plan ou
réduit, rien n'est capturé ; la liste des sauvegardes de ForeverBridge est relue toutes les `OUTBOX_LIST_S` secondes
(leur date, à chaque pas)."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Protocol

from forever.bridge import lock as _lock
from forever.bridge.agent import AgentResult, provenance_line
from forever.bridge.buttons import BUTTONS, button_payload, visible_buttons
from forever.bridge.capture import GameWindow, Rect, band_rect, probe_rect
from forever.bridge.codec import SELFTEST_ID, BandError, Decoded, decode_band, detect_cell_px, selftest_payload
from forever.bridge.format import normalize_reply
from forever.bridge.image import Image
from forever.bridge.journal import Journal
from forever.bridge.prompt import message_text
from forever.bridge.record import CONTEXT_KEYS, Record, RecordError, parse_payload
from forever.bridge.slots import ADDON, SLOTS, inbox_lua, publish, status_lua
from forever.bridge.state import BridgeState

REFRESH_S = 600.0
FIND_EVERY_S = 3.0
IDLE_INTERVAL_S = 1.0  # pas du pont tant qu'aucune fenêtre du jeu n'est connue
OUTBOX_LIST_S = 30.0  # liste des sauvegardes relue (une nouvelle n'apparaît qu'au premier /reload d'un compte)
REJECT_LOG_S = 5.0
HEARTBEAT_S = 30.0  # dernier signe de vie écrit dans le verrou (sonde F : ponts tués sans trace)
_SELFTEST = Decoded(SELFTEST_ID, selftest_payload())

Agent = Callable[[str, str | None], AgentResult]


class Capture(Protocol):
    window: GameWindow | None

    def find(self) -> GameWindow | None: ...
    def client(self) -> Rect | None: ...
    def allowed(self) -> bool: ...
    def grab(self, rect: Rect) -> Image | None: ...


def _context(text: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in str(text or "").split("\n"):
        key, sep, value = line.partition("=")
        if sep and key in CONTEXT_KEYS:
            out[key] = value
    return out


def outbox_records(path: Path) -> list[Record]:
    """Messages de la boîte d'envoi lus dans la sauvegarde de ForeverBridge (`ForeverBridgeDB.outbox`, écrite par le
    jeu au `/reload`), sans exécuter de Lua."""
    from forever.pipeline.lua_table import parse_lua_assignments

    db = parse_lua_assignments(path.read_text(encoding="utf-8", errors="replace")).get("ForeverBridgeDB")
    if not isinstance(db, dict) or not isinstance(db.get("session"), str):
        return []
    entries = db.get("outbox")
    entries = list(entries.values()) if isinstance(entries, dict) else entries if isinstance(entries, list) else []
    records = []
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("id"), int)
            or not isinstance(entry.get("text"), str)
        ):
            continue
        flags = frozenset(f for f in str(entry.get("flags") or "").split(",") if f)
        slot = entry.get("slot") if isinstance(entry.get("slot"), int) else None
        records.append(Record(db["session"], entry["id"], flags, _context(entry.get("context")), entry["text"], slot))
    return records


class Bridge:
    def __init__(
        self,
        *,
        addons_dir: Path,
        capture: Capture,
        agent: Agent,
        journal: Journal,
        state: BridgeState,
        status: Callable[[], dict[str, Any]],
        outbox_files: Callable[[], Iterable[Path]],
        slots: int = SLOTS,
        clock: Callable[[], float] = time.monotonic,
        epoch: Callable[[], int] = lambda: int(time.time()),
        executor: Callable[[Callable[[], None]], None] | None = None,
        describe: Callable[[Record], str | None] | None = None,
        prepare: Callable[[Record], Any] | None = None,
        keeper: Any | None = None,
        heartbeat: Callable[[], None] | None = None,
    ) -> None:
        self.addons_dir = addons_dir
        self.capture = capture
        self.agent = agent
        self.journal = journal
        self.state = state
        self.status = status
        self.outbox_files = outbox_files
        self.slots = slots
        self.clock = clock
        self.epoch = epoch
        self.executor = executor or self._thread
        self.describe = describe
        self.prepare = prepare  # plans.prepare_record : notes, consigne du bouton, défauts, lien (prime sur describe)
        self.keeper = keeper  # keeper.AddonKeeper : addon tenu à jour, jeu fermé
        self.heartbeat = heartbeat
        self.last_beat: float | None = None
        self.queue: deque[Record] = deque()
        self.busy = False
        self.first_slot = 1
        self.status_cache: dict[str, Any] = {}
        self.buttons = button_payload(visible_buttons())
        self.last_refresh: float | None = None
        self.last_find: float | None = None
        self.last_reject: float | None = None
        self.outbox_mtimes: dict[Path, float] = {}
        self.outbox_paths: list[Path] = []
        self.last_outbox_list: float | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _thread(job: Callable[[], None]) -> None:
        threading.Thread(target=job, daemon=True).start()

    # --- publication ---------------------------------------------------------------------------------------------

    def _publish(self, first: int, reason: str) -> None:
        with self._lock:
            inbox = inbox_lua(self.epoch(), self.status_cache, self.state.replies, self.buttons)
            started = time.perf_counter()
            try:
                count = publish(self.addons_dir, inbox, self.slots, first)
            except OSError as exc:  # le jeu lit peut-être un fichier à cet instant : nouvel essai au pas suivant
                self.journal.write("error", where="publication", error=str(exc))
                self.last_refresh = None
                return
            ms = round((time.perf_counter() - started) * 1000, 1)
            self.journal.write("published", reason=reason, first=first, files=count, ms=ms)

    def refresh(self) -> None:
        """État des données relu ; `Status.lua` et toute la réserve réécrits."""
        self.status_cache = {**self.status(), "slots": self.slots}  # l'addon en tire les emplacements restants
        if self.keeper is not None:
            from forever.bridge.status import status_line

            self.status_cache["addon"] = self.keeper.addon_state()
            if self.status_cache.get("version"):
                self.status_cache["line"] = status_line(self.status_cache)
        path = self.addons_dir / ADDON / "Status.lua"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_bytes(status_lua(self.status_cache, self.buttons, self.epoch()).encode("utf-8"))
            tmp.replace(path)
        except OSError as exc:
            self.journal.write("error", where="Status.lua", error=str(exc))
        self.last_refresh = self.clock()
        self._publish(1, "rafraîchissement")

    # --- entrées ---------------------------------------------------------------------------------------------------

    def _rejected(self, now: float, reason: str) -> None:
        if self.last_reject is None or now - self.last_reject >= REJECT_LOG_S:
            self.last_reject = now
            self.journal.write("band_rejected", reason=reason)

    def _capture(self, now: float) -> None:
        cap = self.capture
        if cap.window is None:
            if self.last_find is not None and now - self.last_find < FIND_EVERY_S:
                return
            self.last_find = now
            window = cap.find()
            if window is None:
                return
            self.journal.write("window", title=window.title, pid=window.pid)
        client = cap.client()
        if client is None or not cap.allowed():
            return
        probe_r = probe_rect(client)
        probe = cap.grab(probe_r) if probe_r is not None else None
        cell = detect_cell_px(probe) if probe is not None else None
        if cell is None:
            return
        started = time.perf_counter()
        band_r = band_rect(client, cell)
        band = cap.grab(band_r) if band_r is not None else None
        if band is None:
            return
        decoded = decode_band(band, cell)
        if isinstance(decoded, BandError):
            self._rejected(now, decoded.reason)
            return
        if decoded is None or decoded == _SELFTEST:
            return
        try:
            record = parse_payload(decoded.payload)
        except RecordError:
            self._rejected(now, "message")
            return
        self._accept(record, "pixels", capture_ms=round((time.perf_counter() - started) * 1000, 1))

    def _read_outboxes(self) -> None:
        now = self.clock()
        if self.last_outbox_list is None or now - self.last_outbox_list >= OUTBOX_LIST_S:
            self.last_outbox_list = now
            self.outbox_paths = list(self.outbox_files())
        for path in self.outbox_paths:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if self.outbox_mtimes.get(path) == mtime:
                continue
            self.outbox_mtimes[path] = mtime
            try:
                records = outbox_records(path)
            except Exception as exc:  # noqa: BLE001 : une sauvegarde illisible ne doit pas arrêter le pont
                self.journal.write("error", where="boîte d'envoi", error=f"{type(exc).__name__}: {exc}")
                continue
            for record in records:
                self._accept(record, "reload")

    def _accept(self, record: Record, via: str, capture_ms: float | None = None) -> None:
        with self._lock:
            if self.state.seen(record.session, record.message_id):
                return
            self.state.mark(record.session, record.message_id)
            self.journal.write(
                "message",
                session=record.session,
                id=record.message_id,
                via=via,
                flags=sorted(record.flags),
                slot=record.slot,
                context_keys=list(record.context),
                text=record.text,
                capture_ms=capture_ms,
            )
            # après un /reload (boîte d'envoi), le compteur d'emplacements de l'addon est revenu à 1
            self.first_slot = record.slot if via == "pixels" and record.slot else 1
            self.state.put_reply(
                {"session": record.session, "id": record.message_id, "status": "working", "since": self.epoch()}
            )
            self.queue.append(record)
        self._publish(self.first_slot, "accusé")

    # --- conversation ----------------------------------------------------------------------------------------------

    def _dispatch(self) -> None:
        with self._lock:
            if self.busy or not self.queue:
                return
            self.busy = True
            record = self.queue.popleft()
        self.executor(lambda: self._work(record))

    def _notice(self, record: Record) -> str | None:
        key = next((f.split("=", 1)[1] for f in record.flags if f.startswith("b=")), None)
        button = next((b for b in BUTTONS if b.key == key), None)
        return button.notice_for(record.context.get("class", "")) if button else None

    def _work(self, record: Record) -> None:
        try:
            session = None if "n" in record.flags else self.state.session
            started = self.clock()
            self.journal.write("agent", id=record.message_id, resumed=session is not None)
            prefer: str | None = None
            try:
                guide = None
                if self.prepare is not None:
                    prepared = self.prepare(record)
                    talents, guide, prefer = prepared.notes, prepared.guide, prepared.link
                    for d in prepared.defects:
                        self.journal.write(
                            "context_defect", id=record.message_id, kind=d.kind, value=d.value, reason=d.reason
                        )
                else:
                    talents = self.describe(record) if self.describe and record.context.get("talents") else None
                result = self.agent(message_text(record, talents=talents, guide=guide), session)
            except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                result = AgentResult(text="", session_id=None, is_error=True, error=f"{type(exc).__name__}: {exc}")
            if result.denied:
                self.journal.write("denied", id=record.message_id, tools=result.denied)
            reply: dict[str, Any] = {"session": record.session, "id": record.message_id}
            if result.is_error:
                reply.update(status="error", text=f"Erreur : {result.error or 'réponse impossible'}")
                self.journal.write("error", id=record.message_id, where="conversation", error=result.error)
            else:
                text = normalize_reply(result.text)
                notice = self._notice(record)
                if notice:
                    text = f"{text}\n\n{notice}"
                reply.update(status="done", text=text, provenance=provenance_line(result.provenances))
                link = result.links.get(prefer) if prefer else None
                if link or result.link:
                    reply["link"] = link or result.link
                if result.session_id:
                    self.state.set_session(result.session_id)
                self.journal.write(
                    "reply",
                    id=record.message_id,
                    seconds=round(self.clock() - started, 1),
                    length=len(text),
                    provenance=reply["provenance"],
                    tools=result.tools,
                    timings=result.timings,
                    cost_usd=result.cost_usd,
                )
            self.state.put_reply(reply)
            self._publish(self.first_slot, "réponse")
        finally:
            with self._lock:
                self.busy = False

    # --- boucle ----------------------------------------------------------------------------------------------------

    def step(self) -> None:
        now = self.clock()
        if self.heartbeat is not None and (self.last_beat is None or now - self.last_beat >= HEARTBEAT_S):
            self.last_beat = now
            try:
                self.heartbeat()
            except OSError as exc:
                self.journal.write("error", where="signe de vie", error=str(exc))
        if self.keeper is not None:
            try:
                if self.keeper.tick():
                    self.last_refresh = None  # état de l'addon changé : Status.lua réécrit tout de suite
            except Exception as exc:  # noqa: BLE001 : l'addon tenu à jour ne doit jamais arrêter le pont
                self.journal.write("error", where="addon tenu à jour", error=f"{type(exc).__name__}: {exc}")
        if self.last_refresh is None or now - self.last_refresh >= REFRESH_S:
            self.refresh()
        self._capture(now)
        self._read_outboxes()
        self._dispatch()

    def run(
        self,
        stop_file: Path,
        *,
        sleep: Callable[[float], None] = time.sleep,
        interval_s: float = 0.25,
        started: float | None = None,
    ) -> int:
        """Boucle jusqu'au fichier d'arrêt (`forever bridge stop`) ; rend 0. Un fichier d'arrêt plus ancien que le
        lancement (`started`, défaut : maintenant ; la CLI donne l'heure d'avant la prise du verrou : un `stop` posé
        pendant la préparation est obéi) est effacé, jamais obéi."""
        started = time.time() if started is None else started
        stale = False
        try:
            stale = stop_file.stat().st_mtime < started
        except OSError:
            pass
        if stale:
            stop_file.unlink(missing_ok=True)
        self.journal.write("start", slots=self.slots, pid=os.getpid(), stale_stop_file=stale)
        reason = "fichier d'arrêt"
        try:
            while True:
                if stop_file.exists():
                    stop_file.unlink(missing_ok=True)
                    break
                self.step()
                sleep(interval_s if self.capture.window is not None else max(interval_s, IDLE_INTERVAL_S))
        except KeyboardInterrupt:
            reason = "interruption (Ctrl+C)"
        self.journal.write("stop", reason=reason)
        return 0


# --- verrou ------------------------------------------------------------------------------------------------------

# Le verrou vit dans `forever.bridge.lock` (bibliothèque standard seulement, lu par la surveillance du démarrage
# automatique) ; ses fonctions restent accessibles ici.
lock_path = _lock.lock_path
lock_holder = _lock.lock_holder
acquire_lock = _lock.acquire_lock
touch_lock = _lock.touch_lock
lock_info = _lock.lock_info
release_lock = _lock.release_lock
