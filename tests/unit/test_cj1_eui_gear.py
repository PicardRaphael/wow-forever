"""CJ1, bloc 5 (décision 274, demandes de l'utilisateur du 2026-10-15) :
- EllesmereUI éteint par défaut : ni lien de profil dans « Exports », ni bascule par rôle, tant que le joueur ne l'a pas
  rallumé (`/fb eui on`, envoyé dans le contexte `eui=on`) ; `/fb eui off` l'éteint, `/fb role clear` efface le rôle ;
- exports d'équipement accessibles depuis le chat, sans terminal : « Exports » et toute réponse qui donne des poids ou
  une liste BiS portent les liens [Naowh : poids], [Forever Companion : échelle] et [Naowh : BiS], à copier.

Valeurs : addons d'équipement fabriqués (`tests/fixtures/addons/gear/`), contexte réel `contexts/mage19.txt`, client
simulé de `tests/fixtures/bridge/`. Aucun chiffre de jeu ici."""

import shutil

import pytest
from conftest import FIXTURES
from test_bridge_profile_gap import context

from forever.bridge.exports import exports_reply, typed_links

GEAR = FIXTURES / "addons" / "gear"


@pytest.fixture
def deps(make_deps_at_pre_70450_version, tmp_path):
    # contexte mage19 relevé avant le correctif 112753 (Elemental Precision 5/5) : données d'avant 70450 (conftest)
    root = tmp_path / "wow"
    shutil.copytree(GEAR, root / "Interface" / "AddOns")
    return make_deps_at_pre_70450_version(wow_dir=root)


def test_exports_reply_has_no_ellesmere_link_by_default(deps):
    text, links = exports_reply(deps, {**context(), "role": "dps"}, [])
    assert not [link for link in links if link["kind"] == "ellesmere"] and "EllesmereUI" not in text
    text, _ = exports_reply(deps, {**context(), "role": "dps", "eui": "on"}, [])
    assert "EllesmereUI" in text  # proposé seulement une fois rallumé


def test_exports_reply_gives_the_gear_links(deps):
    text, links = exports_reply(deps, context(), [])
    kinds = {link["kind"]: link for link in links}
    assert kinds["naowh_weights"]["text"].startswith("NFSW1:") and kinds["naowh_weights"]["label"] == "Naowh : poids"
    assert kinds["companion_scale"]["text"].startswith("( Pawn: v1:")
    assert kinds["companion_scale"]["label"] == "Forever Companion : échelle"
    assert kinds["naowh_bis"]["text"].startswith("!NBIS1!") and kinds["naowh_bis"]["label"] == "Naowh : BiS"
    assert "Import weights" in text and "Import scale" in text and "Import a list" in text


def test_gear_tool_results_carry_typed_links():
    weights = {"naowh": "NFSW1:frost-mage:int=1", "pawn": '( Pawn: v1: "x": Class=Mage, Intellect=1 )'}
    found = typed_links(weights)["gear"]
    assert [link["kind"] for link in found] == ["naowh_weights", "companion_scale"]
    bis = {"export": "!NBIS1!abc", "name": "Forever · Jen · Givre", "naowh": "NFSW1:frost-mage:int=1"}
    kinds = [link["kind"] for link in typed_links(bis)["gear"]]
    assert kinds == ["naowh_weights", "naowh_bis"]


# --- jeu : réglage EllesmereUI -------------------------------------------------------------------------------------


def _game():
    pytest.importorskip("lupa")
    from test_bridge_addon_lua import Game
    from test_bridge_role_lua import ELLESMERE

    game = Game(prelude=ELLESMERE)
    game.stub.Fire("PLAYER_ENTERING_WORLD", True, False)
    game.slash("/fv")
    return game


def test_no_profile_switch_by_default_and_on_demand_only():
    game = _game()
    game.slash("/fb role dps")
    assert list(game.lua.globals().EUI.calls.values()) == []  # éteint par défaut : jamais de bascule
    game.slash("/fb eui on")
    assert game.lua.globals().ForeverBridgeDB.eui is True
    game.slash("/fb role dps")
    assert list(game.lua.globals().EUI.calls.values()) == ["Jen - DPS"]
    game.slash("/fb eui off")
    assert not game.lua.globals().ForeverBridgeDB.eui


def test_role_clear_and_context_flag():
    pytest.importorskip("lupa")
    from test_bridge_p06b_lua import collect, waiting_slots
    from test_bridge_send_lua import type_and_enter

    game = _game()
    waiting_slots(game)
    game.slash("/fb role dps")
    game.slash("/fb role clear")
    assert game.lua.globals().ForeverBridgeDB.roles["Jen - Forever"] is None
    type_and_enter(game, "Question")
    record, _ = collect(game)
    assert "eui" not in record.context and "role" not in record.context
