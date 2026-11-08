"""SIM2 (plan 3c) : temps pour tuer un monstre normal du niveau de la tranche et XP par heure, par tranche.

- temps pour tuer = PV mesurés au niveau (`monsters.json`, `mob_hp`) / DPS de la ligne (wowsims corrigé) ;
- XP par heure = XP d'un monstre de même niveau (`mob_kill_xp`, `PerKill` du client) sur le temps d'un monstre : combat
  plus course entre deux monstres du moteur (`leveling.defaults.run_between_s`) ; repos non compté (wowsims ne rend ni
  la mana dépensée ni les dégâts subis), dit dans la provenance ;
- donnée absente pour un niveau : champ absent, raison dite.

Données de test du dépôt (`DATA_DIR`) lues par les fonctions du moteur ; simulateur fabriqué (`LevelSim` : DPS égal
au niveau) : aucun chiffre de jeu écrit ici."""

import dataclasses

import pytest
from test_sims_brackets import FROST_STEPS, LevelSim, _setup

from forever.engine.dungeon import SECONDS_PER_HOUR
from forever.engine.monsters import grind_xp_per_hour, mob_hp, time_to_kill
from forever.engine.xp import mob_kill_xp
from forever.gamedata import build_game_data
from forever.sims.brackets import run_brackets
from forever.sims.leveling_rates import add_rates
from forever.store import load_version


def test_time_to_kill_is_hit_points_over_damage_per_second():
    assert time_to_kill(100.0, 20.0) == pytest.approx(5.0)
    with pytest.raises(ValueError):
        time_to_kill(100.0, 0.0)


def test_grind_xp_per_hour_counts_the_fight_and_the_time_between_fights():
    assert grind_xp_per_hour(50.0, 10.0, 8.0) == pytest.approx(50.0 * SECONDS_PER_HOUR / 18.0)
    with pytest.raises(ValueError):
        grind_xp_per_hour(50.0, 0.0, 0.0)


def _out(make_deps, tmp_path, brackets="10-19,20-29"):
    deps = _setup(make_deps, tmp_path)
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets=brackets, steps=FROST_STEPS,
                       picks_at=None, iterations=100, runner=LevelSim())  # fmt: skip
    return deps, out


def test_each_row_gets_time_to_kill_and_xp_per_hour_from_the_engine(make_deps, tmp_path):
    deps, out = _out(make_deps, tmp_path)
    gd = build_game_data(load_version(deps))
    out = add_rates(deps, out)
    for row in out["rows"]:
        level = row["level"]
        hp = mob_hp(gd, level)
        assert row["ttk_s"] == pytest.approx(hp.value / row["dps"])
        between = gd.leveling.default_run_between_s
        xp = mob_kill_xp(gd, level, level).xp
        assert row["xp_per_hour"] == pytest.approx(xp * SECONDS_PER_HOUR / (row["ttk_s"] + between))
        rates = row["rates"]
        assert rates["mob_hp"] == {"level": level, "value": hp.value, "certainty": hp.certainty, "source": hp.source}
        assert rates["xp_per_kill"]["value"] == xp
        assert rates["between_s"] == between
        assert rates["certainty"] == "suppose"  # le DPS vient de wowsims (suppose)
    text = " ".join(out["provenance"]["assumptions"])
    assert "temps pour tuer" in text and "monsters.json" in text
    assert "repos" in text and "run_between_s" in text and "PerKill" in text
    assert out["provenance"]["certainty"] == "suppose"


def test_missing_hit_points_leave_the_fields_out_with_the_reason(make_deps, tmp_path):
    deps, out = _out(make_deps, tmp_path, brackets="10-19")
    gd = build_game_data(load_version(deps))
    empty = dataclasses.replace(gd, monsters=dataclasses.replace(gd.monsters, hp_by_level={}))
    row = add_rates(deps, out, gd=empty)["rows"][0]
    assert "ttk_s" not in row and "xp_per_hour" not in row
    assert "15" in row["rates_missing"] and "monsters.json" in row["rates_missing"]


def test_rows_in_error_are_left_alone(make_deps, tmp_path):
    deps = _setup(make_deps, tmp_path)
    bad = [{"level": 10, "key": "iceShards", "rank": 1}]
    out = run_brackets(deps, preset="mage/dps/Fire", race="Human", brackets="10-19", steps=bad, picks_at=None,
                       iterations=100, runner=LevelSim())  # fmt: skip
    row = add_rates(deps, out)["rows"][0]
    assert "error" in row and "ttk_s" not in row and "rates_missing" not in row
