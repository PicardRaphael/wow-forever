"""SIM2 : spécialisation de GearQuest Forever déduite du préréglage de wowsims, pour que l'équipement d'une tranche
soit celui de la bonne spécialisation : dossier de la spé s'il porte un nom de GearQuest (`retribution`,
`balance`, `elemental`, `enhancement` ; `feralcat` -> `feral`, `feralbear` -> `bear`), sinon arbre le plus pris par
les talents du préréglage (nom en minuscules, espaces en `_` ; « Feral Combat » -> `feral`). Clé rendue sous la forme
`<spé>-<classe>` attendue par `forever_gear`."""

import pytest

from forever.sims.brackets import gearquest_spec


@pytest.mark.parametrize(
    ("key", "lead_tree", "expected"),
    [
        ("paladin/retribution/unsealed_wrath", "Holy", "retribution-paladin"),
        ("druid/feralcat/défaut", "Feral Combat", "feral-druid"),
        ("druid/feralbear/défaut", "Feral Combat", "bear-druid"),
        ("hunter/dps/bm", "Beast Mastery", "beast_mastery-hunter"),
        ("warrior/dps/Fury Pre-BiS", "Fury", "fury-warrior"),
        ("mage/dps/Frost Frost Incin", "Frost", "frost-mage"),
        ("shaman/enhancement/testing", "Enhancement", "enhancement-shaman"),
    ],
)
def test_gearquest_spec_from_the_preset(key, lead_tree, expected):
    assert gearquest_spec(key, lead_tree) == expected
