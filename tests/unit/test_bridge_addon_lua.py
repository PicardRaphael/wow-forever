"""Vrai Lua de ForeverBridge exécuté sous lupa.lua51 (Lua 5.1, celui du jeu) avec le client simulé
`tests/fixtures/bridge/wow_stub.lua` (P06a). Bloc A : codec Lua = codec Python, bande de test `/fv test` relue par le
décodeur du pont à la géométrie physique, autotest `/fv diag`, aucune fonction interdite, événements sous pcall."""

import random

import pytest
from conftest import FIXTURES, REPO_ROOT

from forever.bridge.codec import (
    BAND_HEIGHT,
    BAND_WIDTH,
    MAX_PAYLOAD,
    SELFTEST_ID,
    Decoded,
    cell_mismatches,
    decode_band,
    encode_cells,
    selftest_payload,
)
from forever.bridge.image import Image

lupa = pytest.importorskip("lupa")
from lupa import lua51

ADDON = REPO_ROOT / "addon" / "ForeverBridge"
STUB = FIXTURES / "bridge" / "wow_stub.lua"
CTL = "Interface\\AddOns\\ForeverBridge\\ctl\\"
CELLS_EMPTY = [6, 1, 6, 1, 5, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 1, 4]
CELLS_A = [6, 1, 6, 1, 5, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1, 2, 0, 2, 4, 1, 5, 0, 7]
CELLS_TALENT = [6, 1, 6, 1, 5, 0, 0, 1, 0, 0, 4, 0, 0, 0, 0, 7, 2, 5, 0, 6, 0, 5, 5, 4, 3, 1, 2, 6, 7, 1, 6, 4, 1, 7,
                7, 3, 1, 4, 2, 5]  # fmt: skip


def toc_files() -> list[str]:
    lines = (ADDON / "ForeverBridge.toc").read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


class Game:
    """Un client simulé avec ForeverBridge chargé comme le jeu le fait : fichiers du .toc, SavedVariables, puis
    ADDON_LOADED et PLAYER_LOGIN."""

    def __init__(self, *, screen=(1920, 1080), files=None, saved=None, unknown_events=(), probe=None, prelude=None):
        self.lua = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB.read_bytes())
        if prelude:
            self.lua.execute(prelude)
        self.stub = self.lua.globals().Stub
        self.stub.screen = self.lua.table(*screen)
        for path, state in (files or {}).items():
            self.stub.files[CTL + path] = state
        for event in unknown_events:
            self.stub.unknown_events[event] = True
        if probe is not None:
            self.stub.addons["ForeverBridge_Probe"] = f'ForeverBridge_ProbeValue = "{probe}"\n'
        for name in toc_files():
            self.lua.execute((ADDON / name).read_bytes(), "ForeverBridge", self.lua.table())
        if saved is not None:
            self.lua.globals().ForeverBridgeDB = self.lua.table_from(saved)
        self.stub.Fire("ADDON_LOADED", "ForeverBridge")
        self.stub.Fire("PLAYER_LOGIN")

    def slash(self, line: str) -> None:
        assert self.stub.Slash(line), line

    def printed(self) -> list[str]:
        return list(self.stub.printed.values())

    def band(self):
        return self.lua.globals().ForeverBridgeBand

    def screen_image(self) -> Image:
        """Pixels physiques du coin haut gauche de l'écran, peints d'après les textures visibles de la bande."""
        width, height = BAND_WIDTH, BAND_HEIGHT
        pixels = bytearray(b"\x00\x00\x00\xff" * width * height)
        band = self.band()
        if band is None or not band.IsVisible(band):
            return Image(width, height, bytes(pixels))
        point = band.points[1]
        assert (point.point, point.relPoint, point.x, point.y) == ("TOPLEFT", "TOPLEFT", 0, 0)
        assert self.lua.eval("rawequal")(point.rel, self.lua.globals().UIParent)
        k = band.GetEffectiveScale(band) * self.stub.screen[2] / 768
        for t in self.stub.ShownTextures(band).values():
            x, y, w, h, r, g, b = (t[i] for i in range(1, 8))
            left, top = round(x * k), round(-y * k)
            right, bottom = round((x + w) * k), round((-y + h) * k)
            color = bytes([round(b * 255), round(g * 255), round(r * 255), 255])
            for py in range(max(top, 0), min(bottom, height)):
                for px in range(max(left, 0), min(right, width)):
                    pixels[(py * width + px) * 4 : (py * width + px) * 4 + 4] = color
        return Image(width, height, bytes(pixels))


def lua_cells(lua, message_id, payload: bytes) -> list[int]:
    cells = lua.globals().ForeverBridge_Codec.Encode(message_id, payload)
    return [int(cells[i]) for i in range(1, len(cells) + 1)]


def test_lua_version_and_no_bit_library():
    game = Game()
    assert game.lua.eval("_VERSION") == "Lua 5.1"
    assert game.lua.eval("bit") is None


@pytest.fixture(scope="module")
def codec_lua():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute((ADDON / "Codec.lua").read_bytes())
    return lua


@pytest.mark.parametrize(
    ("message_id", "payload", "expected"),
    [(1, b"", CELLS_EMPTY), (1, b"A", CELLS_A), (258, b"Talent?", CELLS_TALENT)],
)
def test_codec_lua_known_sequences(codec_lua, message_id, payload, expected):
    assert lua_cells(codec_lua, message_id, payload) == expected


def test_codec_lua_matches_python_on_random_bytes(codec_lua):
    rng = random.Random(1)
    payload = bytes(rng.randrange(256) for _ in range(1000))
    assert lua_cells(codec_lua, 777, payload) == encode_cells(777, payload)


def test_codec_lua_selftest_vector_matches_python(codec_lua):
    codec = codec_lua.globals().ForeverBridge_Codec
    assert codec.SELFTEST_ID == SELFTEST_ID and codec.MAX_PAYLOAD == MAX_PAYLOAD
    raw = codec_lua.eval("{ ForeverBridge_Codec.SelftestPayload():byte(1, -1) }")
    assert bytes(raw[i] for i in range(1, len(raw) + 1)) == selftest_payload()
    assert codec_lua.eval(f"#ForeverBridge_Codec.Encode({SELFTEST_ID}, ForeverBridge_Codec.SelftestPayload())") == len(
        encode_cells(SELFTEST_ID, selftest_payload())
    )


def test_codec_lua_refuses_oversized_payload(codec_lua):
    cells, reason = codec_lua.globals().ForeverBridge_Codec.Encode(1, bytes(MAX_PAYLOAD + 1))
    assert cells is None and reason


def test_addon_loaded_initializes_the_saved_variable():
    game = Game()
    db = game.lua.globals().ForeverBridgeDB
    assert db.schema == 1 and db.next_id == 1
    assert isinstance(db.session, str) and len(db.session) >= 8
    band = game.band()
    assert band is None or not band.IsShown(band)
    again = Game(saved={"schema": 1, "session": "abcd1234", "next_id": 5})
    assert again.lua.eval("ForeverBridgeDB.next_id") == 5 and again.lua.eval("ForeverBridgeDB.session") == "abcd1234"


@pytest.mark.parametrize("screen", [(1920, 1080), (2560, 1440), (1366, 768)])
def test_fv_test_draws_the_selftest_band_pixel_perfect(screen):
    game = Game(screen=screen)
    game.slash("/fv test")
    band = game.band()
    assert band.IsShown(band)
    assert band.GetFrameStrata(band) == "TOOLTIP" and band.ignoreParentScale
    assert band.GetEffectiveScale(band) == pytest.approx(768 / screen[1])
    image = game.screen_image()
    assert decode_band(image) == Decoded(SELFTEST_ID, selftest_payload())
    assert cell_mismatches(image, encode_cells(SELFTEST_ID, selftest_payload())) == []


WITHOUT_IGNORE_PARENT_SCALE = """
UIParent.scale = 0.8
local create = CreateFrame
function CreateFrame(...)
    local frame = create(...)
    frame.SetIgnoreParentScale = nil
    return frame
end
"""


def test_band_compensates_the_ui_scale_without_set_ignore_parent_scale():
    game = Game(screen=(2560, 1440), prelude=WITHOUT_IGNORE_PARENT_SCALE)
    game.slash("/fv test")
    band = game.band()
    assert not band.ignoreParentScale
    assert band.GetEffectiveScale(band) == pytest.approx(768 / 1440)
    image = game.screen_image()
    assert decode_band(image) == Decoded(SELFTEST_ID, selftest_payload())


def test_fv_test_hides_after_two_minutes_or_when_typed_again():
    game = Game()
    game.slash("/fv test")
    game.stub.Advance(119)
    assert game.band().IsShown(game.band())
    game.stub.Advance(2)
    assert not game.band().IsShown(game.band())
    game.slash("/fv test")
    assert game.band().IsShown(game.band())
    game.slash("/fv test")
    assert not game.band().IsShown(game.band())
    assert decode_band(game.screen_image()) is None


ALL_FILES = {"empty.wav": "empty", "valid.wav": "valid", "flip.wav": "empty", "empty.ogg": "empty"}


def diag_lines(game) -> str:
    game.stub.printed = game.lua.table()
    game.slash("/fv diag")
    return "\n".join(game.printed())


def test_fv_diag_reports_each_control_file():
    game = Game(files={**ALL_FILES, "valid.ogg": "valid", "flip.ogg": "empty"}, probe="installation")
    text = diag_lines(game)
    assert "1920 × 1080" in text
    assert "ctl/empty.wav : ne joue pas" in text and "ctl/valid.wav : joue" in text
    assert "ctl/flip.wav : ne joue pas" in text and "ctl/late.wav : ne joue pas" in text
    assert "ctl/valid.ogg : joue" in text and "ctl/late.ogg : ne joue pas" in text
    assert "autotest .wav : réussi" in text and "autotest .ogg : réussi" in text
    assert "ForeverBridge_Probe : chargé" in text and "« installation »" in text
    played = list(game.stub.played.values())
    assert CTL + "late.wav" in played and CTL + "flip.ogg" in played
    assert len(game.stub.stopped) == 2  # chaque son valide est arrêté aussitôt


def test_fv_diag_sees_files_changed_while_the_game_runs():
    game = Game(files=ALL_FILES)
    assert "ctl/flip.wav : ne joue pas" in diag_lines(game)
    game.stub.files[CTL + "flip.wav"] = "valid"
    game.stub.files[CTL + "late.wav"] = "valid"
    text = diag_lines(game)
    assert "ctl/flip.wav : joue" in text and "ctl/late.wav : joue" in text
    assert "autotest .ogg : échoué" in text  # aucun .ogg valide installé
    assert "ForeverBridge_Probe : non chargé (MISSING)" in text


def test_fv_diag_survives_a_failing_play_sound_file():
    game = Game(files=ALL_FILES)
    game.stub.sound_error = True
    text = diag_lines(game)
    assert "PlaySoundFile en erreur" in text
    assert "autotest .wav : échoué" in text


def test_unknown_events_do_not_stop_the_addon():
    game = Game(unknown_events=("PLAYER_LOGIN",))
    game.slash("/fv test")
    assert game.band().IsShown(game.band())


def test_no_forbidden_call_and_no_combat_log_subscription():
    game = Game(files={**ALL_FILES, "valid.ogg": "valid"}, probe="installation")
    game.slash("/fv test")
    game.stub.Advance(130)
    game.slash("/fv diag")
    game.slash("/fv")
    game.slash("/forever test")
    assert list(game.stub.forbidden.values()) == []
    registered = set(game.stub.registered.keys())
    assert "ADDON_LOADED" in registered
    assert not {e for e in registered if e.startswith("COMBAT_LOG_EVENT")}
