"""Réserve d'emplacements et fichiers Lua écrits par le pont (P06a, bloc B, décision 212 amendée le 2026-10-09) :
200 emplacements `ForeverBridge_S001`…, publication à partir de l'emplacement annoncé, chaînes Lua sûres."""

from lupa import lua51

from forever.bridge.slots import SLOTS, inbox_lua, lua_string, publish, slot_name, status_lua


def lua_eval(source: str, name: str):
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(source)
    return lua.globals()[name]


def test_slot_names():
    assert SLOTS == 200
    assert slot_name(1) == "ForeverBridge_S001"
    assert slot_name(37) == "ForeverBridge_S037"
    assert slot_name(200) == "ForeverBridge_S200"


def test_lua_string_is_safe():
    assert lua_string('a"b') == '"a\\"b"'
    assert lua_string("a\\b") == '"a\\\\b"'
    assert lua_string("l1\nl2") == '"l1\\nl2"'
    assert lua_string("]]") == '"]]"'
    assert lua_string("|cffff0000rouge|r") == '"||cffff0000rouge||r"'
    assert lua_string("a\x00b\x07c\rd") == '"abcd"'
    lua = lua51.LuaRuntime()
    weird = 'x"\\\n]]|y é'
    assert lua.eval(lua_string(weird)) == weird.replace("|", "||")


def test_inbox_lua_is_valid_lua():
    replies = [{"session": "abcd1234", "id": 3, "status": "working", "since": 1700000000}]
    status = {"version": "1.60.1.70245", "freshness": "fresh", "pending": 2}
    buttons = [{"key": "talents", "label": "Talents", "question": "Q ?", "questions": {"MAGE": "QM ?"}}]
    slot = lua_eval(inbox_lua(1700000005, status, replies, buttons), "ForeverBridgeSlot")
    assert slot.v == 1 and slot.now == 1700000005
    assert slot.status.version == "1.60.1.70245" and slot.status.pending == 2
    assert slot.replies[1].status == "working" and slot.replies[1].id == 3
    assert slot.buttons[1].questions.MAGE == "QM ?"
    st = lua_eval(status_lua(status, buttons), "ForeverBridgeStatus")
    assert st.v == 1 and st.status.freshness == "fresh" and st.buttons[1].key == "talents"


def test_publish_from_the_announced_slot(tmp_path):
    inbox = inbox_lua(1, {}, [], [])
    assert publish(tmp_path, inbox, slots=200, first=37) == 165
    assert (tmp_path / "ForeverBridge_S037" / "Inbox.lua").read_text(encoding="utf-8") == inbox
    assert (tmp_path / "ForeverBridge_S200" / "Inbox.lua").is_file()
    assert not (tmp_path / "ForeverBridge_S036").exists()
    assert (tmp_path / "ForeverBridge" / "Inbox.lua").read_text(encoding="utf-8") == inbox
    assert not list(tmp_path.rglob("*.tmp"))


def test_publish_everything_without_an_announced_slot(tmp_path):
    assert publish(tmp_path, inbox_lua(1, {}, [], []), slots=8) == 9
    assert sorted(p.name for p in tmp_path.iterdir())[:2] == ["ForeverBridge", "ForeverBridge_S001"]
