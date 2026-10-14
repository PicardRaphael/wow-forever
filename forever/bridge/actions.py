"""Actions du jeu traitées par le pont sans le modèle (P06b, décision 235). Un message porte le drapeau
`a=<action>[:<identifiant>]` ; le pont l'intercepte avant la file : l'agent n'est jamais appelé pour une action.
Liste fermée ; l'identifiant venu de la bande est apparié exactement à une entrée connue (carte de test publiée,
attente approuvable de `list_pending`, proposition de profil), jamais passé tel quel à une commande.

- Carte de test (`forever bridge selftest --card`, bloc A) : le pont note l'action et ne lance rien.
- Mise à jour (bloc B) : `update`, `approve:<id>`, `reject:<id>` lancent une commande fixée (`update_argv`) par
  `spawn` détaché, journal du passage dans `<cache>/update/` ; hors ligne, `update` est refusé ; un passage déjà en
  cours n'en relance pas un autre."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

ACTIONS = ("update", "approve", "reject", "profile_apply", "profile_dismiss", "choice", "route_deliver", "exports")
WITH_ID = frozenset({"approve", "reject", "profile_apply", "profile_dismiss", "choice"})
_ID = re.compile(r"[A-Za-z0-9._-]{1,120}")


def parse_action(flag: str) -> tuple[str, str | None] | None:
    """(action, identifiant) d'un drapeau `a=…` ; None si l'action n'est pas de la liste fermée, si l'identifiant
    manque, est en trop ou porte un caractère hors de `[A-Za-z0-9._-]`."""
    if not flag.startswith("a="):
        return None
    name, sep, target = flag[2:].partition(":")
    if name not in ACTIONS:
        return None
    if name in WITH_ID:
        return (name, target) if sep and _ID.fullmatch(target) else None
    return None if sep else (name, None)


def action_flag(flags: frozenset[str]) -> str | None:
    """Drapeau `a=…` du message, s'il en porte un."""
    return next((f for f in sorted(flags) if f.startswith("a=")), None)


def card_for(cards: Sequence[Mapping[str, Any]], action: str, target: str | None) -> Mapping[str, Any] | None:
    """Carte publiée dont l'identifiant est exactement `target` et qui offre le bouton de cette action."""
    if target is None:
        return None
    wanted = f"{action}:{target}"
    for card in cards:
        if card.get("id") != target:
            continue
        if any(isinstance(b, Mapping) and b.get("action") == wanted for b in card.get("buttons") or ()):
            return card
    return None


APPROVABLE_KINDS = ("install_version", "install_revision", "measures")
REJECT_REASON = "refusé en jeu"


def approvable(entry: Mapping[str, Any]) -> bool:
    """Attente que Valider et Refuser peuvent traiter : installation d'action `attente` ou mesure, à l'état
    `en_attente`."""
    return (
        entry.get("kind") in APPROVABLE_KINDS
        and entry.get("action") == "attente"
        and entry.get("state") == "en_attente"
    )


def update_argv(kind: str, pending_id: str | None = None) -> list[str]:
    """Commande fixée d'une action : passage, approbation ou rejet d'une attente."""
    from forever.spawn import update_command

    if kind == "update":
        return update_command()
    base = update_command()[:4]  # interpréteur, -u, -m, forever
    if kind == "approve" and pending_id:
        return [*base, "update", "approve", pending_id, "--json"]
    if kind == "reject" and pending_id:
        return [*base, "update", "reject", pending_id, "--reason", REJECT_REASON, "--json"]
    raise ValueError(f"action sans commande fixée : {kind}")


class ActionHandler:
    """Actions de mise à jour du jeu (bloc B) : commandes fixées lancées par `spawn(argv, journal_du_passage)`."""

    def __init__(
        self,
        *,
        cache_dir: Path,
        now: Callable[[], datetime],
        offline: bool = False,
        spawn: Callable[[Sequence[str], Path], None] | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.now = now
        self.offline = offline
        self.spawn = spawn or _spawn_detached

    def handle(self, action: str, target: str | None) -> tuple[str, str]:
        """(résultat noté au journal, texte de la réponse en mots de joueur, décision 240)."""
        from forever.bridge.cards import card_title
        from forever.bridge.status import update_stage
        from forever.update import list_pending, run_log_path, update_summary

        now = self.now()
        summary = update_summary(self.cache_dir, now)
        stage = update_stage(summary.get("running_step"), summary.get("running_detail"))
        if action == "update":
            if self.offline:
                return "refusée", "Mise à jour impossible : le pont tourne hors ligne sur ton PC."
            if summary.get("running"):
                return "passage en cours", f"Une mise à jour est déjà en cours ({stage}) : attends sa fin."
            return self._launch(update_argv("update"), run_log_path(self.cache_dir, now), "Mise à jour lancée.")
        if action not in ("approve", "reject") or target is None:
            return "refusée", "Action refusée : action inconnue."
        entry = next((e for e in list_pending(self.cache_dir) if e.get("id") == target), None)
        if entry is None:
            return "refusée", "Action refusée : cette carte n'existe plus."
        if not approvable(entry):
            return "refusée", "Action refusée : cette carte ne se valide pas en jeu."
        pending_id = str(entry["id"])  # identifiant relu dans l'attente, jamais celui de la bande
        title = card_title(entry)
        if action == "approve":
            later = f"mise à jour déjà en cours ({stage}), prise à la suivante" if summary.get("running") else ""
            text = f"Validé : {title} ; {later or 'mise à jour lancée'}."
        else:
            text = f"Refusé : {title}."
        return self._launch(update_argv(action, pending_id), run_log_path(self.cache_dir, now), text)

    def _launch(self, argv: list[str], log: Path, text: str) -> tuple[str, str]:
        try:
            self.spawn(argv, log)
        except OSError:
            return "erreur", "La mise à jour n'a pas pu démarrer sur ton PC : ouvre une session Claude."
        return "lancée", text


def _spawn_detached(argv: Sequence[str], log: Path) -> None:
    from forever.spawn import spawn_detached

    spawn_detached(argv, log)
