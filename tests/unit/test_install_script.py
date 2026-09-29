"""Installation du plugin (T06, décision D1 précisée) : `scripts/install_plugin.ps1` lu comme texte, détection du
dossier du client dans les deux Program Files (`forever.config.default_wow_dir`, utilisée aussi par
`scripts/install_addon.py`) et mode d'emploi `docs/USAGE.md`."""

import importlib.util
import re
from pathlib import Path

import pytest
from conftest import REPO_ROOT

from forever.config import WOW_DIR_CANDIDATES, default_wow_dir
from forever.hooks import GAME_NUMBER

SCRIPT = REPO_ROOT / "scripts" / "install_plugin.ps1"
USAGE = REPO_ROOT / "docs" / "USAGE.md"
X86 = Path(r"C:\Program Files (x86)\World of Warcraft\_classic_beta_")
X64 = Path(r"C:\Program Files\World of Warcraft\_classic_beta_")


def script():
    return SCRIPT.read_text(encoding="utf-8-sig")


# --- Dossier du client ---------------------------------------------------------------------------------------------


def test_candidates_cover_both_program_files():
    assert WOW_DIR_CANDIDATES == (X86, X64)


def test_environment_variable_wins():
    assert default_wow_dir({"FOREVER_WOW_DIR": r"D:\Jeux\WoW"}, exists=lambda p: True) == Path(r"D:\Jeux\WoW")


def test_program_files_without_x86_is_found():
    assert default_wow_dir({}, exists=lambda p: p == X64) == X64


def test_x86_first_when_both_exist():
    assert default_wow_dir({}, exists=lambda p: True) == X86


def test_default_when_nothing_is_found():
    assert default_wow_dir({}, exists=lambda p: False) == X86


def test_install_addon_reads_forever_wow_dir(tmp_path, monkeypatch, capsys):
    wow = tmp_path / "wow"
    (wow / "Interface" / "AddOns").mkdir(parents=True)
    monkeypatch.setenv("FOREVER_WOW_DIR", str(wow))
    spec = importlib.util.spec_from_file_location("install_addon", REPO_ROOT / "scripts" / "install_addon.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--dry-run"]) == 0
    assert str(wow / "Interface" / "AddOns" / "ForeverLogger") in capsys.readouterr().out


# --- Script d'installation -----------------------------------------------------------------------------------------


def test_script_is_utf8_with_bom_for_windows_powershell():
    assert SCRIPT.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("tool", ["git", "uv", "claude"])
def test_script_checks_required_tools(tool):
    assert re.search(rf"Get-Command\s+{tool}\b", script())


def test_script_sets_user_environment_variables():
    text = script()
    for name in ("FOREVER_HOME", "FOREVER_WOW_DIR"):
        assert re.search(rf"SetEnvironmentVariable\(\s*['\"]{name}['\"][^)]*['\"]User['\"]\s*\)", text), name


def test_script_detects_wow_in_both_program_files():
    text = script()
    assert "Program Files (x86)" in text
    assert re.search(r"Program Files\\World of Warcraft|ProgramW6432|\$env:ProgramFiles\b", text)
    assert "_classic_beta_" in text


def test_script_installs_the_plugin_at_user_scope():
    text = script()
    assert "uv sync" in text
    assert "claude plugin marketplace add" in text
    assert "claude plugin marketplace update wow-forever" in text
    assert "claude plugin install forever@wow-forever --scope user" in text
    assert "claude plugin update forever@wow-forever --scope user" in text


def test_script_ends_with_checks():
    text = script()
    checks = [text.rfind(c) for c in ("claude plugin validate", "forever status --offline", "claude plugin list")]
    installs = text.rfind("claude plugin install")
    assert all(c > installs for c in checks)


def test_script_writes_nothing_in_the_data_and_has_no_game_number():
    text = script()
    assert "forever/data" not in text and "forever\\data" not in text
    assert not GAME_NUMBER.search(text)
    assert "statusLine" not in text


# --- Mode d'emploi -------------------------------------------------------------------------------------------------


def test_usage_gives_the_execution_policy_bypass_command():
    assert r"powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1" in USAGE.read_text(encoding="utf-8")


def test_usage_sections():
    text = USAGE.read_text(encoding="utf-8")
    for heading in (
        "## Installation",
        "## Mise à jour",
        "## Poser une question",
        "## Lire la réponse",
        "## Ce que le plugin ne sait pas encore",
        "## Évaluation",
    ):
        assert heading in text, heading
    assert "claude plugin eval" in text
    assert "FOREVER_WOW_DIR" in text and "FOREVER_HOME" in text
