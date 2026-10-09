"""Mesure du temps de réponse (P06a, sonde en jeu E du 2026-10-09, point 7) : durées de chaque étape de la
conversation (démarrage de `claude` et du serveur MCP, chaque appel d'outil, réponse), coût, durée d'écriture de la
réserve, dans le journal du pont ; modèle de la conversation « jeu » réglable, Sonnet par défaut."""

import io
import json
import time

from conftest import FIXTURES
from forever.bridge.config import DEFAULT_MODEL, load_config, save_config
from test_bridge_loop import RECORD as LOOP_RECORD
from test_bridge_loop import FakeAgent, FakeCapture, band_of, events, make

from forever.bridge.agent import AgentResult, run_claude, stream_timings
from forever.cli import main

LINES = (FIXTURES / "bridge" / "claude_stream_status.jsonl").read_text(encoding="utf-8").splitlines()


def test_timings_of_the_real_stream():
    timed = [(10.0 + 0.5 * i, line) for i, line in enumerate(LINES)]
    t = stream_timings(timed, started=10.0)
    assert t["init_s"] == 1.0  # troisième événement : system/init (claude et serveur MCP prêts)
    assert [x["tool"] for x in t["tools"]] == ["mcp__forever__forever_status"]
    assert t["tools"][0]["seconds"] > 0
    assert t["result_s"] == 0.5 * (len(LINES) - 1)
    assert t["tools_s"] <= t["result_s"]


class SlowPopen:
    def __call__(self, args, **kwargs):
        self.stdin = io.BytesIO()
        self.stdin.close = lambda: None
        self.stderr = io.BytesIO(b"")
        self.returncode = 0
        self.pid = 0

        def lines():
            for line in LINES:
                time.sleep(0.01)
                yield (line + "\n").encode("utf-8")

        self.stdout = lines()
        return self

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


def test_run_claude_reports_timings_and_cost(tmp_path):
    result = run_claude(["claude.exe"], "Q", cwd=tmp_path, env={}, popen=SlowPopen())
    assert result.timings["result_s"] >= result.timings["init_s"] > 0
    assert result.cost_usd is not None and result.cost_usd >= 0


def test_journal_reply_carries_timings_and_publish_duration(tmp_path):
    timed = AgentResult(text="Réponse", session_id="s", timings={"init_s": 4.2, "result_s": 12.0}, cost_usd=0.03)
    bridge, _, _ = make(tmp_path, FakeCapture(band_of(LOOP_RECORD)), FakeAgent([timed]))
    bridge.step()
    reply = next(e for e in events(tmp_path) if e["event"] == "reply")
    assert reply["timings"]["init_s"] == 4.2 and reply["cost_usd"] == 0.03
    published = [e for e in events(tmp_path) if e["event"] == "published"]
    assert published and all("ms" in e for e in published)
    message = next(e for e in events(tmp_path) if e["event"] == "message")
    assert "capture_ms" in message


def test_model_is_configurable_and_sonnet_by_default(tmp_path):
    assert DEFAULT_MODEL == "sonnet"
    assert load_config(tmp_path)["model"] == "sonnet"
    save_config(tmp_path, {"model": "haiku"})
    assert load_config(tmp_path)["model"] == "haiku"
    assert json.loads((tmp_path / "bridge" / "config.json").read_text(encoding="utf-8"))["model"] == "haiku"


def test_cli_config_and_ask_use_the_configured_model(capsys, make_deps, monkeypatch):
    seen = []
    monkeypatch.setattr(
        "forever.bridge.agent.ask",
        lambda prompt, **kw: seen.append(kw["model"]) or AgentResult(text="ok", session_id=None),
    )
    monkeypatch.setattr("forever.bridge.agent.find_claude", lambda: "claude.exe")
    deps = make_deps()
    assert main(["bridge", "ask", "Q"], deps) == 0
    assert main(["bridge", "config", "--model", "haiku"], deps) == 0
    assert main(["bridge", "ask", "Q"], deps) == 0
    assert main(["bridge", "ask", "Q", "--model", "opus"], deps) == 0
    capsys.readouterr()
    assert seen == ["sonnet", "haiku", "opus"]
    assert main(["bridge", "config", "--json"], deps) == 0
    assert json.loads(capsys.readouterr()[0])["model"] == "haiku"
