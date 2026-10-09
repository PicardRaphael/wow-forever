"""Installation de la réserve d'emplacements (P06a, bloc B) : `ForeverBridge_S001`…, `.toc` chargé à la demande,
`Inbox.lua` d'attente écrit seulement s'il manque ; aucun drapeau son ; bornes de `--slots`."""

import pytest
from test_bridge_install import check_addon, fake_wow

from forever.bridge.install import InstallError, install_bridge


def slot_dir(wow, index):
    return wow / "Interface" / "AddOns" / f"ForeverBridge_S{index:03d}"


def test_install_creates_the_reserve(tmp_path):
    wow = fake_wow(tmp_path)
    install_bridge(wow, slots=8)
    for index in (1, 8):
        toc = (slot_dir(wow, index) / f"ForeverBridge_S{index:03d}.toc").read_text(encoding="utf-8").splitlines()
        for line in ("## Interface: 16001", "## LoadOnDemand: 1", "## Dependencies: ForeverBridge", "Inbox.lua"):
            assert line in toc, line
        inbox = (slot_dir(wow, index) / "Inbox.lua").read_text(encoding="utf-8")
        assert "ForeverBridgeSlot" in inbox and "replies" in inbox
        assert check_addon.check_addon(slot_dir(wow, index)) == []
    assert not slot_dir(wow, 9).exists()
    bridge = wow / "Interface" / "AddOns" / "ForeverBridge"
    assert not (bridge / "sig").exists() and not (bridge / "ack").exists()
    assert (bridge / "Inbox.lua").is_file() and (bridge / "Status.lua").is_file()


def test_default_reserve_is_two_hundred(tmp_path):
    wow = fake_wow(tmp_path)
    report = install_bridge(wow, dry_run=True)
    assert any("ForeverBridge_S200" in a for a in report.actions)
    assert not any("ForeverBridge_S201" in a for a in report.actions)


def test_reinstall_keeps_the_published_inbox(tmp_path):
    wow = fake_wow(tmp_path)
    install_bridge(wow, slots=8)
    (slot_dir(wow, 3) / "Inbox.lua").write_text("ForeverBridgeSlot = { v = 1, now = 42, replies = {} }\n")
    install_bridge(wow, slots=8)
    assert "now = 42" in (slot_dir(wow, 3) / "Inbox.lua").read_text(encoding="utf-8")


@pytest.mark.parametrize("slots", [7, 201])
def test_reserve_bounds(tmp_path, slots):
    with pytest.raises(InstallError, match="8 à 200"):
        install_bridge(fake_wow(tmp_path), slots=slots)
