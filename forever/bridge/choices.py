"""Questions à choix du pont (RX1, bloc E, décision 258), ouvertes à toutes les conversations.

Une question (`Choice` : identifiant, intitulé, options) est publiée comme une carte « À valider » de sorte `choice`,
un bouton par option ; un clic envoie l'action `a=choice:<question>.<option>` (le drapeau `c=` désigne déjà la
conversation). Le pont apparie exactement la réponse aux questions publiées, retire la question et transmet à la
conversation le texte fixe « Réponse : <libellé> » ; une réponse inconnue est refusée et journalisée, jamais transmise.
Questions de la feuille de route : `ROUTE_CHOICES`. Aucun chiffre de jeu ici."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

CARD_PREFIX = "choice-"
ACTION = "choice"


@dataclass(frozen=True)
class Option:
    key: str
    label: str


@dataclass(frozen=True)
class Choice:
    id: str
    prompt: str
    options: tuple[Option, ...]
    multi: bool = False
    default: str | None = None


ROUTE_CHOICES: tuple[Choice, ...] = (
    Choice(
        "route_levels",
        "Feuille de route : combien de niveaux ?",
        (Option("3", "3 niveaux"), Option("5", "5 niveaux"), Option("10", "10 niveaux")),
        default="5",
    ),
    Choice(
        "route_dungeons",
        "Feuille de route : donjons ?",
        (Option("auto", "Donjons à leur meilleur niveau"), Option("none", "Sans donjon")),
        default="auto",
    ),
    Choice(
        "route_group", "Feuille de route : seul ou en groupe ?", (Option("solo", "Seul"), Option("group", "En groupe"))
    ),
    Choice(
        "route_class",
        "Feuille de route : quêtes de classe ?",
        (Option("yes", "Avec les quêtes de classe"), Option("no", "Sans les quêtes de classe")),
        default="yes",
    ),
)


def choice_card(choice: Choice) -> dict[str, Any]:
    """Carte « À valider » d'une question : un bouton par option, action `choice:<question>.<option>`."""
    return {
        "id": CARD_PREFIX + choice.id,
        "kind": "choice",
        "title": choice.prompt,
        "lines": [],
        "buttons": [
            {"key": o.key, "label": o.label, "action": f"{ACTION}:{choice.id}.{o.key}"} for o in choice.options
        ],
    }


def find_answer(choices: Sequence[Choice], target: str) -> tuple[Choice, Option] | None:
    """(question, option) publiées dont `<question>.<option>` vaut exactement `target` ; None sinon."""
    for choice in choices:
        for option in choice.options:
            if target == f"{choice.id}.{option.key}":
                return choice, option
    return None


def answer_text(option: Option) -> str:
    """Texte transmis à la conversation : « Réponse : <libellé> »."""
    return f"Réponse : {option.label}"
