"""Exports vers les addons d'interface dans le pont (EX1, bloc C) : liens typés d'une réponse (`links` de
l'emplacement : Talents Forever, code Naowh…), chacun copiable depuis le panneau d'action, et réponse du bouton
« Exports » rédigée par le pont sans le modèle (comme le résumé d'une attente, décision 235)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps

LABELS = {
    "talents_forever": "Talents Forever",
    "naowh_build": "Naowh : build",
    "naowh_macros": "Naowh : macros",
    "ellesmere": "EllesmereUI",
}


def typed_link(kind: str, text: str, label: str | None = None) -> dict[str, str]:
    """Lien typé de l'emplacement : `{kind, label, text}`."""
    return {"kind": kind, "label": label or LABELS[kind], "text": text}


def typed_links(value: Any) -> dict[str, list[dict[str, str]]]:
    """Liens typés d'un résultat d'outil forever, rangés comme `AgentResult.links` : `build` (export de
    `forever_build`), `closest` (build populaire le plus proche), `check` (`build_check`), `export`
    (`forever_lookup(kind="export")`)."""
    raise NotImplementedError


def exports_reply(
    deps: Deps, context: Mapping[str, str], last: Sequence[Mapping[str, str]]
) -> tuple[str, list[dict[str, str]]]:
    """Réponse du bouton « Exports » pour le personnage du contexte : texte (une ligne par export, ce qui manque
    dit) et liens typés à copier."""
    raise NotImplementedError
