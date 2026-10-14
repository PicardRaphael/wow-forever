"""`forever doctor` sur une installation de fixture saine (LN1, bloc D, décision 271) : chaque contrôle `ok` (ou
`unknown` quand il ne peut pas être vérifié, ou `info`), code 0, aucun réseau. Les sondes du système sont simulées ;
installation, addons, journaux, profil, sauvegardes et cache vivent dans `tmp_path`."""

import json
import os
import shutil
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from conftest import FIXTURES, NOW, PRODUCT, REPO_ROOT, FakeHttp
from test_installs import BETA_V, make_root

from forever import doctor_probes
from forever.backup import make_backup
from forever.bridge.install import install_bridge
from forever.cli import main
from forever.doctor import Probes, exit_code, run_checks
from forever.errors import EXIT_DOCTOR
from forever.provenance import validate_provenance

LOG_HEADER = (
    (FIXTURES / "combatlog" / "WoWCombatLog-092726_145346.anon.txt").read_text(encoding="utf-8").splitlines()[0]
)
IDS = [
    "repo",
    "env.python",
    "env.state",
    "env.uv",
    "wow.installs",
    "wow.choice",
    "wow.unknown",
    "wow.env",
    "wow.paths",
    "addons.logger",
    "addons.bridge",
    "combatlog",
    "addons.data",
    "env.vars",
    "gh",
    "claude",
    "tasks.bridge",
    "tasks.update",
    "bridge.running",
    "bridge.journal",
    "profile",
    "backup",
    "antivirus",
    "info.sv_bridge",
]


class World:
    """Installation saine et ses sondes, modifiables cas par cas."""

    def __init__(self, tmp_path: Path, make_deps):
        self.tmp = tmp_path
        self.repo = tmp_path / "depot"
        for rel in ("forever", ".venv"):
            (self.repo / rel).mkdir(parents=True)
        for rel in ("pyproject.toml", "uv.lock"):
            (self.repo / rel).write_text("", encoding="utf-8")
        self.root = make_root(tmp_path / "jeu", [(PRODUCT, BETA_V)], {"_classic_beta_": (PRODUCT, "WowB.exe")})
        self.wow = self.root / "_classic_beta_"
        addons = self.wow / "Interface" / "AddOns"
        addons.mkdir(parents=True)
        shutil.copytree(REPO_ROOT / "addon" / "ForeverLogger", addons / "ForeverLogger")
        install_bridge(self.wow)
        sv = self.wow / "WTF" / "Account" / "COMPTE" / "SavedVariables"
        sv.mkdir(parents=True)
        (sv / "ForeverLogger.lua").write_text("ForeverLoggerDB = {}\n", encoding="utf-8")
        (self.wow / "WTF" / "Config.wtf").write_text('SET advancedCombatLogging "1"\n', encoding="utf-8")
        logs = self.wow / "Logs"
        logs.mkdir()
        self.log = logs / "WoWCombatLog-092626_200000.txt"
        self.log.write_text(LOG_HEADER + "\n", encoding="utf-8")
        self.age_log(timedelta(days=1))
        self.pythonw = tmp_path / "pythonw.exe"
        self.pythonw.write_bytes(b"")
        self.http = FakeHttp.failing()
        deps = make_deps(wow_dir=self.wow, http=self.http)
        self.environ = {
            "FOREVER_WOW_ROOTS": str(self.root),
            "FOREVER_WOW_DIR": str(self.wow),
            "FOREVER_HOME": str(self.repo),
            "FOREVER_BACKUP_DIR": str(tmp_path / "sauvegardes"),
        }
        self.deps = replace(deps, environ=self.environ)
        self.deps.profile_path.parent.mkdir(parents=True)
        self.deps.profile_path.write_text('{"schema_version": 3, "active": null, "characters": {}}', encoding="utf-8")
        make_backup(self.deps, NOW - timedelta(hours=1), reason="test")
        self.tasks = {
            "WoW Forever - pont": self.task("-m forever.bridge.autostart --cache-dir x"),
            "WoW Forever - mise à jour": self.task("-m forever.update_task"),
        }
        self.probes = Probes(
            windows=True,
            system_drive="Z:",
            repo=self.repo,
            gh_version=lambda: "gh version 2.102.0 (2026-09-30)",
            gh_token=lambda: True,
            claude_path=lambda: "claude",
            claude_auth=lambda: {"loggedIn": True, "authMethod": "claude.ai"},
            uv_check=lambda repo: (True, "Would make no changes"),
            python_check=lambda: None,
            task=lambda name: self.tasks.get(name),
            supervisor_pid=lambda cache: 111,
            bridge_pid=lambda cache: 222,
        )

    def task(self, arguments: str) -> dict:
        return {
            "command": str(self.pythonw),
            "arguments": arguments,
            "working_directory": str(self.repo),
            "user": r"PC\joueur",
        }

    def age_log(self, age: timedelta) -> None:
        when = (NOW - age).timestamp()
        os.utime(self.log, (when, when))

    def checks(self, **probes):
        return {c.id: c for c in run_checks(self.deps, replace(self.probes, **probes))}


@pytest.fixture
def world(tmp_path, make_deps):
    return World(tmp_path, make_deps)


def test_a_healthy_installation(world):
    checks = run_checks(world.deps, world.probes)
    assert [c.id for c in checks] == IDS
    by_id = {c.id: c for c in checks}
    bad = {c.id: (c.status, c.finding) for c in checks if c.status in ("warn", "fail")}
    assert bad == {}
    assert by_id["antivirus"].status == "unknown"
    assert by_id["wow.choice"].status == "ok" and str(world.wow) in by_id["wow.choice"].finding
    assert exit_code(checks) == 0
    assert world.http.calls == []


def test_every_problem_has_a_fix(world):
    world.tasks.clear()
    for check in run_checks(world.deps, replace(world.probes, gh_token=lambda: False)):
        if check.status in ("warn", "fail"):
            assert check.fix, check.id


def test_cli_text_and_json(world, monkeypatch, capsys):
    monkeypatch.setattr(doctor_probes, "default_probes", lambda: world.probes)
    assert main(["doctor"], world.deps) == 0
    out = capsys.readouterr().out
    assert "[ok] wow.choice" in out and "[?] antivirus" in out
    assert out.rstrip().splitlines()[-1].startswith("Provenance")
    assert main(["doctor", "--json"], world.deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert validate_provenance(data["provenance"]) == []
    assert [c["id"] for c in data["checks"]] == IDS
    assert data["summary"]["fail"] == 0
    antivirus = next(c for c in data["checks"] if c["id"] == "antivirus")
    assert antivirus["certainty"] == "suppose"
    assert next(c for c in data["checks"] if c["id"] == "repo")["certainty"] == "certain"


def test_cli_exit_code_7_on_a_failure(world, monkeypatch, capsys):
    monkeypatch.setattr(doctor_probes, "default_probes", lambda: replace(world.probes, gh_version=lambda: None))
    assert main(["doctor", "--json"], world.deps) == EXIT_DOCTOR == 7
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["fail"] >= 1
    assert validate_provenance(data["provenance"]) == []


def test_claude_auth_status_keeps_two_fields_only():
    raw = json.dumps(
        {
            "loggedIn": True,
            "authMethod": "claude.ai",
            "email": "joueur@example.org",
            "orgName": "Organisation",
            "orgId": "x",
            "subscriptionType": "max",
        }
    )
    assert doctor_probes.reduce_auth(raw) == {"loggedIn": True, "authMethod": "claude.ai"}
    assert doctor_probes.reduce_auth("pas du JSON") is None


def test_doctor_output_never_carries_the_account(world, monkeypatch, capsys):
    auth = doctor_probes.reduce_auth(json.dumps({"loggedIn": True, "authMethod": "claude.ai", "email": "a@b.c"}))
    monkeypatch.setattr(doctor_probes, "default_probes", lambda: replace(world.probes, claude_auth=lambda: auth))
    main(["doctor", "--json"], world.deps)
    out = capsys.readouterr().out
    assert "a@b.c" not in out and "email" not in out


def test_outside_windows_the_windows_checks_are_not_applicable(world):
    checks = world.checks(windows=False)
    for name in ("tasks.bridge", "tasks.update", "antivirus"):
        assert checks[name].status == "unknown" and "non applicable" in checks[name].finding
