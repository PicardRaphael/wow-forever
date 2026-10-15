"""Naowh Forever 1.1.19 (relevé du 2026-10-15) : les quêtes de Completo passent dans l'addon chargé à la demande
`NaowhForever_DiscoveryData` (`Quests.lua`) et les positions de Journeys dans `NaowhForever_JourneysData`
(`QuestSpots.lua`), même format. Les lecteurs prennent le nouvel emplacement, sinon l'ancien.

Fixture : `tests/fixtures/addons/quests/` (ancienne disposition), recopiée dans `tmp_path` à la nouvelle. Aucun réseau."""

import shutil

from conftest import FIXTURES

from forever.pipeline.quest_sources import read_completo, read_journeys, source_files

OLD = FIXTURES / "addons" / "quests" / "Interface" / "AddOns"


def _new_layout(tmp_path):
    addons = tmp_path / "AddOns"
    shutil.copytree(OLD, addons)
    discovery, journeys = addons / "NaowhForever_Discovery", addons / "NaowhForever_Journeys"
    (addons / "NaowhForever_DiscoveryData").mkdir()
    (discovery / "QuestList" / "Data" / "Quests.lua").rename(addons / "NaowhForever_DiscoveryData" / "Quests.lua")
    (addons / "NaowhForever_JourneysData").mkdir()
    (journeys / "Data" / "QuestSpots.lua").rename(addons / "NaowhForever_JourneysData" / "QuestSpots.lua")
    return addons


def test_completo_and_journeys_read_from_the_data_addons(tmp_path):
    addons = _new_layout(tmp_path)
    old_completo, new_completo = read_completo(OLD), read_completo(addons)
    assert new_completo is not None and new_completo.source.quests == old_completo.source.quests
    assert new_completo.zone_names == old_completo.zone_names and new_completo.zone_names
    old_spots, new_spots = read_journeys(OLD), read_journeys(addons)
    assert new_spots is not None and new_spots.quests == old_spots.quests


def test_cache_fingerprint_sees_the_data_addons(tmp_path):
    addons = _new_layout(tmp_path)
    files = {p.relative_to(addons).as_posix() for p in source_files(addons, None)}
    assert {"NaowhForever_DiscoveryData/Quests.lua", "NaowhForever_JourneysData/QuestSpots.lua"} <= files
