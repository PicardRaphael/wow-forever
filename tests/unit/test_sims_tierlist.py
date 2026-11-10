"""Tier list à la demande (demande du 2026-11-10 : « tout doit être calculable à la demande ») : toutes les
spécialisations de dégâts d'une faction classées par contexte, chaque chiffre venant de wowsims par les calculs déjà
là (`compare_presets` à équipement GearQuest égal pour le raid, `run_from_sources` par tranche pour le donjon et le
leveling) :

- `raid` : niveau 60, mêmes buffs, consommables de chacun, équipement GearQuest du 60 ; classé au DPS ;
- `donjon` : par tranche, buffs de groupe, plusieurs cibles ; classé au DPS ;
- `leveling` : par tranche, seul, repos compris ; classé à l'XP par heure (DPS affiché).

Une race par classe, la première race jouable de la faction dans `races.json` (ou celle donnée) ; résultat gardé
dans le cache et relu. Calculs fabriqués : aucune valeur de jeu."""

import pytest
from test_sims_brackets import _setup as brackets_setup

from forever.errors import InvalidArgumentError
from forever.sims import tierlist
from forever.store import load_version


def _fake_brackets(calls):
    def run(**kw):
        calls.append(kw)
        bonus = {"mage/dps/Fire": 10.0}.get(kw["preset"], 0.0)
        rows = [{"bracket": "20-29", "level": 25, "dps": 100.0 + bonus, "stdev": 1.0,
                 "xp_per_hour": 5000.0 - 10 * bonus, "rotation": kw["preset"]}]  # fmt: skip
        return {"rows": rows, "provenance": {"assumptions": ["calcul fabriqué"]}}

    return run


def _fake_compare(calls):
    def run(cases, **kw):
        calls.append((cases, kw))
        rows = [{"preset": key, "race": race, "dps": 50.0 + i, "stdev": 1.0} for i, (key, race) in enumerate(cases)]
        return sorted(rows, key=lambda r: -r["dps"]), ["calcul fabriqué"]

    return run


PRESETS = ["mage/dps/Fire", "shaman/elemental/testing"]


def test_races_are_the_first_playable_race_of_the_faction(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    races = load_version(deps).read_json("races.json")["races"]
    chosen = tierlist.faction_races(deps, "horde")
    assert chosen["Mage"] in {n for n, r in races.items() if r["faction"] == "Horde" and "Mage" in r["classes"]}
    first = next(n for n in races if races[n]["faction"] == "Horde" and "Mage" in races[n]["classes"])
    assert chosen["Mage"] == first
    assert tierlist.faction_races(deps, "horde", overrides={"Mage": "Troll"})["Mage"] == "Troll"
    with pytest.raises(InvalidArgumentError, match="Faction"):
        tierlist.faction_races(deps, "neutre")


def test_leveling_is_ranked_by_xp_per_hour_and_dungeon_by_dps(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    calls = []
    lev = tierlist.tier_list(deps, context="leveling", faction="horde", presets=PRESETS,
                             run_brackets=_fake_brackets(calls))  # fmt: skip
    assert [r["preset"] for r in lev["brackets"][0]["ranking"]] == ["shaman/elemental/testing", "mage/dps/Fire"]
    assert {c["objective"] for c in calls} == {"leveling"} and {c["conditions"] for c in calls} == {"solo"}
    calls.clear()
    dun = tierlist.tier_list(deps, context="donjon", faction="horde", presets=PRESETS,
                             run_brackets=_fake_brackets(calls))  # fmt: skip
    assert [r["preset"] for r in dun["brackets"][0]["ranking"]] == ["mage/dps/Fire", "shaman/elemental/testing"]
    assert {c["conditions"] for c in calls} == {"group"} and {c["targets"] for c in calls} == {tierlist.DUNGEON_TARGETS}
    assert any("calcul fabriqué" in a for a in dun["provenance"]["assumptions"])


def test_raid_compares_at_level_60_and_result_is_kept(make_deps, tmp_path):
    deps = brackets_setup(make_deps, tmp_path)
    calls = []
    out = tierlist.tier_list(deps, context="raid", faction="horde", presets=PRESETS, run_compare=_fake_compare(calls))
    assert len(calls) == 1 and out["brackets"][0]["level"] == 60
    assert out["brackets"][0]["ranking"][0]["preset"] == "shaman/elemental/testing"
    again = tierlist.tier_list(deps, context="raid", faction="horde", presets=PRESETS,
                               run_compare=_fake_compare(calls))  # fmt: skip
    assert len(calls) == 1 and again["brackets"] == out["brackets"]  # relu, pas recalculé
    assert tierlist.read_tier_list(deps, "raid", "horde")["brackets"] == out["brackets"]
    assert tierlist.read_tier_list(deps, "leveling", "horde") is None
    with pytest.raises(InvalidArgumentError, match="Contexte"):
        tierlist.tier_list(deps, context="bg", faction="horde", presets=PRESETS)


def test_simulate_action_reads_the_kept_tier_list(make_deps, tmp_path):
    from forever.sims.report import simulate

    deps = brackets_setup(make_deps, tmp_path)
    with pytest.raises(InvalidArgumentError, match="forever sims tierlist"):
        simulate(deps, "tierlist", context="leveling", faction="horde")
    tierlist.tier_list(deps, context="leveling", faction="horde", presets=PRESETS, run_brackets=_fake_brackets([]))
    out = simulate(deps, "tierlist", context="leveling", faction="horde")
    assert out["context"] == "leveling" and out["brackets"][0]["ranking"]
