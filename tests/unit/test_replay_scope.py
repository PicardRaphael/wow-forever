"""Rejeu limité aux cas concernés par ce qui change (décision 230, point 2).

Un changement qui ne touche que `monsters.json` (PV des monstres, mesure des journaux) ne rejoue que les cas qui lisent
les PV des monstres : le leveling (simulation et build) et les contextes de fin de partie dont un scénario n'est pas un
boss (`build.scenarios`, `hp` différent de `boss`) ; au relevé du 2026-10-10, le donjon (scénario de paquet de
monstres), pas le raid (boss seulement) ni le PvP (aucun scénario). L'ensemble est tiré des données, jamais écrit à la
main. Tout autre fichier (sorts, talents, règles…) rejoue tous les cas.

Garde : les conseils du raid et du PvP ne lisent jamais la table des monstres (piège sur `GameData.monsters`)."""

import dataclasses
import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION

from forever.engine_inputs import ENGINES, cases_to_replay, compare_inputs, monster_contexts, targeted_replay
from forever.optimize.endgame import optimize_context


def version_copy(tmp_path, name):
    folder = tmp_path / name
    shutil.copytree(DATA_DIR / LOCAL_VERSION, folder)
    return folder


def edit(folder, file, change):
    path = folder / file
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def bump_monsters(doc):
    level = next(iter(doc["hp_by_level"]))
    doc["hp_by_level"][level]["value"] = doc["hp_by_level"][level]["value"] + 1


def contexts_of(cases):
    return {case.rsplit("-", 1)[0] for _, case in cases}


def test_monster_contexts_come_from_the_scenarios(tmp_path):
    folder = version_copy(tmp_path, "v")
    found = monster_contexts(folder)
    assert {"leveling", "sim-leveling", "dungeon"} <= found
    assert "raid" not in found and not any(c.startswith("pvp") for c in found)
    # un raid avec un paquet de monstres le ferait entrer : l'ensemble suit les données
    edit(
        folder,
        "mechanics.json",
        lambda d: d["values"]["build.contexts"]["value"]["raid"].append("dungeon_pack"),
    )
    assert "raid" in monster_contexts(folder)


def test_a_monster_change_replays_only_the_cases_that_read_monster_hp(tmp_path):
    before, after = version_copy(tmp_path, "a"), version_copy(tmp_path, "b")
    edit(after, "monsters.json", bump_monsters)
    diffs = compare_inputs(before, after)
    scope = monster_contexts(before) | monster_contexts(after)
    chosen = cases_to_replay(diffs, monster_scope=scope)
    assert contexts_of(chosen) == {"leveling", "dungeon", "sim-leveling"}
    assert len(chosen) < len(cases_to_replay(diffs))  # sans portée : tous les cas, comme avant
    build_cases = {case for engine, case in chosen if engine == "mage_build"}
    assert build_cases == {c for c in ENGINES["mage_build"].cases if c.startswith(("leveling", "dungeon"))}


def test_a_spell_change_replays_every_case(tmp_path):
    before, after = version_copy(tmp_path, "a"), version_copy(tmp_path, "b")
    edit(after, "monsters.json", bump_monsters)
    edit(after, "mechanics.json", lambda d: d.setdefault("note_de_test", 1))
    diffs = compare_inputs(before, after)
    scope = monster_contexts(before) | monster_contexts(after)
    chosen = cases_to_replay(diffs, monster_scope=scope)
    assert {case for engine, case in chosen if engine == "mage_build"} == set(ENGINES["mage_build"].cases)


def test_targeted_replay_follows_the_scope(tmp_path):
    before, after = version_copy(tmp_path, "a"), version_copy(tmp_path, "b")
    edit(after, "monsters.json", bump_monsters)
    diffs = compare_inputs(before, after)
    calls = []
    targeted_replay(diffs, lambda e, c: calls.append(c), monster_scope=monster_contexts(before))
    assert calls and all(c.startswith(("leveling", "dungeon", "sim-leveling")) for c in calls)


class _Trap:
    def __getattr__(self, name):
        raise AssertionError(f"table des monstres lue ({name})")


@pytest.mark.parametrize("context", ["raid", "pvp-bg", "pvp-world"])
def test_raid_and_pvp_advice_never_read_monster_hp(game_data, context):
    trapped = dataclasses.replace(game_data, monsters=_Trap())
    assert optimize_context(trapped, context, 20, shortlist=1, mc_n=0, depth=1)


def test_the_trap_catches_the_dungeon_pack(game_data):
    """Contrôle du piège : le donjon (paquet de monstres) lit bien la table des monstres."""
    trapped = dataclasses.replace(game_data, monsters=_Trap())
    with pytest.raises(AssertionError, match="table des monstres lue"):
        optimize_context(trapped, "dungeon", 20, shortlist=1, mc_n=0, depth=1)
