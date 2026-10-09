"""Pont au repos (décision 226) : lancé à l'ouverture de la session, il tourne pendant que le jeu est fermé ou en
arrière-plan. Il ne capture alors rien, cherche la fenêtre du jeu toutes les `FIND_EVERY_S` secondes seulement, se
réveille moins souvent tant qu'aucune fenêtre n'est connue, et relit la liste des sauvegardes à intervalles.

Cas corrigé : la fenêtre trouvée n'était jamais oubliée. Jeu fermé puis relancé, le pont gardait l'ancienne fenêtre
et ne voyait plus la nouvelle (plus aucune capture jusqu'au redémarrage du pont)."""

from test_bridge_capture import CLIENT, FakeApi
from test_bridge_loop import FakeAgent, make

from forever.bridge.capture import GameWindow, WindowsCapture
from forever.bridge.loop import FIND_EVERY_S, IDLE_INTERVAL_S, OUTBOX_LIST_S


class ClosingApi(FakeApi):
    """Fenêtres du jeu modifiables : `windows` vide = jeu fermé."""

    def client_rect(self, hwnd):
        return CLIENT if any(w.hwnd == hwnd for w in self.windows) else None


def test_a_closed_window_is_forgotten_and_the_next_one_found():
    api = ClosingApi()
    cap = WindowsCapture({"WowB.exe"}, api)
    assert cap.find() is not None and cap.client() == CLIENT
    api.windows = []  # jeu fermé
    assert cap.client() is None and cap.window is None
    api.windows = [GameWindow(8, 4343, "WowB.exe", "World of Warcraft")]  # jeu relancé
    api.foreground_hwnd = 8
    assert cap.find() is not None and cap.window is not None and cap.window.hwnd == 8
    assert cap.allowed()


class NoGame:
    """Jeu fermé : aucune fenêtre, rien à capturer."""

    def __init__(self):
        self.window = None
        self.finds = 0

    def find(self):
        self.finds += 1

    def client(self):
        raise AssertionError("zone client lue sans fenêtre")

    def allowed(self):
        return False

    def grab(self, rect):
        raise AssertionError("capture jeu fermé")


def test_game_closed_nothing_is_captured_and_the_window_is_sought_sparingly(tmp_path):
    capture = NoGame()
    bridge, _, clock = make(tmp_path, capture, FakeAgent())
    for _ in range(120):
        bridge.step()
        clock.t += 0.25
    assert capture.finds == 30 / FIND_EVERY_S  # 30 s simulées


def test_the_bridge_sleeps_longer_while_no_window_is_known(tmp_path):
    capture = NoGame()
    bridge, _, _ = make(tmp_path, capture, FakeAgent())
    stop = tmp_path / "stop"
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 3:
            capture.window = GameWindow(7, 4242, "WowB.exe", "World of Warcraft")
            capture.client = lambda: CLIENT  # type: ignore[method-assign]
        if len(sleeps) == 5:
            stop.write_text("", encoding="utf-8")

    bridge.run(stop, sleep=sleep)
    assert sleeps == [IDLE_INTERVAL_S] * 3 + [0.25] * 2


def test_the_list_of_saved_variables_is_read_at_intervals(tmp_path):
    saved = tmp_path / "ForeverBridge.lua"
    saved.write_text("ForeverBridgeDB = {}\n", encoding="utf-8")
    lists = []
    bridge, _, clock = make(tmp_path, NoGame(), FakeAgent())

    def outbox_files():
        lists.append(clock())
        return [saved]

    bridge.outbox_files = outbox_files
    for _ in range(240):
        bridge.step()
        clock.t += 0.25
    assert len(lists) == 60 / OUTBOX_LIST_S
