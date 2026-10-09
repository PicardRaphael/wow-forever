"""Message porté par la bande (P06a, bloc B, décision 212) : champs séparés par 0x1F, dans cet ordre : version du
protocole (`1`), jeton de session de l'addon, numéro du message, drapeaux séparés par des virgules (`n` nouvelle
conversation, `h` bonjour sans question, `b=<bouton>` question d'un bouton), numéro du prochain emplacement que le jeu
chargera (vide s'il est inconnu), contexte en lignes `clé=valeur`, texte. Écrit par `addon/ForeverBridge/Message.lua`.

Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : format des
enregistrements de la bande, `bridge/protocol.js`), sous la licence suivante :

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

from collections.abc import Mapping
from dataclasses import dataclass, field

from forever.errors import EXIT_USAGE, ForeverError

PROTOCOL = "1"
FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"
FIELDS = 7
# Ordre des clés du contexte (message à Claude, lignes de la bande) ; une clé inconnue est ignorée.
CONTEXT_KEYS = (
    "name",
    "realm",
    "level",
    "class",
    "race",
    "faction",
    "zone",
    "subzone",
    "map",
    "talents",
    "gear",
    "target",
    "client",
)


class RecordError(ForeverError):
    """Charge de la bande qui n'est pas un message du protocole."""

    exit_code = EXIT_USAGE

    def __init__(self, message: str) -> None:
        super().__init__("bridge_record", message, "taper la question à nouveau dans la fenêtre /fv")


@dataclass(frozen=True)
class Record:
    session: str
    message_id: int
    flags: frozenset[str]
    context: Mapping[str, str]
    text: str
    slot: int | None = field(default=None)


def _clean(text: str) -> str:
    return text.replace(FIELD_SEP, " ").replace(RECORD_SEP, " ")


def context_lines(context: Mapping[str, str]) -> str:
    """Contexte en lignes `clé=valeur` dans l'ordre de CONTEXT_KEYS ; clés inconnues ignorées."""
    lines = []
    for key in CONTEXT_KEYS:
        if key in context:
            value = _clean(str(context[key])).replace("\n", " ").replace("\r", " ")
            lines.append(f"{key}={value}")
    return "\n".join(lines)


def build_payload(record: Record) -> bytes:
    """Charge de la bande ; séparateurs retirés du texte et du contexte."""
    fields = [
        PROTOCOL,
        _clean(record.session),
        str(record.message_id),
        ",".join(sorted(_clean(f).replace(",", " ") for f in record.flags)),
        "" if record.slot is None else str(record.slot),
        context_lines(record.context),
        _clean(record.text),
    ]
    return FIELD_SEP.join(fields).encode("utf-8")


def parse_payload(payload: bytes) -> Record:
    """Message lu dans la charge ; RecordError si l'encodage, la version, le nombre de champs ou un numéro ne vont pas."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RecordError("message illisible : UTF-8 invalide") from exc
    fields = text.split(FIELD_SEP)
    if len(fields) != FIELDS:
        raise RecordError(f"message illisible : {len(fields)} champ(s), {FIELDS} attendus")
    version, session, number, flags, slot, context, body = fields
    if version != PROTOCOL:
        raise RecordError(f"version du protocole {version!r} inconnue (attendue : {PROTOCOL})")
    if not number.isdigit():
        raise RecordError(f"numéro de message invalide : {number!r}")
    if slot and not slot.isdigit():
        raise RecordError(f"numéro d'emplacement invalide : {slot!r}")
    pairs: dict[str, str] = {}
    for line in context.split("\n"):
        key, sep, value = line.partition("=")
        if sep and key in CONTEXT_KEYS:
            pairs[key] = value
    return Record(
        session=session,
        message_id=int(number),
        flags=frozenset(f for f in flags.split(",") if f),
        context=pairs,
        text=body,
        slot=int(slot) if slot else None,
    )
