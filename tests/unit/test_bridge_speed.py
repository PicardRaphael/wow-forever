"""Mesure des accélérations de la conversation « jeu » (P06b, bloc G, décision 235) : variantes A (ligne actuelle),
B (réflexion coupée, `MAX_THINKING_TOKENS=0`), C (session `claude` gardée ouverte, `--input-format stream-json`),
D (B et C) ; critères de qualité automatiques écrits avant la mesure ; règle de décision ; session gardée ouverte sur
un faux processus (forme du flux relevée par la sonde 0.3 du 2026-10-10, `claude_stream_persistent.jsonl`) ;
réglages `forever bridge config --thinking --persistent`. Aucun `claude` réel."""

import json
import queue

import pytest
from conftest import FIXTURES

from forever.bridge.agent import AgentResult, PersistentSession, claude_argv, parse_stream
from forever.bridge.plans import Call, Plan
from forever.bridge.speed import VARIANTS, keep, quality_failures, variant_env

PERSISTENT = FIXTURES / "bridge" / "claude_stream_persistent.jsonl"


# --- Règle de décision --------------------------------------------------------------------------------------------


def test_keep():
    assert keep([20.0, 18.0, 22.0], [15.0, 16.0, 17.0], 0)
    assert not keep([20.0, 18.0, 22.0], [15.0, 16.0, 17.0], 1)
    assert not keep([20.0, 18.0, 22.0], [19.5, 17.8, 21.6], 0)
    assert keep([10.0, 10.0, 10.0], [8.4, 8.5, 8.6], 0)  # 15 % de moins, moins de 2 s
    assert not keep([10.0, 10.0, 10.0], [8.7, 8.7, 8.7], 0)


# --- Critères de qualité ------------------------------------------------------------------------------------------

PLAN = Plan("talents", (Call("forever_build", {"level": 20, "current": "a=5"}),), ("lecture",), link="projected")


def result(text="Réponse courte.", calls=(("forever_build", {"level": 20, "current": "a=5"}),), link="L",
           provenances=({"game_version": "1.60.1.70338", "certainty": "probable"},), **extra):  # fmt: skip
    return AgentResult(
        text=text, session_id="s", provenances=list(provenances), links={"projected": link} if link else {},
        tools=[f"mcp__forever__{name}" for name, _ in calls],
        calls=[(f"mcp__forever__{name}", dict(args)) for name, args in calls], **extra,
    )  # fmt: skip


def test_a_clean_answer_has_no_failure():
    assert quality_failures(result(), PLAN, "L") == []


def test_quality_failures():
    assert "appel hors consigne" in quality_failures(result(calls=(("forever_lookup", {"kind": "spell"}),)), PLAN, "L")
    assert "appel hors consigne" in quality_failures(result(calls=(("forever_build", {"level": 21}),)), PLAN, "L")
    assert "lien changé" in quality_failures(result(link="M"), PLAN, "L")
    assert "réponse trop longue" in quality_failures(result(text="x" * 601), PLAN, "L")
    assert "réponse trop longue" not in quality_failures(result(text="**" + "x" * 600 + "**"), PLAN, "L")
    assert "provenance absente" in quality_failures(result(provenances=()), PLAN, "L")
    assert "erreur" in quality_failures(result(is_error=True, error="délai dépassé"), PLAN, "L")


def test_free_question_without_plan():
    free = result(calls=(("forever_lookup", {"kind": "spell", "name": "frostbolt"}),), link=None)
    assert quality_failures(free, None, None) == []


def test_unsourced_game_number_is_a_failure():
    events = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "mcp__forever__forever_lookup",
                                                       "input": {"kind": "spell"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                  "content": json.dumps({"damage": 42, "provenance": {}})}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Frostbolt fait 57 points de dégâts."}]}},
        {"type": "result", "result": "Frostbolt fait 57 points de dégâts.", "session_id": "s"},
    ]  # fmt: skip
    parsed = parse_stream(json.dumps(e) for e in events)
    assert parsed.calls == [("mcp__forever__forever_lookup", {"kind": "spell"})]
    assert "chiffre hors des résultats d'outil" in quality_failures(parsed, None, None)
    sourced = [*events[:2], {"type": "result", "result": "Frostbolt fait 42 points de dégâts.", "session_id": "s"}]
    assert "chiffre hors des résultats d'outil" not in quality_failures(
        parse_stream(json.dumps(e) for e in sourced), None, None
    )


# --- Variantes ----------------------------------------------------------------------------------------------------


def test_variants():
    assert set(VARIANTS) == {"A", "B", "C", "D"}
    assert (VARIANTS["A"].thinking_off, VARIANTS["A"].persistent) == (False, False)
    assert (VARIANTS["B"].thinking_off, VARIANTS["B"].persistent) == (True, False)
    assert (VARIANTS["C"].thinking_off, VARIANTS["C"].persistent) == (False, True)
    assert (VARIANTS["D"].thinking_off, VARIANTS["D"].persistent) == (True, True)
    base = {"PATH": "x", "MAX_THINKING_TOKENS": "8000"}
    assert "MAX_THINKING_TOKENS" not in variant_env(base, VARIANTS["A"])
    assert variant_env(base, VARIANTS["B"])["MAX_THINKING_TOKENS"] == "0"
    assert variant_env(base, VARIANTS["D"])["PATH"] == "x"


def test_input_stream_argv(tmp_path):
    argv = claude_argv(claude="claude", plugin_dir=tmp_path, mcp_config=tmp_path / "m.json", system_prompt="s",
                       input_stream=True)  # fmt: skip
    assert argv[argv.index("--input-format") + 1] == "stream-json"
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert "--input-format" not in claude_argv(claude="claude", plugin_dir=tmp_path, mcp_config=tmp_path / "m.json",
                                               system_prompt="s")  # fmt: skip


# --- Session gardée ouverte ---------------------------------------------------------------------------------------


def turns_of_the_probe():
    """Lignes de la sonde 0.3 découpées en tours (un `result` par message écrit)."""
    out, current = [], []
    for line in PERSISTENT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        current.append(line)
        if json.loads(line).get("type") == "result":
            out.append(current)
            current = []
    return out


class FakeProc:
    """Faux `claude --input-format stream-json` : à chaque message lu sur l'entrée, il écrit le tour suivant ; il
    garde les messages reçus. `hang` : ne répond jamais (délai dépassé)."""

    started = 0

    def __init__(self, argv, turns, hang=False):
        FakeProc.started += 1
        self.argv = argv
        self.turns = list(turns)
        self.hang = hang
        self.received: list[dict] = []
        self.out: queue.Queue = queue.Queue()
        self.killed = False
        self.stdin = self
        self.stdout = iter(self.out.get, None)
        self.stderr = None
        self.returncode = None

    def write(self, data):
        self.received.append(json.loads(data.decode("utf-8")))
        if not self.hang and self.turns:
            for line in self.turns.pop(0):
                self.out.put((line + "\n").encode("utf-8"))

    def flush(self):
        pass

    def close(self):
        self.out.put(None)

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        self.out.put(None)

    def wait(self, timeout=None):
        return self.returncode


@pytest.fixture
def procs():
    made: list[FakeProc] = []
    return made


def session(procs, *, hang=False, clock=None, timeout_s=5.0):
    turns = turns_of_the_probe()
    assert len(turns) == 2

    def popen(argv, **kwargs):
        proc = FakeProc(argv, turns * 3, hang=hang)
        procs.append(proc)
        return proc

    return PersistentSession(lambda resume: ["claude", "--input-format", "stream-json"] + (["--resume", resume] if resume else []),
                             cwd=".", env={}, popen=popen, timeout_s=timeout_s,
                             clock=clock or (lambda: 0.0))  # fmt: skip


def test_two_messages_in_one_process(procs):
    s = session(procs)
    first = s.ask("Quelle est la version des données ?", new=True)
    second = s.ask("Et la fraîcheur ?")
    assert len(procs) == 1
    assert [m["message"]["content"] for m in procs[0].received] == ["Quelle est la version des données ?",
                                                                     "Et la fraîcheur ?"]  # fmt: skip
    assert procs[0].received[0] == {
        "type": "user",
        "message": {"role": "user", "content": procs[0].received[0]["message"]["content"]},
    }
    assert not first.is_error and not second.is_error
    assert first.text.startswith("Version des données") and second.session_id == first.session_id
    assert second.cost_usd is not None and second.cost_usd < first.cost_usd  # coût du seul tour (cumul du processus)
    s.close()


def test_new_conversation_and_idle_restart_the_process(procs):
    now = {"t": 0.0}
    s = session(procs, clock=lambda: now["t"])
    s.ask("Un", new=True)
    s.ask("Deux", new=True)
    assert len(procs) == 2 and procs[0].killed
    now["t"] += 16 * 60
    s.ask("Trois")
    assert len(procs) == 3 and "--resume" in procs[2].argv


def test_timeout_restarts_on_the_next_message(procs):
    s = session(procs, hang=True, timeout_s=0.2)
    hung = s.ask("Un", new=True)
    assert hung.is_error and "délai dépassé" in hung.error and procs[0].killed
    s2 = session(procs)
    assert not s2.ask("Deux", new=True).is_error


def test_bridge_config_thinking_and_persistent(make_deps, capsys):
    from forever.bridge.config import load_config
    from forever.cli import main

    deps = make_deps()
    assert load_config(deps.cache_dir)["thinking"] == "on" and load_config(deps.cache_dir)["persistent"] == "off"
    assert main(["bridge", "config", "--thinking", "off", "--persistent", "on", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert (payload["thinking"], payload["persistent"], payload["model"]) == ("off", "on", "sonnet")
    assert main(["bridge", "config"], deps) == 0
    out = capsys.readouterr()[0]
    assert "réflexion : off" in out and "session gardée ouverte : on" in out


def test_close_stops_the_process(procs):
    s = session(procs)
    s.ask("Un", new=True)
    s.close()
    assert procs[0].killed or procs[0].returncode is not None
