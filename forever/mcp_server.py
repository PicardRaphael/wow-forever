"""Serveur MCP : outils `forever_status` et `forever_lookup` (même cœur que la CLI)."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from forever.config import Deps


def build_server(deps: Deps) -> MCPServer:
    raise NotImplementedError
