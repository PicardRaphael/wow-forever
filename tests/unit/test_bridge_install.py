"""Installation de ForeverBridge dans un faux dossier du client (P06a). Bloc A : addon, fichiers de contrôle des
drapeaux (`ctl/`), addon de sonde chargé à la demande, fichiers modifiés pendant que le jeu tourne (`touch_probe`)."""

import importlib.util
from datetime import datetime

import pytest
from conftest import REPO_ROOT

from forever.bridge.install import InstallError, find_ogg, install_bridge, touch_probe
from forever.bridge.slots import SILENT_WAV

spec = importlib.util.spec_from_file_location("check_addon", REPO_ROOT / "scripts" / "check_addon.py")
assert spec and spec.loader
check_addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_addon)

SOURCE = REPO_ROOT / "addon" / "ForeverBridge"
NOW = datetime(2026, 10, 9, 14, 5, 9)  # noqa: DTZ001 : heure locale affichée en jeu


def fake_wow(tmp_path, *, oggs=True):
    addons = tmp_path / "wow" / "Interface" / "AddOns"
    sounds = addons / "AutreAddon" / "media"
    sounds.mkdir(parents=True)
    if oggs:
        (sounds / "long.ogg").write_bytes(b"O" * 10)
        (sounds / "court.ogg").write_bytes(b"OggS1")
    return tmp_path / "wow"


def ctl(wow, name):
    return wow / "Interface" / "AddOns" / "ForeverBridge" / "ctl" / name


def test_find_ogg_takes_the_smallest_outside_our_addons(tmp_path):
    wow = fake_wow(tmp_path)
    addons = wow / "Interface" / "AddOns"
    (addons / "ForeverBridge" / "ctl").mkdir(parents=True)
    (addons / "ForeverBridge" / "ctl" / "tiny.ogg").write_bytes(b"x")
    assert find_ogg(addons) == addons / "AutreAddon" / "media" / "court.ogg"
    assert find_ogg(fake_wow(tmp_path / "vide", oggs=False) / "Interface" / "AddOns") is None


def test_install_copies_the_addon_and_the_control_files(tmp_path):
    wow = fake_wow(tmp_path)
    report = install_bridge(wow)
    dest = wow / "Interface" / "AddOns" / "ForeverBridge"
    for name in ("ForeverBridge.toc", "Codec.lua", "ForeverBridge.lua"):
        assert (dest / name).read_bytes() == (SOURCE / name).read_bytes(), name
    assert ctl(wow, "empty.wav").read_bytes() == b""
    assert ctl(wow, "valid.wav").read_bytes() == SILENT_WAV
    assert ctl(wow, "flip.wav").read_bytes() == b""
    assert ctl(wow, "empty.ogg").read_bytes() == b""
    assert ctl(wow, "valid.ogg").read_bytes() == b"OggS1"
    assert ctl(wow, "flip.ogg").read_bytes() == b""
    assert not ctl(wow, "late.wav").exists() and not ctl(wow, "late.ogg").exists()
    assert report.ogg_source == wow / "Interface" / "AddOns" / "AutreAddon" / "media" / "court.ogg"
    probe = wow / "Interface" / "AddOns" / "ForeverBridge_Probe"
    toc = (probe / "ForeverBridge_Probe.toc").read_text(encoding="utf-8").splitlines()
    for line in ("## Interface: 16001", "## LoadOnDemand: 1", "## Dependencies: ForeverBridge", "Probe.lua"):
        assert line in toc, line
    assert (probe / "Probe.lua").read_text(encoding="utf-8") == 'ForeverBridge_ProbeValue = "installation"\n'
    assert check_addon.check_addon(probe) == []
    assert report.actions and not any(a.startswith("[simulation]") for a in report.actions)


def test_install_without_any_ogg(tmp_path):
    wow = fake_wow(tmp_path, oggs=False)
    report = install_bridge(wow)
    assert report.ogg_source is None
    assert not ctl(wow, "valid.ogg").exists()
    assert ctl(wow, "empty.ogg").read_bytes() == b""
    assert any("aucun .ogg" in a for a in report.actions)


def test_dry_run_writes_nothing(tmp_path):
    wow = fake_wow(tmp_path)
    before = sorted(p.relative_to(wow) for p in wow.rglob("*"))
    report = install_bridge(wow, dry_run=True)
    assert sorted(p.relative_to(wow) for p in wow.rglob("*")) == before
    assert report.actions and all(a.startswith("[simulation]") for a in report.actions)


def test_invalid_destination_is_refused(tmp_path):
    with pytest.raises(InstallError, match="Interface/AddOns"):
        install_bridge(tmp_path)


def test_touch_probe_changes_the_files_while_the_game_runs(tmp_path):
    wow = fake_wow(tmp_path)
    install_bridge(wow)
    actions = touch_probe(wow, NOW)
    assert ctl(wow, "flip.wav").read_bytes() == SILENT_WAV
    assert ctl(wow, "late.wav").read_bytes() == SILENT_WAV
    assert ctl(wow, "flip.ogg").read_bytes() == b"OggS1"
    assert ctl(wow, "late.ogg").read_bytes() == b"OggS1"
    assert ctl(wow, "empty.wav").read_bytes() == b""  # témoins inchangés
    probe = wow / "Interface" / "AddOns" / "ForeverBridge_Probe" / "Probe.lua"
    assert probe.read_text(encoding="utf-8") == 'ForeverBridge_ProbeValue = "modifié à 14:05:09"\n'
    assert len(actions) >= 3


def test_touch_probe_requires_an_installed_bridge(tmp_path):
    with pytest.raises(InstallError, match="forever bridge install"):
        touch_probe(fake_wow(tmp_path), NOW)


def test_reinstall_resets_the_probe(tmp_path):
    wow = fake_wow(tmp_path)
    install_bridge(wow)
    touch_probe(wow, NOW)
    install_bridge(wow)
    assert ctl(wow, "flip.wav").read_bytes() == b""
    assert ctl(wow, "flip.ogg").read_bytes() == b""
    assert not ctl(wow, "late.wav").exists() and not ctl(wow, "late.ogg").exists()
    probe = wow / "Interface" / "AddOns" / "ForeverBridge_Probe" / "Probe.lua"
    assert probe.read_text(encoding="utf-8") == 'ForeverBridge_ProbeValue = "installation"\n'
