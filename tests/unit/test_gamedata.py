"""Construction de `GameData` depuis les fichiers de la version (après contrôle d'intégrité).

Sources : seed/forever-mage/tests/run_all.py (tests `donnees_completes` et `valeurs_client_70009`) ;
seed/forever-mage/data/1.60.1.70009/{spells,talents,racials,leveling}.json ; forever/data/1.60.1.70009/mechanics.json."""

import json
from collections import Counter

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json, tamper

from forever.engine import Rank, coefficient
from forever.errors import DataIntegrityError, DataSchemaError
from forever.gamedata import build_game_data, load_game_data
from forever.manifest import write_manifest
from forever.profile import CLASSES
from forever.store import load_version


def edit_mechanics(data_dir, change):
    path = data_dir / LOCAL_VERSION / "mechanics.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc["values"])
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    write_manifest(data_dir)  # modification voulue : l'intégrité reste valide, seul le schéma est en cause


def test_trees(game_data):
    assert Counter(t.tree for t in game_data.talents.values()) == {"Arcane": 18, "Fire": 17, "Frost": 19}
    assert game_data.trees == ("Arcane", "Fire", "Frost")
    assert game_data.game_version == LOCAL_VERSION


def test_spell_ranks(game_data):
    assert len(game_data.spells) >= 15
    assert game_data.spells["frostbolt"].ranks[1] == Rank(2, 8, 34, 38, 0, 0, 1.8, 35, 0)
    assert game_data.spells["fireball"].ranks[2] == Rank(3, 12, 48, 66, 6, 6, 2.5, 65, 0)
    ice_lance = game_data.spells["ice_lance"]
    assert (ice_lance.talent, ice_lance.frozen_mult, ice_lance.range_yd) == ("iceLance", 4.0, 30)
    assert game_data.spells["arcane_blast"].mana_pct_base == 0.15
    assert game_data.spells["arcane_missiles"].channel is True
    assert game_data.spells["frostbolt"].slow == 0.4
    assert game_data.spells["frost_nova"].range_yd is None


def test_talent_ranks(game_data):
    t = game_data.talents
    assert t["iceLance"].ranks == ((26, 30, 300),)
    assert [r[0] for r in t["improvedFrostbolt"].ranks] == [0.1, 0.2, 0.3, 0.4, 0.5]
    assert t["shatter"].ranks[0][0] == 17 and t["shatter"].ranks[-1][0] == 50
    assert (t["improvedFrostbolt"].tree, t["improvedFrostbolt"].tier, t["improvedFrostbolt"].max_rank) == (
        "Frost",
        1,
        5,
    )
    assert t["improvedFrostbolt"].prereq is None
    assert list(t)[:3] == ["wandSpecialization", "arcaneFocus", "improvedChanneling"]


def test_combat_rules(game_data):
    r = game_data.rules
    assert (r.gcd_s, r.min_miss, r.crit_mult_spell, r.dot_can_crit) == (1.5, 0.01, 1.5, True)
    assert r.spell_miss_by_level_diff["3"] == 0.17
    assert r.spell_miss_by_level_diff["-"] == 0.04


def test_racials(game_data):
    assert game_data.racials.sword_crit["Human"] == 0.02
    assert game_data.racials.spirit_pct["Human"] == 0.05
    assert game_data.racials.mana_pct["Gnome"] == 0.05
    assert game_data.racials.sword_crit.get("Orc", 0.0) == 0.0


def test_constants(game_data):
    c = game_data.constants
    assert c.coefficients.cast_divisor == 3.5
    assert (c.coefficients.cast_min_s, c.coefficients.cast_max_s) == (1.5, 3.5)
    assert c.coefficients.fixed["ice_lance"].value == 0.1429
    assert c.coefficients.fixed["fire_blast"].cast_s == 1.5
    assert c.coefficients.fixed["cone_of_cold"].slowed is True
    assert (c.talents.first_level, c.talents.points_per_tier) == (10, 5)
    assert c.character.crit_base == 0.002
    assert c.crit_per_winters_chill_stack == 0.02
    assert (c.talent_rank_mana_ratio, c.talent_rank_mana_default) == (0.75, 50.0)
    assert c.default_range_yd == 30
    assert c.miss_per_level_below == 0.01  # T04b, décision 4 : cible plus basse (règle Classic, suppose)


def test_missing_constant_is_schema_error(make_deps, data_copy):
    edit_mechanics(data_copy, lambda values: values.pop("coefficient.cast_divisor"))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert exc.value.code == "data_schema"
    assert exc.value.exit_code == 3
    assert "coefficient.cast_divisor" in exc.value.message


def test_wrong_type_is_schema_error(make_deps, data_copy):
    edit_mechanics(data_copy, lambda values: values["talents.first_level"].update(value="dix"))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert "talents.first_level" in exc.value.message


def test_tampered_data_is_integrity_error(make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "mechanics.json")
    with pytest.raises(DataIntegrityError):
        load_game_data(make_deps(data_dir=data_copy))


def test_coefficient_reads_data(make_deps, data_copy):
    """Preuve que le diviseur vient des données : le changer change le coefficient."""
    edit_mechanics(data_copy, lambda values: values["coefficient.cast_divisor"].update(value=4.0))
    gd = load_game_data(make_deps(data_dir=data_copy))
    assert coefficient(gd, "frostbolt", gd.spells["frostbolt"].ranks[-1], rules="seed") == pytest.approx(
        3.0 / 4.0 * 0.95
    )


# --- T04e : schéma 2 de spell_scaling.json, clés de mécanique ----------------------------------------


def edit_scaling(data_dir, change):
    path = data_dir / LOCAL_VERSION / "spell_scaling.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    write_manifest(data_dir)  # modification voulue : seule la forme est en cause


def test_spell_scaling_schema_1_is_refused(make_deps, data_copy):
    edit_scaling(data_copy, lambda doc: doc.update(schema_version=1))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert "schema_version" in exc.value.message


def test_spell_scaling_component_without_coefficient_is_refused(make_deps, data_copy):
    edit_scaling(data_copy, lambda doc: doc["spells"]["frostbolt"][0]["components"][0].pop("bonus_coefficient"))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert "frostbolt" in exc.value.message


def test_spell_scaling_without_fire_vulnerability_is_refused(make_deps, data_copy):
    edit_scaling(data_copy, lambda doc: doc["auras"].pop("fire_vulnerability"))
    with pytest.raises(DataSchemaError) as exc:
        load_game_data(make_deps(data_dir=data_copy))
    assert "fire_vulnerability" in exc.value.message


def test_low_level_default_read(game_data):
    """mechanics.json : pénalité des sorts de bas niveau appliquée par défaut (suppose, T04e décision 2) ; plus de
    rangs d'Improved Cone of Cold propres au mode forever (décision 77 : talents.json, courbe du client)."""
    c = game_data.constants
    assert c.coefficients.low_level_default is True
    assert not hasattr(c, "improved_cone_of_cold_pct")


# --- PV1, bloc B4 : savoir des 9 classes et raciaux décodés du client (décisions 31, 106 ; D5) ---------------


def test_game_data_exposes_nine_classes(game_data):
    assert set(game_data.classes) == set(CLASSES)
    rogue = game_data.classes["Rogue"]
    assert len(rogue.trees) == 3 and all(tree["talents"] for tree in rogue.trees)
    assert any(s["name"] == "Kidney Shot" for s in rogue.spells.values())
    assert game_data.classes["Warlock"].pet_spells and not game_data.classes["Rogue"].pet_spells
    mage_talents = {t["key"] for tree in game_data.classes["Mage"].trees for t in tree["talents"]}
    assert mage_talents == set(game_data.talents)  # même savoir que le moteur du Mage


def test_engine_racials_read_from_races_json(game_data):
    races = read_json(DATA_DIR / LOCAL_VERSION / "races.json")["races"]
    assert not (DATA_DIR / LOCAL_VERSION / "racials.json").exists()
    fields = {"spirit_pct": game_data.racials.spirit_pct, "mana_pct": game_data.racials.mana_pct}
    fields["sword_crit"] = game_data.racials.sword_crit
    for name, race in races.items():
        for key, table in fields.items():
            assert table.get(name, 0.0) == race["mage_values"].get(key, 0.0), (name, key)


def test_seed_mode_reads_frozen_racials(make_deps):
    frozen = read_json(DATA_DIR / LOCAL_VERSION / "_seed_racials.json")["races"]
    seed = build_game_data(load_version(make_deps()), rules="seed")
    assert seed.racials.spirit_pct["Human"] == frozen["Human"]["human_spirit"]["spirit_pct"]
    assert seed.racials.mana_pct["Gnome"] == frozen["Gnome"]["expansive_mind"]["mana_pct"]
    assert seed.racials.sword_crit["Human"] == frozen["Human"]["sword_spec"]["crit"]
