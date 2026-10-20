"""1.60.1.70450, bloc A (`tasks/70450-plan.md`) : règles de lecture qui suivent la refonte du Mage sans changer la
lecture des versions passées.

- variables d'infobulle **selon leur nombre** (Winter's Chill : quatre variables avant, trois après) ;
- aura posée par un talent lue par une aura de repli et sa sorte (Winter's Chill : critique 308 avant, dégâts subis
  271 après, la sorte guide le moteur) ;
- marqueur de modèle d'un talent d'après sa description du client (Arcane Blast, Missile Barrage, Fire Power, Winter's
  Chill) : absent, le moteur garde l'ancien sens ;
- raciaux du Mage lus par leur sort (Ruthless, Savage, Wind Blessed, Eureka!) et l'ancien nom gardé ;
- `frozen_mult` d'Ice Lance lu dans le talent (1 + bonus / 100), plus recopié du seed ;
- champs d'un sort nouveau (école, portée, ralentissement, talent) lus dans le client.

Lignes et règles fabriquées ici (même forme que celles du client) ; aucun chiffre de jeu ici."""

import pytest

from forever.errors import DataSchemaError
from forever.pipeline.decode import (
    _select,
    frozen_mult_of,
    new_spell_fields,
    pick_target_aura,
    racial_mage_values,
    talent_model,
)

APPLY_AURA = 6


def test_rank_variables_follow_the_tooltip_shape():
    by_shape = {"4": [0, 3], "3": [0, 2]}
    assert _select("wc", [[20, 2, 15, 1], [40, 2, 15, 2]], by_shape) == [[20, 1], [40, 2]]
    assert _select("wc", [[20, 40, 5], [40, 40, 5]], by_shape) == [[20, 5], [40, 5]]
    assert _select("wc", [[20, 2]], [0]) == [[20]]  # liste simple : inchangé
    with pytest.raises(DataSchemaError):
        _select("wc", [[20, 2]], by_shape)  # forme inconnue : refus, jamais une lecture devinée


def effect(aura, points=0, misc=0):
    return {"Effect": APPLY_AURA, "EffectAura": aura, "EffectBasePointsF": points, "EffectMiscValue_0": misc}


SPEC = {"aura": 308, "kind": "crit", "alternatives": [{"aura": 271, "kind": "cone_of_cold"}]}


def test_target_aura_reads_its_kind():
    kind, row = pick_target_aura(SPEC, [effect(308, 2)], apply_aura=APPLY_AURA)
    assert kind == "crit" and row["EffectBasePointsF"] == 2
    kind, row = pick_target_aura(SPEC, [effect(271, 40)], apply_aura=APPLY_AURA)
    assert kind == "cone_of_cold" and row["EffectBasePointsF"] == 40
    assert pick_target_aura({"aura": 308}, [effect(308, 2)], apply_aura=APPLY_AURA)[0] == "crit"  # règle d'avant
    assert pick_target_aura(SPEC, [effect(999)], apply_aura=APPLY_AURA) is None


MODELS = {
    "arcaneBlast": [{"contains": "of your Intellect as Spell Damage", "model": "intellect_spell_power"}],
    "firePower": [{"contains": "per your Fire effects", "model": "per_fire_effect"}],
}


def test_talent_model_from_the_client_description():
    new = "Each time you cast Arcane Blast, you gain $400573s1% of your Intellect as Spell Damage"
    assert talent_model(MODELS, "arcaneBlast", new) == "intellect_spell_power"
    assert talent_model(MODELS, "arcaneBlast", "the damage of all your other spells is increased by {2}%") is None
    assert talent_model(MODELS, "frostbolt", new) is None


VALUES = {
    "sword_crit": {"aura": 290, "spell_name": "Sword Specialization", "scale": 0.01},
    "crit": {"aura": 290, "spell_names": ["Ruthless", "Savage"], "scale": 0.01},
    "haste": {"aura": 65, "spell_name": "Wind Blessed", "scale": 0.01},
    "eureka_dmg": {"aura": 108, "misc": 0, "spell_name": "Eureka!", "scale": 0.01},
    "eureka_cost": {"aura": 108, "misc": 14, "spell_name": "Eureka!", "scale": 0.01},
    "eureka_duration_s": {"field": "duration_s", "spell_name": "Eureka!"},
    "eureka_cooldown_s": {"field": "cooldown_s", "spell_name": "Eureka!"},
}


def racial(name, effects, duration=None, cooldown=None):
    rows = [{"aura": a, "misc": m, "base_points": p} for a, m, p in effects]
    return {"name": name, "effects": rows, "duration_s": duration, "cooldown_s": cooldown}


def test_racial_values_by_spell_name():
    assert racial_mage_values(VALUES, racial("Ruthless", [(290, 0, 2)])) == {"crit": 0.02}
    assert racial_mage_values(VALUES, racial("Savage", [(290, 0, 1)])) == {"crit": 0.01}
    assert racial_mage_values(VALUES, racial("Sword Specialization", [(290, 0, 5)])) == {"sword_crit": 0.05}
    assert racial_mage_values(VALUES, racial("Wind Blessed", [(342, 0, 3), (65, 0, 3)])) == {"haste": 0.03}
    eureka = racial("Eureka!", [(108, 14, -10), (108, 0, 10), (108, 22, 10)], duration=8, cooldown=120)
    assert racial_mage_values(VALUES, eureka) == {
        "eureka_dmg": 0.1,
        "eureka_cost": -0.1,
        "eureka_duration_s": 8,
        "eureka_cooldown_s": 120,
    }


def test_frozen_multiplier_from_the_talent():
    assert frozen_mult_of([26, 30, 300], 2) == 4.0
    assert frozen_mult_of([26, 30, 200], 2) == 3.0


def test_new_spell_fields_from_the_client():
    masks = {"fire": 4, "frost": 16, "arcane": 64}
    fields = new_spell_fields(school_mask=16, masks=masks, range_max=30, slow_points=-40, durations=[9], talent=None)
    assert fields == {"school": "frost", "range": 30, "slow": 0.4, "slow_dur": [9]}
    wrath = new_spell_fields(school_mask=64, masks=masks, range_max=30, slow_points=None, durations=[None],
                             talent="arcaneWrath")  # fmt: skip
    assert wrath == {"school": "arcane", "range": 30, "talent": "arcaneWrath"}
