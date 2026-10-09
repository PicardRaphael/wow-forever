"""Mise en forme restreinte des réponses (P06a, bloc B, décision 212 amendée le 2026-10-09) : seules les lignes
`## titre`, `- élément` et les passages `**en évidence**` restent ; le reste est converti ou retiré."""

import pytest
from forever.bridge.format import normalize_reply


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("# Titre", "## Titre"),
        ("### Titre", "## Titre"),
        ("## Titre", "## Titre"),
        ("* élément", "- élément"),
        ("+ élément", "- élément"),
        ("• élément", "- élément"),
        ("__important__", "**important**"),
        ("un *mot* en italique", "un mot en italique"),
        ("le sort `Frostbolt`", "le sort Frostbolt"),
        ("voir [Talents Forever](https://example.org/tf)", "voir Talents Forever"),
    ],
)
def test_conversions(raw, expected):
    assert normalize_reply(raw) == expected


def test_code_fences_and_tables():
    raw = "Avant\n```lua\nprint(1)\n```\n| Sort | Rang |\n| --- | --- |\n| Frostbolt | 3 |\nAprès"
    assert normalize_reply(raw) == "Avant\nprint(1)\nSort · Rang\nFrostbolt · 3\nAprès"


def test_conforming_text_is_unchanged():
    text = "## Prochain talent\n- **Improved Frostbolt** au niveau 20\n- puis Frostbite\n\nTexte simple."
    assert normalize_reply(text) == text


def test_blank_lines_and_trailing_spaces():
    assert normalize_reply("a  \n\n\n\nb\n") == "a\n\nb"
