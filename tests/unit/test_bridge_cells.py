"""Taille de case de la bande (P06a, bloc A2, décision 212 amendée le 2026-10-09) : une case par pixel physique par
défaut, repli à 2, 3 ou 4 pixels ; le pont reconnaît la taille sur le marqueur, puis ne lit que le rectangle de la
bande à cette taille. Non-régression sur la capture réelle de la sonde en jeu A (`band_live.bmp`, cases de 4 pixels)."""

import pytest
from conftest import FIXTURES
from test_bridge_selftest import CLIENT, ScreenApi, run_live, selftest_cells

from forever.bridge.capture import Rect, band_rect, probe_rect
from forever.bridge.codec import (
    CELL_PX,
    CELL_SIZES,
    PROBE_HEIGHT,
    PROBE_WIDTH,
    SELFTEST_ID,
    Decoded,
    cell_mismatches,
    cell_values,
    decode_band,
    detect_cell_px,
    encode_cells,
    marker_present,
    render_band,
    selftest_payload,
)
from forever.bridge.image import read_bmp, solid

BAND_LIVE = FIXTURES / "bridge" / "band_live.bmp"


def test_cell_sizes():
    assert CELL_SIZES == (1, 2, 3, 4) and CELL_PX == max(CELL_SIZES)


@pytest.mark.parametrize("cell_px", [1, 2, 3, 4])
def test_band_drawn_at_each_cell_size_is_read_back(cell_px):
    cells = encode_cells(42, "Quel talent à Westfall ?".encode())
    image = render_band(cells, cell_px)
    assert (image.width, image.height) == (200 * cell_px, cell_px)
    assert detect_cell_px(image) == cell_px
    assert decode_band(image) == Decoded(42, "Quel talent à Westfall ?".encode())
    assert decode_band(image, cell_px) == Decoded(42, "Quel talent à Westfall ?".encode())
    assert cell_mismatches(image, cells) == []
    assert cell_values(image, 1, cell_px)[: len(cells)] == cells
    probe = image.crop(0, 0, min(PROBE_WIDTH, image.width), min(PROBE_HEIGHT, image.height))
    assert marker_present(probe)


def test_full_selftest_band_at_one_pixel_per_cell():
    cells = selftest_cells()
    image = render_band(cells, 1)
    assert (image.width, image.height) == (200, 24)
    assert decode_band(image) == Decoded(SELFTEST_ID, selftest_payload())


def test_no_marker_no_size():
    assert detect_cell_px(solid(800, 96, (0, 0, 0))) is None
    assert detect_cell_px(solid(800, 96, (255, 255, 255))) is None
    assert decode_band(solid(800, 96, (0, 0, 0))) is None


def test_band_rect_follows_the_cell_size():
    client = Rect(100, 50, 1920, 1080)
    assert band_rect(client, 1) == Rect(100, 50, 200, 24)
    assert band_rect(client, 2) == Rect(100, 50, 400, 48)
    assert band_rect(client) == Rect(100, 50, 800, 96)
    assert band_rect(Rect(0, 0, 150, 24), 1) == Rect(0, 0, 150, 24)
    assert probe_rect(client) == Rect(100, 50, 20, 4)


def test_live_capture_of_the_first_in_game_probe_still_decodes():
    """Capture réelle du 2026-10-09 (sonde en jeu A, 2 560 × 1 440, cases de 4 pixels)."""
    image = read_bmp(BAND_LIVE)
    assert (image.width, image.height) == (800, 96)
    assert detect_cell_px(image) == 4
    assert decode_band(image) == Decoded(SELFTEST_ID, selftest_payload())
    assert cell_mismatches(image, selftest_cells()) == []


def test_live_selftest_reads_a_one_pixel_band_and_only_its_rectangle():
    api = ScreenApi(render_band(selftest_cells(), 1))
    report, _ = run_live(api)
    assert report.ok and report.cell_px == 1
    assert report.decoded == Decoded(SELFTEST_ID, selftest_payload())
    assert any("case de 1 pixel" in line for line in report.lines)
    assert api.blits[0] == Rect(CLIENT.left, CLIENT.top, 20, 4)
    assert Rect(CLIENT.left, CLIENT.top, 200, 24) in api.blits
    assert all(r.width <= 200 and r.height <= 24 for r in api.blits[1:])
    assert report.to_json()["cell_px"] == 1


def test_live_selftest_names_the_cell_size_at_two_pixels():
    report, _ = run_live(ScreenApi(render_band(selftest_cells(), 2)))
    assert report.ok and report.cell_px == 2
    assert any("case de 2 pixels" in line for line in report.lines)
