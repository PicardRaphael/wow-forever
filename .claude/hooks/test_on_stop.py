"""Stop : si du code a changé, lance les tests rapides concernés avant que Claude ne s'arrête.
- Sélection de `uv run tasks.py quick` (`scripts/select_tests.py`) : tests concernés par les fichiers modifiés depuis
  main, hors `slow`, ou tous les tests rapides pour un fichier partagé ; aucun test concerné : rien n'est lancé.
- Les tests listés dans tasks/.rouge (phase rouge d'une tranche) sont ignorés.
- Anti-boucle : ne relance pas si l'arrêt a déjà été bloqué une fois (stop_hook_active)."""

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    data = {}
if data.get("stop_hook_active"):
    sys.exit(0)
cwd = data.get("cwd") or "."
changed = subprocess.run(
    ["git", "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True, cwd=cwd, check=False
).stdout
if not any(p.endswith((".py", ".yaml", ".json")) for p in (line[3:] for line in changed.splitlines())):
    sys.exit(0)
if not pathlib.Path(cwd, "tests/unit").is_dir():
    sys.exit(0)
if shutil.which("uv"):
    runner = ["uv", "run", "pytest"]
elif importlib.util.find_spec("pytest"):
    runner = [sys.executable, "-m", "pytest"]
else:
    sys.exit(0)  # impossible de lancer les tests ici : ne pas bloquer
cmd = runner + ["-q", "-m", "not slow"]
selector = pathlib.Path(cwd, "scripts", "select_tests.py")
if selector.is_file():
    spec = importlib.util.spec_from_file_location("select_tests", selector)
    assert spec and spec.loader
    sel = importlib.util.module_from_spec(spec)
    sys.modules["select_tests"] = sel
    spec.loader.exec_module(sel)
    root = pathlib.Path(cwd).resolve()
    files = sel.select(sel.changed_since("main", root), sel.TestIndex(root)).files
    if files == []:
        sys.exit(0)  # aucun test concerné
    cmd += ["-n", "auto"] + (files if files is not None else ["tests"])
else:
    cmd += ["tests/unit"]
rouge = pathlib.Path(cwd, "tasks/.rouge")
if rouge.exists():
    for test_id in (line.strip() for line in rouge.read_text(encoding="utf-8").splitlines()):
        if test_id:
            cmd += ["--deselect", test_id]
r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)
if r.returncode not in (0, 5):
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-25:])
    print(
        f"Les tests rapides échouent (hors tests attendus rouges). Corrige avant de t'arrêter :\n{tail}",
        file=sys.stderr,
    )
    sys.exit(2)
sys.exit(0)
