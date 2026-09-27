"""Registre des mécaniques (`docs/MECHANICS_REGISTRY.yaml`) : lecture, validation, couverture.

Une référence de test prend la forme `tests/…/fichier.py::test_nom` ; la fonction doit exister (analyse `ast`, sans
import). Les fonctions du moteur citent leurs identifiants dans leur docstring : « Registre : A3, A4 ».

Preuves de journal (champ `preuves`, T04) : chaque preuve cite une fixture de journal sous `tests/fixtures/combatlog/`
(ou une liste de fixtures, mesure faite sur leur réunion), sa date, la mesure, l'effectif `n` et le test qui la lit.
`valide-journal` exige que les preuves valides d'une même mesure totalisent `n` ≥ `tolerance.n_min` (décision 2 du
plan T04b : les preuves se cumulent) ; avec `tolerance.ecart_s`, chaque preuve déclare `ecart_median_s` (médiane -
valeur des données, en valeur absolue) et `ecart_p10_s` (valeur des données - 10e percentile), recalculés par son
test, et tous deux doivent rester sous la tolérance ; le minimum n'est pas contrôlé (gigue d'horodatage). Le statut ne change pas la certitude (règle observée, pas valeur)."""

from __future__ import annotations

import ast
import difflib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from forever.config import PACKAGE_DIR, REGISTRY_PATH, REPO_ROOT
from forever.errors import UnknownMechanicError

STATUSES = ("absent", "modelise", "teste", "valide-journal", "valide-jeu")
COVERED_STATUSES = frozenset({"teste", "valide-journal", "valide-jeu"})
CERTAINTIES = frozenset({"certain", "probable", "suppose"})
FOREVER_VALUES = frozenset({"oui", "modifie", "inconnu"})
REQUIRED_FIELDS = ("id", "categorie", "description", "forever", "statut", "certitude", "sources", "tests")
PROOF_FIELDS = ("journal", "date", "mesure", "n", "test")
GAP_FIELDS = ("ecart_median_s", "ecart_p10_s")
GAP_LABELS = {"ecart_median_s": "écart médian", "ecart_p10_s": "écart du 10e percentile"}
PROOF_DIR = "tests/fixtures/combatlog/"
ENGINE_DIR = PACKAGE_DIR / "engine"
# Catégories (première lettre de l'identifiant) dont une entrée testée doit être implémentée dans le moteur.
ENGINE_CATEGORIES = frozenset("ABCDEFGH")
CITATION_RE = re.compile(r"Registre\s*:\s*([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)")
ID_SPLIT_RE = re.compile(r"\s*,\s*")
# Nombre isolé dans une formule : seuls 0 et 1 (bornes mathématiques) sont admis.
NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w])")


class RegistryError(ValueError):
    """Registre absent, illisible ou mal formé."""


@dataclass(frozen=True)
class Mechanic:
    id: str
    category: str
    description: str
    forever: str
    status: str
    certainty: str
    sources: tuple[str, ...]
    tests: tuple[str, ...]
    tolerance: object
    formula: str | None
    note: str | None
    proofs: tuple[dict[str, Any], ...] = ()


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    total: int = 0


def _raw_entries(path: Path) -> list[Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RegistryError(f"registre introuvable ou illisible : {path} ({exc.strerror or exc})") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"registre au YAML invalide : {path}") from exc
    mechanics = data.get("mechanics") if isinstance(data, dict) else None
    if not isinstance(mechanics, list):
        raise RegistryError(f"registre sans liste « mechanics » : {path}")
    return mechanics


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _texts(value: object) -> tuple[str, ...]:
    return tuple(str(v) for v in value) if isinstance(value, list) else ()


def _optional(value: object) -> str | None:
    return None if value is None else str(value)


def load(path: Path) -> list[Mechanic]:
    """Entrées du registre ; lève RegistryError s'il est absent ou illisible."""
    out = []
    for m in _raw_entries(path):
        if not isinstance(m, dict):
            raise RegistryError(f"entrée du registre qui n'est pas un objet : {m!r}")
        out.append(
            Mechanic(
                id=_text(m.get("id")),
                category=_text(m.get("categorie")),
                description=_text(m.get("description")),
                forever=_text(m.get("forever")),
                status=_text(m.get("statut")),
                certainty=_text(m.get("certitude")),
                sources=_texts(m.get("sources")),
                tests=_texts(m.get("tests")),
                tolerance=m.get("tolerance"),
                formula=_optional(m.get("formule")),
                note=_optional(m.get("note")),
                proofs=tuple(p for p in m.get("preuves") or [] if isinstance(p, dict)),
            )
        )
    return out


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def implementations(dirs: Sequence[Path], repo_root: Path) -> dict[str, list[str]]:
    """Identifiant -> fonctions du moteur qui le citent (`forever/engine/crit.py::crit_chance`)."""
    found: dict[str, list[str]] = {}
    for directory in dirs:
        for file in sorted(directory.rglob("*.py")):
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    continue
                match = CITATION_RE.search(ast.get_docstring(node) or "")
                if match:
                    for mechanic_id in ID_SPLIT_RE.split(match.group(1)):
                        found.setdefault(mechanic_id, []).append(f"{_relative(file, repo_root)}::{node.name}")
    return found


def _defined_names(file: Path, cache: dict[Path, set[str]]) -> set[str]:
    if file not in cache:
        tree = ast.parse(file.read_text(encoding="utf-8"))
        cache[file] = {
            n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        }
    return cache[file]


def _check_tests(mid: str, tests: list[Any], repo_root: Path, cache: dict[Path, set[str]]) -> list[str]:
    errors = []
    for ref in tests:
        ref = str(ref)
        file_part, _, name = ref.partition("::")
        file = repo_root / file_part
        if not file_part.startswith("tests/") or not file.resolve().is_relative_to((repo_root / "tests").resolve()):
            errors.append(f"{mid} : référence hors de tests/ refusée '{ref}'")
            continue
        if not file.is_file():
            errors.append(f"{mid} : test introuvable '{ref}'")
            continue
        if name:
            try:
                names = _defined_names(file, cache)
            except SyntaxError:
                errors.append(f"{mid} : fichier de test illisible '{ref}'")
                continue
            if name.split("[")[0] not in names:
                errors.append(f"{mid} : fonction de test introuvable '{ref}'")
    return errors


def _n_min(tolerance: object) -> int | None:
    value = tolerance.get("n_min") if isinstance(tolerance, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _check_journal(where: str, journal: str, repo_root: Path) -> list[str]:
    path = repo_root / journal
    if not journal.startswith(PROOF_DIR) or not path.resolve().is_relative_to((repo_root / PROOF_DIR).resolve()):
        return [f"{where} : journal hors de {PROOF_DIR} refusé '{journal}'"]
    if not path.is_file():
        return [f"{where} : journal introuvable '{journal}'"]
    return []


def _check_proofs(
    mid: str, status: object, m: dict[str, Any], repo_root: Path, cache: dict[Path, set[str]]
) -> list[str]:
    """Erreurs du champ `preuves` ; pour `valide-journal`, au moins une preuve valide avec n ≥ tolerance.n_min."""
    raw = m.get("preuves")
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        return [f"{mid} : 'preuves' doit être une liste"]
    errors: list[str] = []
    valid_n: dict[str, int] = {}
    gap_errors: list[str] = []
    ecart_s = _number(m.get("tolerance", {}).get("ecart_s")) if isinstance(m.get("tolerance"), dict) else None
    for i, proof in enumerate(raw, start=1):
        where = f"{mid} : preuve {i}"
        if not isinstance(proof, dict):
            errors.append(f"{where} n'est pas un objet")
            continue
        missing = [f for f in PROOF_FIELDS if f not in proof]
        errors += [f"{where} : champ '{f}' manquant" for f in missing]
        if missing:
            continue
        own: list[str] = []
        journals = proof["journal"] if isinstance(proof["journal"], list) else [proof["journal"]]
        if not journals:
            own.append(f"{where} : liste de journaux vide")
        for journal in journals:
            own += _check_journal(where, str(journal), repo_root)
        n = proof["n"]
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            own.append(f"{where} : 'n' doit être un entier positif")
        own += [e.replace(f"{mid} :", f"{where} :", 1) for e in _check_tests(mid, [proof["test"]], repo_root, cache)]
        if "::" not in str(proof["test"]):
            own.append(f"{where} : test sans référence ::nom de fonction")
        errors += own
        if own:
            continue
        mesure = str(proof["mesure"])
        valid_n[mesure] = valid_n.get(mesure, 0) + n
        if ecart_s is None:
            continue
        for gap in GAP_FIELDS:
            value = _number(proof.get(gap))
            if gap not in proof:
                gap_errors.append(f"{where} : champ '{gap}' manquant (tolerance.ecart_s)")
            elif value is None:
                gap_errors.append(f"{where} : '{gap}' doit être un nombre")
            elif value > ecart_s:
                gap_errors.append(f"{where} : {GAP_LABELS[gap]} {value:g} s > tolerance.ecart_s = {ecart_s:g} s")
    if status == "valide-journal":
        n_min = _n_min(m.get("tolerance"))
        if n_min is None:
            errors.append(f"{mid} : 'valide-journal' exige tolerance.n_min (effectif minimal d'une preuve)")
        elif not raw:
            errors.append(f"{mid} : 'valide-journal' sans preuve de journal")
        elif not any(n >= n_min for n in valid_n.values()):
            best = max(valid_n.values(), default=0)
            errors.append(f"{mid} : 'valide-journal' sans preuve suffisante (n = {best} < n_min = {n_min})")
        errors += gap_errors
    return errors


def validate(
    path: Path, repo_root: Path, *, strict: bool, engine_dirs: Sequence[Path] = (ENGINE_DIR,)
) -> ValidationReport:
    """Contrôle complet du registre ; en mode strict, une entrée `modelise` sans test est une erreur."""
    report = ValidationReport()
    try:
        entries = _raw_entries(path)
    except RegistryError as exc:
        report.errors.append(str(exc))
        return report
    impl = implementations(engine_dirs, repo_root)
    cache: dict[Path, set[str]] = {}
    ids: set[str] = set()
    for m in entries:
        if not isinstance(m, dict):
            report.errors.append(f"entrée qui n'est pas un objet : {m!r}")
            continue
        mid = str(m.get("id", "?"))
        report.errors += [f"{mid} : champ '{f}' manquant" for f in REQUIRED_FIELDS if f not in m]
        if mid in ids:
            report.errors.append(f"{mid} : identifiant en double")
        ids.add(mid)
        status = m.get("statut")
        if status not in STATUSES:
            report.errors.append(f"{mid} : statut inconnu '{status}'")
        if m.get("certitude") not in CERTAINTIES:
            report.errors.append(f"{mid} : certitude inconnue '{m.get('certitude')}'")
        if m.get("forever") not in FOREVER_VALUES:
            report.errors.append(f"{mid} : valeur 'forever' inconnue '{m.get('forever')}'")
        tests = m.get("tests") or []
        if not isinstance(tests, list):
            report.errors.append(f"{mid} : 'tests' doit être une liste")
            tests = []
        report.errors += _check_tests(mid, tests, repo_root, cache)
        report.errors += _check_proofs(mid, status, m, repo_root, cache)
        rank = STATUSES.index(status) if status in STATUSES else 0
        if rank >= 2 and not tests:
            report.errors.append(f"{mid} : statut '{status}' sans test")
        elif rank >= 2 and not any("::" in str(t) for t in tests):
            report.errors.append(f"{mid} : statut '{status}' sans référence ::nom de fonction de test")
        elif rank == 1 and not tests:
            (report.errors if strict else report.warnings).append(f"{mid} : 'modelise' sans test")
        if rank >= 3 and not m.get("sources"):
            report.errors.append(f"{mid} : statut '{status}' sans source")
        if rank >= 2 and mid[:1] in ENGINE_CATEGORIES and not impl.get(mid):
            report.errors.append(f"{mid} : statut '{status}' sans aucune implémentation citée dans le moteur")
        formula = m.get("formule")
        if formula is not None:
            numbers = [n for n in NUMBER_RE.findall(str(formula)) if n not in ("0", "1")]
            if numbers:
                report.errors.append(
                    f"{mid} : formule chiffrée ({', '.join(numbers)}) ; seuls 0 et 1 sont admis, "
                    "les valeurs vivent dans forever/data/"
                )
    for mechanic_id, where in sorted(impl.items()):
        if mechanic_id not in ids:
            report.errors.append(f"{mechanic_id} cité par {', '.join(where)} mais absent du registre")
    report.total = len(entries)
    report.counts = {s: sum(1 for m in entries if isinstance(m, dict) and m.get("statut") == s) for s in STATUSES}
    return report


def find_entry(mechanics: Sequence[Mechanic], mechanic_id: str) -> Mechanic:
    """Entrée par identifiant (casse ignorée) ; lève UnknownMechanicError avec des suggestions."""
    wanted = mechanic_id.strip().upper()
    for m in mechanics:
        if m.id.upper() == wanted:
            return m
    ids = [m.id for m in mechanics]
    raise UnknownMechanicError(mechanic_id, difflib.get_close_matches(wanted, ids, n=3, cutoff=0.5))


def coverage(path: Path) -> str:
    """`<couvertes>/<total>` ; `0/0` si le registre est absent."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return "0/0"
    mechanics = data.get("mechanics") if isinstance(data, dict) else None
    if not isinstance(mechanics, list):
        return "0/0"
    covered = sum(1 for m in mechanics if isinstance(m, dict) and m.get("statut") in COVERED_STATUSES)
    return f"{covered}/{len(mechanics)}"


def main(argv: Sequence[str], path: Path = REGISTRY_PATH, repo_root: Path = REPO_ROOT) -> int:
    """Contrôle en ligne de commande (`scripts/check_registry.py [--strict]`) : 0 si le registre est valide."""
    report = validate(path, repo_root, strict="--strict" in argv)
    print(f"Registre : {report.total} mécaniques | " + " | ".join(f"{s} {n}" for s, n in report.counts.items()))
    for w in report.warnings:
        print(f"  avertissement : {w}")
    for e in report.errors:
        print(f"  ERREUR : {e}")
    return 1 if report.errors else 0
