"""Installation de l'addon ForeverLogger (`scripts/install_addon.py`) dans un faux dossier du client."""

import importlib.util
from datetime import datetime

import pytest
from conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location("install_addon", REPO_ROOT / "scripts" / "install_addon.py")
assert spec and spec.loader
install_addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install_addon)

NOW = datetime(2026, 9, 27, 15, 30, 0)  # noqa: DTZ001 : horodatage local du nom de sauvegarde


def fake_wow(tmp_path, with_old=True):
    addons = tmp_path / "wow" / "Interface" / "AddOns"
    addons.mkdir(parents=True)
    if with_old:
        (addons / "ForeverLogger").mkdir()
        (addons / "ForeverLogger" / "ForeverLogger.toc").write_text("ancien", encoding="utf-8")
    return tmp_path / "wow"


def test_install_copies_and_backs_up(tmp_path):
    wow = fake_wow(tmp_path)
    actions = install_addon.install(REPO_ROOT / "addon" / "ForeverLogger", wow, dry_run=False, now=NOW)
    dest = wow / "Interface" / "AddOns" / "ForeverLogger"
    backup = wow / "Interface" / "AddOns" / "ForeverLogger.bak-20260927-153000"
    assert (backup / "ForeverLogger.toc").read_text(encoding="utf-8") == "ancien"
    assert (dest / "ForeverLogger.toc").read_bytes() == (
        REPO_ROOT / "addon/ForeverLogger/ForeverLogger.toc"
    ).read_bytes()
    assert (dest / "ForeverLogger.lua").is_file()
    assert any("sauvegarde" in a for a in actions) and any("copie" in a for a in actions)


def test_dry_run_writes_nothing(tmp_path):
    wow = fake_wow(tmp_path)
    before = sorted(p.relative_to(wow) for p in wow.rglob("*"))
    actions = install_addon.install(REPO_ROOT / "addon" / "ForeverLogger", wow, dry_run=True, now=NOW)
    assert sorted(p.relative_to(wow) for p in wow.rglob("*")) == before
    assert actions and all(a.startswith("[simulation]") for a in actions)


def test_first_install_without_backup(tmp_path):
    wow = fake_wow(tmp_path, with_old=False)
    actions = install_addon.install(REPO_ROOT / "addon" / "ForeverLogger", wow, dry_run=False, now=NOW)
    assert not any("sauvegarde" in a for a in actions)
    assert (wow / "Interface" / "AddOns" / "ForeverLogger" / "ForeverLogger.lua").is_file()


def test_invalid_destination_is_refused(tmp_path):
    with pytest.raises(install_addon.InstallError, match="Interface/AddOns"):
        install_addon.install(REPO_ROOT / "addon" / "ForeverLogger", tmp_path, dry_run=True, now=NOW)


def test_main_dry_run(tmp_path, capsys):
    wow = fake_wow(tmp_path)
    assert install_addon.main(["--wow-dir", str(wow), "--dry-run"]) == 0
    assert "[simulation]" in capsys.readouterr().out
    assert install_addon.main(["--wow-dir", str(tmp_path / "absent")]) == 2
