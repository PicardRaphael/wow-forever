"""Serveur MCP : outils `forever_status` et `forever_lookup` (même cœur que la CLI).

Une erreur métier est renvoyée comme résultat d'outil (`is_error`, `structured_content` avec l'erreur et la
provenance) : une exception brute ne montrerait au modèle qu'un message générique."""

from __future__ import annotations

import json
from typing import cast

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from forever import __version__
from forever.config import Deps
from forever.errors import ForeverError, UnsupportedKindError
from forever.lookup import SpellLookup, lookup_spell
from forever.provenance import error_payload
from forever.status import StatusReport, status_report

INSTRUCTIONS = (
    "Données de World of Warcraft: Forever, versionnées par version du jeu. Chaque résultat porte un bloc "
    "`provenance` (version, empreinte, fraîcheur, certitude, hypothèses) à citer dans la réponse."
)


def _error_result(deps: Deps, err: ForeverError) -> CallToolResult:
    payload = error_payload(deps, err)
    text = f"Erreur ({err.code}) : {err.message} À faire : {err.action}."
    if err.suggestions:
        text += f" Suggestions : {', '.join(err.suggestions)}."
    return CallToolResult(
        is_error=True,
        structured_content=json.loads(json.dumps(payload)),
        content=[TextContent(type="text", text=text)],
    )


def build_server(deps: Deps) -> MCPServer:
    server = MCPServer("forever", version=__version__, instructions=INSTRUCTIONS)

    @server.tool()
    def forever_status(offline: bool = False) -> StatusReport:
        """Fraîcheur des données (dernière version publiée du jeu), intégrité des empreintes, couverture du registre.

        `offline=True` : aucun appel réseau, dernier état connu seulement."""
        return status_report(deps, allow_network=not offline)

    @server.tool()
    def forever_lookup(
        kind: str,
        name: str,
        rank: int | None = None,
        detail: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> SpellLookup:
        """Consulte une entité du jeu. T01 : `kind="spell"` (sorts de dégâts, nom anglais, ex. « frostbolt »).

        `rank` : position du rang à partir de 1 (tous les rangs, paginés, s'il est omis).
        `detail=True` : champs complémentaires (ralentissement, vitesse de projectile…)."""
        try:
            if kind != "spell":
                raise UnsupportedKindError(f"type « {kind} »", ["spell"])
            return lookup_spell(deps, name, rank, detail=detail, limit=limit, offset=offset)
        except ForeverError as err:
            # Le SDK transmet tel quel un CallToolResult renvoyé par l'outil (vérifié avec mcp 2.2).
            return cast(SpellLookup, _error_result(deps, err))

    return server
