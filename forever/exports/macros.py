"""Macros par classe (EX1, bloc D, décision 195) : texte de macros au format d'import de Naowh Forever (`!NFM1!`),
calculé depuis le catalogue `macros.yaml` (clés de sorts) et les sorts de la classe appris au niveau (`classes.json`,
noms anglais du client enUS). Seulement `/cast`, `/use`, `/stopcasting`, `/startattack` et `#showtooltip` : jamais
`/run`, `/script`, `/dump` ni commande d'un autre addon. `/cast` sans rang (le jeu prend le meilleur rang appris :
`suppose`, question MAC1). Notre addon ne crée, n'édite ni ne lance aucune macro : le joueur colle la chaîne."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from forever.config import Deps
from forever.engine.model import GameData

ALLOWED_COMMANDS = ("/cast", "/use", "/stopcasting", "/startattack")
TEMPLATES: dict[str, tuple[str, ...]] = {
    "help": ("#showtooltip", "/cast [@mouseover,help,nodead][] {spell}"),
    "focus": ("#showtooltip", "/cast [@focus,harm,nodead][] {spell}"),
    "interrupt": ("#showtooltip", "/stopcasting", "/cast {spell}"),
    "melee": ("#showtooltip", "/startattack", "/cast {spell}"),
}
NAME_PREFIX = "F "


@dataclass(frozen=True)
class Macro:
    name: str
    body: str
    spell: str
    template: str


def macro_violations(body: str) -> list[str]:
    """Lignes interdites d'un corps de macro : toute commande hors de `ALLOWED_COMMANDS` (dont `/run`, `/script`,
    `/dump`), toute directive `#` autre que `#showtooltip`."""
    raise NotImplementedError


def class_macros(gd: GameData, class_name: str, level: int, talents: Mapping[str, int] | None = None) -> list[Macro]:
    raise NotImplementedError


def macros_export(deps: Deps, class_name: str, level: int, talents: Mapping[str, int] | None = None) -> dict[str, Any]:
    raise NotImplementedError
