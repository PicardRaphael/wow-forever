"""Codec commun des chaînes de Naowh Forever (EX1, bloc A) : Python seul.

Valeurs attendues tirées des formats publiés, sans chiffre de jeu : section « Encoding format » du README de
LibSerialize (octet de type, nombres intégrés sur 7 et 12 bits, compte intégré sur 4 bits), alphabet de
`EncodeForPrint` de LibDeflate (`a`=0 … `)`=63, poids faible d'abord) ; bornes de lecture de Naowh Forever 1.1.12
(`NaowhForever_Training/Builds.lua`, `DECODE_LIMITS`) relevées au plan d'EX1."""

import random
import re
import string
import zlib

import pytest

from forever.exports.codec import (
    NAOWH_LIMITS,
    ExportFormatError,
    Limits,
    decode_for_print,
    deflate,
    deserialize,
    encode_for_print,
    inflate,
    pack,
    serialize,
    unpack,
)

ALPHABET = re.compile(r"[a-zA-Z0-9()]*")


# --- encodage 6 bits ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("length", range(8))
def test_encode_for_print_round_trip_all_lengths(length: int) -> None:
    rng = random.Random(length)
    data = bytes(rng.randrange(256) for _ in range(length))
    text = encode_for_print(data)
    assert ALPHABET.fullmatch(text)
    assert decode_for_print(text) == data


def test_encode_for_print_known_vectors() -> None:
    # trois octets → quatre caractères ; reste d'un octet → deux caractères, de deux octets → trois
    assert encode_for_print(b"") == ""
    assert encode_for_print(b"\x00") == "aa"
    assert encode_for_print(b"\xff\xff\xff") == "))))"
    assert encode_for_print(b"\x01\x00\x00") == "baaa"
    assert encode_for_print(b"\x40\x00") == "aba"
    assert len(encode_for_print(bytes(range(256)))) == 342


def test_decode_for_print_refuses_foreign_characters() -> None:
    with pytest.raises(ExportFormatError):
        decode_for_print("abc-")
    with pytest.raises(ExportFormatError):
        decode_for_print("a")


# --- LibSerialize ---------------------------------------------------------------------------------------------------


def test_serialize_known_bytes() -> None:
    assert serialize(None) == b"\x01\x00"
    assert serialize(5) == b"\x01\x0b"
    assert serialize(True) == b"\x01\x60"
    assert serialize(False) == b"\x01\x68"
    assert serialize("ab") == b"\x01\x22ab"
    assert serialize(300) == b"\x01\xc4\x12"
    assert serialize(-300) == b"\x01\xcc\x12"
    assert serialize(5000) == b"\x01\x08\x13\x88"
    assert serialize(-5000) == b"\x01\x10\x13\x88"
    assert serialize([1, 2]) == b"\x01\x2a\x03\x05"
    assert serialize({"a": 1}) == b"\x01\x16\x12a\x03"


def test_serialize_is_deterministic() -> None:
    a = {"v": 1, "name": "Givre", "points": [3, 1, 2], "spec": "Frost", "nested": {"z": 1, "a": 2}}
    b = {"nested": {"a": 2, "z": 1}, "spec": "Frost", "points": [3, 1, 2], "name": "Givre", "v": 1}
    assert serialize(a) == serialize(b)


ROUND_TRIP = [
    None,
    True,
    False,
    0,
    127,
    128,
    -1,
    4095,
    -4095,
    4096,
    70000,
    -70000,
    2**31 + 5,
    2**40,
    -(2**40),
    2**53 - 1,
    1.5,
    -2.25,
    0.1,
    1e-300,
    "",
    "ab",
    "Éclair de givre",
    "x" * 300,
    "y" * 70000,
    [1, 2, 3],
    list(range(40)),
    {"a": 1, "b": [True, False]},
    {1: "a", 2: "b", "x": 1},
    {1: "a", 2: "b", 3: "c", 4: "d", 5: "e", "x": 1, "y": 2},
    {"k": {"k": {"k": "fond"}}},
    {"répété": ["répété", "répété", "répété"]},
    {str(i): i for i in range(20)},
    {10: "dix", -3: "moins trois"},
]


@pytest.mark.parametrize("value", ROUND_TRIP, ids=range(len(ROUND_TRIP)))
def test_round_trip_python(value: object) -> None:
    assert deserialize(serialize(value)) == value


def test_tuple_is_written_as_array() -> None:
    assert deserialize(serialize((1, 2, 3))) == [1, 2, 3]


@pytest.mark.parametrize("value", [{1, 2}, object(), b"octets", {(1, 2): 3}])
def test_unsupported_type_raises_type_error(value: object) -> None:
    with pytest.raises(TypeError):
        serialize(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 2**60])
def test_unrepresentable_number_raises_value_error(value: object) -> None:
    with pytest.raises(ValueError):
        serialize(value)


def test_deserialize_reads_string_and_table_references() -> None:
    # version 1 ; tableau de 2 : chaîne « abc » (compte intégré), puis référence de chaîne n° 1 (STRINGREF_8)
    strings = b"" + bytes([16 * 2 + 4 * 2 + 2, 16 * 3 + 2]) + b"abc" + bytes([8 * 26, 1])
    assert deserialize(strings) == ["abc", "abc"]
    # tableau de 2 (table n° 1) : table vide (n° 2), puis référence de table n° 2 (TABLEREF_8)
    tables = b"" + bytes([16 * 2 + 4 * 2 + 2, 4 * 1 + 2, 8 * 29, 2])
    value = deserialize(tables)
    assert value == [{}, {}]
    assert value[0] is value[1]


def test_deserialize_reads_float_string_encoding() -> None:
    # NUM_FLOATSTR (type 10) : longueur puis texte décimal ; NUM_FLOATSTR_NEG (type 11)
    assert deserialize(b"\x01" + bytes([8 * 10, 3]) + b"0.5") == 0.5
    assert deserialize(b"\x01" + bytes([8 * 11, 3]) + b"0.5") == -0.5


def test_deserialize_refuses_damaged_input() -> None:
    with pytest.raises(ExportFormatError):
        deserialize(b"")
    with pytest.raises(ExportFormatError):
        deserialize(b"\x03\x0b")  # version de sérialisation inconnue
    with pytest.raises(ExportFormatError):
        deserialize(b"\x01\x22a")  # chaîne tronquée
    with pytest.raises(ExportFormatError):
        deserialize(b"\x01\x0b\x0b")  # deux valeurs


# --- deflate --------------------------------------------------------------------------------------------------------


def test_deflate_is_raw_deflate() -> None:
    data = b"forever " * 50
    packed = deflate(data)
    assert zlib.decompress(packed, wbits=-15) == data
    assert inflate(packed, 1000) == data


def test_inflate_is_bounded() -> None:
    bomb = deflate(b"\x00" * 200_000)
    with pytest.raises(ExportFormatError):
        inflate(bomb, 100_000)
    with pytest.raises(ExportFormatError):
        inflate(b"\xff\xff\xff", 100)


# --- chaîne complète ------------------------------------------------------------------------------------------------


def test_pack_and_unpack() -> None:
    value = {"v": 1, "name": "Mon build", "points": [10, 10, 11]}
    text = pack("!NFB1!", value)
    assert text.startswith("!NFB1!")
    assert ALPHABET.fullmatch(text[len("!NFB1!") :])
    assert unpack("!NFB1!", text) == value
    assert unpack("!NFB1!", f"  {text}\n") == value


def test_unpack_refuses_wrong_prefix_and_second_token() -> None:
    text = pack("!NFB1!", {"v": 1})
    with pytest.raises(ExportFormatError):
        unpack("!NFM1!", text)
    with pytest.raises(ExportFormatError):
        unpack("!NFB1!", text + " abc")
    with pytest.raises(ExportFormatError):
        unpack("!NFB1!", "!NFB1!")


def test_unpack_applies_limits() -> None:
    assert NAOWH_LIMITS == Limits(max_chars=100_000, max_bytes=1_048_576, max_depth=8, max_values=20_000)
    rng = random.Random(1)
    big = pack("!NFB1!", {"s": "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(120_000))})
    with pytest.raises(ExportFormatError, match="caractères"):
        unpack("!NFB1!", big)
    bomb = "!NFB1!" + encode_for_print(deflate(serialize("a" * 2_000_000)))
    assert len(bomb) < NAOWH_LIMITS.max_chars
    with pytest.raises(ExportFormatError):
        unpack("!NFB1!", bomb)
    deep: object = "fond"
    for _ in range(12):
        deep = [deep]
    with pytest.raises(ExportFormatError, match="profondeur"):
        unpack("!NFB1!", pack("!NFB1!", deep))
    many = pack("!NFB1!", list(range(30_000)))
    with pytest.raises(ExportFormatError, match="valeurs"):
        unpack("!NFB1!", many)
    small = Limits(max_chars=100_000, max_bytes=10, max_depth=8, max_values=20_000)
    with pytest.raises(ExportFormatError):
        unpack("!NFB1!", pack("!NFB1!", "z" * 50), small)
