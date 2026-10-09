"""Aucun processus durable ne tient `.venv\\Scripts\\forever.exe` (demande de l'utilisateur du 2026-10-09) : le serveur
MCP du plugin, celui que le pont passe à `claude` et les hooks lancent forever par l'interpréteur du projet en module
(`uv run --no-sync … python -m forever …`), jamais par le lanceur `forever.exe` que `uv sync` doit pouvoir remplacer ;
aucun hook ne synchronise l'environnement (`uv run` toujours avec `--no-sync` ou `--no-project`)."""

import ast
import json
import re
import sys

from conftest import REPO_ROOT

from forever.bridge.agent import mcp_config
from forever.spawn import update_command

PLUGIN = REPO_ROOT / "plugin"
DIRECT = re.compile(r"(?<!-m )\bforever(?:\.exe)? (?:mcp|hook|update|bridge)\b")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def assert_module_launch(args, where):
    assert "forever.exe" not in " ".join(args), where
    index = args.index("forever")
    assert args[index - 2 : index] == ["python", "-m"], (where, args)
    assert "--no-sync" in args, (where, args)


def test_plugin_mcp_server_runs_forever_as_a_module():
    for name, server in read_json(PLUGIN / ".mcp.json")["mcpServers"].items():
        assert server["command"] == "uv", name
        assert_module_launch(server["args"], f"plugin/.mcp.json {name}")


def test_bridge_mcp_server_runs_forever_as_a_module():
    server = mcp_config(REPO_ROOT)["mcpServers"]["forever"]
    assert server["command"] == "uv"
    assert_module_launch(server["args"], "pont : --mcp-config")


def hook_commands(doc):
    for groups in (doc.get("hooks") or {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command":
                    yield hook["command"]


def test_plugin_hooks_never_sync_nor_use_the_launcher():
    commands = list(hook_commands(read_json(PLUGIN / "hooks" / "hooks.json")))
    assert commands
    for command in commands:
        assert "forever.exe" not in command and not DIRECT.search(command), command
        assert "python -m forever" in command, command
        for run in re.findall(r"uv run[^;&|]*", command):
            assert "--no-sync" in run, command


def test_project_hooks_never_sync():
    commands = list(hook_commands(read_json(REPO_ROOT / ".claude" / "settings.json")))
    assert commands
    for command in commands:
        for run in re.findall(r"uv run[^;&|]*", command):
            assert "--no-sync" in run or "--no-project" in run, command
    for script in sorted((REPO_ROOT / ".claude" / "hooks").glob("*.py")):
        for node in ast.walk(ast.parse(script.read_text(encoding="utf-8"))):
            if isinstance(node, ast.List) and len(node.elts) >= 2:
                head = [e.value for e in node.elts[:2] if isinstance(e, ast.Constant)]
                if head == ["uv", "run"]:
                    rest = [e.value for e in node.elts[2:] if isinstance(e, ast.Constant)]
                    assert "--no-sync" in rest or "--no-project" in rest, (script.name, rest)


def test_bridge_and_update_launches_use_the_interpreter():
    assert update_command()[:4] == [sys.executable, "-u", "-m", "forever"]
    # pont : vrai interpréteur en module (décision 226), par `autostart.launch_bridge` (`bridge start`, surveillance)
    autostart = (REPO_ROOT / "forever" / "bridge" / "autostart.py").read_text(encoding="utf-8")
    assert "exe, env = spawn.current_interpreter()" in autostart
    assert '[exe, "-u", "-m", "forever", "bridge", "run"' in autostart
    assert "launch_bridge(" in (REPO_ROOT / "forever" / "cli.py").read_text(encoding="utf-8")
    for path in [*sorted((REPO_ROOT / "forever" / "bridge").glob("*.py")), PLUGIN / ".mcp.json"]:
        assert "forever.exe" not in path.read_text(encoding="utf-8"), path
