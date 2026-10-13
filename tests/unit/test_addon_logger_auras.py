"""T04f, bloc D : ForeverLogger 0.5.0 (vrai Lua sous lupa.lua51) : auras actives du joueur dans chaque état de l'XP et
chaque gain (cumuls, temps restant, nombre borné), rangs des perks Legacy lus hors combat (`C_Traits` sous `pcall`,
arbres fournis par ForeverBridge depuis les données) ; lecture Python (`addon_sv.py`) et rang relié au perk du
moteur. Valeurs synthétiques (client simulé, fixture inventée)."""

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, REPO_ROOT, read_json

lupa = pytest.importorskip("lupa")
from test_addon_logger_xp import Logger

from forever.pipeline.addon_sv import read_logger_db
from forever.xp_bonuses import legacy_ranks_from_logger, legacy_rested_spell

SAMPLE = FIXTURES / "addon" / "ForeverLoggerDB_auras.lua"
SAMPLE_GUID = "Player-0000-0000BEEF"
WELL_RESTED = 429959
OTHER = 12345


def legacy():
    doc = read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")
    perk = next(a for a in doc["auras"] if a["access"] == "legacy")
    return perk["spell_id"], perk["legacy"]["tree"], perk["legacy"]["node"]


def with_auras(logger, auras):
    lua = logger.lua
    logger.stub.time = 500
    logger.stub.player.auras = lua.table_from(
        [lua.table_from({"spellId": s, "applications": n, "expirationTime": e}) for s, n, e in auras]
    )


def test_xp_states_and_gains_keep_the_active_auras():
    game = Logger()
    with_auras(game, [(WELL_RESTED, 3, 2500), (OTHER, 1, 0)])
    game.kill("You gain 10 experience.", xp_after=10)
    (gain,) = game.entries("xp")
    assert [(a.spell, a.stacks, a.remaining) for a in gain.auras.values()] == [(WELL_RESTED, 3, 2000), (OTHER, 1, None)]
    state = game.entries("xp_states")[-1]
    assert [a.spell for a in state.auras.values()] == [WELL_RESTED, OTHER]
    assert game.errors() == {}


def test_auras_are_bounded():
    game = Logger()
    with_auras(game, [(OTHER + i, 1, 0) for i in range(80)])
    game.kill("You gain 10 experience.", xp_after=10)
    (gain,) = game.entries("xp")
    assert 0 < len(gain.auras) < 80


def test_failing_aura_api_leaves_the_field_absent():
    game = Logger(failing=("C_UnitAuras.GetAuraDataByIndex",))
    game.kill("You gain 10 experience.", xp_after=10)
    assert game.entries("xp")[0].auras is None and game.errors() == {}


def legacy_game(*, combat=False, failing=()):
    _spell, tree, node = legacy()
    game = Logger(failing=failing)
    lua = game.lua
    game.stub.player.tree_configs = lua.table_from({tree: 77})
    game.stub.player.nodes = lua.table_from({tree: lua.table_from([node])})
    game.stub.player.ranks = lua.table_from({node: 3})
    lua.globals().ForeverBridgeStatus = lua.table_from(
        {"xp": lua.table_from({"legacy_trees": lua.table_from([tree])})}, recursive=True
    )
    game.stub.combat = combat
    game.fire("PLAYER_LOGIN")
    return game, tree, node


def test_legacy_ranks_are_read_out_of_combat():
    game, tree, node = legacy_game()
    ranks = game.me().legacy.trees[tree]
    assert ranks[node] == 3 and game.errors() == {}


def test_legacy_ranks_wait_for_the_end_of_combat():
    game, tree, node = legacy_game(combat=True)
    assert game.me().legacy is None
    game.stub.combat = False
    game.fire("PLAYER_REGEN_ENABLED")
    assert game.me().legacy.trees[tree][node] == 3


def test_failing_traits_api_leaves_legacy_absent():
    game, _, _ = legacy_game(failing=("C_Traits.GetConfigIDByTreeID",))
    assert game.me().legacy is None and game.errors() == {}


def test_schema_and_version():
    assert Logger().db().schema == 4  # DJ1 : schéma 4 (passages, butin)
    toc = (REPO_ROOT / "addon" / "ForeverLogger" / "ForeverLogger.toc").read_text(encoding="utf-8")
    assert "## Version: 0.6.0" in toc.splitlines()  # DJ1 : 0.6.0


def test_python_reads_auras_and_legacy(game_data):
    spell, tree, node = legacy()
    db = read_logger_db(SAMPLE)
    character = db.characters[SAMPLE_GUID]
    gain = character.xp[-1]
    assert gain.auras == [{"spell": WELL_RESTED, "stacks": 2, "remaining": 1500.0}]
    assert character.xp_states[-1].auras == [{"spell": WELL_RESTED, "stacks": 2, "remaining": 1600.0}]
    assert character.legacy == {"trees": {tree: {node: 2}}, "time": 1791547300}
    assert legacy_rested_spell(game_data) == spell
    assert legacy_ranks_from_logger(game_data, character.legacy) == {spell: 2}
    assert legacy_ranks_from_logger(game_data, None) == {}


def test_profile_keeps_the_legacy_rank(make_deps):
    from forever.cli import main
    from forever.profile import read_profile, set_character

    spell, _, _ = legacy()
    deps = make_deps()
    set_character(deps, "Traqueur", cls="Hunter", legacy_ranks={spell: 2})
    assert read_profile(deps)["character"]["legacy_ranks"] == {str(spell): 2}
    assert main(["profile", "set", "Traqueur", "--legacy-rested-rank", "3"], deps) == 0
    assert read_profile(deps)["character"]["legacy_ranks"] == {str(spell): 3}
