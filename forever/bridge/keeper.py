"""Addon ForeverBridge tenu à jour par le pont (sonde en jeu F du 2026-10-09, point 3). Cas réel : après une fusion,
l'addon installé dans le jeu était encore l'ancienne version, jusqu'à un `forever bridge install` à la main. Le pont
compare l'addon installé à celui du dépôt (`install.addon_outdated`) au démarrage et à chaque rafraîchissement ; s'il
diffère, il le réinstalle dès que le jeu est fermé (vérifié toutes les `CHECK_S` secondes, jamais pendant qu'il
tourne : le client ne relit ses fichiers qu'à son lancement), puis l'annonce dans la ligne d'état pendant la partie
suivante. Jeu ouvert : « addon mis à jour à la prochaine fermeture du jeu »."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from forever.bridge.install import addon_outdated, install_bridge
from forever.bridge.journal import Journal
from forever.bridge.state import BridgeState
from forever.timefmt import format_utc

CHECK_S = 3.0


class AddonKeeper:
    def __init__(
        self,
        *,
        wow_dir: Path,
        addons_dir: Path,
        game_running: Callable[[], bool],
        journal: Journal,
        state: BridgeState,
        clock: Callable[[], float],
        slots: int,
        install: Callable[..., Any] = install_bridge,
    ) -> None:
        self.wow_dir = wow_dir
        self.addons_dir = addons_dir
        self.game_running = game_running
        self.journal = journal
        self.state = state
        self.clock = clock
        self.slots = slots
        self.install = install
        self.outdated: list[str] = []
        self.running: bool | None = None
        self.last_check: float | None = None

    def check(self) -> None:
        """Fichiers de l'addon installé à remplacer, relus (démarrage, rafraîchissement)."""
        try:
            self.outdated = addon_outdated(self.addons_dir)
        except OSError as exc:
            self.journal.write("error", where="addon installé", error=str(exc))
            self.outdated = []

    def addon_state(self) -> str | None:
        """Clé de `status.ADDON_LINES` : en_attente (à remplacer, jeu ouvert), mis_a_jour (annonce), ou None."""
        if self.outdated:
            return "en_attente"
        if self.state.addon_updated_at:
            return "mis_a_jour"
        return None

    def tick(self) -> bool:
        """Un pas : jeu fermé et addon à remplacer → réinstallation ; partie suivante terminée → fin de l'annonce.
        Vrai si l'état affiché a changé."""
        if not self.outdated and not self.state.addon_updated_at:
            return False
        now = self.clock()
        if self.last_check is not None and now - self.last_check < CHECK_S:
            return False
        self.last_check = now
        before = self.addon_state()
        try:
            running = bool(self.game_running())
        except OSError:
            return False  # état du jeu inconnu : on ne touche à rien
        if self.outdated and not running:
            self._reinstall()
        elif not self.outdated and self.state.addon_updated_at:
            if running:
                self.state.set_addon_notice(self.state.addon_updated_at, seen_running=True)
            elif self.state.addon_seen_running:
                self.state.set_addon_notice(None)
        self.running = running
        return self.addon_state() != before

    def _reinstall(self) -> None:
        files = list(self.outdated)
        try:
            self.install(self.wow_dir, slots=self.slots)
        except Exception as exc:  # noqa: BLE001 : la réinstallation est retentée au prochain contrôle
            self.journal.write("error", where="réinstallation de l'addon", error=f"{type(exc).__name__}: {exc}")
            return
        self.check()
        if self.outdated:
            self.journal.write("error", where="réinstallation de l'addon", error="fichiers toujours différents")
            return
        when = format_utc(self.journal.now())
        self.state.set_addon_notice(when, seen_running=False)
        self.journal.write("addon_updated", files=files)
