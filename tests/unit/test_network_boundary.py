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


def test_measures_refresh_reads_the_disk_only():
    """T04c : `forever measures refresh` lit les journaux et SavedVariables sur disque, sans aucun module réseau."""
    assert network_uses(PACKAGE / "pipeline" / "refresh.py") == set()
    assert network_uses(PACKAGE / "pipeline" / "measure.py") == set()


# --- T08d, bloc G : git et `gh` du clone dédié ----------------------------------------------------------------


def imported_modules(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_subprocess_only_in_gitops_and_the_detached_launch():
    """git et `gh` (réseau : fetch, push, API GitHub) ne passent que par `forever/pipeline/gitops.py` ; les seuls
    autres sous-processus sont le lancement détaché de `forever update` (`forever/spawn.py`, interpréteur Python) et
    la liste des processus du système pour savoir si le jeu est ouvert (`forever/pipeline/live_logs.py`, `tasklist`
    ou `ps`, local, décision 205)."""
    users = {
        str(path.relative_to(PACKAGE).as_posix())
        for path in PACKAGE.rglob("*.py")
        if "subprocess" in imported_modules(path)
    }
    assert users == {"pipeline/gitops.py", "spawn.py", "pipeline/live_logs.py"}
    spawn = (PACKAGE / "spawn.py").read_text(encoding="utf-8")
    assert '"git"' not in spawn and '"gh"' not in spawn
    live = (PACKAGE / "pipeline" / "live_logs.py").read_text(encoding="utf-8")
    assert '"git"' not in live and '"gh"' not in live and network_uses(PACKAGE / "pipeline" / "live_logs.py") == set()


def test_update_imports_no_network_module_nor_subprocess():
    path = PACKAGE / "update.py"
    assert network_uses(path) == set()
    assert "subprocess" not in imported_modules(path)
