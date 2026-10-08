"""Autotest de la bande (P06a, bloc A) et commandes `forever bridge selftest` et `forever bridge install`.
Écran et fenêtres simulés : la zone client du jeu commence en (100, 50) et la bande y est dessinée."""

import json

from forever.bridge.capture import GameWindow, Rect, WindowsCapture
from forever.bridge.codec import CELLS_PER_ROW, SELFTEST_ID, BandError, Decoded, encode_cells, render_band
from forever.bridge.codec import selftest_payload as payload_of_the_selftest
from forever.bridge.image import Image, read_bmp, solid
from forever.bridge.selftest import selftest_live, selftest_offline
from forever.cli import main

CLIENT = Rect(100, 50, 1280, 720)
WINDOW = GameWindow(7, 4242, "WowB.exe", "World of Warcraft")


def selftest_cells() -> list[int]:
    return encode_cells(SELFTEST_ID, payload_of_the_selftest())


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class ScreenApi:
    """Le jeu passe au premier plan au `front_after`-ième appel de `foreground` ; la bande est `band` (ou rien)."""

    def __init__(self, band: Image | None, *, front_after=0, windows=(WINDOW,)):
        self.band = band
        self.front_after = front_after
        self.calls = 0
        self.windows = list(windows)
        self.blits: list[Rect] = []

    def game_windows(self, executables):
        return list(self.windows)

    def foreground(self):
        self.calls += 1
        return 7 if self.calls > self.front_after else 3

    def is_iconic(self, hwnd):
        return False

    def client_rect(self, hwnd):
        return CLIENT

    def blit(self, rect):
        self.blits.append(rect)
        if self.band is None:
            return solid(rect.width, rect.height, (0, 0, 0))
        x, y = rect.left - CLIENT.left, rect.top - CLIENT.top
        return self.band.crop(x, y, rect.width, rect.height)


def run_live(api, **kwargs):
    clock = Clock()
    report = selftest_live(WindowsCapture({"WowB.exe"}, api), clock=clock, sleep=clock.sleep, **kwargs)
    return report, clock


def test_offline_selftest_recognizes_the_vector():
    report = selftest_offline()
    assert report.ok
    assert report.decoded == Decoded(SELFTEST_ID, payload_of_the_selftest())
    assert any("vecteur reconnu" in line and "1792 octets" in line and "24 rangées" in line for line in report.lines)


def test_live_selftest_waits_for_the_game_in_front(tmp_path):
    api = ScreenApi(render_band(selftest_cells()), front_after=3)
    save = tmp_path / "bande.bmp"
    report, _ = run_live(api, save=save)
    assert report.ok and report.foreground_seen and report.marker_seen
    assert report.window == WINDOW and report.client == CLIENT
    assert report.decoded == Decoded(SELFTEST_ID, payload_of_the_selftest())
    assert report.mismatches == []
    assert report.probe_cells == [6, 1, 6, 1, 5]
    text = "\n".join(report.lines)
    assert "WowB.exe" in text and "4242" in text and "World of Warcraft" in text
    assert "1280 × 720" in text and "vecteur reconnu" in text
    assert read_bmp(save) == render_band(selftest_cells())
    assert api.blits[0] == Rect(100, 50, 20, 4) and Rect(100, 50, 800, 96) in api.blits
    assert all(r.width <= 800 and r.height <= 96 for r in api.blits)


def test_live_selftest_never_reads_when_the_game_stays_behind():
    api = ScreenApi(render_band(selftest_cells()), front_after=10**9)
    report, clock = run_live(api, wait_s=5)
    assert not report.ok and not report.foreground_seen
    assert api.blits == []
    assert any("premier plan" in line for line in report.lines)
    assert 5 <= clock.t < 7


def test_live_selftest_without_window():
    report, _ = run_live(ScreenApi(None, windows=()), wait_s=3)
    assert not report.ok and report.window is None
    assert any("fenêtre du jeu introuvable" in line for line in report.lines)


def test_live_selftest_without_band_reports_the_probe():
    report, _ = run_live(ScreenApi(None), wait_s=2)
    assert not report.ok and report.foreground_seen and not report.marker_seen
    assert report.probe_cells == [0, 0, 0, 0, 0]
    assert any("marqueur absent" in line for line in report.lines)


def test_live_selftest_names_the_wrong_cell():
    expected = selftest_cells()
    cells = list(expected)
    cells[CELLS_PER_ROW * 3 + 17] ^= 4
    report, _ = run_live(ScreenApi(render_band(cells)))
    assert not report.ok and report.marker_seen
    assert report.decoded == BandError("checksum")
    assert report.mismatches == [(3, 17, expected[CELLS_PER_ROW * 3 + 17], cells[CELLS_PER_ROW * 3 + 17])]
    assert any("rangée 3, colonne 17" in line for line in report.lines)


def test_live_selftest_other_message_is_not_the_vector():
    report, _ = run_live(ScreenApi(render_band(encode_cells(1, b"autre message"))))
    assert not report.ok and report.decoded == Decoded(1, b"autre message")
    assert any("pas la bande de test" in line for line in report.lines)


def test_report_json_has_no_pixels():
    report, _ = run_live(ScreenApi(render_band(selftest_cells())))
    payload = report.to_json()
    assert payload["ok"] is True and payload["mismatches"] == 0
    assert payload["window"] == {"hwnd": 7, "pid": 4242, "executable": "WowB.exe", "title": "World of Warcraft"}
    assert payload["decoded"] == {"message_id": SELFTEST_ID, "bytes": 1792}
    assert not {"pixels", "image", "bgra"} & set(payload)
    json.dumps(payload)


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def test_cli_selftest_offline(capsys, make_deps):
    code, out, _ = run(capsys, ["bridge", "selftest"], make_deps())
    assert code == 0 and "vecteur reconnu" in out
    code, out, _ = run(capsys, ["bridge", "selftest", "--json"], make_deps())
    payload = json.loads(out)
    assert code == 0 and payload["ok"] is True and "provenance" in payload


def test_cli_install_and_touch(capsys, make_deps, tmp_path):
    wow = tmp_path / "wow"
    (wow / "Interface" / "AddOns").mkdir(parents=True)
    code, out, _ = run(capsys, ["bridge", "install", "--wow-dir", str(wow), "--dry-run"], make_deps())
    assert code == 0 and "[simulation]" in out
    assert not (wow / "Interface" / "AddOns" / "ForeverBridge").exists()
    code, out, _ = run(capsys, ["bridge", "install", "--wow-dir", str(wow)], make_deps())
    assert code == 0 and (wow / "Interface" / "AddOns" / "ForeverBridge" / "ForeverBridge.toc").is_file()
    assert "relancer le jeu" in out
    code, out, _ = run(capsys, ["bridge", "selftest", "--touch", "--wow-dir", str(wow)], make_deps())
    assert code == 0 and "/fv diag" in out
    assert (wow / "Interface" / "AddOns" / "ForeverBridge" / "ctl" / "late.wav").is_file()


def test_cli_install_refuses_a_bad_folder(capsys, make_deps, tmp_path):
    code, _, err = run(capsys, ["bridge", "install", "--wow-dir", str(tmp_path)], make_deps())
    assert code == 2 and "Interface/AddOns" in err
