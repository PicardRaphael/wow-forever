"""Retour bureau → jeu (P06a, décision 212 amendée le 2026-10-09) : réserve d'emplacements chargés à la demande
(`ForeverBridge_S001`…), consultée par le jeu à intervalles ; chaque publication écrit le même `Inbox.lua` dans les
emplacements que le jeu peut encore charger et dans `ForeverBridge/Inbox.lua` (lu au `/reload`), atomiquement fichier
par fichier. `Status.lua` porte l'état des données et les boutons, lus à la connexion et au `/reload`.

Aucun son dans le chemin des réponses : sur Forever, un fichier son vide « joue » (sonde en jeu A) ; `SILENT_WAV` ne
sert plus qu'aux fichiers de contrôle du diagnostic `/fv diag`.

Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : `bridge/protocol.js`,
`bridge/bridge.js`), sous la licence suivante :

MIT License

Copyright (c) 2026 chelinho139

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

from __future__ import annotations

import os
import re
import struct
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SLOTS = 200
SLOT_PREFIX = "ForeverBridge_S"
ADDON = "ForeverBridge"
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")


def _silent_wav(rate: int = 8000, samples: int = 80) -> bytes:
    fmt = struct.pack("<HHIIHH", 1, 1, rate, rate, 1, 8)  # PCM, mono, octets par seconde, bloc, bits
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", samples)
    return b"RIFF" + struct.pack("<I", len(body) + samples) + body + bytes([128]) * samples


# WAV PCM valide et silencieux : 8 bits, mono, 8 000 Hz, 80 échantillons à 128 (10 ms), 124 octets.
SILENT_WAV: bytes = _silent_wav()


def slot_name(index: int) -> str:
    """Nom de l'emplacement : 1 → `ForeverBridge_S001`."""
    return f"{SLOT_PREFIX}{index:03d}"


def lua_string(text: str) -> str:
    """Chaîne Lua entre guillemets : barre oblique inverse, guillemet et saut de ligne échappés, `|` doublé (séquences
    d'interface neutralisées), autres caractères de contrôle retirés."""
    text = _CONTROL.sub("", text)
    text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("|", "||")
    return f'"{text}"'


def _lua_value(value: Any, indent: str) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return lua_string(value)
    inner = indent + "\t"
    if isinstance(value, Mapping):
        items = []
        for key, item in value.items():
            name = str(key)
            label = name if _IDENTIFIER.fullmatch(name) else f"[{lua_string(name)}]"
            items.append(f"{inner}{label} = {_lua_value(item, inner)},")
    elif isinstance(value, Sequence):
        items = [f"{inner}{_lua_value(item, inner)}," for item in value]
    else:
        raise TypeError(f"valeur non sérialisable en Lua : {type(value).__name__}")
    if not items:
        return "{}"
    return "{\n" + "\n".join(items) + "\n" + indent + "}"


def _assign(name: str, table: Mapping[str, Any]) -> str:
    return f"{name} = {_lua_value(table, '')}\n"


def inbox_lua(
    now: int, status: Mapping[str, Any], replies: Sequence[Mapping[str, Any]], buttons: Sequence[Mapping[str, Any]]
) -> str:
    """Contenu d'un emplacement : `ForeverBridgeSlot = { v, now, status, buttons, replies }`."""
    return _assign(
        "ForeverBridgeSlot",
        {"v": 1, "now": now, "status": dict(status), "buttons": list(buttons), "replies": list(replies)},
    )


def status_lua(status: Mapping[str, Any], buttons: Sequence[Mapping[str, Any]], now: int = 0) -> str:
    """Contenu de `ForeverBridge/Status.lua` : `ForeverBridgeStatus = { v, now, status, buttons }`."""
    return _assign("ForeverBridgeStatus", {"v": 1, "now": now, "status": dict(status), "buttons": list(buttons)})


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(content.encode("utf-8"))
    os.replace(tmp, path)


def publish(addons_dir: Path, inbox: str, slots: int = SLOTS, first: int = 1) -> int:
    """Écrit `inbox` dans les emplacements `first` à `slots` puis dans `ForeverBridge/Inbox.lua` ; nombre de fichiers
    écrits."""
    count = 0
    for index in range(max(1, first), slots + 1):
        _write_atomic(addons_dir / slot_name(index) / "Inbox.lua", inbox)
        count += 1
    _write_atomic(addons_dir / ADDON / "Inbox.lua", inbox)
    return count + 1
