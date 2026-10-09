"""Boutons de la fenêtre ForeverBridge (P06a, décision 212 amendée le 2026-10-09) : chaque bouton envoie une
question fixe par le même chemin que le chat. Un bouton n'apparaît que si les tranches qui le calculent sont faites
(`DONE_SLICES`, fixé au plan et suivi avec `docs/ROADMAP.md`) et pour les classes qu'elles servent ; le pont écrit la
liste dans `Status.lua` et dans chaque emplacement, l'addon n'affiche que ce qu'il reçoit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from typing import Any

# Tranches faites qui calculent un bouton (feuille de route du 2026-10-09).
DONE_SLICES: frozenset[str] = frozenset({"T04b", "T04c", "T05", "FA1", "CH0", "PV1"})

TALENTS_NOTICE = "Build populaire de Talents Forever (choix de joueurs), pas encore calculé par le moteur de forever."


@dataclass(frozen=True)
class Button:
    key: str
    label: str
    question: str
    requires: tuple[str, ...]
    classes: tuple[str, ...] | None = None  # None : toutes les classes
    questions: Mapping[str, str] = field(default_factory=dict)  # question propre à une classe
    computed_for: tuple[str, ...] | None = None  # classes calculées par le moteur ; ailleurs, la mention
    notice: str | None = None
    needs_player_target: bool = False

    def question_for(self, class_token: str) -> str:
        return self.questions.get(class_token, self.question)

    def notice_for(self, class_token: str) -> str | None:
        if self.notice is None or self.computed_for is None or class_token in self.computed_for:
            return None
        return self.notice


BUTTONS: tuple[Button, ...] = (
    Button(
        "talents",
        "Talents",
        "Quel build populaire de Talents Forever est le plus proche de mes talents actuels ? "
        "Donne son lien Talents Forever.",
        ("FA1", "T05"),
        questions={"MAGE": "Quel est mon prochain talent, avec le lien Talents Forever ?"},
        computed_for=("MAGE",),
        notice=TALENTS_NOTICE,
    ),
    Button("leveling", "Leveling", "Quel est mon prochain objectif de leveling ?", ("T04b", "T04c"), ("MAGE",)),
    Button("pets", "Familiers", "Où apprivoiser le prochain rang utile près de moi ?", ("CH0",), ("HUNTER",)),
    Button("pvp", "PvP", "Fiche de la classe de ma cible", ("PV1",), needs_player_target=True),
    Button("gear", "Équipement", "Quel est mon prochain objet à viser, et où le trouver ?", ("T10a",)),
    Button("last_fight", "Dernier combat", "Résume mon dernier combat analysé.", ("AN1", "AN2")),
    Button("update", "Mettre à jour", "", ("P06b",)),
)


def visible_buttons(done: AbstractSet[str] = DONE_SLICES) -> list[Button]:
    """Boutons dont toutes les tranches sont faites, dans l'ordre de BUTTONS."""
    return [b for b in BUTTONS if set(b.requires) <= done]


def button_payload(buttons: Sequence[Button]) -> list[dict[str, Any]]:
    """Liste écrite pour l'addon : clé, libellé, question, questions par classe, classes, cible joueur requise."""
    out: list[dict[str, Any]] = []
    for b in buttons:
        entry: dict[str, Any] = {"key": b.key, "label": b.label, "question": b.question}
        if b.questions:
            entry["questions"] = dict(b.questions)
        if b.classes is not None:
            entry["classes"] = list(b.classes)
        if b.needs_player_target:
            entry["target"] = True
        out.append(entry)
    return out
