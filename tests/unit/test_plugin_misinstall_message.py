"""Message « plugin mal installé » accessible depuis tous les skills (relevé en réel avant la fusion de T06 : avec un
FOREVER_HOME faux, le modèle chargé par forever-mage n'avait pas lu la règle du routeur et proposait « /mcp »)."""

import re

from conftest import REPO_ROOT

SKILLS = REPO_ROOT / "plugin" / "skills"


def fixed_message(path):
    m = re.search(r"^> (Le serveur forever ne répond pas : .+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    assert m, f"message fixe absent de {path}"
    return m.group(1)


def test_response_format_carries_the_same_message_as_the_router():
    router = fixed_message(SKILLS / "forever-router" / "SKILL.md")
    assert fixed_message(SKILLS / "forever-router" / "format-reponse.md") == router


def test_domain_skills_check_the_tools_first():
    for name in ("forever-leveling", "forever-mage"):
        text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        head = text.split("\n## ", 1)[0]  # avant la première section
        assert "Plugin mal installé" in head, name
