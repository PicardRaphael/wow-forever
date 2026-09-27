"""Décisions sur les écarts client 1.60.1.70009 ↔ référence (tasks/T03-ecarts.md, tranchées par l'utilisateur).

- Sélection des variables par talent (`decode_rules.json`, `rank_variables`) : `ranks` garde la forme de
  talents.json (positions stables pour le moteur), `tooltip_values` garde toutes les variables de l'infobulle.
- confirmed_changes.json : chaque entrée porte une nature (client, format, convention).
Valeurs : talents.json pour `ranks`, fixtures wago 1.60.1.70009 pour les variables propres au client."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.pipeline.decode import decode_talents

REFERENCE = {
    t["key"]: t for tree in read_json(DATA_DIR / LOCAL_VERSION / "talents.json")["trees"] for t in tree["talents"]
}
CONFIRMED = read_json(DATA_DIR / LOCAL_VERSION / "confirmed_changes.json")["changes"]


@pytest.fixture(scope="module")
def talents(client_tables, decode_rules):
    doc = decode_talents(client_tables, decode_rules, LOCAL_VERSION)
    return {t["key"]: t for tree in doc["trees"] for t in tree["talents"]}


def test_selection_targets_known_talents(decode_rules):
    selection = decode_rules["rank_variables"]
    assert selection and set(selection) <= set(REFERENCE)
    assert all(isinstance(i, int) and i >= 0 for indices in selection.values() for i in indices)


@pytest.mark.parametrize(
    ("key", "ranks", "tooltip_values"),
    [  # ranks : talents.json ; tooltip_values : infobulles des fixtures (Spell, SpellEffect, SpellDuration…)
        ("ignite", [[8], [16], [24], [32], [40]], [[8, 4], [16, 4], [24, 4], [32, 4], [40, 4]]),
        (
            "wintersChill",
            [[20, 1], [40, 2], [60, 3], [80, 4], [100, 5]],
            [[20, 2, 15, 1], [40, 2, 15, 2], [60, 2, 15, 3], [80, 2, 15, 4], [100, 2, 15, 5]],
        ),
        ("arcaneConcentration", [[2], [4], [6], [8], [10]], [[2, 100], [4, 100], [6, 100], [8, 100], [10, 100]]),
        ("frostbite", [[5], [10], [15]], [[5, 5], [10, 5], [15, 5]]),
    ],
)
def test_selected_ranks_keep_reference_shape(talents, key, ranks, tooltip_values):
    assert REFERENCE[key]["ranks"] == ranks
    assert talents[key]["ranks"] == ranks
    assert talents[key]["tooltip_values"] == tooltip_values


def test_every_talent_keeps_all_tooltip_values(talents, decode_rules):
    selection = decode_rules["rank_variables"]
    for key, t in talents.items():
        assert len(t["tooltip_values"]) == t["max"], key
        if key not in selection:
            assert t["ranks"] == t["tooltip_values"], key
        else:
            expected = [[values[i] for i in selection[key]] for values in t["tooltip_values"]]
            assert t["ranks"] == expected, key


def test_selection_beyond_tooltip_is_an_error(client_tables, decode_rules):
    from forever.errors import DataSchemaError

    rules = {**decode_rules, "rank_variables": {**decode_rules["rank_variables"], "ignite": [5]}}
    with pytest.raises(DataSchemaError) as info:
        decode_talents(client_tables, rules, LOCAL_VERSION)
    assert "ignite" in info.value.message


def test_confirmed_changes_have_a_nature():
    assert CONFIRMED
    assert {c["nature"] for c in CONFIRMED} <= {"client", "format", "convention"}


def test_presence_of_mind_is_a_format_change():
    pom = [c for c in CONFIRMED if c["key"] == "presenceOfMind"]
    assert [(c["field"], c["old"], c["new"], c["nature"]) for c in pom] == [("ranks[1]", [10], [], "format")]


def test_talent_rank_one_spells_are_conventions():
    rows = [c for c in CONFIRMED if c["kind"] == "spell" and c["field"].endswith((".min", ".max"))]
    assert len(rows) == 8 and {c["nature"] for c in rows} == {"convention"}
