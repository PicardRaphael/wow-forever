"""Passage `forever update --auto` lancé par le pont quand le client a écrit ses fichiers (demande de l'utilisateur
du 2026-10-10, décision 227). Cas réel : connecté sur 1.60.1.70338 puis jeu quitté, les passages disaient encore
« aucun DBCache.bin du build 70338 archivé » ; le fichier avait été écrit une seconde après le dernier archivage, et
aucun passage n'était dû avant 6 h.

Le pont tourne en permanence (décision 226). Toutes les `CHECK_S` secondes, il relit l'état du jeu (processus du
client) et la date de `DBCache.bin`. Deux événements déclenchent un passage : le jeu qui se ferme (journal de combat
terminé) et `DBCache.bin` réécrit (le client l'écrit à la déconnexion du royaume en fin de session, et parfois en
début de partie, DON14). Le passage part une fois l'ensemble stable depuis `SETTLE_S` secondes (un événement de plus
relance l'attente) ; il prend lui-même le verrou de la tâche de 08:00 et du hook de démarrage. Verrou vivant (`launch`
rend faux) : nouvel essai au relevé suivant, jusqu'au lancement. Au premier relevé, rien n'est lancé : l'état d'avant
le pont est inconnu. État du jeu illisible : rien ne change. Aucun réseau ici : c'est le passage lancé qui y
accède."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from forever.bridge.journal import Journal

CHECK_S = 5.0  # relevé de l'état du jeu et de DBCache.bin (réglage de l'outil)
SETTLE_S = 15.0  # ensemble stable avant le lancement (réglage de l'outil)


class UpdateOnClose:
    def __init__(
        self,
        *,
        game_running: Callable[[], bool],
        dbcache: Path,
        journal: Journal,
        clock: Callable[[], float],
        launch: Callable[[], bool],
    ) -> None:
        self.game_running = game_running
        self.dbcache = dbcache
        self.journal = journal
        self.clock = clock
        self.launch = launch
        self.running: bool | None = None
        self.stamp: tuple[int, int] | None = None
        self.last_check: float | None = None
        self.reasons: set[str] = set()
        self.event_at: float | None = None
        self.deferred = False

    def _stamp(self) -> tuple[int, int] | None:
        try:
            st = self.dbcache.stat()
        except OSError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def _event(self, now: float, reason: str) -> None:
        self.reasons.add(reason)
        self.event_at = now
        self.journal.write(reason)

    def tick(self) -> None:
        """Un pas de la boucle du pont ; le relevé n'a lieu que toutes les `CHECK_S` secondes."""
        now = self.clock()
        if self.last_check is not None and now - self.last_check < CHECK_S:
            return
        self.last_check = now
        try:
            running = bool(self.game_running())
        except OSError:
            return  # état du jeu inconnu : on ne touche à rien
        stamp = self._stamp()
        if self.running is None:
            self.running, self.stamp = running, stamp
            return
        if stamp != self.stamp:
            if stamp is not None:
                self._event(now, "dbcache_written")
            self.stamp = stamp
        if self.running and not running:
            self._event(now, "game_closed")
        self.running = running
        if self.event_at is None or now - self.event_at < SETTLE_S:
            return
        reasons = sorted(self.reasons)
        try:
            launched = self.launch()
        except OSError as exc:
            self.journal.write("error", where="mise à jour à la fermeture", error=str(exc))
            self._reset()
            return
        if not launched:
            if not self.deferred:
                self.deferred = True
                self.journal.write("update_deferred", reasons=reasons, why="un passage tient le verrou")
            return
        self.journal.write("update_launched", reasons=reasons)
        self._reset()

    def _reset(self) -> None:
        self.reasons = set()
        self.event_at = None
        self.deferred = False
