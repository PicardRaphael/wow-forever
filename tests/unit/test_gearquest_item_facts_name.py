"""SIM2 : les fiches d'objets de GearQuest Forever d'une classe se lisent sous `GQ.Data.<classe>ItemFacts` ou, comme
le module Paladin depuis sa dernière version, sous `GQ.Data.itemFacts` (dans le dossier de la classe) ; sans elles,
chaque choix de la classe était écarté pour « source inconnue ». Addon fabriqué dans `tmp_path`."""

from forever.pipeline.gear_sources import read_gearquest_facts

FACTS = """local GQ = _G.GearQuest
GQ.Data = GQ.Data or {}
GQ.Data.NAME = {
    [279899]={name="Cape d'essai",quality=2,ilvl=12,reqLevel=10,sourceType="quest",zone="Elwynn Forest"},
}
"""


def _addon(tmp_path, class_token, name):
    folder = tmp_path / f"GearQuestForever_{class_token}"
    folder.mkdir(parents=True)
    (folder / f"Data.{class_token.title()}.generated.lua").write_text(FACTS.replace("NAME", name), encoding="utf-8")
    return tmp_path


def test_class_named_facts_are_read(tmp_path):
    facts = read_gearquest_facts(_addon(tmp_path, "MAGE", "mageItemFacts"), "MAGE")
    assert 279899 in facts


def test_generic_item_facts_name_is_read_too(tmp_path):
    facts = read_gearquest_facts(_addon(tmp_path, "PALADIN", "itemFacts"), "PALADIN")
    assert 279899 in facts
