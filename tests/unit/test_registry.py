"""Registre des mécaniques : validation stricte, références de test, implémentations citées, couverture.

Registres invalides : tests/fixtures/registry/ (un défaut par fichier) ; faux moteur : tests/fixtures/engine_cites/."""

import ast

import pytest
from conftest import FIXTURES, REGISTRY_PATH, REPO_ROOT

from forever.errors import UnknownMechanicError
from forever.registry import ENGINE_DIR, NUMBER_RE, coverage, find_entry, implementations, load, main, validate

REGISTRIES = FIXTURES / "registry"
NUMBER = NUMBER_RE

DEFECTS = {
    "missing_field.yaml": "champ 'certitude' manquant",
    "duplicate.yaml": "identifiant en double",
    "unknown_status.yaml": "statut inconnu",
    "tested_without_test.yaml": "sans test",
    "file_only_reference.yaml": "référence ::nom",
    "missing_file.yaml": "test introuvable",
    "missing_function.yaml": "fonction de test introuvable",
    "seed_path.yaml": "hors de tests/",
    "traversal_path.yaml": "hors de tests/",
    "decimal_comma_formula.yaml": "formule chiffrée (1,5)",
    "modelise_without_test.yaml": "'modelise' sans test",
    "numeric_formula.yaml": "formule chiffrée",
    "no_implementation.yaml": "aucune implémentation",
}


def check(name, *, strict=True, engine_dirs=()):
    return validate(REGISTRIES / name, REPO_ROOT, strict=strict, engine_dirs=engine_dirs)


def test_repository_registry_is_valid_strict():
    report = validate(REGISTRY_PATH, REPO_ROOT, strict=True)
    assert report.errors == []
    assert report.total == 102  # T04 : G7 (points de base par niveau)


def test_tested_entries_reference_existing_test_functions():
    """Critère 2 : chaque entrée `teste` pointe vers au moins une fonction de test qui existe."""
    tested = [m for m in load(REGISTRY_PATH) if m.status == "teste"]
    assert tested
    for m in tested:
        refs = [t for t in m.tests if "::" in t]
        assert refs, m.id
        for ref in refs:
            file_part, name = ref.split("::", 1)
            assert file_part.startswith("tests/"), (m.id, ref)
            tree = ast.parse((REPO_ROOT / file_part).read_text(encoding="utf-8"))
            names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.ClassDef)}
            assert name.split("[")[0] in names, (m.id, ref)


def test_valid_fixture_has_no_error():
    report = check("valid.yaml")
    assert report.errors == [] and report.warnings == []


@pytest.mark.parametrize("name", DEFECTS)
def test_each_defect_is_reported(name):
    errors = check(name).errors
    assert any(DEFECTS[name] in e for e in errors), errors


def test_modelise_without_test_is_warning_when_not_strict():
    report = check("modelise_without_test.yaml", strict=False)
    assert report.errors == []
    assert any("'modelise' sans test" in w for w in report.warnings)


def test_engine_citing_unknown_id_is_reported():
    errors = check("valid.yaml", engine_dirs=(FIXTURES / "engine_cites",)).errors
    assert any("Z99" in e and "absent du registre" in e for e in errors), errors
    assert not any("J9" in e for e in errors)


def test_formula_accepts_zero_and_one_only():
    assert NUMBER.findall("x = a × (1 - b), bornée à [0, 1]") == ["1", "0", "1"]
    assert check("valid.yaml").errors == []
    assert any("formule chiffrée" in e for e in check("numeric_formula.yaml").errors)


def test_implementations_of_engine():
    impl = implementations([ENGINE_DIR], REPO_ROOT)
    assert "forever/engine/crit.py::crit_chance" in impl["A5"]
    assert "forever/engine/character.py::character" in impl["A5"]
    assert "forever/engine/hit.py::hit_chance" in impl["H1"]
    assert "forever/engine/cast.py::expected_cast" in impl["C2"]


def test_find_entry_ignores_case():
    mechanics = load(REGISTRY_PATH)
    assert find_entry(mechanics, "a5").id == "A5"
    assert find_entry(mechanics, " A5 ").id == "A5"


def test_find_entry_unknown_suggests():
    with pytest.raises(UnknownMechanicError) as exc:
        find_entry(load(REGISTRY_PATH), "Z9")
    assert exc.value.code == "unknown_mechanic"
    assert exc.value.exit_code == 4
    assert exc.value.suggestions


def test_repository_coverage():
    """Seul test qui fige la couverture du registre après T02."""
    assert coverage(REGISTRY_PATH) == "21/101"


def test_load_reads_optional_fields():
    a5 = find_entry(load(REGISTRY_PATH), "A5")
    assert a5.formula and not [n for n in NUMBER.findall(a5.formula) if n not in ("0", "1")]
    assert a5.sources


def test_main_strict_on_repository(capsys):
    assert main(["--strict"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Registre : 101 mécaniques")
    assert "teste 21" in out


def test_main_reports_errors(capsys):
    assert main(["--strict"], path=REGISTRIES / "duplicate.yaml", repo_root=REPO_ROOT) == 1
    assert "ERREUR" in capsys.readouterr().out
