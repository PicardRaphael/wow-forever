"""Règle réseau (CLAUDE.md) : seul forever/pipeline/ ouvre des connexions ; le client de production y vit."""

import ast

from conftest import REPO_ROOT

from forever.config import default_deps

PACKAGE = REPO_ROOT / "forever"
NETWORK_MODULES = {"urllib.request", "http.client", "socket", "ssl", "httpx", "requests", "urllib3", "aiohttp"}


def network_uses(path):
    """Modules réseau importés et appels `urlopen` d'un fichier source."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names if alias.name in NETWORK_MODULES}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = {node.module} | {f"{node.module}.{alias.name}" for alias in node.names}
            found |= modules & NETWORK_MODULES
        elif (isinstance(node, ast.Name) and node.id == "urlopen") or (
            isinstance(node, ast.Attribute) and node.attr == "urlopen"
        ):
            found.add("urlopen")
    return found


def test_no_network_outside_pipeline():
    offenders = {
        str(path.relative_to(REPO_ROOT)): sorted(uses)
        for path in PACKAGE.rglob("*.py")
        if "pipeline" not in path.relative_to(PACKAGE).parts and (uses := network_uses(path))
    }
    assert offenders == {}


def test_pipeline_is_detected_as_network():
    assert "urlopen" in network_uses(PACKAGE / "pipeline" / "http_client.py")


def test_production_client_comes_from_pipeline():
    from forever.pipeline.http_client import urllib_get

    assert default_deps({}).http_get is urllib_get
