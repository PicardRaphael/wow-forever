"""Talents choisis au niveau 60 pour les simulateurs (MS1, décision 301) : conversion de nos clés vers la chaîne de
chaque moteur par identifiant de sort, jamais par position.

- wowsims/forever lit sa chaîne dans l'ordre des champs du message `<Classe>Talents` de `proto/<classe>.proto`, chaque
  champ portant `[(talent_spell_id) = N]` ;
- MythicSim lit, sous les règles de Forever, l'ordre du client de sa table (`talent("champ", "Nom", rangs)` de son code
  épinglé) ; le champ y est relié au sort par l'arbre de son fork Go (`ui/sim/talents/trees/<classe>.json`), le nom du
  client de la table servant de contrôle (un carré dont le talent a changé est sans correspondance) ;
- un talent sans correspondance refuse le calcul en le nommant.

Extraits des deux moteurs dans `tests/fixtures/sims/` (révisions dans son README) ; talents du client : données du
dépôt (`forever/data/`, version courante)."""

import pytest
from conftest import FIXTURES

from forever.errors import ForeverError
from forever.sims.talents import (
    TalentConversionError,
    client_trees,
    mythicsim_layout,
    parse_talents,
    wowsims_layout,
)

SIMS = FIXTURES / "sims"
WOWSIMS = SIMS / "wowsims"
ENGINE = SIMS / "mythicsim" / "engine"
GO = SIMS / "mythicsim" / "go"


def _position(layout, key):
    return next((t, i) for t, tree in enumerate(layout.trees) for i, slot in enumerate(tree) if slot.key == key)


def test_wowsims_order_is_the_proto_order(make_deps):
    """Chaman Enhancement : Improved Ghost Wolf est le 13e champ du proto de wowsims (6e chez Talents Forever)."""
    layout = wowsims_layout(WOWSIMS, "Shaman", client_trees(make_deps(), "Shaman"))
    assert [len(t) for t in layout.trees] == [16, 18, 16]
    assert _position(layout, "improvedGhostWolf") == (1, 12)
    code = layout.encode({"improvedGhostWolf": 2, "stormstrike": 1})
    assert code == "-0000000000012"
    assert layout.decode(code) == {"improvedGhostWolf": 2, "stormstrike": 1}


def test_wowsims_slot_without_a_client_talent_is_named_when_used(make_deps):
    """Call of Thunder (champ du proto sans sort connu du client) : une chaîne qui le prend est refusée en le nommant ;
    notre `lavaBurst` (sans champ chez wowsims) aussi."""
    layout = wowsims_layout(WOWSIMS, "Shaman", client_trees(make_deps(), "Shaman"))
    slot = layout.trees[0][12]
    assert slot.key is None and slot.field == "call_of_thunder"
    with pytest.raises(TalentConversionError, match="call_of_thunder"):
        layout.decode("0000000000001")
    with pytest.raises(TalentConversionError, match="lavaBurst"):
        layout.encode({"lavaBurst": 1})
    assert layout.decode("5") == {"convection": 5}  # sans point sur ce carré : rien à refuser


def test_mythicsim_order_is_the_client_order_of_its_table(make_deps):
    """MythicSim (règles de Forever) : Improved Ghost Wolf en 13e place d'Enhancement aussi, Lightning Mastery (nom du
    client de la table) relié à notre `elementalMastery` par le sort du fork, que wowsims nomme pareil."""
    client = client_trees(make_deps(), "Shaman")
    layout = mythicsim_layout(ENGINE, GO, "Shaman", client, wowsims=WOWSIMS)
    assert [len(t) for t in layout.trees] == [16, 18, 16]
    assert _position(layout, "improvedGhostWolf") == (1, 12)
    assert layout.trees[0][15].key == "elementalMastery" and layout.trees[0][15].name == "Lightning Mastery"
    call = layout.trees[0][12]
    assert call.key is None and call.name == "Call of Thunder"  # le fork y a Lava Burst : carré changé, refusé
    with pytest.raises(TalentConversionError, match="Call of Thunder"):
        layout.decode("0000000000001")


def test_mythicsim_rename_without_wowsims_is_refused(make_deps):
    """Sans le proto de wowsims pour confirmer un nom changé, le carré reste sans correspondance (jamais deviné)."""
    layout = mythicsim_layout(ENGINE, GO, "Shaman", client_trees(make_deps(), "Shaman"), wowsims=None)
    assert layout.trees[0][15].key is None
    assert layout.trees[1][12].key == "improvedGhostWolf"


def test_mage_orders_agree_and_client_names_are_checked(make_deps):
    """Mage : MythicSim nomme Accelerant et Precision comme le client ; une chaîne lue par wowsims se réécrit à
    l'identique pour MythicSim (même ordre du client 70707 des deux côtés)."""
    client = client_trees(make_deps(), "Mage")
    ws = wowsims_layout(WOWSIMS, "Mage", client)
    ms = mythicsim_layout(ENGINE, GO, "Mage", client, wowsims=WOWSIMS)
    assert ms.trees[1][1].key == "improvedFireball" and ms.trees[1][1].name == "Accelerant"
    assert ms.trees[2][2].key == "elementalPrecision"
    code = "050205203100311531-525000012001-003"
    assert ms.encode(ws.decode(code)) == code


def test_class_without_a_read_table_is_refused(make_deps):
    with pytest.raises(TalentConversionError, match="Paladin"):
        mythicsim_layout(ENGINE, GO, "Paladin", client_trees(make_deps(), "Paladin"), wowsims=WOWSIMS)


def test_talents_parameter_is_read():
    assert parse_talents("improvedGhostWolf=2, stormstrike=1") == {"improvedGhostWolf": 2, "stormstrike": 1}
    with pytest.raises(ForeverError, match="clé=rang"):
        parse_talents("improvedGhostWolf")
