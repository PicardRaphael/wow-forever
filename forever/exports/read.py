"""Relecture de n'importe quelle chaîne d'export d'EX1 (`forever export read`, `forever_lookup(kind="export",
name="read")`) : préfixe reconnu, contenu rendu en nos clés quand c'est possible, pour le recoupement et la question
NFB1 (un build exporté par Naowh en jeu, collé dans le chat)."""

from __future__ import annotations

from typing import Any

from forever.config import Deps
from forever.errors import InvalidArgumentError
from forever.exports.codec import ExportFormatError

KNOWN_PREFIXES = ("!NFB1!",)


def read_export(deps: Deps, text: str) -> dict[str, Any]:
    """Contenu d'une chaîne d'export ; `InvalidArgumentError` en français si elle est illisible ou inconnue."""
    from forever.exports.naowh import BUILD_PREFIX, NAOWH_VERSION, read_naowh_build
    from forever.gamedata import build_game_data
    from forever.provenance import local_provenance
    from forever.store import load_version

    body = text.strip()
    try:
        if body.startswith(BUILD_PREFIX):
            build = read_naowh_build(body)
            gd = build_game_data(load_version(deps))
            knowledge = next((k for k in gd.classes.values() if k.id == build.class_id), None)
            keys = {}
            if knowledge is not None:
                keys = {int(t["node_id"]): t["key"] for tree in knowledge.trees for t in tree["talents"]}
            order = [keys.get(n) for n in build.points]
            unknown = sorted({n for n, k in zip(build.points, order, strict=True) if k is None})
            notes = [f"chaîne !NFB1! relue (format de Naowh Forever {NAOWH_VERSION})"]
            if unknown:
                notes.append(f"nœuds absents de nos données : {', '.join(map(str, unknown))}")
            return {
                "kind": "naowh_build",
                "class": knowledge.name if knowledge else None,
                "class_id": build.class_id,
                "name": build.name,
                "spec": build.spec,
                "points": list(build.points),
                "order": order,
                "unknown_nodes": unknown,
                "provenance": local_provenance(deps, certainty="probable", assumptions=notes),
            }
    except ExportFormatError as err:
        raise InvalidArgumentError(
            f"Chaîne d'export illisible : {err}.", "coller la chaîne entière, telle quelle"
        ) from err
    raise InvalidArgumentError(
        "Chaîne d'export inconnue (préfixe non reconnu).", "préfixes lus : " + ", ".join(KNOWN_PREFIXES)
    )
