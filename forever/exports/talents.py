"""Builds de talents vers Naowh Forever (EX1, bloc B) : points d'un build en nœuds du client (`node_id` de
`classes.json`, TraitNodeID chez Naowh), un par point, dans l'ordre de prise ; ordre de leveling quand il existe,
sinon ordre légal généré par le moteur (`forever/engine/talents.py`) et signalé comme tel."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from forever.config import Deps
from forever.engine.model import ClassKnowledge

ORDER_NOTE = "ordre généré (légal à chaque prise), pas un ordre de leveling"


def naowh_points(knowledge: ClassKnowledge, order: Sequence[str]) -> tuple[int, ...]:
    raise NotImplementedError


def naowh_export(
    deps: Deps,
    class_name: str,
    level: int,
    talents: Mapping[str, int],
    order: Sequence[str] | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    raise NotImplementedError
