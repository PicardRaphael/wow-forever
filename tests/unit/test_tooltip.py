"""Évaluation des variables d'infobulle, avec un résolveur simulé (valeurs inventées, sans lien avec le jeu)."""

import pytest

from forever.pipeline.tooltip import half_up, normalize, tooltip_values


def resolver(values):
    """values : {(sort ou None, lettre, indice d'effet): [valeurs signées]} ; garde la trace des appels."""
    calls = []

    def resolve(spell, letter, index):
        calls.append((spell, letter, index))
        return values[(spell, letter, index)]

    resolve.calls = calls
    return resolve


def test_simple_variable_is_absolute():
    assert tooltip_values("Réduit de $s1%.", resolver({(None, "s", 0): [-15]})) == [15]


def test_variance_gives_min_and_max():
    assert tooltip_values("inflige $s1 points", resolver({(None, "s", 0): [50, 58]})) == [50, 58]


def test_order_of_appearance():
    values = {(None, "s", 1): [8], (None, "s", 0): [-15]}
    assert tooltip_values("de $s2 et de $s1%", resolver(values)) == [8, 15]


def test_m_and_big_m():
    values = {(None, "m", 1): [5], (None, "M", 1): [7]}
    assert tooltip_values("$m2 à $M2", resolver(values)) == [5, 7]


def test_duration_charges_and_stacks():
    values = {(None, "d", 0): [15], (None, "n", 0): [4], (400573, "u", 0): [4], (400573, "d", 0): [8]}
    text = "pendant $d, $n charges, jusqu'à $400573u fois pendant $400573d."
    assert tooltip_values(text, resolver(values)) == [15, 4, 4, 8]


def test_periodic_total():
    r = resolver({(None, "o", 1): [44]})
    assert tooltip_values("et $o2 sur la durée", r) == [44]
    assert r.calls == [(None, "o", 1)]


def test_cited_spell_prefix():
    r = resolver({(22959, "s", 0): [3]})
    assert tooltip_values("augmente de $22959s1%", r) == [3]
    assert r.calls == [(22959, "s", 0)]


def test_division_prefix_is_absolute():
    assert tooltip_values("de $/1000;S1 s", resolver({(None, "s", 0): [-100]})) == [0.1]
    assert tooltip_values("de $/10;12536s1%", resolver({(12536, "s", 0): [-1000]})) == [100]


def test_expression_uses_signed_values():
    assert tooltip_values("${$s1/-1000} s", resolver({(None, "s", 0): [-1000]})) == [1]
    assert tooltip_values("${$m1/1000} s", resolver({(None, "m", 0): [2000]})) == [2]


def test_expression_rounds_half_up_to_integer_by_default():
    assert tooltip_values("${$m1/2}%", resolver({(None, "m", 0): [45]})) == [23]


def test_expression_decimals_suffix():
    assert tooltip_values("toutes les ${$m2/10}.1 s", resolver({(None, "m", 1): [5]})) == [0.5]


def test_expression_with_cited_spell_and_parentheses():
    values = {(1279976, "m", 0): [25], (None, "d", 0): [8]}
    assert tooltip_values("${($1279976m1+1)*$d} points", resolver(values)) == [208]


def test_plural_text_is_skipped():
    assert tooltip_values("vos $m1 $lsort:sorts; suivants", resolver({(None, "m", 0): [2]})) == [2]


def test_text_without_variables():
    assert tooltip_values("Rien à lire ici.", resolver({})) == []


@pytest.mark.parametrize(
    "text",
    [
        "${$m2*$<frostdamage>}",  # variable de description
        "$<frostdamage>",
        "$?s11151[${1.02}][${1.0}]",  # condition
        "$z1",  # lettre inconnue
        "${$m1 + os}",  # expression non arithmétique
    ],
)
def test_unsupported_patterns_raise(text):
    values = {(None, "m", 0): [1], (None, "m", 1): [1]}
    with pytest.raises(ValueError):
        tooltip_values(text, resolver(values))


def test_half_up():
    assert half_up(24.5) == 25
    assert half_up(25.49) == 25
    assert half_up(0.05, 1) == pytest.approx(0.1)
    assert half_up(-0.5) == 0


def test_normalize():
    assert normalize(3.0) == 3 and isinstance(normalize(3.0), int)
    assert normalize(0.1 + 0.2) == pytest.approx(0.3) and isinstance(normalize(0.3), float)
