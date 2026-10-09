"""Crédits de wow-ai (P06a, bloc F) : chaque fichier qui reprend du code de wow-ai (liste fermée) porte la notice MIT
complète ; `docs/ADDON.md` et `docs/VISION.md` citent le dépôt et son commit. wow-forever-codex, sans licence, n'est
cité que comme source de mesures : aucun fichier ne s'en réclame."""

import pytest
from conftest import REPO_ROOT

REUSED = (
    "forever/bridge/codec.py",
    "forever/bridge/capture.py",
    "forever/bridge/record.py",
    "forever/bridge/slots.py",
    "forever/bridge/install.py",
    "addon/ForeverBridge/Codec.lua",
    "addon/ForeverBridge/ForeverBridge.lua",
)
NOTICE = (
    "Copyright (c) 2026 chelinho139",
    "Permission is hereby granted, free of charge",
    'THE SOFTWARE IS PROVIDED "AS IS"',
    "https://github.com/chelinho139/wow-ai",
    "3756eb5a",
)


@pytest.mark.parametrize("path", REUSED)
def test_reused_files_carry_the_mit_notice(path):
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    for line in NOTICE:
        assert line in text, (path, line)


def test_the_list_is_closed():
    found = {
        str(p.relative_to(REPO_ROOT).as_posix())
        for root in ("forever", "addon")
        for p in (REPO_ROOT / root).rglob("*")
        if p.suffix in {".py", ".lua"} and "chelinho139" in p.read_text(encoding="utf-8", errors="ignore")
    }
    assert found == set(REUSED)


@pytest.mark.parametrize("doc", ["docs/ADDON.md", "docs/VISION.md"])
def test_docs_credit_wow_ai(doc):
    text = (REPO_ROOT / doc).read_text(encoding="utf-8")
    assert "chelinho139/wow-ai" in text and "3756eb5a" in text and "MIT" in text


def test_no_code_claims_wow_forever_codex():
    for root in ("forever", "addon"):
        for p in (REPO_ROOT / root).rglob("*"):
            if p.suffix in {".py", ".lua"}:
                assert "wow-forever-codex" not in p.read_text(encoding="utf-8", errors="ignore"), p
