"""Hooks du plugin (T06, décision D4 précisée par l'utilisateur) : ligne de fraîcheur au démarrage (cache seulement,
seulement dans le dépôt) et contrôle des chiffres de jeu en fin de réponse (seulement si la session a utilisé forever).

Transcripts : tests/fixtures/transcripts/ (session réelle et trace d'évaluation du bloc A réduites et anonymisées,
cas synthétiques de même forme ; voir le README du dossier)."""

import importlib.util
import io
import json
import time
from datetime import timedelta

import pytest
from conftest import FIXTURES, LOCAL_VERSION, NOW, REGISTRY_PATH, REPO_ROOT, FakeHttp, tamper

from forever import hooks
from forever.cli import main
from forever.freshness import freshness_for_version
from forever.registry import coverage

TRANSCRIPTS = FIXTURES / "transcripts"
HOME = {"FOREVER_HOME": str(REPO_ROOT)}


def lines(name):
    return hooks.read_transcript(TRANSCRIPTS / name)


def last_text(name):
    texts = [
        b["text"]
        for x in lines(name)
        if x["type"] == "assistant"
        for b in x["message"]["content"]
        if b.get("type") == "text"
    ]
    return texts[-1]


def hook_input(name, **extra):
    return {"transcript_path": str(TRANSCRIPTS / name), "last_assistant_message": last_text(name), **extra}


def fresh_cache(make_deps, tmp_path):
    cache = tmp_path / "cache"
    freshness_for_version(
        make_deps(http=FakeHttp.fixture("builds_fresh.json"), now=NOW - timedelta(hours=3), cache_dir=cache),
        LOCAL_VERSION,
        allow_network=True,
    )
    return cache


# --- Ligne de fraîcheur -------------------------------------------------------------------------------------------


def test_session_line_on_repo_data(make_deps, tmp_path):
    http = FakeHttp.failing()
    line = hooks.session_line(make_deps(http=http, cache_dir=fresh_cache(make_deps, tmp_path)), HOME)
    assert "\n" not in line
    assert line.startswith("WoW Forever")
    assert LOCAL_VERSION in line
    assert "à jour" in line and "3 h" in line
    assert coverage(REGISTRY_PATH) in line
    assert "FOREVER_HOME" not in line
    assert http.calls == []


def test_session_line_empty_cache_says_what_to_do(make_deps):
    http = FakeHttp.failing()
    line = hooks.session_line(make_deps(http=http), HOME)
    assert "\n" not in line
    assert "inconnue" in line and "forever status" in line
    assert http.calls == []


def test_session_line_tampered_data(make_deps, data_copy):
    tamper(data_copy / LOCAL_VERSION / "spells.json")
    line = hooks.session_line(make_deps(data_dir=data_copy), HOME)
    assert "\n" not in line
    assert "altérées" in line and "forever status" in line


def test_session_line_without_forever_home(make_deps):
    line = hooks.session_line(make_deps(), {})
    assert "FOREVER_HOME" in line and "install_plugin.ps1" in line


def test_session_line_never_raises(make_deps, tmp_path):
    line = hooks.session_line(make_deps(data_dir=tmp_path / "absent"), HOME)
    assert "\n" not in line
    assert line.startswith("WoW Forever") and "forever status" in line


def test_session_line_is_fast(make_deps):
    start = time.perf_counter()
    hooks.session_line(make_deps(), HOME)
    assert time.perf_counter() - start < 2.0


def test_session_start_only_inside_the_repo(make_deps, tmp_path):
    deps = make_deps()
    assert hooks.session_start_output({"cwd": str(tmp_path)}, deps, HOME, repo_root=REPO_ROOT) is None
    assert hooks.session_start_output({}, deps, HOME, repo_root=REPO_ROOT) is None
    out = hooks.session_start_output({"cwd": str(REPO_ROOT / "docs")}, deps, HOME, repo_root=REPO_ROOT)
    assert out is not None
    line = hooks.session_line(deps, HOME)
    assert out["systemMessage"] == line
    assert out["hookSpecificOutput"] == {"hookEventName": "SessionStart", "additionalContext": line}


# --- Chiffres de jeu ------------------------------------------------------------------------------------------------


def test_game_numbers_pattern():
    text = "Il inflige 20 à 22 points de dégâts, coûte 25 de mana, se lance en 1,5 s, s'apprend au niveau 4 (rang 3/5)."
    found = hooks.game_numbers(text)
    assert [g.text for g in found] == ["20 à 22 points de dégâts", "25 de mana", "1,5 s"]
    assert found[0].values == (20.0, 22.0)
    assert found[2].values == (1.5,) and found[2].decimals == (1,)


def test_game_numbers_thousands_and_units():
    found = hooks.game_numbers("Environ 12 300 XP/h, 2,1 min par monstre, 5,2 % de critique, 30 mètres, 5 sorts.")
    assert [g.text for g in found] == ["12 300 XP/h", "2,1 min", "5,2 %", "30 mètres"]
    assert found[0].values == (12300.0,)


def test_check_script_uses_the_same_pattern():
    spec = importlib.util.spec_from_file_location("check_game_numbers", REPO_ROOT / "scripts" / "check_game_numbers.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.MOTIF is hooks.GAME_NUMBER


@pytest.mark.parametrize("name", ["session_sourced.jsonl", "eval_trace_sourced.jsonl"])
def test_numbers_from_forever_tools_are_sourced(name):
    assert hooks.session_used_forever(lines(name))
    assert hooks.unsourced_numbers(lines(name), last_text(name)) == []


def test_invented_number_is_reported():
    assert hooks.unsourced_numbers(lines("session_invented.jsonl"), last_text("session_invented.jsonl")) == [
        "18 à 20 points de dégâts",
        "5 secondes",
    ]


def test_other_tool_is_not_a_source():
    got = hooks.unsourced_numbers(lines("session_other_tool.jsonl"), last_text("session_other_tool.jsonl"))
    assert got == ["18 à 20 dégâts"]


def test_numbers_of_the_question_are_not_reported():
    got = hooks.unsourced_numbers(lines("session_user_numbers.jsonl"), last_text("session_user_numbers.jsonl"))
    assert got == []


def test_rounding_percent_minutes_and_decimal_separator():
    got = hooks.unsourced_numbers(lines("session_rounding.jsonl"), last_text("session_rounding.jsonl"))
    assert got == ["15 %"]


def test_sim_runner_result_is_a_source():
    got = hooks.unsourced_numbers(lines("session_sim_runner.jsonl"), last_text("session_sim_runner.jsonl"))
    assert got == []


def test_last_message_defaults_to_the_transcript():
    assert hooks.unsourced_numbers(lines("session_invented.jsonl")) == ["18 à 20 points de dégâts", "5 secondes"]


# --- Sortie du hook Stop ----------------------------------------------------------------------------------------------


def test_check_numbers_message_does_not_block():
    out = hooks.check_numbers_output(hook_input("session_invented.jsonl"))
    assert out is not None
    assert set(out) == {"systemMessage"}
    assert out["systemMessage"].startswith(hooks.NUMBERS_MARKER)
    assert "18 à 20 points de dégâts" in out["systemMessage"] and "5 secondes" in out["systemMessage"]


def test_check_numbers_silent_when_everything_is_sourced():
    assert hooks.check_numbers_output(hook_input("session_sourced.jsonl")) is None


def test_check_numbers_only_in_sessions_that_used_forever():
    # Session de travail sans outil ni skill forever : réponse avec un chiffre de jeu, aucun contrôle.
    assert not hooks.session_used_forever(lines("session_no_forever.jsonl"))
    assert hooks.check_numbers_output(hook_input("session_no_forever.jsonl")) is None


def test_check_numbers_missing_transcript_is_silent(tmp_path):
    assert hooks.check_numbers_output({"transcript_path": str(tmp_path / "absent.jsonl")}) is None
    assert hooks.check_numbers_output({}) is None


# --- Sous-commandes de la CLI ---------------------------------------------------------------------------------------


def run_hook(capsys, monkeypatch, argv, stdin, deps):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def test_cli_check_numbers(capsys, monkeypatch, make_deps):
    payload = json.dumps(hook_input("session_invented.jsonl"))
    code, out, _ = run_hook(capsys, monkeypatch, ["hook", "check-numbers"], payload, make_deps())
    assert code == 0
    assert json.loads(out)["systemMessage"].startswith(hooks.NUMBERS_MARKER)


def test_cli_check_numbers_prints_nothing_outside_forever(capsys, monkeypatch, make_deps):
    payload = json.dumps(hook_input("session_no_forever.jsonl"))
    code, out, _ = run_hook(capsys, monkeypatch, ["hook", "check-numbers"], payload, make_deps())
    assert code == 0 and out == ""


def test_cli_session_start_outside_the_repo_prints_nothing(capsys, monkeypatch, make_deps, tmp_path):
    payload = json.dumps({"cwd": str(tmp_path), "hook_event_name": "SessionStart"})
    code, out, _ = run_hook(capsys, monkeypatch, ["hook", "session-start"], payload, make_deps())
    assert code == 0 and out == ""


def test_cli_session_start_in_the_repo(capsys, monkeypatch, make_deps):
    payload = json.dumps({"cwd": str(REPO_ROOT), "hook_event_name": "SessionStart"})
    code, out, _ = run_hook(capsys, monkeypatch, ["hook", "session-start"], payload, make_deps())
    assert code == 0
    assert json.loads(out)["systemMessage"].startswith("WoW Forever")


@pytest.mark.parametrize("sub", ["session-start", "check-numbers"])
def test_cli_hook_bad_input_is_silent(capsys, monkeypatch, make_deps, sub):
    code, out, _ = run_hook(capsys, monkeypatch, ["hook", sub], "pas du JSON", make_deps())
    assert code == 0 and out == ""
