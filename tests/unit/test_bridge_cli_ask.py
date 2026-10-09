"""`forever bridge ask "question"` (P06a, préparation de la sonde E) : même conversation « jeu » que le pont, sans le
jeu, en nouvelle session ; réponse mise en forme et ligne de provenance. `claude` simulé."""

import json

from forever.bridge.agent import AgentResult
from forever.cli import main


def test_ask_runs_the_game_conversation_once(capsys, make_deps, monkeypatch):
    calls = []

    def fake_ask(prompt, **kwargs):
        calls.append((prompt, kwargs))
        return AgentResult(
            text="# Titre\n* élément",
            session_id="s",
            provenances=[{"game_version": "1.60.1.70245", "certainty": "probable"}],
            link="https://talents-forever.example/x",
        )

    monkeypatch.setattr("forever.bridge.agent.ask", fake_ask)
    monkeypatch.setattr("forever.bridge.agent.find_claude", lambda: "claude.exe")
    deps = make_deps()
    code = main(["bridge", "ask", "Quelle est la version des données ?"], deps)
    out, _ = capsys.readouterr()
    assert code == 0 and len(calls) == 1
    prompt, kwargs = calls[0]
    assert prompt.rstrip().endswith("Quelle est la version des données ?")
    assert kwargs["session_id"] is None
    assert kwargs["cwd"] == deps.cache_dir / "bridge" / "conversation"
    assert "## Titre" in out and "- élément" in out
    assert "Données 1.60.1.70245 · probable" in out and "https://talents-forever.example/x" in out
    code = main(["bridge", "ask", "Q", "--json"], deps)
    payload = json.loads(capsys.readouterr()[0])
    assert payload["text"] == "## Titre\n- élément" and "provenance" in payload


def test_ask_reports_an_error(capsys, make_deps, monkeypatch):
    monkeypatch.setattr(
        "forever.bridge.agent.ask",
        lambda prompt, **kw: AgentResult(text="", session_id=None, is_error=True, error="délai dépassé (180 s)"),
    )
    monkeypatch.setattr("forever.bridge.agent.find_claude", lambda: "claude.exe")
    code = main(["bridge", "ask", "Q"], make_deps())
    out, _ = capsys.readouterr()
    assert code != 0 and "délai dépassé" in out
