"""Ignite roulant (T04c, bloc C ; registre A18).

Client 1.60.1.70009 (fixtures wago) : aura 412538 « Ignite », SpellMisc.DurationIndex -> SpellDuration 4000 ms,
SpellEffect période 2000 ms, SpellAuraOptions.CumulativeAura 1 (pas de cumul par empilement). Règle roulante
(décision 2 de T04c, suppose) : à chaque critique, montant = part du critique + reste non infligé ; l'aura repart
pour sa durée et le compteur de tics repart du critique. Montants de test choisis (80 et 60), pas des chiffres de jeu.
"""

import pytest

from forever.engine.damage import IgniteState, ignite_ticks_due, roll_ignite
from forever.sim.leveling_mc import mc

IGNITE_AURA = 412538  # identifiant de l'aura d'Ignite (Spell.csv, infobulle du talent 11119 : $412538d)
FIRE_IGNITE = {"improvedFireball": 5, "ignite": 5}
FIRE_PLAIN = {"improvedFireball": 5}
HIGH_CRIT = {"spell_crit": 0.5}  # critique relevé sur la fiche (valeur de test) : chevauchements fréquents


def _client_ignite(tables):
    misc = next(r for r in tables["SpellMisc"] if r["SpellID"] == IGNITE_AURA and r["DifficultyID"] == 0)
    duration = next(r["Duration"] for r in tables["SpellDuration"] if r["ID"] == misc["DurationIndex"])
    period = next(r["EffectAuraPeriod"] for r in tables["SpellEffect"] if r["SpellID"] == IGNITE_AURA)
    aura = next(r for r in tables["SpellAuraOptions"] if r["SpellID"] == IGNITE_AURA)
    return duration, period, aura["CumulativeAura"]


def test_ignite_constants_come_from_the_client(game_data, client_tables):
    duration_ms, period_ms, cumulative = _client_ignite(client_tables)
    assert (duration_ms, period_ms, cumulative) == (4000, 2000, 1)
    lv = game_data.leveling
    assert lv.ignite_duration_s == duration_ms / 1000
    assert lv.ignite_tick_s == period_ms / 1000
    assert lv.ignite_cumulative == cumulative
    assert lv.ignite_rule == "rolling"
    assert lv.ignite_ticks == 2  # mode seed : durée / période = 2 tics par critique, comme le seed


def test_single_crit_ticks_twice(game_data):
    state = roll_ignite(game_data, None, 0.0, 80.0)
    assert state == IgniteState(80.0, (2.0, 4.0))
    assert ignite_ticks_due(state, 1.0) == (0.0, state)
    dealt, rest = ignite_ticks_due(state, 2.0)
    assert dealt == 40.0 and rest == IgniteState(40.0, (4.0,))
    assert ignite_ticks_due(rest, 4.0) == (40.0, None)


def test_second_crit_rolls_the_remainder_and_restarts_the_ticks(game_data):
    """Critique de 80 à t = 0, puis de 60 à t = 1 : reste 80 + 60 = 140, tics de 70 à 3 s et 5 s."""
    state = roll_ignite(game_data, roll_ignite(game_data, None, 0.0, 80.0), 1.0, 60.0)
    assert state == IgniteState(140.0, (3.0, 5.0))
    dealt, rest = ignite_ticks_due(state, 3.0)
    assert dealt == 70.0 and rest == IgniteState(70.0, (5.0,))
    assert ignite_ticks_due(rest, 10.0) == (70.0, None)


def test_rolled_ignite_deals_exactly_what_was_posted(game_data):
    """Après un tic (40 infligés), critique de 60 à 2,5 s : reste 40 + 60 = 100, tics de 50 à 4,5 s et 6,5 s."""
    state = roll_ignite(game_data, None, 0.0, 80.0)
    first, state = ignite_ticks_due(state, 2.0)
    state = roll_ignite(game_data, state, 2.5, 60.0)
    assert state == IgniteState(100.0, (4.5, 6.5))
    rest_dealt, end = ignite_ticks_due(state, 100.0)
    assert end is None and first + rest_dealt == pytest.approx(80.0 + 60.0, rel=1e-12)


def test_remainder_at_death_is_never_negative(game_data):
    state = roll_ignite(game_data, None, 0.0, 80.0)
    dealt, rest = ignite_ticks_due(state, 3.0)  # le monstre meurt à 3 s
    assert rest is not None and rest.remaining >= 0 and dealt + rest.remaining == pytest.approx(80.0, rel=1e-12)


def test_forever_monte_carlo_differs_from_the_seed_only_through_ignite(game_data):
    """Sans le talent, aucune différence entre `forever` et `seed` au niveau 16 (feu) ; avec, l'Ignite roulant
    change le résultat (effet mesuré par différence, graine fixe). Critique relevé à 50 % : au critique de base, deux
    critiques à moins de 4 s sont trop rares pour que l'écart soit visible à n = 150."""
    plain = mc(game_data, 16, FIRE_PLAIN, "Orc", "fire", 150, seed=11, over=HIGH_CRIT)
    assert plain == mc(game_data, 16, FIRE_PLAIN, "Orc", "fire", 150, seed=11, over=HIGH_CRIT, rules="seed")
    rolling = mc(game_data, 16, FIRE_IGNITE, "Orc", "fire", 150, seed=11, over=HIGH_CRIT)
    assert rolling != mc(game_data, 16, FIRE_IGNITE, "Orc", "fire", 150, seed=11, over=HIGH_CRIT, rules="seed")
    assert rolling == mc(game_data, 16, FIRE_IGNITE, "Orc", "fire", 150, seed=11, over=HIGH_CRIT)  # reproductible
