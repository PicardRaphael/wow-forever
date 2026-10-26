"""Stop : si du code a changé, lance les tests rapides concernés avant que Claude ne s'arrête.
- Sélection de `uv run tasks.py quick` (`scripts/select_tests.py`) : tests concernés par les fichiers modifiés depuis
  main, hors `slow`, ou tous les tests rapides pour un fichier partagé ; aucun test concerné : rien n'est lancé.
- Les tests listés dans tasks/.rouge (phase rouge d'une tranche) sont ignorés.
- Arbre déjà vert (même empreinte que le dernier passage réussi, gardée dans le dossier .git) : rien n'est relancé.
- Budget sous le délai du hook (300 s) : au-delà, les tests et leurs processus enfants sont arrêtés, sans bloquer.
- Anti-boucle : ne relance pas si l'arrêt a déjà été bloqué une fois (stop_hook_active)."""

import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys

BUDGET_S = 270


def _git(cwd, *args):
    return subprocess.run(["git", *args], capture_output=True, cwd=cwd, check=False).stdout


def fingerprint(cwd):
    """Empreinte de l'arbre de travail : HEAD, modifications suivies, fichiers non suivis et tests attendus rouges."""
    h = hashlib.sha256()
    h.update(_git(cwd, "rev-parse", "HEAD"))
    h.update(_git(cwd, "diff", "HEAD", "--binary"))
    for name in _git(cwd, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if name:
            h.update(name + b"\0")
            path = pathlib.Path(cwd, os.fsdecode(name))
            h.update(path.read_bytes() if path.is_file() else b"")
    rouge = pathlib.Path(cwd, "tasks/.rouge")
    h.update(rouge.read_bytes() if rouge.is_file() else b"")
    return h.hexdigest()


def _green_file(cwd):
    return pathlib.Path(cwd, os.fsdecode(_git(cwd, "rev-parse", "--git-path", "forever-stop-hook").strip()))


def already_green(cwd):
    green = _green_file(cwd)
    return green.is_file() and green.read_text(encoding="utf-8") == fingerprint(cwd)


def record_green(cwd):
    _green_file(cwd).write_text(fingerprint(cwd), encoding="utf-8")


def run_with_budget(cmd, cwd, budget=BUDGET_S):
    """Lance cmd ; au-delà du budget, arrête tout l'arbre de processus (workers de pytest-xdist compris), rend None."""
    kwargs = {"start_new_session": True} if os.name != "nt" else {}
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
    try:
        out, err = p.communicate(timeout=budget)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, check=False)
        else:
            os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        return None
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}
    if data.get("stop_hook_active"):
        sys.exit(0)
    cwd = data.get("cwd") or "."
    changed = _git(cwd, "status", "--porcelain", "--untracked-files=all").decode("utf-8", "replace")
    if not any(p.endswith((".py", ".yaml", ".json")) for p in (line[3:] for line in changed.splitlines())):
        sys.exit(0)
    if not pathlib.Path(cwd, "tests/unit").is_dir():
        sys.exit(0)
    if already_green(cwd):
        sys.exit(0)
    if shutil.which("uv"):
        runner = ["uv", "run", "--no-sync", "pytest"]  # jamais de sync : uv sync explicite seulement
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
    r = run_with_budget(cmd, cwd)
    if r is None:
        print(
            json.dumps(
                {
                    "systemMessage": f"Tests rapides arrêtés après {BUDGET_S} s (sélection trop large pour la fin "
                    "de tour) : lancer `uv run tasks.py quick`."
                },
                ensure_ascii=False,
            )
        )
        sys.exit(0)
    if r.returncode not in (0, 5):
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-25:])
        print(
            f"Les tests rapides échouent (hors tests attendus rouges). Corrige avant de t'arrêter :\n{tail}",
            file=sys.stderr,
        )
        sys.exit(2)
    record_green(cwd)
    sys.exit(0)


if __name__ == "__main__":
    main()
