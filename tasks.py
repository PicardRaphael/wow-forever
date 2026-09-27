"""Commandes du projet, identiques sous Windows, macOS et Linux : `uv run tasks.py <commande>`.

  test        tous les tests
  test-fast   tests unitaires rapides
  lint        ruff check
  fmt         ruff format
  typecheck   mypy strict sur forever/
  registry    contrôle du registre des mécaniques
  numbers     contrôle des chiffres de jeu dans le plugin
  verify      lint + typecheck + test + registry + numbers (définition de « fini »)
  status      fraîcheur des données (après T01)
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
STRICT_REGISTRY = False  # passer à True en T02 : une mécanique « modelise » sans test fera échouer verify


def run(cmd: list[str], ok_codes: tuple[int, ...] = (0,)) -> bool:
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode in ok_codes


PY = [sys.executable]


def test() -> bool:
    return run(PY + ["-m", "pytest", "-q"], ok_codes=(0, 5))  # 5 = aucun test (projet vide)


def test_fast() -> bool:
    if not (ROOT / "tests/unit").is_dir():
        print("tests/unit absent : rien à lancer")
        return True
    return run(PY + ["-m", "pytest", "-q", "-m", "not slow", "tests/unit"], ok_codes=(0, 5))


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


def verify() -> bool:
    results = {name: step() for name, step in
               [("lint", lint), ("typecheck", typecheck), ("test", test), ("registry", registry), ("numbers", numbers)]}
    print("\nVérification : " + " | ".join(f"{k} {'OK' if v else 'ÉCHEC'}" for k, v in results.items()))
    return all(results.values())


def status() -> bool:
    return run(PY + ["-m", "forever.cli", "status"])


COMMANDS = {"test": test, "test-fast": test_fast, "lint": lint, "fmt": fmt, "typecheck": typecheck,
            "registry": registry, "numbers": numbers, "verify": verify, "status": status}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(0 if COMMANDS[sys.argv[1]]() else 1)
