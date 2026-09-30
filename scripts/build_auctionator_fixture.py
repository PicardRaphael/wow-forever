"""Écrit la fixture `tests/fixtures/addon/Auctionator.lua` à partir de `auctionator_source.json` (PV1, bloc A).

    uv run python scripts/build_auctionator_fixture.py

Valeurs inventées (pas des relevés). La forme reproduit celle de mes SavedVariables (`tasks/inventaire-addons.md`) :
`AUCTIONATOR_PRICE_DATABASE = {["__dbversion"] = 8, ["<royaume>"] = "<chaîne CBOR>"}`, chaîne écrite octet par
octet avec les échappements du client (`\\"`, `\\\\`, `\\n`, `\\r`, `\\000`), lignes terminées par CRLF comme le
fichier du client. `AUCTIONATOR_POSTING_HISTORY` porte une sentinelle que l'import ne doit jamais lire. Encodeur
CBOR minimal (RFC 8949 : entiers positifs, texte, tables), écrit pour cette fixture seulement."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "addon"


def _head(major: int, n: int) -> bytes:
    if n < 24:
        return bytes([major << 5 | n])
    for info, size in ((24, 1), (25, 2), (26, 4), (27, 8)):
        if n < 1 << (8 * size):
            return bytes([major << 5 | info]) + n.to_bytes(size, "big")
    raise ValueError(n)


def encode(value: object) -> bytes:
    if isinstance(value, bool) or value is None:
        raise TypeError(value)
    if isinstance(value, int):
        if value < 0:
            raise ValueError(value)
        return _head(0, value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return _head(3, len(raw)) + raw
    if isinstance(value, dict):
        return _head(5, len(value)) + b"".join(encode(k) + encode(v) for k, v in value.items())
    raise TypeError(value)


def lua_string(data: bytes) -> bytes:
    out = bytearray(b'"')
    for b in data:
        if b == 0x22:
            out += b'\\"'
        elif b == 0x5C:
            out += b"\\\\"
        elif b == 0x0A:
            out += b"\\n"
        elif b == 0x0D:
            out += b"\\r"
        elif b == 0x00:
            out += b"\\000"
        else:
            out.append(b)
    return bytes(out + b'"')


def build(source: dict) -> bytes:
    lines = [b"AUCTIONATOR_CONFIG = {", b'["price_history_days"] = 21,', b"}"]
    lines += [b"AUCTIONATOR_PRICE_DATABASE = {", f'["__dbversion"] = {source["dbversion"]},'.encode()]
    for realm, items in source["realms"].items():
        lines.append(f'["{realm}"] = '.encode() + lua_string(encode(items)) + b",")
    lines += [b"}", b"AUCTIONATOR_POSTING_HISTORY = {"]
    lines += [b'["1001"] = {', b"{", f'["name"] = "{source["posting_history_sentinel"]}",'.encode()]
    lines += [b'["price"] = 1,', b"}, -- [1]", b"},", b"}"]
    return b"\r\n".join(lines) + b"\r\n"


def main() -> None:
    source = json.loads((FIXTURES / "auctionator_source.json").read_text(encoding="utf-8"))
    (FIXTURES / "Auctionator.lua").write_bytes(build(source))


if __name__ == "__main__":
    main()
