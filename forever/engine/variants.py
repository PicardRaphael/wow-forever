"""Hypothèses incertaines et leurs variantes : une copie des données où une seule hypothèse prend une autre valeur de
sa plage (`range` de l'entrée de `mechanics.json`), pour mesurer la sensibilité d'un résultat (T05, décision 81).

Fonctions pures : `with_assumption` rend une nouvelle `GameData` (`dataclasses.replace`), l'originale est inchangée.
Le mode seed ne lit aucune de ces clés (parité avec le seed)."""

from __future__ import annotations

from dataclasses import replace
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


def _key(name: str) -> str:
    if name not in ASSUMPTIONS:
        raise ValueError(f"hypothèse inconnue « {name} » ({', '.join(ASSUMPTIONS)} attendue)")
    return ASSUMPTIONS[name]


def assumption_range(gd: GameData, name: str) -> tuple[Variant, ...]:
    """Plage d'une hypothèse (valeur des données en premier), lue dans `mechanics.json` ; ValueError si le nom est
    inconnu.

    Registre : I5"""
    return tuple(gd.assumption_ranges[_key(name)])


def current_value(gd: GameData, name: str) -> Any:
    """Valeur de l'hypothèse dans `gd`.

    Registre : I5"""
    _key(name)
    c = gd.constants
    values: dict[str, Any] = {
        "a3_miss": c.miss_per_level_below,
        "ignite_rule": gd.leveling.ignite_rule,
        "mob_hp": gd.leveling.mob_source,
        "regen_stacking": c.regen_stacking,
        "low_level_penalty": c.coefficients.low_level_default,
        "bonus_stacking": c.bonus_stacking,
        "ice_lance_coef": c.coefficients.ice_lance_source,
    }
    return values[name]


def with_assumption(gd: GameData, name: str, value: Any) -> GameData:
    """Copie de `gd` où l'hypothèse `name` vaut `value` (une valeur de sa plage) ; ValueError sinon.

    Registre : A3, A18, A20, B7, G4, H11"""
    allowed = [v.value for v in assumption_range(gd, name)]
    if not any(type(value) is type(a) and value == a for a in allowed):
        raise ValueError(f"{name} = {value!r} hors de la plage des données ({', '.join(map(repr, allowed))})")
    c, lv = gd.constants, gd.leveling
    if name == "ignite_rule":
        return replace(gd, leveling=replace(lv, ignite_rule=value))
    if name == "mob_hp":
        return replace(gd, leveling=replace(lv, mob_source=value))
    if name == "low_level_penalty":
        return replace(gd, constants=replace(c, coefficients=replace(c.coefficients, low_level_default=value)))
    if name == "ice_lance_coef":
        return replace(gd, constants=replace(c, coefficients=replace(c.coefficients, ice_lance_source=value)))
    field = {"a3_miss": "miss_per_level_below", "regen_stacking": "regen_stacking", "bonus_stacking": "bonus_stacking"}
    return replace(gd, constants=replace(c, **{field[name]: value}))
