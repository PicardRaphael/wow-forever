"""Chaîne du Cozy Sleeping Bag (T04f, bloc E) : lue dans Naowh Forever Discovery, recoupée avec FojjiCore Dungeon
Journal, ordre selon le camp, étape suivante d'après les quêtes faites, écarts entre sources signalés, source
manquante nommée, rien écrit dans le dépôt. Fixtures : extraits structurels `tests/fixtures/addons/xp_bonuses/`."""

import shutil

from conftest import FIXTURES, REPO_ROOT

from forever.pipeline.sleeping_bag import read_fojji_chain, read_naowh_chain
from forever.xp_bonuses import lookup_xp_bonuses, sleeping_bag_chain

WOW = FIXTURES / "addons" / "xp_bonuses"
ADDONS = WOW / "Interface" / "AddOns"
BAG = 211527


def test_naowh_reader_resolves_shared_steps_and_concatenation():
    chain = read_naowh_chain(ADDONS)
    assert (chain.addon, chain.version, chain.level, chain.item) == ("NaowhForever_Discovery", "1.1.11", 14, BAG)
    assert len(chain.steps["H"]) == len(chain.steps["A"]) == 7
    assert chain.steps["H"][0]["started"] == 79007 and chain.steps["H"][2]["object"] == "Pocket Litter"
    assert chain.steps["H"][5]["tip"] == "tip (suite)"
    assert chain.optional["quest"] == "Rekindle"


def test_fojji_reader_keeps_sides():
    chain = read_fojji_chain(ADDONS)
    assert (chain.addon, chain.version, chain.level, chain.item) == ("FojjiCore_DungeonJournal", "3.3.5", 14, BAG)
    zones = [s["zone"] for s in chain.steps["*"]]
    assert zones[0] == "Westfall" and zones[-1] == "Hillsbrad Foothills"
    assert chain.steps["*"][1]["side"] == "Horde"


def test_order_depends_on_the_faction(make_deps):
    deps = make_deps(wow_dir=WOW)
    horde = sleeping_bag_chain(deps, faction="horde", addons_dir=ADDONS)
    alliance = sleeping_bag_chain(deps, faction="alliance", addons_dir=ADDONS)
    assert horde.steps[0].zone == "The Barrens" and alliance.steps[0].zone == "Westfall"
    assert horde.next_step == horde.steps[0] and horde.level == 14 and horde.item == BAG
    for step in horde.steps:
        assert step.map and step.x is not None and step.y is not None and step.source and step.certainty


def test_done_quest_moves_to_the_next_step(make_deps):
    chain = sleeping_bag_chain(make_deps(wow_dir=WOW), faction="horde", done_quests=[79007], addons_dir=ADDONS)
    assert chain.next_step.quest_id == 79192 and chain.next_step.zone == "Stonetalon Mountains"
    done = sleeping_bag_chain(
        make_deps(wow_dir=WOW), faction="horde", done_quests=[79007, 79192, 79980, 79974, 79975, 79976]
    )
    assert done.next_step is None


def test_sources_disagree_on_the_last_zone(make_deps):
    chain = sleeping_bag_chain(make_deps(wow_dir=WOW), faction="horde", addons_dir=ADDONS)
    text = " ".join(chain.discrepancies)
    assert "Arathi Highlands" in text and "Hillsbrad Foothills" in text
    assert set(chain.sources) == {"NaowhForever_Discovery 1.1.11", "FojjiCore_DungeonJournal 3.3.5"}


def test_missing_naowh_is_named_and_fojji_is_used(make_deps, tmp_path):
    addons = tmp_path / "AddOns"
    shutil.copytree(ADDONS / "FojjiCore_DungeonJournal", addons / "FojjiCore_DungeonJournal")
    chain = sleeping_bag_chain(make_deps(), faction="horde", addons_dir=addons)
    assert any("NaowhForever_Discovery" in m for m in chain.missing)
    assert chain.steps and chain.steps[0].zone == "The Barrens" and chain.steps[0].certainty == "suppose"
    empty = sleeping_bag_chain(make_deps(), faction="horde", addons_dir=tmp_path / "rien")
    assert empty.steps == [] and empty.next_step is None and len(empty.missing) == 2


def test_chain_is_cached_outside_the_repository(make_deps, tmp_path):
    before = {p for p in REPO_ROOT.rglob("sleeping_bag*.json")}
    deps = make_deps(wow_dir=WOW, cache_dir=tmp_path / "cache")
    sleeping_bag_chain(deps, faction="horde", addons_dir=ADDONS)
    assert list((tmp_path / "cache").rglob("sleeping_bag_chain*.json"))
    assert {p for p in REPO_ROOT.rglob("sleeping_bag*.json")} == before


def test_lookup_gives_the_chain_or_names_the_missing_source(make_deps, tmp_path):
    found = lookup_xp_bonuses(make_deps(wow_dir=WOW))
    assert found["sleeping_bag_chain"]["steps"] and found["sleeping_bag_chain"]["discrepancies"]
    empty = tmp_path / "wow"
    (empty / "Interface" / "AddOns").mkdir(parents=True)
    missing = lookup_xp_bonuses(make_deps(wow_dir=empty))["sleeping_bag_chain"]
    assert missing["steps"] == [] and any("NaowhForever_Discovery" in m for m in missing["missing"])
