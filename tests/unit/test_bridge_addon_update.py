"""Addon tenu à jour par le pont (retours de la sonde en jeu F du 2026-10-09, point 3). Cas réel : après la fusion,
l'addon installé dans le jeu était encore l'ancienne version, jusqu'à un `forever bridge install` à la main. Le pont
compare les fichiers de l'addon installé à ceux du dépôt (le `## Version:` du .toc n'est jamais changé, il ne dirait
rien) ; s'ils diffèrent, il réinstalle lui-même dès que le jeu est fermé, jamais pendant qu'il tourne, et l'annonce
dans la fenêtre au lancement suivant ; jeu ouvert, la ligne d'état dit « addon mis à jour à la prochaine fermeture
du jeu ». Sans pont, `forever bridge status` dit « addon à réinstaller : forever bridge install, jeu fermé »."""

import json

from forever.bridge.install import ADDON, addon_outdated, install_bridge
from forever.bridge.keeper import AddonKeeper
from forever.bridge.state import BridgeState
from forever.bridge.status import ADDON_LINES, status_line
from forever.cli import main

OUTDATED = "addon à réinstaller : forever bridge install, jeu fermé"
PENDING = "addon mis à jour à la prochaine fermeture du jeu"


def wow(tmp_path):
    root = tmp_path / "wow"
    (root / "Interface" / "AddOns").mkdir(parents=True)
    return root


def installed(tmp_path):
    root = wow(tmp_path)
    install_bridge(root, slots=8)
    return root, root / "Interface" / "AddOns"


class Game:
    def __init__(self, running: bool):
        self.running = running
        self.checks = 0

    def __call__(self) -> bool:
        self.checks += 1
        return self.running


def keeper(tmp_path, root, addons, game, journal=None):
    from test_bridge_loop import NOW, Clock

    from forever.bridge.journal import Journal

    clock = Clock()
    return (
        AddonKeeper(
            wow_dir=root,
            addons_dir=addons,
            game_running=game,
            journal=journal or Journal(tmp_path / "journal", lambda: NOW),
            state=BridgeState.load(tmp_path / "state.json"),
            clock=clock,
            slots=8,
        ),
        clock,
    )


def test_fresh_install_is_up_to_date(tmp_path):
    _, addons = installed(tmp_path)
    assert addon_outdated(addons) == []


def test_changed_missing_and_bridge_written_files(tmp_path):
    _, addons = installed(tmp_path)
    (addons / ADDON / "Message.lua").write_text("-- ancienne version\n", encoding="utf-8")
    (addons / ADDON / "Codec.lua").unlink()
    (addons / ADDON / "Inbox.lua").write_text("-- écrit par le pont\n", encoding="utf-8")
    (addons / ADDON / "Status.lua").write_text("-- écrit par le pont\n", encoding="utf-8")
    (addons / ADDON / "ctl" / "flip.wav").write_bytes(b"x")
    assert addon_outdated(addons) == ["Codec.lua", "Message.lua"]


def test_not_installed_is_outdated(tmp_path):
    addons = wow(tmp_path) / "Interface" / "AddOns"
    assert "ForeverBridge.toc" in addon_outdated(addons)


def test_status_lines():
    base = {"version": "1.60.1.70245", "freshness": "fresh"}
    assert status_line({**base, "addon": "a_reinstaller"}).endswith(OUTDATED)
    assert status_line({**base, "addon": "en_attente"}).endswith(PENDING)
    assert "addon mis à jour" in status_line({**base, "addon": "mis_a_jour"})
    assert status_line(base) == "Données 1.60.1.70245 · à jour"
    assert set(ADDON_LINES) == {"a_reinstaller", "en_attente", "mis_a_jour"}


def test_never_reinstalls_while_the_game_runs(tmp_path):
    root, addons = installed(tmp_path)
    (addons / ADDON / "Message.lua").write_text("-- ancienne version\n", encoding="utf-8")
    game = Game(running=True)
    k, clock = keeper(tmp_path, root, addons, game)
    k.check()
    for _ in range(5):
        k.tick()
        clock.t += 10
    assert addon_outdated(addons) == ["Message.lua"]
    assert k.addon_state() == "en_attente"


def test_reinstalls_once_the_game_is_closed_and_announces_it_at_next_launch(tmp_path):
    from test_bridge_loop import events

    root, addons = installed(tmp_path)
    (addons / ADDON / "Message.lua").write_text("-- ancienne version\n", encoding="utf-8")
    game = Game(running=True)
    k, clock = keeper(tmp_path, root, addons, game)
    k.check()
    assert k.tick() is False and k.addon_state() == "en_attente"
    game.running = False
    clock.t += 10
    assert k.tick() is True  # état changé : le pont réécrit Status.lua
    assert addon_outdated(addons) == []
    assert k.addon_state() == "mis_a_jour"
    assert [e["event"] for e in events(tmp_path)].count("addon_updated") == 1
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert saved["addon_updated_at"]
    # lancement suivant : l'annonce reste pendant la partie, puis disparaît à la fermeture du jeu
    game.running = True
    clock.t += 10
    k.tick()
    assert k.addon_state() == "mis_a_jour"
    game.running = False
    clock.t += 10
    assert k.tick() is True
    assert k.addon_state() is None


def test_up_to_date_addon_never_checks_the_game(tmp_path):
    root, addons = installed(tmp_path)
    game = Game(running=False)
    k, clock = keeper(tmp_path, root, addons, game)
    k.check()
    for _ in range(3):
        k.tick()
        clock.t += 10
    assert game.checks == 0 and k.addon_state() is None


def test_bridge_refresh_carries_the_addon_state(tmp_path):
    from test_bridge_loop import FakeAgent, FakeCapture, make

    root, addons = installed(tmp_path)
    (addons / ADDON / "Message.lua").write_text("-- ancienne version\n", encoding="utf-8")
    k, _ = keeper(tmp_path, root, addons, Game(running=True))
    bridge, _, _ = make(tmp_path, FakeCapture(), FakeAgent())
    bridge.keeper = k
    k.check()
    bridge.refresh()
    assert bridge.status_cache["addon"] == "en_attente"
    assert bridge.status_cache["line"].endswith(PENDING)


def test_cli_status_without_bridge_says_reinstall(capsys, make_deps, tmp_path):
    root, addons = installed(tmp_path)
    (addons / ADDON / "Message.lua").write_text("-- ancienne version\n", encoding="utf-8")
    deps = make_deps(wow_dir=root)
    assert main(["bridge", "status"], deps) == 0
    assert OUTDATED in capsys.readouterr()[0]
    assert main(["bridge", "status", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["data"]["addon"] == "a_reinstaller" and payload["data"]["addon_files"] == ["Message.lua"]
