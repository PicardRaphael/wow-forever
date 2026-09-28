"""Hypothèses incertaines et leurs variantes : une copie des données où une seule hypothèse prend une autre valeur de
sa plage (`range` de l'entrée de `mechanics.json`), pour mesurer la sensibilité d'un résultat (T05, décision 81).

Fonctions pures : `with_assumption` rend une nouvelle `GameData` (`dataclasses.replace`), l'originale est inchangée.
Le mode seed ne lit aucune de ces clés (parité avec le seed)."""

from __future__ import annotations

from typing import Any

from forever.engine.model import GameData, Variant

# Nom de l'hypothèse -> clé de mechanics.json qui porte sa valeur et sa plage.
ASSUMPTIONS: dict[str, str] = {
    "a3_miss": "hit.miss_per_level_below",
    "ignite_rule": "leveling.ignite_rule",
    "mob_hp": "leveling.mob_source",
    "regen_stacking": "mana.regen_stacking",
    "low_level_penalty": "coefficient.low_level_default",
    "bonus_stacking": "damage.bonus_stacking",
    "ice_lance_coef": "coefficient.ice_lance_source",
}


def assumption_range(gd: GameData, name: str) -> tuple[Variant, ...]:
    """Plage d'une hypothèse (valeur des données en premier), lue dans `mechanics.json` ; ValueError si le nom est
    inconnu.

    Registre : I5"""
    raise NotImplementedError


def current_value(gd: GameData, name: str) -> Any:
    """Valeur de l'hypothèse dans `gd`.

    Registre : I5"""
    raise NotImplementedError


def with_assumption(gd: GameData, name: str, value: Any) -> GameData:
    """Copie de `gd` où l'hypothèse `name` vaut `value` (une valeur de sa plage) ; ValueError sinon.

    Registre : A3, A18, A20, B7, G4, H11"""
    raise NotImplementedError
