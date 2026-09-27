"""Registre des mécaniques : validation stricte, références de test, implémentations citées, couverture.

Registres invalides : tests/fixtures/registry/ (un défaut par fichier) ; faux moteur : tests/fixtures/engine_cites/."""

import ast

import pytest
import yaml
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
    # T04 : preuves de journal (champ `preuves`, contrôle de `valide-journal`)
    "journal_without_proof.yaml": "'valide-journal' sans preuve",
    "journal_without_n_min.yaml": "tolerance.n_min",
    "proof_missing_log.yaml": "journal introuvable",
    "proof_log_outside_fixtures.yaml": "hors de tests/fixtures/combatlog/",
    "proof_missing_test.yaml": "fonction de test introuvable",
    "proof_below_n_min.yaml": "n = 3 < n_min = 50",
    "proof_missing_field.yaml": "champ 'n' manquant",
    # T04b : preuves cumulées par mesure, preuve de plusieurs journaux, écarts à la recharge globale (décision 2)
    "proof_cumulative_below.yaml": "n = 45 < n_min = 50",
    "proof_other_measures_not_summed.yaml": "n = 30 < n_min = 50",
    "proof_median_gap.yaml": "écart médian 0.08 s > tolerance.ecart_s = 0.05 s",
    "proof_p10_gap.yaml": "écart du 10e percentile 0.06 s > tolerance.ecart_s = 0.05 s",
    "proof_gap_missing.yaml": "champ 'ecart_median_s' manquant",
    "proof_journal_list_missing.yaml": "journal introuvable 'tests/fixtures/combatlog/absent.txt'",
}


def check(name, *, strict=True, engine_dirs=()):
    return validate(REGISTRIES / name, REPO_ROOT, strict=strict, engine_dirs=engine_dirs)


def test_repository_registry_is_valid_strict():
    report = validate(REGISTRY_PATH, REPO_ROOT, strict=True)
    assert report.errors == []
    assert report.total == 104  # T04b : H11 (PV des monstres par niveau) ; T04c : I7 (zone ou donjon à mon niveau)


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
    assert coverage(REGISTRY_PATH) == "33/104"  # T04b : H11 ; T04c : I7 ajoutée et testée, B15 testée


def test_load_reads_optional_fields():
    a5 = find_entry(load(REGISTRY_PATH), "A5")
    assert a5.formula and not [n for n in NUMBER.findall(a5.formula) if n not in ("0", "1")]
    assert a5.sources


def test_main_strict_on_repository(capsys):
    assert main(["--strict"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Registre : 104 mécaniques")
    assert "teste 32" in out and "valide-journal 1" in out  # B1 validée par les journaux (T04b) ; T04c : I7, B15


def test_main_reports_errors(capsys):
    assert main(["--strict"], path=REGISTRIES / "duplicate.yaml", repo_root=REPO_ROOT) == 1
    assert "ERREUR" in capsys.readouterr().out


def test_valid_journal_proof_is_accepted():
    report = check("valid_journal.yaml")
    assert report.errors == [] and report.counts["valide-journal"] == 1


def test_b1_is_validated_by_the_two_logs():
    """B1 (critère de l'utilisateur, 2026-09-27) : preuve des deux journaux, n = 50 = n_min, médiane à 0,011 s de la
    recharge globale, 10e percentile 1,4569 s (écart 0,0431 s ≤ 0,05 s) : `valide-journal`, certitude `probable`."""
    b1 = find_entry(load(REGISTRY_PATH), "B1")
    assert (b1.status, b1.certainty) == ("valide-journal", "probable")
    assert b1.tolerance == {"n_min": 50, "ecart_s": 0.05}
    (proof,) = b1.proofs
    assert proof["journal"] == [
        "tests/fixtures/combatlog/WoWCombatLog-092726_145346.anon.txt",
        "tests/fixtures/combatlog/WoWCombatLog-092726_150346.anon.txt.gz",
    ]
    assert (proof["n"], proof["ecart_median_s"], proof["ecart_p10_s"]) == (50, 0.011, 0.0431)
    assert proof["test"] == "tests/unit/test_measure_second_log.py::test_b1_proof_matches_the_registry"


def test_the_minimum_interval_no_longer_counts(tmp_path):
    """Seuls la médiane et le 10e percentile sont contrôlés : un `ecart_min_s` éventuel est ignoré."""
    raw = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    (b1,) = [m for m in raw["mechanics"] if m["id"] == "B1"]
    b1["preuves"][0]["ecart_min_s"] = 0.086
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump({**raw, "mechanics": [b1]}, allow_unicode=True), encoding="utf-8")
    report = validate(path, REPO_ROOT, strict=True, engine_dirs=())
    assert [e for e in report.errors if "écart" in e] == []


def test_cumulative_and_multi_log_proofs_are_accepted():
    for name in ("valid_cumulative.yaml", "valid_gap.yaml"):
        report = check(name)
        assert report.errors == [] and report.counts["valide-journal"] == 1, name


def test_leveling_mechanics_are_tested_after_t04b():
    """T04b : mécaniques portées du simulateur de leveling du seed, testées ; H2 reste absente (armure et
    résistances de la cible non modélisées par le seed)."""
    entries = {m.id: m for m in load(REGISTRY_PATH)}
    for mid in ("B6", "B7", "B13", "C1", "C5", "I1", "I6", "J2"):
        assert entries[mid].status == "teste", mid
        assert any("::" in t for t in entries[mid].tests), mid
    assert entries["H2"].status == "absent"
    impl = implementations([ENGINE_DIR], REPO_ROOT)
    for mid in ("B6", "B7", "B13", "C1", "C5"):
        assert impl.get(mid), mid
