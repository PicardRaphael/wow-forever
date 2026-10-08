"""Codec de la bande de ForeverBridge (P06a, bloc A).

Valeurs attendues : Fletcher-16 publiées (0xC8F0 pour « abcde », 0x2057 pour « abcdef », 0x0627 pour « abcdefgh ») ;
séquences de cellules calculées au plan et recalculées le 2026-10-08 par le `Codec.lua` de wow-ai (commit 3756eb5a)
exécuté sous lupa.lua51."""

import random

import pytest

from forever.bridge.codec import (
    BAND_HEIGHT,
    BAND_WIDTH,
    CELL_PX,
    CELLS_PER_ROW,
    MARKER_CELLS,
    MAX_PAYLOAD,
    MAX_ROWS,
    PROBE_HEIGHT,
    PROBE_WIDTH,
    SELFTEST_ID,
    BandError,
    Decoded,
    cell_color,
    cell_mismatches,
    cell_values,
    decode_band,
    encode_cells,
    fletcher16,
    marker_present,
    render_band,
    selftest_payload,
)
from forever.bridge.image import Image, read_bmp, solid, write_bmp

CELLS_EMPTY = [6, 1, 6, 1, 5, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 1, 4]
CELLS_A = [6, 1, 6, 1, 5, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1, 2, 0, 2, 4, 1, 5, 0, 7]
CELLS_TALENT = [6, 1, 6, 1, 5, 0, 0, 1, 0, 0, 4, 0, 0, 0, 0, 7, 2, 5, 0, 6, 0, 5, 5, 4, 3, 1, 2, 6, 7, 1, 6, 4, 1, 7,
                7, 3, 1, 4, 2, 5]  # fmt: skip


def bytes_to_cells(data: bytes) -> list[int]:
    """Découpage indépendant du codec (bits de poids fort d'abord, 3 bits par cellule, dernière cellule complétée)."""
    bits = "".join(f"{b:08b}" for b in data)
    bits += "0" * (-len(bits) % 3)
    return [int(bits[i : i + 3], 2) for i in range(0, len(bits), 3)]


def test_constants():
    assert (CELL_PX, CELLS_PER_ROW, MAX_ROWS, MAX_PAYLOAD) == (4, 200, 24, 1792)
    assert MARKER_CELLS == (6, 1, 6, 1, 5)
    assert (BAND_WIDTH, BAND_HEIGHT, PROBE_WIDTH, PROBE_HEIGHT) == (800, 96, 20, 4)


@pytest.mark.parametrize(("data", "expected"), [(b"abcde", (240, 200)), (b"abcdef", (87, 32)), (b"abcdefgh", (39, 6))])
def test_fletcher16_published_values(data, expected):
    assert fletcher16(data) == expected


@pytest.mark.parametrize(
    ("message_id", "payload", "expected"),
    [(1, b"", CELLS_EMPTY), (1, b"A", CELLS_A), (258, b"Talent?", CELLS_TALENT)],
)
def test_encode_cells_known_sequences(message_id, payload, expected):
    assert encode_cells(message_id, payload) == expected


def test_encode_cells_talent_bytes():
    raw = bytes.fromhex("C71A0102000754616C656E743FB315")
    assert bytes_to_cells(raw) == CELLS_TALENT


def test_encode_refuses_oversized_payload_and_bad_id():
    with pytest.raises(ValueError):
        encode_cells(1, bytes(MAX_PAYLOAD + 1))
    with pytest.raises(ValueError):
        encode_cells(65536, b"")
    assert len(encode_cells(1, bytes(MAX_PAYLOAD))) <= MAX_ROWS * CELLS_PER_ROW


def test_cell_color():
    assert cell_color(5) == (255, 0, 255)
    assert cell_color(0) == (0, 0, 0)
    assert cell_color(7) == (255, 255, 255)
    assert cell_color(6) == (255, 255, 0)
    assert cell_color(1) == (0, 0, 255)


def test_render_band_geometry():
    image = render_band(CELLS_TALENT)
    assert (image.width, image.height) == (BAND_WIDTH, CELL_PX)
    assert image.pixel(0, 0) == (255, 255, 0)  # cellule 6
    assert image.pixel(CELL_PX * 4 + 3, 3) == (255, 0, 255)  # cellule 5, dernier pixel
    assert image.pixel(BAND_WIDTH - 1, 0) == (0, 0, 0)  # cellule de remplissage
    assert cell_values(image, 1)[: len(CELLS_TALENT)] == CELLS_TALENT
    two_rows = render_band([7] * (CELLS_PER_ROW + 1))
    assert two_rows.height == 2 * CELL_PX and two_rows.pixel(0, CELL_PX) == (255, 255, 255)


@pytest.mark.parametrize("size", [0, 1, 1000, MAX_PAYLOAD])
def test_round_trip(size):
    rng = random.Random(size)
    text = "Quel talent prendre à Westfall ? éàçœ ".encode()
    payload = (text * (size // len(text) + 1))[:size] if size < 1000 else bytes(rng.randrange(256) for _ in range(size))
    assert decode_band(render_band(encode_cells(42, payload))) == Decoded(42, payload)


def test_selftest_vector_fills_the_band():
    payload = selftest_payload()
    assert len(payload) == MAX_PAYLOAD and payload[:3] == b"\x00\x01\x02" and payload[256] == 0
    cells = encode_cells(SELFTEST_ID, payload)
    image = render_band(cells)
    assert image.height == BAND_HEIGHT
    assert decode_band(image) == Decoded(SELFTEST_ID, payload)
    assert cell_mismatches(image, cells) == []


def noisy(image: Image, rng: random.Random, jitter: int, gamma: float) -> Image:
    out = bytearray(image.bgra)
    for i in range(len(out)):
        if i % 4 == 3:
            continue
        value = 255 * (out[i] / 255) ** gamma + rng.randint(-jitter, jitter)
        out[i] = max(0, min(255, round(value)))
    return Image(image.width, image.height, bytes(out))


@pytest.mark.parametrize("gamma", [0.8, 1.25])
def test_noise_and_gamma_keep_decoding(gamma):
    rng = random.Random(7)
    payload = bytes(rng.randrange(256) for _ in range(600))
    image = noisy(render_band(encode_cells(9, payload)), rng, 40, gamma)
    assert decode_band(image) == Decoded(9, payload)


def test_rejections():
    payload = bytes(range(256)) * 4
    cells = encode_cells(3, payload)
    bad_magic = [0, *cells[1:]]
    assert decode_band(render_band(bad_magic)) is None
    bad_payload = list(cells)
    bad_payload[30] ^= 1
    assert decode_band(render_band(bad_payload)) == BandError("checksum")
    image = render_band(cells)
    assert decode_band(image.crop(0, 0, image.width, 2 * CELL_PX)) == BandError("truncated")
    too_long = bytes_to_cells(bytes([0xC7, 0x1A, 0, 1, 0xFF, 0xFF]))
    assert decode_band(render_band(too_long)) == BandError("length")


def test_blank_screens_have_no_band():
    assert decode_band(solid(BAND_WIDTH, BAND_HEIGHT, (0, 0, 0))) is None
    assert decode_band(solid(BAND_WIDTH, BAND_HEIGHT, (255, 255, 255))) is None


def probe_of(cells) -> Image:
    return render_band(cells).crop(0, 0, PROBE_WIDTH, PROBE_HEIGHT)


def test_marker_present():
    assert marker_present(probe_of(CELLS_EMPTY))
    assert marker_present(probe_of(list(MARKER_CELLS)))
    assert not marker_present(solid(PROBE_WIDTH, PROBE_HEIGHT, (0, 0, 0)))
    assert not marker_present(solid(PROBE_WIDTH, PROBE_HEIGHT, (255, 255, 255)))
    for i in range(len(MARKER_CELLS)):
        cells = list(MARKER_CELLS)
        cells[i] ^= 2
        assert not marker_present(probe_of(cells)), i


def test_cell_mismatches_names_row_and_column():
    cells = encode_cells(SELFTEST_ID, selftest_payload())
    read = list(cells)
    read[CELLS_PER_ROW * 3 + 17] ^= 4
    assert cell_mismatches(render_band(read), cells) == [
        (3, 17, cells[CELLS_PER_ROW * 3 + 17], cells[CELLS_PER_ROW * 3 + 17] ^ 4)
    ]


@pytest.mark.parametrize("bits", [24, 32])
def test_bmp_round_trip(tmp_path, bits):
    image = render_band(encode_cells(5, b"Frostbolt ?"))
    path = tmp_path / f"bande-{bits}.bmp"
    write_bmp(image, path, bits=bits)
    assert read_bmp(path) == image


def test_bmp_rows_are_stored_bottom_up(tmp_path):
    red, blue = (255, 0, 0), (0, 0, 255)
    top = solid(2, 1, red)
    bottom = solid(2, 1, blue)
    image = Image(2, 2, top.bgra + bottom.bgra)
    path = tmp_path / "deux.bmp"
    write_bmp(image, path, bits=24)
    raw = path.read_bytes()
    offset = int.from_bytes(raw[10:14], "little")
    assert raw[offset : offset + 3] == bytes([255, 0, 0])  # premier pixel stocké : bas gauche, bleu en BGR
    assert read_bmp(path).pixel(0, 0) == red and read_bmp(path).pixel(1, 1) == blue
