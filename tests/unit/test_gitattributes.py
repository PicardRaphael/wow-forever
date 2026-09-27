"""Fins de ligne normalisées par Git (T04c, bloc A) : texte en LF, chemins `-text` intouchés."""

import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BINARY_PATHS = ("forever/data/", "seed/forever-mage/data/", "tests/fixtures/")


def _rules() -> list[str]:
    lines = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def test_first_rule_normalises_text_to_lf():
    assert _rules()[0] == "* text=auto eol=lf"


def test_byte_stable_paths_stay_outside_normalisation():
    rules = _rules()
    for prefix in BINARY_PATHS:
        rule = f"{prefix}** -text"
        assert rule in rules
        assert rules.index(rule) > 0  # après la règle générale : elle l'emporte


@pytest.mark.skipif(shutil.which("git") is None, reason="git absent")
def test_no_crlf_in_index_outside_byte_stable_paths():
    out = subprocess.run(["git", "ls-files", "--eol"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    offenders = []
    for line in out.splitlines():
        info, _, path = line.partition("\t")
        if path.startswith(BINARY_PATHS):
            continue
        if "i/crlf" in info or "i/mixed" in info:
            offenders.append(path)
    assert offenders == []
