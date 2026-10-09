"""Conversation « jeu » (P06a, bloc C, décision 212) : ligne de commande de `claude` retenue par la sonde 0.4 (outils
réduits à `Skill` et aux six outils forever, réglages ignorés, seul serveur MCP `forever`, dossier de travail hors du
dépôt), environnement, lecture du flux `stream-json`, ligne de provenance, délai, reprise de session. Aucun appel réel :
flux de fixture et faux `Popen`. Un texte tapé en jeu ne passe que par l'entrée standard, jamais par la ligne de
commande ni par un shell (demande de l'utilisateur du 2026-10-09)."""

import io
import json
import threading

import pytest
from conftest import FIXTURES, REPO_ROOT
from forever.bridge.agent import (
    ALLOWED_TOOLS,
    FOREVER_TOOLS,
    AgentResult,
    ask,
    claude_argv,
    claude_env,
    conversation_dir,
    mcp_config,
    parse_stream,
    provenance_line,
    run_claude,
    write_mcp_config,
)
from forever.bridge.prompt import SYSTEM_PROMPT, message_text

from forever.bridge.record import Record

STREAMS = FIXTURES / "bridge"
QUESTION = "Quel talent à Westfall ? $(rm -rf /) ; & | `whoami` %PATH% \"' > nul"


def lines(name):
    return (STREAMS / name).read_text(encoding="utf-8").splitlines()


def argv(tmp_path, **kwargs):
    return claude_argv(
        claude="claude.exe",
        plugin_dir=REPO_ROOT / "plugin",
        mcp_config=tmp_path / "mcp.json",
        system_prompt=SYSTEM_PROMPT,
        **kwargs,
    )


def test_allowed_tools_are_skill_and_the_six_forever_tools():
    assert FOREVER_TOOLS == (
        "mcp__forever__forever_status",
        "mcp__forever__forever_lookup",
        "mcp__forever__forever_player_profile",
        "mcp__forever__forever_explain_mechanic",
        "mcp__forever__forever_sim_leveling",
        "mcp__forever__forever_build",
    )
    assert ALLOWED_TOOLS == ("Skill", *FOREVER_TOOLS)


def test_command_line_of_the_probe(tmp_path):
    args = argv(tmp_path)
    assert args[:6] == ["claude.exe", "-p", "--output-format", "stream-json", "--verbose", "--tools"]
    assert args[args.index("--tools") + 1] == "Skill"
    assert "--restricted" in args and "--strict-mcp-config" in args
    assert args[args.index("--mcp-config") + 1] == str(tmp_path / "mcp.json")
    assert args[args.index("--plugin-dir") + 1] == str(REPO_ROOT / "plugin")
    assert args[args.index("--allowedTools") + 1] == ",".join(ALLOWED_TOOLS)
    assert args[args.index("--permission-mode") + 1] == "dontAsk"
    assert args[args.index("--permission-prompts") + 1] == "none"
    assert args[args.index("--append-system-prompt") + 1] == SYSTEM_PROMPT
    assert "--resume" not in args and "--model" not in args
    assert all(isinstance(a, str) for a in args)
    joined = " ".join(args)
    for forbidden in ("bypassPermissions", "--dangerously-skip-permissions", "--allow-dangerously-skip-permissions"):
        assert forbidden not in joined
    for tool in ("Bash", "Edit", "Write", "WebFetch", "WebSearch", "Read", "Glob", "Grep"):
        assert tool not in args[args.index("--allowedTools") + 1].split(",")
        assert args[args.index("--tools") + 1] != tool


def test_resume_and_model(tmp_path):
    args = argv(tmp_path, session_id="abc", model="claude-sonnet-5-5")
    assert args[args.index("--resume") + 1] == "abc"
    assert args[args.index("--model") + 1] == "claude-sonnet-5-5"


def test_only_the_forever_mcp_server(tmp_path):
    config = mcp_config(REPO_ROOT)
    assert list(config["mcpServers"]) == ["forever"]
    server = config["mcpServers"]["forever"]
    assert server["command"] == "uv"
    assert server["args"] == ["run", "--no-sync", "--quiet", "--project", str(REPO_ROOT), "forever", "mcp"]
    path = write_mcp_config(tmp_path, REPO_ROOT)
    assert json.loads(path.read_text(encoding="utf-8")) == config


def test_conversation_folder_is_outside_the_repository(tmp_path):
    folder = conversation_dir(tmp_path / "cache")
    assert folder == tmp_path / "cache" / "bridge" / "conversation"
    assert not folder.resolve().is_relative_to(REPO_ROOT.resolve())


def test_environment():
    env = claude_env(
        {"PATH": "x", "CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli", "FOREVER_OFFLINE": "0"}, REPO_ROOT
    )
    assert env["FOREVER_HOME"] == str(REPO_ROOT)
    assert env["FOREVER_OFFLINE"] == "1" and env["FOREVER_BRIDGE"] == "1"
    assert env["PATH"] == "x"
    assert "CLAUDECODE" not in env and "CLAUDE_CODE_ENTRYPOINT" not in env


def test_parse_the_real_status_stream():
    result = parse_stream(lines("claude_stream_status.jsonl"))
    assert result.text.startswith("Les données sont en version 1.60.1.70245")
    assert result.session_id == "00000000-0000-4000-8000-000000000003"
    assert [p["game_version"] for p in result.provenances] == ["1.60.1.70245"]
    assert result.denied == [] and not result.is_error and result.link is None
    assert result.tools == ["mcp__forever__forever_status"]


def test_parse_the_resumed_stream():
    result = parse_stream(lines("claude_stream_resume.jsonl"))
    assert result.text == "Fraîche." and result.provenances == []


def test_parse_a_denied_tool():
    result = parse_stream(lines("claude_stream_denied.jsonl"))
    assert result.denied == ["WebSearch"] and result.provenances == []


def test_parse_a_build_with_its_talents_forever_link():
    result = parse_stream(lines("claude_stream_build.jsonl"))
    assert result.link == "https://talents-forever.example/mage/20/--0530002001-klps-6"
    assert [p["certainty"] for p in result.provenances] == ["probable"]


def test_stream_without_result_is_an_error():
    result = parse_stream(lines("claude_stream_status.jsonl")[:-1])
    assert result.is_error and result.error


def test_provenance_line():
    probable = {"game_version": "1.60.1.70245", "certainty": "probable"}
    suppose = {"game_version": "1.60.1.70245", "certainty": "suppose"}
    certain = {"game_version": "1.60.1.70245", "certainty": "certain"}
    assert (
        provenance_line([probable, suppose, certain, probable]) == "Données 1.60.1.70245 · suppose, probable, certain"
    )
    assert provenance_line([]) == "Aucun outil forever appelé : réponse sans chiffre de jeu."


class FakeStdin(io.BytesIO):
    def close(self):
        self.sent = self.getvalue()
        super().close()


class FakePopen:
    """Faux processus : rend les lignes d'une fixture, ou bloque jusqu'à `kill` (`hang`)."""

    calls: list = []

    def __init__(self, stream_lines=(), *, hang=False):
        self.stream_lines = list(stream_lines)
        self.hang = hang

    def __call__(self, args, **kwargs):
        FakePopen.calls.append((args, kwargs))
        self.args, self.kwargs = args, kwargs
        self.stdin = FakeStdin()
        self.killed = threading.Event()
        self.pid = 0
        self.returncode = None
        if self.hang:
            self.stdout = self._hanging()
        else:
            self.stdout = io.BytesIO(("\n".join(self.stream_lines) + "\n").encode("utf-8"))
        self.stderr = io.BytesIO(b"")
        return self

    def _hanging(self):
        self.killed.wait(10)
        return
        yield b""

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed.set()
        self.returncode = -9


def test_run_claude_sends_the_question_on_stdin_only(tmp_path):
    popen = FakePopen(lines("claude_stream_status.jsonl"))
    args = argv(tmp_path)
    result = run_claude(args, QUESTION, cwd=tmp_path, env={"A": "1"}, popen=popen)
    assert result == parse_stream(lines("claude_stream_status.jsonl"))
    assert popen.args == args and isinstance(popen.args, list)
    assert QUESTION not in " ".join(popen.args)
    assert popen.stdin.sent == QUESTION.encode("utf-8")
    assert popen.kwargs.get("shell", False) is False
    assert popen.kwargs["cwd"] == tmp_path and popen.kwargs["env"] == {"A": "1"}


def test_run_claude_kills_after_the_delay(tmp_path):
    popen = FakePopen(hang=True)
    result = run_claude(argv(tmp_path), "Q", cwd=tmp_path, env={}, timeout_s=0.2, popen=popen)
    assert popen.killed.is_set()
    assert result.is_error and "délai dépassé (0.2 s)" in (result.error or "")


def test_ask_resumes_then_retries_without_a_lost_session(tmp_path):
    failed = [json.dumps({"type": "result", "is_error": True, "result": "No conversation found", "session_id": "x"})]

    class Sequence:
        def __init__(self):
            self.argvs = []
            self.popens = [FakePopen(failed), FakePopen(lines("claude_stream_resume.jsonl"))]

        def __call__(self, args, **kwargs):
            self.argvs.append(args)
            return self.popens[len(self.argvs) - 1](args, **kwargs)

    seq = Sequence()
    result = ask(
        "Q",
        session_id="perdue",
        claude="claude.exe",
        plugin_dir=REPO_ROOT / "plugin",
        mcp_path=tmp_path / "mcp.json",
        cwd=tmp_path,
        env={},
        popen=seq,
    )
    assert "--resume" in seq.argvs[0] and "--resume" not in seq.argvs[1]
    assert not result.is_error and result.text == "Fraîche."


def test_system_prompt_has_no_context_and_the_message_starts_with_it():
    record = Record("s1", 3, frozenset(), {"level": "19", "class": "MAGE", "zone": "Westfall"}, "Quel talent ?")
    text = message_text(record)
    assert text.startswith("Contexte du personnage")
    assert "level=19" in text and text.rstrip().endswith("Quel talent ?")
    assert "level=" not in SYSTEM_PROMPT and "Westfall" not in SYSTEM_PROMPT
    for rule in ("600 caractères", "##", "**", "Talents Forever", "anglais"):
        assert rule in SYSTEM_PROMPT


def test_agent_result_is_a_value():
    assert AgentResult(text="x", session_id=None) == AgentResult(text="x", session_id=None)


@pytest.mark.parametrize("name", ["claude_stream_status.jsonl", "claude_stream_build.jsonl"])
def test_fixtures_have_one_result(name):
    assert sum(1 for line in lines(name) if json.loads(line)["type"] == "result") == 1
