"""Période effective d'un instantané à recharge dans une rotation sans interruption (T05, `cooldown_period`, registre
B13) : recharge globale, puis des incantations de remplissage entières jusqu'à la fin de la recharge."""

import math

import pytest

from forever.engine.casting import cooldown_period


@pytest.mark.parametrize(("cooldown", "filler"), [(8.0, 3.0), (6.0, 1.5), (10.0, 2.5), (45.0, 3.5)])
def test_cooldown_period_waits_for_whole_filler_casts(game_data, cooldown, filler):
    gcd = game_data.rules.gcd_s
    period = cooldown_period(game_data, cooldown, filler)
    assert period == pytest.approx(gcd + math.ceil((cooldown - gcd) / filler) * filler)
    assert period >= cooldown  # jamais plus tôt que la recharge
    assert period - cooldown < filler  # au plus une incantation d'attente
    n = (period - gcd) / filler
    assert n == pytest.approx(round(n))  # un nombre entier d'incantations de remplissage
