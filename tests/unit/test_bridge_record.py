"""Message porté par la bande (P06a, bloc B) : champs séparés par 0x1F (version `1`, session, numéro, drapeaux,
emplacement annoncé, contexte en lignes `clé=valeur`, texte). Valeurs du contexte synthétiques (aucune règle de jeu)."""

import pytest
from forever.bridge.record import PROTOCOL, Record, RecordError, build_payload, context_lines, parse_payload

from forever.bridge.codec import MAX_PAYLOAD

CONTEXT = {
    "name": "Jen",
    "realm": "Forever",
    "level": "19",
    "class": "MAGE",
    "race": "Human",
    "faction": "Alliance",
    "zone": "Westfall",
    "subzone": "Sentinel Hill",
    "map": "1436",
    "talents": "101:2,102:3,140:1",
    "gear": "1:12345:Hat of Testing;5:23456:Robe of Testing",
    "target": "ROGUE",
    "client": "1.60.1.70291",
}


def test_round_trip_with_context():
    record = Record("abcd1234", 3, frozenset({"b=talents"}), CONTEXT, "Quel talent à Westfall ?", slot=37)
    assert parse_payload(build_payload(record)) == record


def test_round_trip_hello_and_new_conversation():
    hello = Record("abcd1234", 1, frozenset({"h"}), {}, "")
    assert parse_payload(build_payload(hello)) == hello
    fresh = Record("abcd1234", 2, frozenset({"n"}), {"level": "5"}, "Bonjour", slot=None)
    parsed = parse_payload(build_payload(fresh))
    assert parsed == fresh and parsed.slot is None


def test_layout_of_the_payload():
    payload = build_payload(Record("s1", 7, frozenset({"n"}), {"level": "5", "class": "MAGE"}, "Q ?", slot=4))
    fields = payload.split(b"\x1f")
    assert fields[:5] == [PROTOCOL.encode(), b"s1", b"7", b"n", b"4"]
    assert fields[5] == b"level=5\nclass=MAGE" and fields[6] == b"Q ?"


def test_separators_are_replaced_by_a_space():
    record = Record("s1", 1, frozenset(), {"zone": "A\x1fB\nC"}, "x\x1fy\x1ez")
    parsed = parse_payload(build_payload(record))
    assert parsed.text == "x y z" and parsed.context["zone"] == "A B C"


@pytest.mark.parametrize(
    "payload",
    [
        b"2\x1fs\x1f1\x1f\x1f\x1f\x1ftexte",
        b"1\x1fs\x1fun\x1f\x1f\x1f\x1ftexte",
        b"1\x1fs\x1f1\x1f\x1fx\x1f\x1ftexte",
        b"1\x1fs\x1f1",
        b"\xff\xfe",
    ],
)
def test_invalid_payloads(payload):
    with pytest.raises(RecordError):
        parse_payload(payload)


def test_context_lines_fixed_order_unknown_keys_ignored():
    text = context_lines({"gear": "g", "level": "19", "zzz": "?", "class": "MAGE", "name": "Jen", "target": "ROGUE"})
    assert text.splitlines() == ["name=Jen", "level=19", "class=MAGE", "gear=g", "target=ROGUE"]


def test_typical_message_fits_the_band():
    talents = ",".join(f"{1000 + i}:3" for i in range(51))
    gear = ";".join(f"{slot}:{20000 + slot}:{'N' * 40}" for slot in range(1, 18))
    context = {**CONTEXT, "talents": talents, "gear": gear}
    record = Record("abcd1234", 65535, frozenset({"n", "b=talents"}), context, "é" * 255, slot=200)
    assert len(build_payload(record)) <= MAX_PAYLOAD
