"""Corrections du contrôle des chiffres après le premier passage d'évaluation de T06 (docs/research/plugin-eval-T06.md) :
valeur négative d'un outil citée en valeur absolue (signe dit en mots), et rapport qui reprend le message du hook Stop.

Fixtures : tests/fixtures/transcripts/session_negative_values.jsonl, tests/fixtures/plugin_eval/aggregate_hook.json."""

import importlib.util
import json

from conftest import FIXTURES, REPO_ROOT

from forever import hooks


def test_negative_tool_value_is_a_source_for_its_magnitude():
    lines = hooks.read_transcript(FIXTURES / "transcripts" / "session_negative_values.jsonl")
    assert hooks.unsourced_numbers(lines) == []


def test_report_prefers_the_stop_hook_message():
    spec = importlib.util.spec_from_file_location("plugin_eval_report", REPO_ROOT / "scripts" / "plugin_eval_report.py")
    assert spec and spec.loader
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    path = FIXTURES / "plugin_eval" / "aggregate_hook.json"
    flagged = report.flagged_numbers(json.loads(path.read_text(encoding="utf-8")), path.parent)
    assert flagged == [{"case": "mage-x", "numbers": ["10 %", "31 points"]}]
