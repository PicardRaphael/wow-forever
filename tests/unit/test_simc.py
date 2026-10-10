"""Export de l'addon SimulationCraft (P06b, décisions 225 et 235). Bloc A : somme de contrôle (adler32, valeurs
publiées de l'algorithme), anonymisation des seules lignes qui portent le nom et le royaume, somme recalculée.
Fixture construite `tests/fixtures/simc/constructed_mage.txt`."""

import pytest
from conftest import FIXTURES

from forever.simc import ANON_NAME, ANON_REALM, anonymize_simc, checksum_ok, simc_checksum

CONSTRUCTED = (FIXTURES / "simc" / "constructed_mage.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("abc", "24d0127"), ("Wikipedia", "11e60398"), ('mage="Jen"\nlevel=19\n', "4466060c")],
)
def test_checksum_vectors(text, expected):
    assert simc_checksum(text) == expected


def test_doubled_pipes_are_counted_once():
    assert simc_checksum("a||b") == simc_checksum("a|b")


def test_constructed_export_checksum():
    assert checksum_ok(CONSTRUCTED) is True
    assert checksum_ok(CONSTRUCTED.replace("\n", "\r\n")) is True
    assert checksum_ok(CONSTRUCTED.replace("level=19", "level=18")) is False
    assert checksum_ok(CONSTRUCTED.rsplit("# Checksum:", 1)[0]) is None
    assert checksum_ok(CONSTRUCTED + "\n") is True


def test_anonymized_export():
    text, original = anonymize_simc(CONSTRUCTED)
    assert original is True and checksum_ok(text) is True
    lines = text.splitlines()
    assert lines[0] == f"# {ANON_NAME} - 2026-10-10 14:02 - EU/{ANON_REALM}"
    assert f'mage="{ANON_NAME}"' in lines and f"server={ANON_REALM.lower()}" in lines
    assert "Jen" not in text and "classic_beta_pve_2" not in text and "Classic Beta PvE 2" not in text
    assert "region=eu" in lines and "# Staff of Orgrimmar (20)" in lines
    before = [line for line in CONSTRUCTED.splitlines() if "Jen" not in line and "lassic" not in line]
    after = [line for line in lines if ANON_NAME not in line and ANON_REALM.lower() not in line.lower()]
    assert before[:-1] == after[:-1]  # seule la ligne de la somme change en dehors des trois lignes


def test_anonymization_touches_only_the_three_lines():
    """Un nom d'objet qui contient le nom du personnage n'est pas touché."""
    body = CONSTRUCTED.rsplit("# Checksum:", 1)[0].replace("# Deckhand's Shirt (1)", "# Jen's Shirt (1)")
    text, original = anonymize_simc(body + "# Checksum: " + simc_checksum(body))
    assert original is True and "# Jen's Shirt (1)" in text and checksum_ok(text) is True


def test_wrong_or_missing_checksum_is_reported():
    text, original = anonymize_simc(CONSTRUCTED.replace("level=19", "level=18"))
    assert original is False and "Jen" not in text
    text, original = anonymize_simc(CONSTRUCTED.rsplit("# Checksum:", 1)[0])
    assert original is None and "# Checksum:" not in text and "Jen" not in text
