"""PostToolUse (Edit|Write|MultiEdit) : formate et corrige automatiquement les fichiers Python modifiés avec ruff.
Ne bloque jamais : le lint restant est vérifié par uv run tasks.py verify."""

import json
import os
import shutil
import subprocess
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)
path = (data.get("tool_input") or {}).get("file_path") or ""
if not path.endswith(".py") or not os.path.exists(path) or "/seed/" in path.replace(os.sep, "/"):
    sys.exit(0)
if shutil.which("uv") is None:
    sys.exit(0)
cwd = data.get("cwd") or os.getcwd()
subprocess.run(["uv", "run", "--no-sync", "ruff", "format", path], capture_output=True, cwd=cwd, check=False)
subprocess.run(["uv", "run", "--no-sync", "ruff", "check", "--fix", "--quiet", path], capture_output=True, cwd=cwd, check=False)
sys.exit(0)
