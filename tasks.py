"""Commandes du projet, identiques sous Windows, macOS et Linux : `uv run tasks.py <commande>`.

quick       pendant le travail : lint + typage + tests rapides concernés par les fichiers modifiés depuis main
verify      une fois avant chaque push : lint + typage + suite complète en parallèle + registry + numbers + origins
            (définition de « fini ») ; `verify --data [--engines=a,b]` : vérification des données seulement
            (clone de `forever update`, décision 206), suite complète si autre chose que des données a changé
test        tous les tests, en parallèle
test-fast   tests rapides (hors `slow`), en parallèle
lint        ruff check
fmt         ruff format
typecheck   mypy strict sur forever/
registry    contrôle du registre des mécaniques
numbers     contrôle des chiffres de jeu dans le plugin
origins     contrôle de l'origine déclarée de chaque valeur des données (T08b)
e2e         bout en bout de forever update, CI simulée du clone comprise (long ; job e2e de la CI)
status      fraîcheur des données (après T01)

Règle : `quick` en boucle pendant le travail, `verify` une seule fois avant le push, la CI (Ubuntu et Windows) juge.
"""

import importlib.util
import os
import pathlib
import subprocess
import sys
from collections.abc import Callable, Sequence
from types import ModuleType

ROOT = pathlib.Path(__file__).resolve().parent
STRICT_REGISTRY = True  # depuis T02 : une mécanique « modelise » sans test fait échouer verify
PARALLEL = ["-n", "auto"]  # pytest-xdist : un processus par cœur
FAST = ["-m", "not slow"]  # tests marqués `slow` (Monte Carlo, rejeux, parité, bout en bout) : verify et CI seulement


def run(cmd: list[str], ok_codes: tuple[int, ...] = (0,)) -> bool:
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode in ok_codes


PY = [sys.executable]


def _selector() -> ModuleType:
    spec = importlib.util.spec_from_file_location("select_tests", ROOT / "scripts" / "select_tests.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("select_tests", module)
    spec.loader.exec_module(module)
    return module


def pytest(*args: str) -> bool:
    return run(PY + ["-m", "pytest", "-q", *args], ok_codes=(0, 5))  # 5 = aucun test


def test() -> bool:
    return pytest(*PARALLEL)


def test_fast() -> bool:
    return pytest(*PARALLEL, *FAST, "tests")


def lint() -> bool:
    return run(PY + ["-m", "ruff", "check", "."])


def fmt() -> bool:
    return run(PY + ["-m", "ruff", "format", "."])


def typecheck() -> bool:
    if not (ROOT / "forever").is_dir():
        print("forever/ absent : rien à typer")
        return True
    return run(PY + ["-m", "mypy", "forever"])


def registry() -> bool:
    return run(PY + ["scripts/check_registry.py"] + (["--strict"] if STRICT_REGISTRY else []))


def numbers() -> bool:
    return run(PY + ["scripts/check_game_numbers.py"])


def origins() -> bool:
    return run(PY + ["scripts/check_origins.py"])


def integrity() -> bool:
    """Intégrité de la version installée : manifeste et empreintes, puis contrôles de `forever verify`."""
    return run(PY + ["-m", "forever.cli", "manifest", "--check"]) & run(PY + ["-m", "forever.cli", "verify"])


def _summary(title: str, steps: Sequence[tuple[str, Callable[[], bool]]]) -> bool:
    results = {name: step() for name, step in steps}
    print(f"\n{title} : " + " | ".join(f"{k} {'OK' if v else 'ÉCHEC'}" for k, v in results.items()))
    return all(results.values())


def quick_selection() -> tuple[list[str] | None, list[str]]:
    """(fichiers de test concernés par les changements depuis main, ou None pour tous les tests rapides ; raisons)."""
    sel = _selector()
    selection = sel.select(sel.changed_since("main", ROOT), sel.TestIndex(ROOT))
    return selection.files, selection.reasons


def quick() -> bool:
    """Pendant le travail : lint, typage et tests rapides concernés par les fichiers modifiés depuis main."""
    files, reasons = quick_selection()
    for reason in reasons:
        print(f"  {reason}")
    if files is None:
        tests: Callable[[], bool] = test_fast
    elif not files:
        print("  aucun test concerné")
        tests = lambda: True
    else:
        print(f"  {len(files)} fichier(s) de test retenu(s)")
        tests = lambda: pytest(*PARALLEL, *FAST, *files)
    return _summary("Contrôle rapide", [("lint", lint), ("typecheck", typecheck), ("tests", tests)])


def uncommitted_paths() -> list[str]:
    return list(_selector().uncommitted(ROOT))


def verify(data: bool = False, engines: list[str] | None = None) -> bool:
    """Suite complète (avant le push, CI). `data` : vérification des données seulement si seules des données ont
    changé (clone de `forever update`) : intégrité, origines, registre, chiffres, tests des données et des moteurs
    `engines` (None : tous les moteurs)."""
    if data:
        sel = _selector()
        paths = uncommitted_paths()
        if sel.data_only(paths):
            index = sel.TestIndex(ROOT)
            chosen = list(sel.ENGINE_MODULES) if engines is None else engines
            files = sorted(set(sel.DATA_TESTS) | set(sel.engine_tests(index, chosen)))
            print(f"Vérification des données : moteurs {', '.join(chosen) or 'aucun'}, {len(files)} fichier(s) de test")
            return _summary(
                "Vérification des données",
                [
                    ("integrity", integrity),
                    ("origins", origins),
                    ("registry", registry),
                    ("numbers", numbers),
                    ("tests", lambda: pytest(*PARALLEL, *files)),
                ],
            )
        outside = [p for p in paths if not p.startswith(sel.DATA_ONLY_PREFIXES)]
        print(f"verify --data : changements hors des données ({', '.join(outside[:5]) or 'aucun'}) : suite complète")
    return _summary(
        "Vérification",
        [
            ("lint", lint),
            ("typecheck", typecheck),
            ("test", test),
            ("registry", registry),
            ("numbers", numbers),
            ("origins", origins),
        ],
    )


def e2e() -> bool:
    """Version fictive installée par `forever update`, vérification du clone et suite complète de la CI simulée
    comprises (décisions 192 et 206) ; hors de `test` : il tournerait aussi dans la CI simulée du clone."""
    env = {**os.environ, "FOREVER_E2E": "1"}
    cmd = PY + ["-m", "pytest", "-q", "tests/e2e"]
    print(f"$ FOREVER_E2E=1 {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode == 0


def status() -> bool:
    return run(PY + ["-m", "forever.cli", "status"])


COMMANDS: dict[str, Callable[[], bool]] = {
    "quick": quick,
    "verify": verify,
    "test": test,
    "test-fast": test_fast,
    "lint": lint,
    "fmt": fmt,
    "typecheck": typecheck,
    "registry": registry,
    "numbers": numbers,
    "origins": origins,
    "e2e": e2e,
    "status": status,
}


def main(argv: Sequence[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    name, options = argv[0], list(argv[1:])
    if name == "verify":
        data = "--data" in options
        engines: list[str] | None = None
        for option in options:
            if option.startswith("--engines="):
                engines = [e for e in option.removeprefix("--engines=").split(",") if e]
        if [o for o in options if o != "--data" and not o.startswith("--engines=")]:
            print(__doc__)
            return 2
        return 0 if verify(data=data, engines=engines) else 1
    if options:
        print(__doc__)
        return 2
    return 0 if COMMANDS[name]() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
