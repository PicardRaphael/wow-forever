"""FOREVER_HOME absent ou faux (demande de l'utilisateur avant la fusion de T06) : le serveur forever ne démarre pas
(le plugin installé est une copie hors du dépôt) ; le routeur le détecte et donne un message fixe qui dit quoi faire."""

import re

from conftest import REPO_ROOT

ROUTER = REPO_ROOT / "plugin" / "skills" / "forever-router" / "SKILL.md"


def section(text, title):
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert m, f"section « {title} » absente"
    return m.group(1)


def test_router_has_a_misinstall_section_before_the_domain_map():
    text = ROUTER.read_text(encoding="utf-8")
    body = section(text, "0. Plugin mal installé")
    assert text.index("## 0. Plugin mal installé") < text.index("## 2. Carte des domaines couverts")
    # détection : outils du serveur introuvables par ToolSearch, ou serveur en échec
    assert "ToolSearch" in body and "mcp__plugin_forever_forever__" in body


def test_misinstall_message_says_what_to_do():
    body = section(ROUTER.read_text(encoding="utf-8"), "0. Plugin mal installé")
    m = re.search(r"^> (.+)$", body, re.MULTILINE)
    assert m, "message fixe (ligne de citation) absent"
    message = m.group(1)
    for needle in (
        "FOREVER_HOME",
        r"powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1",
        "nouveau terminal",
    ):
        assert needle in message, needle
    assert "de mémoire" in body  # ne pas répondre à la question de mémoire
