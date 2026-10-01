"""Entête d'une GameTable à colonnes nommées avec espace (« Death Knight ») : acceptée (T08b, bloc A1).

Constat de l'accès réseau 3 du 2026-10-01 : basemp et npctotalhp refusées par un contrôle d'entête trop strict.
Fixture synthétique (structure, valeurs inventées) : tests/fixtures/wago/gametables/synthetique_espaces.txt."""

from conftest import FIXTURES

from forever.pipeline.fetch import looks_like_gametable


def test_header_with_spaces_is_a_gametable():
    assert looks_like_gametable((FIXTURES / "wago" / "gametables" / "synthetique_espaces.txt").read_bytes())


def test_html_is_still_refused():
    assert not looks_like_gametable(b"<html>\t<body>\n")
