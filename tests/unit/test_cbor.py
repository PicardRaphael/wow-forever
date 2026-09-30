"""Décodeur CBOR maison (PV1, bloc A, D1). Exemples tirés de la RFC 8949, annexe A (« Examples of Encoded CBOR Data
Items »), https://www.rfc-editor.org/rfc/rfc8949#appendix-A : encodages et valeurs cités tels quels."""

import pytest

from forever.pipeline.cbor import CborError, decode

RFC_8949_APPENDIX_A = [
    ("00", 0),
    ("17", 23),
    ("1818", 24),
    ("1903e8", 1000),
    ("1a000f4240", 1000000),
    ("1b000000e8d4a51000", 1000000000000),
    ("20", -1),
    ("3863", -100),
    ("f4", False),
    ("f5", True),
    ("f6", None),
    ("f93c00", 1.0),
    ("fb3ff199999999999a", 1.1),
    ("60", ""),
    ("6161", "a"),
    ("6449455446", "IETF"),
    ("62c3bc", "ü"),
    ("4401020304", b"\x01\x02\x03\x04"),
    ("80", []),
    ("83010203", [1, 2, 3]),
    ("8301820203820405", [1, [2, 3], [4, 5]]),
    ("a0", {}),
    ("a201020304", {1: 2, 3: 4}),
    ("a26161016162820203", {"a": 1, "b": [2, 3]}),
    ("826161a161626163", ["a", {"b": "c"}]),
    ("7f657374726561646d696e67ff", "streaming"),
    ("9f018202039f0405ffff", [1, [2, 3], [4, 5]]),
    ("bf6346756ef563416d7421ff", {"Fun": True, "Amt": -2}),
    ("c11a514b67b0", 1363896240),
]


@pytest.mark.parametrize(("encoded", "expected"), RFC_8949_APPENDIX_A)
def test_cbor_decodes_maps_arrays_ints_strings(encoded, expected):
    value = decode(bytes.fromhex(encoded))
    assert value == expected and type(value) is type(expected)


@pytest.mark.parametrize(
    "encoded",
    [
        "",  # rien
        "19",  # entier sur 2 octets sans ses octets
        "1a000f",  # entier sur 4 octets tronqué
        "644945",  # texte annoncé de 4 octets, 2 présents
        "830102",  # tableau de 3 éléments, 2 présents
        "a20102",  # table de 2 paires, 1 présente
        "7f6573747265",  # texte de longueur indéfinie sans fin
    ],
)
def test_cbor_rejects_truncated_input(encoded):
    data = bytes.fromhex(encoded)
    with pytest.raises(CborError):
        decode(data)


def test_cbor_rejects_trailing_bytes_and_reserved_values():
    with pytest.raises(CborError):
        decode(bytes.fromhex("0000"))  # deux valeurs : octet en trop
    with pytest.raises(CborError):
        decode(bytes.fromhex("1c"))  # information additionnelle réservée (28)
    with pytest.raises(CborError):
        decode(bytes.fromhex("ff"))  # « break » hors d'un élément de longueur indéfinie
