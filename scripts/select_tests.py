"""Sélection des tests concernés par des fichiers modifiés (`uv run tasks.py quick`, hook de fin de tour) et tests de
la vérification des données du clone de `forever update` (`uv run tasks.py verify --data`, décision 206).

Analyse statique, bibliothèque standard seulement (le hook la lance hors de l'environnement du projet) :

- un module de `forever/` sélectionne les tests qui l'importent, directement ou par la fermeture des imports de
  `forever/` (imports dans les fonctions compris), y compris par une fixture ou une aide de `tests/conftest.py`
  nommée dans le fichier de test ;
- un autre fichier (fixture, document, script, addon, plugin) sélectionne les tests dont une chaîne (ou une chaîne
  d'une constante de `conftest.py` nommée dans le test) désigne ce fichier, son nom ou l'un de ses dossiers ;
- un fichier partagé par tous les tests (`conftest.py`, `pyproject.toml`, `uv.lock`, `tasks.py`, ce module) ou les
  données installées (`forever/data/`, lues par presque tous les tests) : repli sur tous les tests rapides.

L'approximation est assumée : `uv run tasks.py verify`, une fois avant le push, puis la CI, restent les juges."""

from __future__ import annotations

import ast
import re
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent

# Repli sur les tests rapides : fichiers lus par tous les tests, ou par presque tous.
SHARED = frozenset({"tests/conftest.py", "pyproject.toml", "uv.lock", "tasks.py", "scripts/select_tests.py"})
SHARED_PREFIXES = ("forever/data/",)
# Parties de chemin trop générales pour désigner un fichier.
DOCUMENT_PREFIXES = ("docs/", "tasks/")
GENERIC_PARTS = frozenset(
    {"tests", "fixtures", "unit", "docs", "forever", "data", "scripts", "README.md", "__init__.py"}
)

# Chemins qu'écrit `forever update` dans le clone (décisions 181 et 191) : une écriture qui ne touche qu'eux ne change
# que des données.
DATA_ONLY_PREFIXES = ("forever/data/", "docs/research/data-", "docs/research/valeurs-ecrites-a-la-main.md")
# Tests de cohérence des données installées, lancés par la vérification des données du clone.
DATA_TESTS = (
    "tests/unit/test_manifest.py",
    "tests/unit/test_revision_constants.py",
    "tests/unit/test_verify_version.py",
    "tests/unit/test_origins.py",
    "tests/unit/test_origins_inventory.py",
    "tests/unit/test_registry.py",
    "tests/unit/test_engine_inputs.py",
)
# Modules d'entrée de chaque moteur déclaré dans `forever/engine_inputs.py` (ENGINES) : ses tests sont ceux qui
# importent directement l'un de ces modules (ou un sous-module).
ENGINE_MODULES: dict[str, tuple[str, ...]] = {
    "mage_build": ("forever.build", "forever.optimize"),
    "mage_leveling": ("forever.leveling", "forever.sim", "forever.engine.leveling"),
    "pvp_dr": ("forever.pvp", "forever.engine.pvp", "forever.engine.diminishing"),
}

_MODULE_STRING = re.compile(r"^forever(\.\w+)+$")


class Selection(NamedTuple):
    """`files` : fichiers de test retenus (vide : aucun), ou None pour tous les tests rapides ; `reasons` : pourquoi."""

    files: list[str] | None
    reasons: list[str]


class _Source(NamedTuple):
    imports: set[str]  # modules importés (noms complets, candidats compris)
    strings: set[str]  # chaînes littérales
    names: set[str]  # identifiants employés


def _parse(path: Path, package: str) -> _Source:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    src = _Source(set(), set(), set())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            src.imports.update({a.name for a in node.names})
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")[: len(package.split(".")) - node.level + 1]
                base = ".".join(parts + ([base] if base else []))
            src.imports.add(base)
            src.imports.update({f"{base}.{a.name}" for a in node.names})
            src.names.update({a.asname or a.name for a in node.names})
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            src.strings.add(node.value)
            if _MODULE_STRING.match(node.value):  # monkeypatch.setattr("forever.update._fetch", …), python -m
                src.imports.add(node.value)
        elif isinstance(node, ast.Name):
            src.names.add(node.id)
        elif isinstance(node, ast.arg):
            src.names.add(node.arg)  # fixture demandée en paramètre
    return src


class TestIndex:
    """Graphe des imports de `forever/` et sources des fichiers de test d'un dépôt."""

    __test__ = False  # pas une classe de test pour pytest

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.graph: dict[str, set[str]] = {}
        for path in sorted((root / "forever").rglob("*.py")):
            module = self._module(path)
            package = module if path.name == "__init__.py" else module.rpartition(".")[0]
            self.graph[module] = _parse(path, package).imports
        for module, imports in self.graph.items():
            self.graph[module] = {self._known(name) for name in imports} - {None}  # type: ignore[assignment]
        conftest = root / "tests" / "conftest.py"
        self.conftest_top = self._closure(self._top_imports(conftest)) if conftest.is_file() else set()
        self.helpers = self._helpers(conftest) if conftest.is_file() else {}
        self.tests: dict[str, _Source] = {}
        for path in sorted((root / "tests").rglob("test_*.py")):
            if "fixtures" in path.relative_to(root).parts:
                continue
            self.tests[path.relative_to(root).as_posix()] = _parse(path, "tests")
        self._closures: dict[str, set[str]] = {}

    def _module(self, path: Path) -> str:
        parts = list(path.relative_to(self.root).with_suffix("").parts)
        return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)

    def _known(self, name: str) -> str | None:
        """Module de `forever/` désigné par `name` (le plus long préfixe connu : `forever.update._fetch` → update)."""
        while name:
            if name in self.graph:
                return name
            name = name.rpartition(".")[0]
        return None

    def _closure(self, start: Iterable[str]) -> set[str]:
        seen: set[str] = set()
        todo = [m for m in (self._known(n) for n in start) if m]
        while todo:
            module = todo.pop()
            if module in seen:
                continue
            seen.add(module)
            todo += self.graph.get(module, ())
            parent = module.rpartition(".")[0]
            if parent:
                todo.append(parent)  # un sous-module charge son paquet
        return seen

    @staticmethod
    def _top_imports(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names |= {node.module} | {f"{node.module}.{a.name}" for a in node.names}
        return names

    @staticmethod
    def _helpers(path: Path) -> dict[str, _Source]:
        """Fonction ou constante de premier niveau de conftest → (imports, chaînes, noms) de son corps."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        out: dict[str, _Source] = {}
        for node in tree.body:
            targets: list[str] = []
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                targets = [node.name]
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                nodes = node.targets if isinstance(node, ast.Assign) else [node.target]
                targets = [t.id for t in nodes if isinstance(t, ast.Name)]
            if not targets:
                continue
            src = _Source(set(), set(), set())
            module = ast.Module(body=[node], type_ignores=[])
            for sub in ast.walk(module):
                if isinstance(sub, ast.ImportFrom) and sub.module:
                    src.imports.update({sub.module} | {f"{sub.module}.{a.name}" for a in sub.names})
                elif isinstance(sub, ast.Import):
                    src.imports.update({a.name for a in sub.names})
                elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    src.strings.add(sub.value)
                elif isinstance(sub, ast.Name):
                    src.names.add(sub.id)
            for name in targets:
                out[name] = src
        return out

    def expanded(self, test: str) -> _Source:
        """Source d'un fichier de test augmentée des aides de conftest qu'il nomme (transitivement)."""
        src = self.tests[test]
        full = _Source(set(src.imports), set(src.strings), set(src.names))
        todo = [n for n in src.names if n in self.helpers]
        seen: set[str] = set()
        while todo:
            name = todo.pop()
            if name in seen:
                continue
            seen.add(name)
            helper = self.helpers[name]
            full.imports.update(helper.imports)
            full.strings.update(helper.strings)
            todo += [n for n in helper.names if n in self.helpers and n not in seen]
        return full

    def closure(self, test: str) -> set[str]:
        if test not in self._closures:
            self._closures[test] = self._closure(self.expanded(test).imports) | self.conftest_top
        return self._closures[test]


def _designates(strings: set[str], path: str) -> bool:
    parts = path.split("/")
    if path.startswith(DOCUMENT_PREFIXES):  # un document : désigné par son seul nom de fichier
        return parts[-1] in strings
    names = {p for p in parts if p not in GENERIC_PARTS} | {Path(path).stem}
    names.discard("")
    for s in strings:
        if s in names:
            return True
        if "/" in s and len(s) > 3 and (path.startswith(s.rstrip("/")) or s in path):
            return True
    return False


def select(changed: Sequence[str], index: TestIndex) -> Selection:
    """Tests concernés par les chemins `changed` (relatifs à la racine, en `/`)."""
    files: set[str] = set()
    reasons: list[str] = []
    for path in sorted(set(changed)):
        if path in SHARED or path.startswith(SHARED_PREFIXES) or (path.endswith("/conftest.py")):
            return Selection(None, [f"{path} : lu par tous les tests, tous les tests rapides"])
        if path in index.tests:
            files.add(path)
            reasons.append(f"{path} : test modifié")
            continue
        if path.startswith("tests/") and Path(path).name.startswith("test_") and path.endswith(".py"):
            reasons.append(f"{path} : test retiré")
            continue
        hits: set[str]
        if path.startswith("forever/") and path.endswith(".py"):
            module = index._module(index.root / path)
            if module not in index.graph:  # module retiré : on ne sait plus qui l'importait
                return Selection(None, [f"{path} : module retiré, tous les tests rapides"])
            hits = {t for t in index.tests if module in index.closure(t)}
        else:
            hits = {t for t in index.tests if _designates(index.expanded(t).strings, path)}
        files |= hits
        reasons.append(f"{path} : {len(hits)} fichier(s) de test")
    return Selection(sorted(files), reasons)


def engine_tests(index: TestIndex, engines: Iterable[str]) -> list[str]:
    """Tests des moteurs `engines` : fichiers qui importent directement un module d'entrée du moteur."""
    prefixes = tuple(p for e in engines for p in ENGINE_MODULES[e])
    out = []
    for test, src in index.tests.items():
        if any(name == p or name.startswith(p + ".") for name in src.imports for p in prefixes):
            out.append(test)
    return sorted(out)


def data_only(paths: Sequence[str]) -> bool:
    """Vrai si `paths` n'est pas vide et ne touche que des chemins de données (`DATA_ONLY_PREFIXES`)."""
    return bool(paths) and all(p.startswith(DATA_ONLY_PREFIXES) for p in paths)


def _git(root: Path, *args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False)
    return [line for line in out.stdout.splitlines() if line.strip()] if out.returncode == 0 else []


def uncommitted(root: Path = ROOT) -> list[str]:
    """Chemins modifiés, ajoutés, retirés ou non suivis par rapport à `HEAD`."""
    paths = []
    for line in _git(root, "status", "--porcelain", "--untracked-files=all", "--no-renames"):
        paths.append(line[3:].strip().strip('"'))
    return sorted(set(paths))


def changed_since(base: str = "main", root: Path = ROOT) -> list[str]:
    """Chemins modifiés depuis le point de divergence avec `base` (commits de la branche), plus l'arbre de travail."""
    merge_base = _git(root, "merge-base", "HEAD", base)
    committed = _git(root, "diff", "--name-only", "--no-renames", merge_base[0]) if merge_base else []
    return sorted(set(committed) | set(uncommitted(root)))


if __name__ == "__main__":
    import sys

    selection = select(changed_since(), TestIndex())
    for reason in selection.reasons:
        print(reason, file=sys.stderr)
    print("\n".join(selection.files) if selection.files is not None else "*")
