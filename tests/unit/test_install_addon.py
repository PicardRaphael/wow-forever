"""Installation de l'addon ForeverLogger (`scripts/install_addon.py`) dans un faux dossier du client ; sauvegardes de
l'ancien addon rangées dans le cache du projet, jamais dans le dossier des addons."""

import importlib.util
from datetime import datetime

import pytest
from conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location("install_addon", REPO_ROOT / "scripts" / "install_addon.py")
assert spec and spec.loader
install_addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install_addon)

NOW = datetime(2026, 9, 27, 15, 30, 0)  # noqa: DTZ001 : horodatage local du nom de sauvegarde
SOURCE = REPO_ROOT / "addon" / "ForeverLogger"


def fake_wow(tmp_path, with_old=True):
    addons = tmp_path / "wow" / "Interface" / "AddOns"
    addons.mkdir(parents=True)
    if with_old:
        (addons / "ForeverLogger").mkdir()
        (addons / "ForeverLogger" / "ForeverLogger.toc").write_text("ancien", encoding="utf-8")
    return tmp_path / "wow"


def backups(tmp_path):
    return tmp_path / "cache" / "addons" / "backups"


def old_backup(wow, stamp):
    folder = wow / "Interface" / "AddOns" / f"ForeverLogger.bak-{stamp}"
    folder.mkdir()
    (folder / "ForeverLogger.toc").write_text(stamp, encoding="utf-8")
    return folder


def test_install_copies_and_backs_up_into_the_cache(tmp_path):
    """La sauvegarde de l'ancien addon va dans le cache du projet, jamais dans le dossier des addons."""
    wow = fake_wow(tmp_path)
    actions = install_addon.install(SOURCE, wow, dry_run=False, now=NOW, backup_dir=backups(tmp_path))
    dest = wow / "Interface" / "AddOns" / "ForeverLogger"
    backup = backups(tmp_path) / "ForeverLogger.bak-20260927-153000"
    assert (backup / "ForeverLogger.toc").read_text(encoding="utf-8") == "ancien"
    assert sorted(p.name for p in (wow / "Interface" / "AddOns").iterdir()) == ["ForeverLogger"]
    assert (dest / "ForeverLogger.toc").read_bytes() == (SOURCE / "ForeverLogger.toc").read_bytes()
    assert (dest / "ForeverLogger.lua").is_file()
    assert any("sauvegarde" in a for a in actions) and any("copie" in a for a in actions)


def test_dry_run_writes_nothing(tmp_path):
    wow = fake_wow(tmp_path)
    old_backup(wow, "20261002-073506")
    before = sorted(p.relative_to(wow) for p in wow.rglob("*"))
    actions = install_addon.install(SOURCE, wow, dry_run=True, now=NOW, backup_dir=backups(tmp_path))
    assert sorted(p.relative_to(wow) for p in wow.rglob("*")) == before
    assert not backups(tmp_path).exists()
    assert actions and all(a.startswith("[simulation]") for a in actions)
    assert any("sauvegarde déplacée" in a for a in actions)


def test_first_install_without_backup(tmp_path):
    wow = fake_wow(tmp_path, with_old=False)
    actions = install_addon.install(SOURCE, wow, dry_run=False, now=NOW, backup_dir=backups(tmp_path))
    assert not any("sauvegarde" in a for a in actions)
    assert (wow / "Interface" / "AddOns" / "ForeverLogger" / "ForeverLogger.lua").is_file()


def test_invalid_destination_is_refused(tmp_path):
    with pytest.raises(install_addon.InstallError, match="Interface/AddOns"):
        install_addon.install(SOURCE, tmp_path, dry_run=True, now=NOW, backup_dir=backups(tmp_path))


def test_old_backups_leave_the_addons_folder(tmp_path):
    """Les sauvegardes `ForeverLogger.bak-*` laissées par les anciennes installations vont dans le cache, contenu
    intact ; un autre addon dont le nom commence pareil n'est pas touché ; un second passage ne fait rien."""
    wow = fake_wow(tmp_path)
    addons = wow / "Interface" / "AddOns"
    for stamp in ("20261002-073506", "20261002-073519"):
        old_backup(wow, stamp)
    other = addons / "ForeverLoggerPlus"
    other.mkdir()
    actions = install_addon.relocate_backups(addons, "ForeverLogger", backups(tmp_path))
    assert not list(addons.glob("*.bak-*")) and other.is_dir()
    for stamp in ("20261002-073506", "20261002-073519"):
        moved = backups(tmp_path) / f"ForeverLogger.bak-{stamp}" / "ForeverLogger.toc"
        assert moved.read_text(encoding="utf-8") == stamp
    assert len(actions) == 2 and all("sauvegarde déplacée" in a for a in actions)
    assert install_addon.relocate_backups(addons, "ForeverLogger", backups(tmp_path)) == []


def test_relocation_never_overwrites_a_backup(tmp_path):
    wow = fake_wow(tmp_path)
    old_backup(wow, "20261002-073506")
    kept = backups(tmp_path) / "ForeverLogger.bak-20261002-073506"
    kept.mkdir(parents=True)
    install_addon.relocate_backups(wow / "Interface" / "AddOns", "ForeverLogger", backups(tmp_path))
    assert kept.is_dir() and not any(kept.iterdir())
    assert (backups(tmp_path) / "ForeverLogger.bak-20261002-073506-2" / "ForeverLogger.toc").is_file()


def test_install_also_moves_old_backups(tmp_path):
    wow = fake_wow(tmp_path)
    old_backup(wow, "20261002-073506")
    install_addon.install(SOURCE, wow, dry_run=False, now=NOW, backup_dir=backups(tmp_path))
    assert sorted(p.name for p in backups(tmp_path).iterdir()) == [
        "ForeverLogger.bak-20260927-153000",
        "ForeverLogger.bak-20261002-073506",
    ]


def test_main_backups_only(tmp_path, capsys, monkeypatch):
    """`--backups-only` déplace les sauvegardes dans le cache (FOREVER_CACHE_DIR) sans réinstaller l'addon."""
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    wow = fake_wow(tmp_path)
    old_backup(wow, "20261002-073506")
    assert install_addon.main(["--wow-dir", str(wow), "--backups-only"]) == 0
    toc = wow / "Interface" / "AddOns" / "ForeverLogger" / "ForeverLogger.toc"
    assert toc.read_text(encoding="utf-8") == "ancien"
    assert (backups(tmp_path) / "ForeverLogger.bak-20261002-073506").is_dir()
    assert "sauvegarde déplacée" in capsys.readouterr().out


def test_main_dry_run(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(tmp_path / "cache"))
    wow = fake_wow(tmp_path)
    assert install_addon.main(["--wow-dir", str(wow), "--dry-run"]) == 0
    assert "[simulation]" in capsys.readouterr().out
    assert install_addon.main(["--wow-dir", str(tmp_path / "absent")]) == 2
