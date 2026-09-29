"""Entrée du hook lue en UTF-8 quel que soit l'encodage local (relecture de T06) : sous Windows sans PYTHONUTF8,
sys.stdin décode en cp1252 et « dégâts », « à » échappaient au contrôle des chiffres.

Fixture : tests/fixtures/transcripts/session_sourced.jsonl (Frostbolt rang 1, 20 à 22 dégâts)."""

import json
import os
import subprocess
import sys

from conftest import FIXTURES, REPO_ROOT


def test_check_numbers_reads_utf8_stdin_without_pythonutf8():
    payload = {
        "transcript_path": str(FIXTURES / "transcripts" / "session_sourced.jsonl"),
        "last_assistant_message": "Frostbolt fait 18 à 999 dégâts.",
    }
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env["PYTHONUTF8"] = "0"
    out = subprocess.run(
        [sys.executable, "-m", "forever.cli", "hook", "check-numbers"],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        cwd=REPO_ROOT,
        env=env,
        check=True,
    ).stdout.decode("utf-8")
    assert "« 18 à 999 dégâts »" in json.loads(out)["systemMessage"]
