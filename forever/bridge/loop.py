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

import json
import os
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol

from forever.bridge import lock as _lock
from forever.bridge.actions import action_flag, card_for, parse_action
from forever.bridge.agent import AgentResult, provenance_line
from forever.bridge.buttons import BUTTONS, button_payload, visible_buttons
from forever.bridge.capture import GameWindow, Rect, band_rect, probe_rect
from forever.bridge.choices import (
    ROUTE_CHOICES,
    VALIDATE,
    Choice,
    answer_text,
    chat_choices,
    find_answer,
    route_options,
)
from forever.bridge.codec import SELFTEST_ID, BandError, Decoded, decode_band, detect_cell_px, selftest_payload
from forever.bridge.format import normalize_reply
from forever.bridge.fragments import Fragment, FragmentBuffer, parse_fragment
from forever.bridge.image import Image
from forever.bridge.journal import Journal
from forever.bridge.profile_gap import GAP_NOTE, gaps_text
from forever.bridge.profile_gap import MENTION as GAP_MENTION
from forever.bridge.prompt import message_text
from forever.bridge.record import CONTEXT_KEYS, Record, RecordError, parse_payload
from forever.bridge.slots import ADDON, SLOTS, inbox_lua, publish, status_lua
from forever.bridge.state import BridgeState
from forever.errors import ForeverError

REFRESH_S = 600.0
FIND_EVERY_S = 3.0
IDLE_INTERVAL_S = 1.0  # pas du pont tant qu'aucune fenêtre du jeu n'est connue
OUTBOX_LIST_S = 30.0  # liste des sauvegardes relue (une nouvelle n'apparaît qu'au premier /reload d'un compte)
REJECT_LOG_S = 5.0
HEARTBEAT_S = 30.0  # dernier signe de vie écrit dans le verrou (sonde F : ponts tués sans trace)
UPDATE_CHECK_S = 5.0  # verrou et dernier passage de forever update relus (fin d'un passage publiée aussitôt)
CARDS_CHECK_S = 1.0  # cartes « À valider » relues (carte de test de selftest --card, attentes au bloc B)
SIMC_FLAG = "k=simc"
ADDONS_FLAG = "c=addons"  # message de l'onglet « Addons » (bloc F)
CONVERSATION_PREFIX = "c="  # CJ1, bloc 6b : autre conversation de jeu (`c=<id>`), chacune avec sa session


def game_conversation(flags: frozenset[str]) -> str | None:
    """Conversation de jeu nommée par le drapeau `c=<id>` (lettres et chiffres, jamais « addons ») ; None pour la
    conversation par défaut."""
    for flag in flags:
        if flag.startswith(CONVERSATION_PREFIX) and flag != ADDONS_FLAG:
            name = flag[len(CONVERSATION_PREFIX) :]
            if name.isalnum() and name.isascii():
                return name
    return None


ACTION_LABELS = {"approve": "Valider", "reject": "Refuser"}
ROUTE_BUTTON = "b=route"  # bouton « Feuille de route » (RX1)
ROUTE_GROUP = "Forever Routes"  # groupe des guides livrés dans RestedXP
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


def player_error(error: str | None) -> str:
    """Erreur de la conversation dite en mots de joueur (le détail reste dans le journal du pont)."""
    if error and "délai" in error:
        return "Pas de réponse à temps (délai dépassé) : repose ta question, le pont était peut-être occupé."
    return (
        "Je n'ai pas pu répondre : un problème est survenu de mon côté (détail dans le journal du pont, "
        "uv run forever bridge status). Repose ta question."
    )


def gear_levels(action: str | None, target: str | None) -> int | tuple[int, int] | None:
    """Niveau des actions d'équipement : « N » (N ≥ 1), ou « de-à » (1 ≤ de < à) pour `gear_level` et `gear_route`
    (route d'équipement d'une tranche, bloc 4d) ; None sinon."""
    low, sep, high = (target or "").partition("-")
    if not low.isdigit() or int(low) < 1:
        return None
    if not sep:
        return int(low)
    if action in ("gear_level", "gear_route") and high.isdigit() and int(high) > int(low):
        return int(low), int(high)
    return None


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
        updater: Any | None = None,
        heartbeat: Callable[[], None] | None = None,
        cards: Any | None = None,
        actions: Any | None = None,
        update_watch: Any | None = None,
        profile: Any | None = None,
        addons: Any | None = None,
        xp_watch: Callable[[], Mapping[str, Any] | None] | None = None,
        exporter: Callable[[Mapping[str, str], Sequence[Mapping[str, str]]], tuple[str, list[dict[str, str]]]]
        | None = None,
        gearer: Callable[[Mapping[str, str], Any], Any] | None = None,
        gear_router: Callable[[Mapping[str, str], Any], Any] | None = None,
        profession_router: Callable[[Mapping[str, str]], str] | None = None,
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
        self.updater = updater  # updater.UpdateOnClose : passage de forever update à la fermeture du jeu (décision 227)
        self.heartbeat = heartbeat
        self.cards = cards  # cards.CardSource : cartes « À valider » publiées (P06b)
        self.actions = actions  # actions.ActionHandler : Mettre à jour, Valider, Refuser (bloc B)
        self.update_watch = update_watch  # updater.UpdateWatch : fin d'un passage publiée aussitôt
        self.profile = profile  # profile_gap.ProfileWatch : écart entre le jeu et le profil (bloc C)
        self.addons = addons  # addons.AddonsTurn : conversation « addons » (bloc F)
        self.xp_watch = xp_watch  # T04f : identifiants surveillés par les addons (xp_bonuses.xp_watch)
        self.exporter = exporter  # EX1 : réponse du bouton Exports (exports.exports_reply), sans le modèle
        # essai CJ-6 et bloc 4c : « Mon équipement à ce niveau » et « En faire une route », sans le modèle
        self.gearer = gearer  # gear_level.gear_level_reply
        self.gear_router = gear_router  # gear_level.gear_route_reply
        self.profession_router = profession_router  # professions.profession_reply : assistant Métier, sans le modèle
        self.last_exports: list[dict[str, str]] = []  # EX1 : liens typés de la dernière réponse qui en portait
        self.last_update_check: float | None = None
        self.card_list: list[dict[str, Any]] = []
        self.choices: list[Choice] = []  # RX1 : questions à choix en attente (CJ1 : posées dans le chat)
        self.route_active = False  # CJ1 : une feuille de route est en cours (aperçu, ajustements, validation)
        self.routes_dir: Path | None = None  # RX1 : plans de forever route plan (`<cache>/routes`)
        self.guide: dict[str, Any] | None = None  # RX1 : guide RestedXP à livrer par l'emplacement
        self.last_cards_check: float | None = None
        self.fragments = FragmentBuffer()
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
            inbox = inbox_lua(
                self.epoch(), self.status_cache, self.state.replies, self.buttons, self._cards(), guide=self.guide
            )
            started = time.perf_counter()
            try:
                count = publish(self.addons_dir, inbox, self.slots, first)
            except OSError as exc:  # le jeu lit peut-être un fichier à cet instant : nouvel essai au pas suivant
                self.journal.write("error", where="publication", error=str(exc))
                self.last_refresh = None
                return
            ms = round((time.perf_counter() - started) * 1000, 1)
            self.journal.write("published", reason=reason, first=first, files=count, ms=ms)

    def _cards(self) -> list[dict[str, Any]]:
        """Cartes publiées : « À valider » de la source seulement (CJ1, décision 276 : plus aucune question en carte,
        les questions partent avec la réponse, sous le message)."""
        return list(self.card_list)

    def _pending_note(self) -> str:
        """Ligne fixe du pont pour le modèle : cartes « À valider » réellement montrées au joueur (CJ1, compteur
        cohérent avec la réponse)."""
        titles = [str(c.get("title") or c.get("id") or "") for c in self.card_list]
        if not titles:
            return "À valider (fenêtre du joueur) : aucune carte."
        return f"À valider (fenêtre du joueur) : {len(titles)} carte(s) : " + " ; ".join(titles)

    def _xp(self) -> Mapping[str, Any] | None:
        if self.xp_watch is None:
            return None
        try:
            return self.xp_watch()
        except ForeverError as exc:  # données sans bonus d'XP : aucune surveillance
            self.journal.write("error", where="xp_watch", error=exc.message)
            return None

    def refresh(self) -> None:
        """État des données relu ; `Status.lua` et toute la réserve réécrits."""
        self.status_cache = {**self.status(), "slots": self.slots}  # l'addon en tire les emplacements restants
        if self.addons is not None:
            self.status_cache["addons"] = self.addons.status()
        if self.keeper is not None:
            from forever.bridge.status import line_parts, status_line

            self.status_cache["addon"] = self.keeper.addon_state()
            if self.status_cache.get("version"):
                self.status_cache["line"] = status_line(self.status_cache)
                self.status_cache["line_head"], self.status_cache["line_tail"] = line_parts(self.status_cache)
        path = self.addons_dir / ADDON / "Status.lua"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            content = status_lua(self.status_cache, self.buttons, self.epoch(), self._cards(), self._xp())
            tmp.write_bytes(content.encode("utf-8"))
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
            fragment = parse_fragment(decoded.payload)
        except RecordError:
            self._rejected(now, "partie")
            return
        if fragment is not None:
            self._fragment(fragment, now)
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

    def _fragment(self, fragment: Fragment, now: float) -> None:
        """Partie d'un message trop long pour une bande (P06b) : gardée, parties reçues publiées pour que l'addon ne
        montre plus que les manquantes ; message complet lu comme un message ordinaire."""
        key = (fragment.session, fragment.message_id)
        with self._lock:
            if self.state.seen(*key):
                return
            before = self.fragments.received(*key)
            try:
                full = self.fragments.add(fragment)
            except RecordError:
                self._rejected(now, "partie")
                return
            if full is None and fragment.index in before:
                return  # partie déjà reçue : le carrousel la remontre, rien de nouveau
        if full is not None:
            try:
                record = parse_payload(full)
            except RecordError:
                self._rejected(now, "message")
                return
            self._accept(record, "pixels", parts=fragment.total)
            return
        got = self.fragments.received(*key)
        self.journal.write(
            "parts", session=fragment.session, id=fragment.message_id, index=fragment.index, total=fragment.total,
            got=got,
        )  # fmt: skip
        self.state.put_reply(
            {"session": fragment.session, "id": fragment.message_id, "status": "parts", "got": got,
             "total": fragment.total, "since": self.epoch()}
        )  # fmt: skip
        self._publish(self.first_slot, "parties")

    def _accept(self, record: Record, via: str, capture_ms: float | None = None, parts: int | None = None) -> None:
        simc = SIMC_FLAG in record.flags
        action = action_flag(record.flags)
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
                context=dict(record.context),
                text=f"(export SimulationCraft, {len(record.text)} caractères)" if simc else record.text,
                capture_ms=capture_ms,
                parts=parts or 1,
            )
            # après un /reload (boîte d'envoi), le compteur d'emplacements de l'addon est revenu à 1
            self.first_slot = record.slot if via == "pixels" and record.slot else 1
            if action is None and not simc:
                self.state.put_reply(
                    {"session": record.session, "id": record.message_id, "status": "working", "since": self.epoch()}
                )
                self.queue.append(record)
        if action is not None:
            self._action(record, action)
        elif simc:
            self._simc(record, parts or 1)
        else:
            self._publish(self.first_slot, "accusé")

    # --- actions et export, sans le modèle (P06b) ---------------------------------------------------------------

    def _done(
        self,
        record: Record,
        text: str,
        reason: str,
        links: Sequence[Mapping[str, str]] = (),
        *,
        choices: Mapping[str, Any] | None = None,
    ) -> None:
        reply: dict[str, Any] = {"session": record.session, "id": record.message_id, "status": "done", "text": text}
        if links:
            reply["links"] = [dict(link) for link in links]
        if choices:
            reply["choices"] = dict(choices)
        self.state.put_reply(reply)
        self._publish(self.first_slot, reason)

    @staticmethod
    def _typed_links(result: AgentResult, prefer: str | None, link: Any) -> list[dict[str, str]]:
        """EX1 : liens typés de la réponse, ceux du lien publié d'abord (`prefer`, sinon l'export du build) ; le lien
        Talents Forever publié (`link`) y figure toujours, en tête."""
        from forever.bridge.exports import typed_link

        found = (
            result.exports.get(prefer)
            if prefer
            else result.exports.get("build") or next(iter(result.exports.values()), [])
        )
        typed = [dict(e) for e in found or []]
        if isinstance(link, str) and not any(e["kind"] == "talents_forever" and e["text"] == link for e in typed):
            typed = [typed_link("talents_forever", link), *(e for e in typed if e["kind"] != "talents_forever")]
        return typed

    def _action(self, record: Record, flag: str) -> None:
        """Action `a=…` : jamais confiée à l'agent. Carte de test : notée, rien de lancé ; Mettre à jour, Valider et
        Refuser : commande fixée de `actions.ActionHandler` ; tout le reste est refusé."""
        parsed = parse_action(flag)
        action, target = parsed if parsed else (None, None)
        card = card_for(self.card_list, action, target) if action else None
        if card is not None and self.cards is not None and str(card.get("id", "")).startswith("selftest-"):
            result = "carte de test"
            label = ACTION_LABELS.get(str(action), str(action))
            text = f"Carte de test : « {label} » reçu par le pont ; rien n'est lancé."
            self.cards.done(str(card["id"]))
            self._check_cards(self.clock(), force=True)
        elif action in ("profile_apply", "profile_dismiss") and self.profile is not None and target:
            try:
                handle = self.profile.apply if action == "profile_apply" else self.profile.dismiss
                result, text = handle(target)
            except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                result, text = "erreur", self._oops("Profil non écrit", "profil", exc)
            self._check_cards(self.clock(), force=True)
        elif action == "choice" and target and (found := find_answer(self.choices, target)) is not None:
            choice, option = found
            self.choices = [c for c in self.choices if c.id != choice.id]
            answer = replace(record, flags=frozenset(), text=answer_text(option))
            with self._lock:
                self.state.put_reply(
                    {"session": record.session, "id": record.message_id, "status": "working", "since": self.epoch()}
                )
                self.queue.append(answer)
            self.journal.write("action", id=record.message_id, flag=flag, action=action, target=target,
                               result="transmise")  # fmt: skip
            self._publish(self.first_slot, "réponse à une question")
            return
        elif action == "exports" and self.exporter is not None:
            try:
                text, links = self.exporter(record.context, list(self.last_exports))
                result = "exports"
            except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                result, text, links = "erreur", self._oops("Exports impossibles", "exports", exc), []
            self.journal.write("action", id=record.message_id, flag=flag, action=action, target=target, result=result)
            self._done(record, text, "action", links)
            return
        elif action == "profession":
            if self.profession_router is None:
                result, text = "refusée", "Action refusée : métiers pas encore pris en charge par ce pont."
            else:
                try:
                    text, result = self.profession_router(record.context), "métiers"
                except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                    result, text = "erreur", self._oops("Métiers non lus", "métiers", exc)
            self.journal.write("action", id=record.message_id, flag=flag, action=action, target=target, result=result)
            self._done(record, text, "action", [])
            return
        elif action in ("gear_level", "gear_route") and gear_levels(action, target) is None:
            result, text = "refusée", "Action refusée : niveau invalide."
        elif action in ("gear_level", "gear_route") and target:
            handler = self.gearer if action == "gear_level" else self.gear_router
            gear_links: list[dict[str, str]] = []
            try:
                if handler is None:
                    result, text = "refusée", "Action refusée : équipement pas encore pris en charge par ce pont."
                else:
                    made = handler(record.context, gear_levels(action, target))
                    text, gear_links = made if isinstance(made, tuple) else (made, [])
                    result = "équipement"
            except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                result, text = "erreur", self._oops("Équipement non calculé", "équipement", exc)
            self.journal.write("action", id=record.message_id, flag=flag, action=action, target=target, result=result)
            offer = None
            if action == "gear_route" and result == "équipement" and "Valider et livrer : " in text:
                offer = {"prompt": "", "buttons": [dict(VALIDATE)]}  # bloc 4d : la route d'équipement se livre ici
            elif action == "gear_level" and result == "équipement":
                # décision 282 : la suite proposée sous la réponse, comme une question du chat
                offer = {"prompt": "", "buttons": [{"label": "Feuille de route de ces objets",
                                                    "action": f"gear_route:{target}"}]}  # fmt: skip
            self._done(record, text, "action", gear_links, choices=offer)
            return
        elif action == "route_deliver":
            try:
                result, text = self._deliver_route(record.context)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                result, text = "erreur", self._oops("Feuille de route illisible", "feuille de route", exc)
        elif action in ("update", "approve", "reject", "undo") and self.actions is not None:
            try:
                result, text = self.actions.handle(str(action), target)
            except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                result, text = "erreur", self._oops("Action non traitée", "action", exc)
            self.last_refresh = None  # attentes et passage relus au pas suivant
        else:
            result = "refusée"
            if parsed is None:
                why = "action inconnue"
            elif card is None:
                why = "carte inconnue ou déjà traitée"
            else:
                why = "action pas encore prise en charge par ce pont"
            text = f"Action refusée : {why}."
        self.journal.write("action", id=record.message_id, flag=flag, action=action, target=target, result=result)
        self._done(record, text, "action")

    def _oops(self, what: str, where: str, exc: BaseException) -> str:
        """Message de joueur pour une action en échec ; nom de l'exception et détail technique au journal seulement."""
        self.journal.write("error", where=where, error=f"{type(exc).__name__}: {exc}")
        return f"{what} : un problème est survenu de mon côté (détail dans le journal du pont, uv run forever bridge status)."

    def _deliver_route(self, context: Mapping[str, str]) -> tuple[str, str]:
        """RX1, CJ1 : dernier plan du personnage (nom du contexte, sinon classe et camp) encodé en guide RestedXP sous
        un nom stable et publié dans l'emplacement ; le jeu l'importe hors combat ; la réponse dit où le trouver."""
        import hashlib

        from forever.route import guide_name
        from forever.rxp import encode_guide

        paths = sorted(self.routes_dir.glob("*.json"), key=lambda p: p.stat().st_mtime) if self.routes_dir else []
        cls, faction = str(context.get("class") or "").lower(), str(context.get("faction") or "").lower()
        who = str(context.get("name") or "")
        docs = [json.loads(path.read_text(encoding="utf-8")) for path in reversed(paths)]
        mine = [d for d in docs if who and (d.get("request") or {}).get("character") == who]
        same = [
            d
            for d in docs
            if (not cls or d.get("class") == cls) and (not faction or d.get("faction") == faction)
            and not (d.get("request") or {}).get("character")
        ]  # fmt: skip
        plan = (mine or same or [None])[0]
        if plan is None:
            return "aucun plan", "Aucune feuille de route calculée : clique d'abord « Feuille de route »."
        name, group = guide_name(plan), ROUTE_GROUP
        text = encode_guide(plan, name=name, group=group)
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        self.guide = {"name": name, "group": group, "text": text, "sha": sha}
        self.route_active = False
        self.choices = []
        return "livrée", (
            f"Ta feuille de route « {name} » est envoyée à RestedXP (elle s'importe hors combat). Pour la suivre : ouvre "
            f"la liste des guides de RestedXP, groupe « {group} », puis « {name} ». Elle remplace la précédente du même "
            "nom ; s'il en reste deux, `forever route rxp-clean` (jeu fermé) retire les anciennes."
        )

    def _simc(self, record: Record, parts: int) -> None:
        """Export SimulationCraft collé : gardé anonymisé dans le journal (fixture réelle, décision 235), sans le
        modèle ; sa lecture arrive au bloc D."""
        from forever.simc import anonymize_simc

        text, original = anonymize_simc(record.text)
        lines = len(record.text.splitlines())
        self.journal.write(
            "simc_export", session=record.session, id=record.message_id, text=text, checksum_ok=original,
            anonymized=True, lines=lines, parts=parts,
        )  # fmt: skip
        if original is True:
            reply = f"Export SimulationCraft reçu ({lines} lignes, somme de contrôle juste)" + self._read_simc(record)
        elif original is False:
            reply = "Export SimulationCraft reçu, mais export incomplet ou modifié : recopiez /simc."
        else:
            reply = "Export SimulationCraft reçu sans somme de contrôle : export incomplet ou modifié : recopiez /simc."
        self._done(record, reply, "export")

    def _read_simc(self, record: Record) -> str:
        """Suite de la réponse à un export juste : lecture (bloc D), écarts avec le profil, carte proposée."""
        from forever.simc import parse_simc

        if self.profile is None:
            return ". Gardé, anonymisé, dans le journal du pont."
        try:
            export = parse_simc(record.text)
            gaps, warnings, proposed = self.profile.check_simc(record.context, export)
        except Exception as exc:  # noqa: BLE001 : un export illisible ne doit pas arrêter le pont
            self.journal.write("error", where="lecture de l'export", error=f"{type(exc).__name__}: {exc}")
            return ", mais illisible : recopiez /simc."
        self.journal.write(
            "simc_read", id=record.message_id, gaps=[g.field for g in gaps], warnings=warnings, proposed=proposed,
            items=len(export.items),
        )  # fmt: skip
        if proposed:
            self._check_cards(self.clock(), force=True)
        parts = [f" et lu : {len(export.items)} objet(s), fiche de {len(export.sheet)} rubrique(s)."]
        if gaps:
            parts.append(f"Écarts avec ton profil : {gaps_text(gaps)}.")
            parts.append("Mettre à jour le profil : voir À valider." if proposed else "Écart déjà ignoré.")
        else:
            parts.append("Aucun écart avec ton profil.")
        parts += [f"Note : {w}." for w in warnings]
        return "\n".join(parts)

    def _check_cards(self, now: float, *, force: bool = False) -> None:
        if self.cards is None:
            return
        if not force and self.last_cards_check is not None and now - self.last_cards_check < CARDS_CHECK_S:
            return
        self.last_cards_check = now
        try:
            cards = list(self.cards.current())
        except Exception as exc:  # noqa: BLE001 : une carte illisible ne doit pas arrêter le pont
            self.journal.write("error", where="cartes", error=f"{type(exc).__name__}: {exc}")
            return
        if cards != self.card_list:
            self.card_list = cards
            self.last_refresh = None  # Status.lua et toute la réserve réécrits au pas courant

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

    def _profile_gap(self, record: Record) -> tuple[str | None, bool]:
        """(ligne d'écart pour le message, carte proposée) ; jamais d'erreur vers le joueur."""
        if self.profile is None:
            return None, False
        try:
            gaps, proposed = self.profile.check(record.context)
        except Exception as exc:  # noqa: BLE001 : le profil ne doit jamais empêcher la réponse
            self.journal.write("error", where="écart avec le profil", error=f"{type(exc).__name__}: {exc}")
            return None, False
        if proposed:
            self._check_cards(self.clock(), force=True)
            self.journal.write("profile_gap", id=record.message_id, fields=[g.field for g in gaps])
        if not gaps:
            return None, False
        return f"Écart avec le profil : {gaps_text(gaps)}. {GAP_NOTE}", proposed

    def _work_addons(self, record: Record) -> None:
        """Tour de la conversation « addons » (`c=addons`) : sauvegarde, agent limité au dossier, commit local."""
        reply: dict[str, Any] = {"session": record.session, "id": record.message_id}
        started = self.clock()
        if self.addons is None:
            reply.update(status="error", text="Erreur : conversation « addons » non configurée (forever bridge addons "
                                              "config --source <dossier>).")  # fmt: skip
        else:
            session = None if "n" in record.flags else self.state.sessions.get("addons")
            self.journal.write("agent", id=record.message_id, resumed=session is not None, conversation="addons")
            try:
                result, tail = self.addons(record.text, session)
            except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                result, tail = (
                    AgentResult(text="", session_id=None, is_error=True, error=f"{type(exc).__name__}: {exc}"),
                    "",
                )
            if result.denied:
                self.journal.write("denied", id=record.message_id, tools=result.denied, conversation="addons")
            if result.is_error:
                reply.update(status="error", text=player_error(result.error))
                self.journal.write("error", id=record.message_id, where="conversation addons", error=result.error)
            else:
                text = normalize_reply(result.text)
                reply.update(status="done", text=f"{text}\n\n{tail}" if tail else text)
                if result.session_id:
                    self.state.set_conversation_session("addons", result.session_id)
                self.journal.write(
                    "reply", id=record.message_id, conversation="addons", seconds=round(self.clock() - started, 1),
                    length=len(text), tools=result.tools, cost_usd=result.cost_usd, commit=tail,
                )  # fmt: skip
        self.state.put_reply(reply)
        self._publish(self.first_slot, "réponse")

    def _work(self, record: Record) -> None:
        if ADDONS_FLAG in record.flags:
            try:
                self._work_addons(record)
            finally:
                with self._lock:
                    self.busy = False
            return
        if ROUTE_BUTTON in record.flags:  # RX1, CJ1 : feuille de route en cours, questions posées dans le chat
            self.choices = list(ROUTE_CHOICES)
            if "lv" in route_options(record.flags):  # CJ1, bloc 6a : niveaux choisis dans l'assistant, pas redemandés
                self.choices = [c for c in self.choices if c.id != "route_levels"]
            self.route_active = True
        try:
            conversation = game_conversation(record.flags)
            stored = self.state.sessions.get(f"game:{conversation}") if conversation else self.state.session
            session = None if "n" in record.flags else stored
            started = self.clock()
            self.journal.write("agent", id=record.message_id, resumed=session is not None)
            prefer: str | None = None
            proposed = False
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
                gap_note, proposed = self._profile_gap(record)
                result = self.agent(
                    message_text(record, talents=talents, guide=guide, profile=gap_note, pending=self._pending_note()),
                    session,
                )
            except Exception as exc:  # noqa: BLE001 : l'erreur est publiée au joueur
                result = AgentResult(text="", session_id=None, is_error=True, error=f"{type(exc).__name__}: {exc}")
            if result.denied:
                self.journal.write("denied", id=record.message_id, tools=result.denied)
            reply: dict[str, Any] = {"session": record.session, "id": record.message_id}
            if result.is_error:
                reply.update(status="error", text=player_error(result.error))
                self.journal.write("error", id=record.message_id, where="conversation", error=result.error)
            else:
                text = normalize_reply(result.text)
                notice = self._notice(record)
                if notice:
                    text = f"{text}\n\n{notice}"
                if proposed:
                    text = f"{text}\n\n{GAP_MENTION}"
                reply.update(status="done", text=text, provenance=provenance_line(result.provenances))
                link = result.links.get(prefer) if prefer else None
                if link or result.link:
                    reply["link"] = link or result.link
                typed = self._typed_links(result, prefer, reply.get("link"))
                if typed:
                    reply["links"] = typed
                    self.last_exports = typed
                if self.route_active:  # CJ1 : question en cours et « Valider et livrer » sous l'aperçu
                    asked = chat_choices(self.choices, validate=True)
                    if asked:
                        reply["choices"] = asked
                if result.session_id and conversation:
                    self.state.set_conversation_session(f"game:{conversation}", result.session_id)
                elif result.session_id:
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
        if self.updater is not None:
            try:
                self.updater.tick()
            except Exception as exc:  # noqa: BLE001 : le lancement de la mise à jour ne doit jamais arrêter le pont
                self.journal.write("error", where="mise à jour à la fermeture", error=f"{type(exc).__name__}: {exc}")
        self._check_cards(now)
        if self.update_watch is not None and (
            self.last_update_check is None or now - self.last_update_check >= UPDATE_CHECK_S
        ):
            self.last_update_check = now
            try:
                if self.update_watch.changed():
                    self.last_refresh = None  # passage commencé ou fini : état et cartes republiés aussitôt
            except Exception as exc:  # noqa: BLE001 : la surveillance ne doit jamais arrêter le pont
                self.journal.write(
                    "error", where="surveillance de forever update", error=f"{type(exc).__name__}: {exc}"
                )
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
