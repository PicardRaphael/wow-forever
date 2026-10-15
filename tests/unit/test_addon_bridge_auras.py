"""T04f, bloc D : contexte des bonus d'XP envoyé par ForeverBridge 0.2.0 (vrai Lua sous lupa.lua51, client simulé
`tests/fixtures/bridge/wow_stub.lua`) et sa lecture par le pont : repos, zone de repos, auras d'XP actives (cumuls,
temps restant), objets surveillés portés ; identifiants fournis par le pont depuis `xp_bonuses.json`, jamais écrits en
dur dans le Lua. Valeurs synthétiques (entrées du client simulé)."""

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, REPO_ROOT, read_json

lupa = pytest.importorskip("lupa")
from test_bridge_addon_lua import Game  # client simulé avec ForeverBridge chargé

from forever.bridge.context import XpContext, xp_context
from forever.bridge.record import CONTEXT_KEYS, Record, build_payload, parse_payload
from forever.bridge.slots import status_lua
from forever.engine.xp import ActiveAura
from forever.xp_bonuses import xp_watch

ADDONS = REPO_ROOT / "addon"
WELL_RESTED, BAG = 429959, 211527
OTHER = 12345  # aura sans rapport (identifiant synthétique)
XP_KEYS = ("rested", "resting", "xp_auras", "xp_items")


def game(*, watch=True, auras=(), items=None, rested=None, resting=None, failing=(), secret=()):
    g = Game()
    stub = g.stub
    for name in failing:
        stub.failing[name] = True
    for name in secret:
        stub.secret[name] = True
    stub.player.rested = rested
    stub.player.resting = resting
    stub.time = 1000
    stub.player.auras = g.lua.table_from(
        [g.lua.table_from({"spellId": s, "applications": n, "expirationTime": e}) for s, n, e in auras]
    )
    stub.player.items = g.lua.table_from(items or {})
    if watch:
        status = g.lua.globals().ForeverBridgeStatus
        status.xp = g.lua.table_from({"auras": g.lua.table_from([WELL_RESTED]), "items": g.lua.table_from([BAG])})
    return g


def context(g):
    ctx = g.lua.globals().ForeverBridge_Message.Context()[0]
    return {k: ctx[k] for k in XP_KEYS if ctx[k] is not None}


def test_watched_auras_items_and_rest_are_sent():
    g = game(
        auras=[(WELL_RESTED, 2, 4000), (OTHER, 1, 0)],
        items={BAG: 1},
        rested=1200,
        resting=True,
    )
    assert context(g) == {
        "rested": "1200",
        "resting": "1",
        "xp_auras": f"{WELL_RESTED}:2:3000",
        "xp_items": f"{BAG}:1",
    }


def test_without_watch_list_auras_are_bounded_and_items_absent():
    many = [(OTHER + i, 1, 0) for i in range(80)]
    g = game(watch=False, auras=many)
    ctx = context(g)
    sent = ctx["xp_auras"].split(",")
    limit = int(g.lua.globals().ForeverBridge_Message.MAX_AURAS)
    assert 0 < len(sent) == limit < len(many)
    assert sent[0] == f"{OTHER}:1:" and "xp_items" not in ctx


def test_failing_or_secret_apis_leave_keys_absent():
    g = game(
        auras=[(WELL_RESTED, 1, 2000)],
        items={BAG: 1},
        rested=10,
        failing=("C_UnitAuras.GetAuraDataByIndex", "C_Item.GetItemCount"),
        secret=("GetXPExhaustion",),
    )
    assert context(g) == {"resting": "0"}


def test_record_keeps_the_new_keys_and_the_bridge_reads_them():
    assert set(XP_KEYS) <= set(CONTEXT_KEYS)
    ctx = {"rested": "1200", "resting": "1", "xp_auras": f"{WELL_RESTED}:2:3000,{OTHER}:1:", "xp_items": f"{BAG}:1"}
    record = parse_payload(build_payload(Record("s", 1, frozenset(), ctx, "question")))
    assert dict(record.context) == ctx
    assert xp_context(record.context) == XpContext(
        rested=1200.0,
        resting=True,
        auras=(ActiveAura(WELL_RESTED, 2, 3000.0), ActiveAura(OTHER, 1, None)),
        items={BAG: 1},
    )
    assert xp_context({"xp_auras": "abc,1:x:", "resting": "?"}) == XpContext()


def test_watch_list_comes_from_the_data_and_is_written_to_status(game_data):
    doc = read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")
    watch = xp_watch(game_data)
    assert set(watch["auras"]) == {a["spell_id"] for a in doc["auras"] if a["access"] not in ("none", "legacy")}
    assert watch["items"] == [doc["sleeping_bag"]["item"]]
    legacy = [a["legacy"]["tree"] for a in doc["auras"] if a["access"] == "legacy"]
    assert watch["legacy_trees"] == sorted(set(legacy))
    text = status_lua({}, [], 0, xp=watch)
    assert "xp" in text and str(WELL_RESTED) in text and str(BAG) in text


def test_no_spell_or_item_identifier_in_the_addons():
    doc = read_json(DATA_DIR / LOCAL_VERSION / "xp_bonuses.json")
    ids = {str(a["spell_id"]) for a in doc["auras"]} | {str(doc["sleeping_bag"]["item"])}
    ids |= {str(f["item"]) for f in doc["food"]}
    for path in ADDONS.rglob("*.lua"):
        text = path.read_text(encoding="utf-8")
        assert not [i for i in ids if i in text], path


def test_bridge_version_is_0_5_0():
    toc = (ADDONS / "ForeverBridge" / "ForeverBridge.toc").read_text(encoding="utf-8")
    assert "## Version: 0.5.0" in toc.splitlines()  # EX1 : 0.4.0 ; CJ1, bloc 6a : 0.5.0, nouvelle fenêtre (Screens.lua)
