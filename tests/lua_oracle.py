"""Oracle Lua d'EX1 (décision 267) : les vraies bibliothèques LibSerialize et LibDeflate, copiées dans
`tests/fixtures/third_party/` (provenance et empreintes dans son `README.md`), exécutées sous `lupa.lua51` avec un
`LibStub` minimal. Elles relisent les chaînes produites par `forever/exports/` et en produisent que forever relit.

Les chaînes Lua passent en octets (`encoding=None`) : aucune conversion de texte entre Python et Lua."""

from __future__ import annotations

from pathlib import Path
from typing import Any

THIRD_PARTY = Path(__file__).resolve().parent / "fixtures" / "third_party"
LIBS = (THIRD_PARTY / "LibSerialize" / "LibSerialize.lua", THIRD_PARTY / "LibDeflate" / "LibDeflate.lua")

_LIBSTUB = b"""
local libs = {}
LibStub = setmetatable({}, { __call = function(_, name) return libs[name] end })
function LibStub:NewLibrary(name) local t = libs[name] or {}; libs[name] = t; return t end
function LibStub:GetLibrary(name) return libs[name] end
"""


def runtime() -> Any:
    """Lua 5.1 avec LibSerialize et LibDeflate chargées (`LS`, `LD` globaux)."""
    from lupa import lua51

    lua = lua51.LuaRuntime(unpack_returned_tuples=True, encoding=None)
    lua.execute(_LIBSTUB)
    for path in LIBS:
        lua.execute(path.read_bytes())
    lua.execute(b'LS = LibStub("LibSerialize"); LD = LibStub("LibDeflate")')
    return lua


def lua_unpack(lua: Any, body: bytes) -> Any:
    """Corps d'une chaîne (sans préfixe) relu par `DecodeForPrint`, `DecompressDeflate` et `Deserialize`, puis
    converti en valeur Python (`to_python`)."""
    fn = lua.eval(
        b"function(s) local p = LD:DecodeForPrint(s); if not p then return 'decode' end; "
        b"local raw = LD:DecompressDeflate(p); if not raw then return 'inflate' end; "
        b"local ok, v = LS:Deserialize(raw); if not ok then return 'deserialize' end; return true, v end"
    )
    ok, value = fn(body)
    assert ok is True, f"relecture Lua impossible à l'étape {ok!r}"
    return to_python(lua, value)


def to_python(lua: Any, value: Any) -> Any:
    """Table Lua → `dict` (clés 1..n consécutives : `list`), chaînes en texte UTF-8, nombres entiers en `int`."""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if lua.eval(b"type")(value) != b"table":
        return value
    items = {to_python(lua, k): to_python(lua, v) for k, v in value.items()}
    if items and sorted(k for k in items if isinstance(k, int) and not isinstance(k, bool)) == list(
        range(1, len(items) + 1)
    ):
        return [items[i] for i in range(1, len(items) + 1)]
    return items


def normalize(value: Any) -> Any:
    """Valeur Python ramenée à la forme de `to_python` (tuples en listes, flottants entiers en `int`, `dict` aux clés
    1..n en `list`)."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list | tuple):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        items = {k: normalize(v) for k, v in value.items()}
        keys = [k for k in items if isinstance(k, int) and not isinstance(k, bool)]
        if items and sorted(keys) == list(range(1, len(items) + 1)):
            return [items[i] for i in range(1, len(items) + 1)]
        return items
    return value
