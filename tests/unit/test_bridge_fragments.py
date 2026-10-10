"""Messages en plusieurs parties (P06b, bloc A, décision 235) : découpage d'une charge trop longue pour une bande,
en-tête `F␟session␟numéro␟i␟n␟`, réassemblage dans n'importe quel ordre, doublons ignorés, parties d'une autre session
à part, limite de 32 768 octets, passage par le codec de la bande."""

import pytest

from forever.bridge.codec import MAX_PAYLOAD, Decoded, decode_band, encode_cells, render_band
from forever.bridge.fragments import MAX_MESSAGE, Fragment, FragmentBuffer, parse_fragment, split_payload
from forever.bridge.record import Record, RecordError, build_payload, parse_payload

SEP = b"\x1f"


def test_a_payload_that_fits_is_not_split():
    payload = b"x" * MAX_PAYLOAD
    assert split_payload(payload, session="abcd1234", message_id=7) == [payload]


def test_long_payload_is_split_in_three_parts():
    payload = bytes(range(256)) * 19 + b"y" * 136  # 5 000 octets, toutes les valeurs d'octet
    assert len(payload) == 5000
    parts = split_payload(payload, session="abcd1234", message_id=7)
    assert len(parts) == 3 and all(len(p) <= MAX_PAYLOAD for p in parts)
    headers = [p[:17] for p in parts]
    assert headers == [
        b"F" + SEP + b"abcd1234" + SEP + b"7" + SEP + f"{i}".encode() + SEP + b"3" + SEP for i in (1, 2, 3)
    ]
    assert [len(p) - 17 for p in parts] == [1775, 1775, 1450]
    assert b"".join(p[17:] for p in parts) == payload


def test_parts_are_read_back():
    payload = b"z" * 5000
    first = parse_fragment(split_payload(payload, session="abcd1234", message_id=7)[0])
    assert first == Fragment("abcd1234", 7, 1, 3, b"z" * 1775)


def test_header_grows_with_the_number_of_parts():
    session = "6ac884ce31ab"  # forme des jetons de session de l'addon (12 caractères)
    payload = b"q" * MAX_MESSAGE
    parts = split_payload(payload, session=session, message_id=12)
    assert len(parts) == 19 and all(len(p) <= MAX_PAYLOAD for p in parts)
    fragments = [parse_fragment(p) for p in parts]
    assert [f.index for f in fragments] == list(range(1, 20)) and {f.total for f in fragments} == {19}
    assert b"".join(f.chunk for f in fragments) == payload


def test_too_long_message_is_refused():
    with pytest.raises(ValueError):
        split_payload(b"x" * (MAX_MESSAGE + 1), session="abcd1234", message_id=7)


@pytest.mark.parametrize("order", [(1, 2, 3), (3, 1, 2), (1, 1, 3, 3, 2, 2)])
def test_reassembly_in_any_order_once(order):
    payload = "é".encode() * 2500  # coupes au milieu d'un caractère UTF-8
    parts = [parse_fragment(p) for p in split_payload(payload, session="abcd1234", message_id=7)]
    buffer = FragmentBuffer()
    results = [buffer.add(parts[i - 1]) for i in order]
    assert [r for r in results if r is not None] == [payload]


def test_received_lists_the_parts_and_sessions_stay_apart():
    parts = [parse_fragment(p) for p in split_payload(b"w" * 5000, session="abcd1234", message_id=7)]
    other = [parse_fragment(p) for p in split_payload(b"v" * 5000, session="autre000", message_id=7)]
    buffer = FragmentBuffer()
    assert buffer.add(parts[0]) is None and buffer.add(parts[2]) is None
    assert buffer.add(other[1]) is None
    assert buffer.received("abcd1234", 7) == [1, 3]
    assert buffer.received("autre000", 7) == [2]
    assert buffer.add(parts[1]) == b"w" * 5000


def test_inconsistent_total_is_an_error():
    buffer = FragmentBuffer()
    buffer.add(Fragment("abcd1234", 7, 1, 3, b"a"))
    with pytest.raises(RecordError):
        buffer.add(Fragment("abcd1234", 7, 2, 4, b"b"))


def test_an_ordinary_message_is_not_a_part():
    payload = build_payload(Record("abcd1234", 7, frozenset(), {"level": "19"}, "Question ?"))
    assert payload.startswith(b"1" + SEP)
    assert parse_fragment(payload) is None


@pytest.mark.parametrize(
    "payload",
    [
        b"F" + SEP + b"abcd1234" + SEP + b"7" + SEP + b"x" + SEP + b"3" + SEP + b"aa",
        b"F" + SEP + b"abcd1234" + SEP + b"7" + SEP + b"4" + SEP + b"3" + SEP + b"aa",
        b"F" + SEP + b"abcd1234" + SEP + b"7" + SEP + b"0" + SEP + b"3" + SEP + b"aa",
        b"F" + SEP + b"abcd1234" + SEP + b"7",
    ],
)
def test_malformed_parts_are_errors(payload):
    with pytest.raises(RecordError):
        parse_fragment(payload)


def test_parts_cross_the_band_and_rebuild_the_record():
    record = Record("abcd1234", 9, frozenset({"b=talents"}), {"level": "19"}, "é" * 2000)
    payload = build_payload(record)
    assert len(payload) > MAX_PAYLOAD
    buffer = FragmentBuffer()
    full = None
    for part in split_payload(payload, session=record.session, message_id=record.message_id):
        decoded = decode_band(render_band(encode_cells(record.message_id, part), 1))
        assert isinstance(decoded, Decoded)
        full = buffer.add(parse_fragment(decoded.payload)) or full
    assert full == payload and parse_payload(full) == record
