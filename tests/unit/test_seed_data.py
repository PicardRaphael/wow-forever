"""Mode seed figé (T06b, bloc A, décision D2) : `_seed_talents.json` et `_seed_spells.json`, copies octet pour octet
du seed, sont lus par `build_game_data(..., rules="seed")` ; le mode forever lit `talents.json` et `spells.json`.

Copie « client » : `talents.json` et `spells.json` d'une copie des données remplacés par ceux de la candidate décodée
des fixtures du client (manifeste régénéré) ; le mode seed doit y rendre exactement les résultats du dépôt."""

import hashlib
import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, PREVIOUS_VERSION, SEED_DATA, SEED_VERSION, isolated_deps

import forever.build as build_module
from forever.build import build_report
from forever.engine.cast import expected_cast
from forever.engine.character import character
from forever.errors import InvalidArgumentError
from forever.gamedata import build_game_data
from forever.leveling import simulate_leveling
from forever.manifest import compute_manifest, write_manifest
from forever.optimize.endgame import seed_pvp_greedy
from forever.pipeline.verify import verify_version
from forever.sim.leveling_mc import mc
from forever.store import load_version

SEED_COPIES = {
    "_seed_talents.json": ("talents.json", "b1dcf6e696ea5783aa12693466014afe6a05e2ac1c7a82c30c50cf2ed71785eb"),
    "_seed_spells.json": ("spells.json", "49272dc659d468dd340597258ccd2c5659283387d7c4ef77d1566ada7994be0d"),
}
SEED_MODE = {"mob_source": "seed", "spell_level": "rank", "rules": "seed"}
# Cas de parité du simulateur (tests/parity/test_sim_leveling_parity.py) qui passe par Ice Lance rang 1.
L24 = {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceLance": 1, "frostChanneling": 3}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def client_copy(tmp_path_factory, candidate):
    """Copie des données dont `talents.json` et `spells.json` sont ceux de la candidate du client."""
    tmp = tmp_path_factory.mktemp("client-copy")
    data = tmp / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("talents.json", "spells.json"):
        shutil.copyfile(candidate.root / PREVIOUS_VERSION / name, data / LOCAL_VERSION / name)
    write_manifest(data)
    return isolated_deps(tmp, data)


def test_seed_copies_are_byte_identical_to_the_seed():
    for copy, (name, digest) in SEED_COPIES.items():
        assert sha(SEED_DATA / SEED_VERSION / name) == digest, name
        assert sha(DATA_DIR / LOCAL_VERSION / copy) == digest, copy


def test_seed_copies_are_covered_by_the_manifest_and_sources():
    files = compute_manifest(DATA_DIR)["versions"][LOCAL_VERSION]["files"]
    sources = json.loads((DATA_DIR / LOCAL_VERSION / "sources.json").read_text(encoding="utf-8"))["files"]
    for copy in SEED_COPIES:
        assert copy in files, copy
        assert sources[copy]["certainty"] in ("certain", "probable", "suppose"), copy
        assert "seed" in sources[copy]["source"], copy


def test_seed_rules_read_the_frozen_copies(client_copy, seed_game_data):
    version = load_version(client_copy)
    seed = build_game_data(version, rules="seed")
    forever = build_game_data(version, rules="forever")
    # talents.json du client : Hot Streak 20 s, Impact 3 / 7 / 10 ; copies du seed : 15 s, 3 / 6 / 9.
    assert forever.talents["hotStreak"].ranks == ((20, 25, 3),)
    assert seed.talents["hotStreak"].ranks == seed_game_data.talents["hotStreak"].ranks == ((15, 25, 3),)
    assert forever.talents["impact"].ranks[1] == (7,) and seed.talents["impact"].ranks[1] == (6,)
    # spells.json du client : coût de Pyroblast rang 1 (SpellPower.ManaCost) ; copie du seed : null.
    assert forever.spells["pyroblast"].ranks[0].mana == 125
    assert seed.spells["pyroblast"].ranks[0].mana is None
    assert seed.spells == seed_game_data.spells and seed.talents == seed_game_data.talents
    assert seed.talent_at == seed_game_data.talent_at and seed.utility == seed_game_data.utility
    # Le reste des données est partagé entre les deux modes.
    assert seed.scaling == forever.scaling and seed.constants == forever.constants


def test_seed_results_do_not_move_with_the_client_values(client_copy, seed_game_data):
    version = load_version(client_copy)
    seed = build_game_data(version, rules="seed")
    forever = build_game_data(version, rules="forever")
    ch = character(seed_game_data, 36, "Human")
    for key in ("pyroblast", "blast_wave", "ice_lance", "arcane_blast"):
        before = expected_cast(seed_game_data, key, 36, {}, ch, rules="seed")
        assert expected_cast(seed, key, 36, {}, character(seed, 36, "Human"), rules="seed") == before, key
    before = mc(seed_game_data, 24, L24, "Orc", "frost", 120, **SEED_MODE)
    assert mc(seed, 24, L24, "Orc", "frost", 120, **SEED_MODE) == before
    assert mc(forever, 24, L24, "Orc", "frost", 120, **SEED_MODE) != before  # Ice Lance rang 1 du client
    assert seed_pvp_greedy(seed, 20, "Orc", beam=2) == seed_pvp_greedy(seed_game_data, 20, "Orc", beam=2)


def test_simulate_leveling_passes_rules_to_the_loader(client_copy, make_deps):
    repo = make_deps()
    args = {"talents": L24, "n": 60, "mob_source": "seed", "spell_level": "rank"}
    seed_here = simulate_leveling(client_copy, 24, rules="seed", **args)
    seed_repo = simulate_leveling(repo, 24, rules="seed", **args)
    assert seed_here["monte_carlo"] == seed_repo["monte_carlo"]
    assert seed_here["analytic"] == seed_repo["analytic"]
    # Révision 2 : le dépôt porte les valeurs du client, comme la copie ; le mode seed garde les siennes.
    forever_here = simulate_leveling(client_copy, 24, rules="forever", **args)
    assert forever_here["monte_carlo"] == simulate_leveling(repo, 24, rules="forever", **args)["monte_carlo"]
    assert forever_here["monte_carlo"] != seed_here["monte_carlo"]


def test_build_report_passes_rules_to_the_loader(make_deps, monkeypatch):
    seen = []
    real = build_module.build_game_data

    def spy(version, rules="forever"):
        seen.append(rules)
        return real(version, rules=rules)

    monkeypatch.setattr(build_module, "build_game_data", spy)
    build_report(make_deps(), "leveling", 11, preset="rapide", rules="seed", sensitivity=False)
    assert seen and set(seen) == {"seed"}


def test_unknown_rules_are_refused(make_deps):
    with pytest.raises(InvalidArgumentError):
        build_game_data(load_version(make_deps()), rules="retail")


def test_verify_builds_the_seed_copies(data_copy, make_deps):
    path = data_copy / LOCAL_VERSION / "_seed_talents.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["trees"][0]["talents"][0]["max"]
    path.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    write_manifest(data_copy)
    report = verify_version(make_deps(data_dir=data_copy))
    assert not report["ok"]
    assert any("_seed_talents.json" in e for e in report["errors"]), report["errors"]
