"""Codec commun d'EX1 (bloc A) face aux vraies bibliothèques (décision 267) : LibSerialize MINOR 7 et LibDeflate 1.0.2
de `tests/fixtures/third_party/`, exécutées sous `lupa.lua51` (`tests/lua_oracle.py`). Une chaîne produite par
Python est relue par `DecodeForPrint`, `DecompressDeflate` et `Deserialize` ; une chaîne produite par les
bibliothèques est relue par `unpack`. Valeurs de test synthétiques, sans chiffre de jeu."""

import random

import pytest

pytest.importorskip("lupa")

from lua_oracle import lua_unpack, normalize, runtime, to_python

from forever.exports.codec import (
    decode_for_print,
    deflate,
    deserialize,
    encode_for_print,
    inflate,
    pack,
    serialize,
    unpack,
)

VALUES = [
    {"v": 1, "class": 8, "name": "Givre", "spec": "Frost", "points": [105815, 105815, 105814]},
    {"macros": [{"name": "Poly", "body": "#showtooltip\n/cast [@focus,harm,nodead][] Polymorph"}]},
    {"répété": ["répété", "répété", "répété"], "autre": "répété"},
    {"f": [1.5, -2.25, 0.1, 1e-300, 123456.789], "n": [-1, -300, -5000, -70000, -(2**40)], "g": [2**31 + 5, 2**53 - 1]},
    {1: "a", 2: "b", "x": True, "y": False},
    {"long": "x" * 300, "très long": "y" * 70000},
    list(range(300)),
    {str(i): {"k": i} for i in range(40)},
]


@pytest.fixture(scope="module")
def lua():  # type: ignore[no-untyped-def]
    return runtime()


def test_encode_for_print_matches_libdeflate(lua) -> None:  # type: ignore[no-untyped-def]
    rng = random.Random(7)
    for length in [*range(12), 255, 1000]:
        data = bytes(rng.randrange(256) for _ in range(length))
        assert encode_for_print(data).encode() == lua.globals().LD.EncodeForPrint(lua.globals().LD, data)
        if length != 1:
            assert decode_for_print(encode_for_print(data)) == data


@pytest.mark.parametrize("value", VALUES, ids=range(len(VALUES)))
def test_python_string_read_by_lua(lua, value) -> None:  # type: ignore[no-untyped-def]
    text = pack("!NFB1!", value)
    assert lua_unpack(lua, text[len("!NFB1!") :].encode()) == normalize(value)


@pytest.mark.parametrize("value", VALUES, ids=range(len(VALUES)))
def test_python_serialization_read_by_libserialize(lua, value) -> None:  # type: ignore[no-untyped-def]
    fn = lua.eval(b"function(s) return LS:Deserialize(s) end")
    ok, out = fn(serialize(value))
    assert ok is True
    assert to_python(lua, out) == normalize(value)


LUA_TABLE = b"""
local shared = "chaine partagee"
local inner = { x = 1 }
return {
    v = 1, name = shared, again = shared, list = { shared, shared, "abc", "abc" },
    floats = { 0.5, -0.25, 1/3, 123456.789, 1e-300 },
    negatives = { -1, -300, -5000, -70000, -2^40 },
    big = { 2^31 + 5, 2^53 - 1 },
    mixed = { "a", "b", key = "c" },
    nested = { deep = { deeper = { "fond" } } },
    same1 = inner, same2 = inner,
}
"""

EXPECTED = {
    "v": 1,
    "name": "chaine partagee",
    "again": "chaine partagee",
    "list": ["chaine partagee", "chaine partagee", "abc", "abc"],
    "floats": [0.5, -0.25, 1 / 3, 123456.789, 1e-300],
    "negatives": [-1, -300, -5000, -70000, -(2**40)],
    "big": [2**31 + 5, 2**53 - 1],
    "mixed": {1: "a", 2: "b", "key": "c"},
    "nested": {"deep": {"deeper": ["fond"]}},
    "same1": {"x": 1},
    "same2": {"x": 1},
}


def test_lua_string_read_by_python(lua) -> None:  # type: ignore[no-untyped-def]
    table = lua.execute(LUA_TABLE)
    body = lua.eval(b"function(t) return LD:EncodeForPrint(LD:CompressDeflate(LS:Serialize(t))) end")(table)
    value = unpack("!NFB1!", "!NFB1!" + body.decode("ascii"))
    assert normalize(value) == EXPECTED


def test_lua_serialization_with_references_read_by_python(lua) -> None:  # type: ignore[no-untyped-def]
    table = lua.execute(LUA_TABLE)
    raw = lua.eval(b"function(t) return LS:Serialize(t) end")(table)
    value = deserialize(raw)
    assert normalize(value) == EXPECTED
    assert value["same1"] is value["same2"]


def test_lua_compression_levels_read_by_python(lua) -> None:  # type: ignore[no-untyped-def]
    data = ("forever " * 400 + "".join(chr(97 + i % 26) for i in range(3000))).encode()
    for level in (0, 1, 5, 9):
        packed = lua.eval(b"function(s, l) return LD:CompressDeflate(s, { level = l }) end")(data, level)
        assert inflate(packed, 1_048_576) == data


def test_python_deflate_read_by_lua(lua) -> None:  # type: ignore[no-untyped-def]
    data = bytes(random.Random(3).randrange(256) for _ in range(5000)) + b"z" * 5000
    assert lua.eval(b"function(s) return LD:DecompressDeflate(s) end")(deflate(data)) == data
