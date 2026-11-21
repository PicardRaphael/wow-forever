"""FR1 : lecture des noms de l'addon QuestieDB (Questie 12.11.1 y a sorti sa base) : métadonnées « cuites » du
`.toc` (`## X-<Type>-IDS`, `## X-<Type>-<id>-S`, `## X-l10n-frFR-<Type>`, morceaux `~N~`), base64, zlib, CBOR.

Valeurs : `.toc` fabriqué ici (format seulement, noms inventés, aucune donnée de Questie)."""

import base64
import struct
import zlib
from pathlib import Path

from forever.rxp_fr.names import questiedb_layer

META = "local Meta = {\n  keys = {\n    ['name'] = 1,\n    ['subName'] = 2,\n  },\n}\n"


def _head(major: int, n: int) -> bytes:
    if n < 24:
        return bytes([major << 5 | n])
    if n < 256:
        return bytes([major << 5 | 24, n])
    return bytes([major << 5 | 25]) + struct.pack(">H", n)


def cbor(value: object) -> bytes:
    """Encodeur CBOR minimal pour le test (entiers positifs, octets, listes, tables, null)."""
    if value is None:
        return b"\xf6"
    if isinstance(value, int):
        return _head(0, value)
    if isinstance(value, str):
        value = value.encode("utf-8")
    if isinstance(value, bytes):
        return _head(2, len(value)) + value
    if isinstance(value, list):
        return _head(4, len(value)) + b"".join(cbor(v) for v in value)
    if isinstance(value, dict):
        return _head(5, len(value)) + b"".join(cbor(k) + cbor(v) for k, v in value.items())
    raise TypeError(value)


def packed(value: object) -> str:
    return base64.b64encode(zlib.compress(cbor(value))).decode("ascii")


def _addon(tmp_path: Path) -> Path:
    root = tmp_path / "AddOns" / "QuestieDB"
    for kind in ("quest", "npc", "item", "object"):
        (root / "src" / "meta").mkdir(parents=True, exist_ok=True)
        (root / "src" / "meta" / f"{kind}Meta.lua").write_text(META, encoding="utf-8")
    french_npcs = packed([[None, "Sanglier des clairières", "Brin Chênevaux"], [None, None, None]])
    lines = [
        "## Title: QuestieDB (fixture FR1)",
        f"## X-Npc-IDS: {packed([900001, 900002, 900003])}",
        f"## X-Npc-900001-S: {base64.b64encode(cbor({1: 'Nobody'})).decode()}",
        f"## X-Npc-900002-S: {base64.b64encode(cbor({1: 'Glade Boar', 4: 1})).decode()}",
        f"## X-Npc-900003-S: {base64.b64encode(cbor({1: 'Brin Oakvale'})).decode()}",
        "## X-l10n-frFR-Npc: ~2~",
        f"## X-l10n-frFR-Npc-1: {french_npcs[:10]}",
        f"## X-l10n-frFR-Npc-2: {french_npcs[10:]}",
        f"## X-Quest-IDS: {packed([90002])}",
        f"## X-Quest-90002-S: {base64.b64encode(cbor({1: 'Tusks for Brin'})).decode()}",
        f"## X-l10n-frFR-Quest: {packed([['Des défenses pour Brin'], [None]])}",
    ]
    (root / "QuestieDB_Forever.toc").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root.parent


def test_names_come_from_the_baked_metadata(tmp_path):
    layer = questiedb_layer(_addon(tmp_path) / "QuestieDB")
    assert layer["npc"]["Glade Boar"] == "Sanglier des clairières"
    assert layer["npc"][900003] == "Brin Chênevaux"
    assert "Nobody" not in layer["npc"] and 900001 not in layer["npc"]  # pas de traduction : pas de nom
    assert layer["quest"][90002] == "Des défenses pour Brin"
    assert layer["quest_title"]["Tusks for Brin"] == "Des défenses pour Brin"


def test_a_missing_or_unreadable_addon_gives_no_name(tmp_path):
    assert questiedb_layer(tmp_path / "absent") == {}
    root = tmp_path / "QuestieDB"
    root.mkdir()
    (root / "QuestieDB_Forever.toc").write_text("## X-Npc-IDS: pas du base64 !\n", encoding="utf-8")
    assert questiedb_layer(root) == {}
