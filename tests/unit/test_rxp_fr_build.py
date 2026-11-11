"""FR1 : assemblage du fichier français (garde-fou en première ligne, marqueur FR1, guides traduits par RestedXP
recopiés tels quels, autres guides générés ligne à ligne, CRLF) et validateur bloquant (commandes, identifiants,
coordonnées et filtres intacts, aucun `]]`, codes couleur équilibrés, `#next` résolus) ; rien n'est écrit sur échec.

Valeurs : mini-addon inventé pour le test (`tests/fixtures/rxp_fr/`)."""

import shutil
from pathlib import Path

import pytest
from forever.rxp_fr.build import GUARD, MARKER, generate_file
from forever.rxp_fr.memory import Memory
from forever.rxp_fr.names import NameTable, client_layer, questie_layer
from forever.rxp_fr.run import translate_addons
from forever.rxp_fr.source import glossary, targets
from forever.rxp_fr.validate import validate_file

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "rxp_fr"
ADDONS = FIX / "AddOns"
EN = ADDONS / "RXPGuides" / "Guides" / "Forever" / "Test-Isle.lua"
FR = ADDONS / "RXPGuides" / "lang" / "Guides-frFR" / "forever" / "Test-Isle.lua"


class Fake:
    """Traducteur factice : préfixe « FR » (garde les jetons)."""

    def __init__(self, broken: str | None = None) -> None:
        self.broken = broken

    def translate(self, items):
        return {p: (self.broken if self.broken and "boat" in p else "FR " + p) for p in items}


def _generate(translator=None):
    rxp = glossary(ADDONS)
    mem = Memory()
    for en, fr in rxp.phrases.items():
        mem.put(en, fr, "restedxp", date="2026-11-11")
    names = NameTable(
        [
            ("restedxp", rxp.names),
            ("client", client_layer(FIX / "wago")),
            ("questie", questie_layer(ADDONS / "Questie")),
        ]
    )
    english = EN.read_bytes().decode("utf-8")
    french = FR.read_bytes().decode("utf-8")
    text, report = generate_file(
        english, french, names=names, memory=mem, translator=translator, meta={"rxp_version": "v9.9.9-test"}
    )
    return english, text, report, rxp


def test_only_files_with_missing_french_guides_are_targets():
    assert [t.rel for t in targets(ADDONS)] == ["Test-Isle.lua"]


def test_guard_marker_and_crlf():
    english, text, _, _ = _generate(Fake())
    lines = text.split("\r\n")
    assert lines[0] == GUARD
    assert lines[1].startswith(MARKER)
    assert "\n" not in text.replace("\r\n", "")
    assert "enabledLocale" not in text  # garde anglaise retirée : le fichier ne sort pas en frFR


def test_restedxp_guides_are_copied_and_the_others_generated():
    _, text, report, _ = _generate(Fake())
    assert report.copied == 1 and report.generated == 2
    assert "#name 1-5 Île d’Essai" in text and ">>Acceptez la quête Un nouveau départ" in text
    assert "#name 5-10 Île d’Essai" in text
    assert "#next 10-12 Marais d’Essai" in text
    assert "#group RestedXP Guide Forever (A) << Alliance" in text
    assert "#subgroup Guide Speedrun 1-20 << Alliance" in text


def test_generated_lines_follow_the_rules():
    _, text, _, _ = _generate(Fake())
    assert "    >>Parlez à |cRXP_FRIENDLY_Brin Chênevaux|r" in text
    assert "    .turnin 90001 >>Rendez la quête Un nouveau départ" in text
    assert "    .accept 90002 >>Acceptez la quête Des défenses pour Brin" in text
    assert "    .target Brin Chênevaux" in text  # nom sans identifiant : traduit (Q2)
    assert "    .train 9133 >>Apprenez |T135846:0|t[Étincelle de givre]" in text
    assert "    .zone Test Marsh >>Allez jusqu'au Marais d’Essai" in text  # argument de .zone gardé
    assert "    *FR |cRXP_WARN_Wait for the boat at the dock|r" in text
    assert "    +FR |cRXP_WARN_Keep 5 silver for the boat|r << Alliance" in text
    assert "    .mob Marsh Lurker,Bog Crawler::900010" in text  # nom inconnu et nom à identifiant intacts


def test_without_translator_new_phrases_stay_english_and_are_reported():
    _, text, report, _ = _generate(None)
    assert "    *|cRXP_WARN_Wait for the boat at the dock|r" in text
    assert "|cRXP_WARN_Wait for the boat at the dock|r" in report.missing_phrases
    assert ("npc", "Marsh Lurkers") in report.missing_names
    assert report.phrases["anglais"] >= 1 and report.phrases["restedxp"] >= 1


def test_the_validator_accepts_the_generated_file():
    english, text, _, _ = _generate(Fake())
    assert validate_file(english, text, known_names=set()) == []


@pytest.mark.parametrize(
    ("old", "new", "word"),
    [
        (".accept 90002 >>", ".accept 90003 >>", "commande"),
        ("Brin Chênevaux|r\r\n    .turnin", "Brin Chênevaux]]|r\r\n    .turnin", "]]"),
        ("|cRXP_WARN_Wait for the boat at the dock|r", "|cRXP_WARN_Wait for the boat at the dock", "couleur"),
        ("    .goto 9001,41.50,22.70", "    .goto 9001,41.50,22.71", "commande"),
        (
            "+FR |cRXP_WARN_Keep 5 silver for the boat|r << Alliance",
            "+FR |cRXP_WARN_Keep 5 silver|r << Horde",
            "filtre",
        ),
    ],
)
def test_the_validator_refuses_a_broken_line(old, new, word):
    english, text, _, _ = _generate(Fake())
    assert old in text
    errors = validate_file(english, text.replace(old, new, 1), known_names=set())
    assert errors and any(word in e for e in errors)


def test_an_unresolved_next_is_refused():
    english, text, _, _ = _generate(Fake())
    broken = text.replace("#next 10-12 Marais d’Essai", "#next 10-12 Nulle part", 1)
    errors = validate_file(english, broken, known_names=set())
    assert any("#next" in e for e in errors)


def test_nothing_is_written_when_validation_fails(make_deps, tmp_path):
    wow = tmp_path / "wow"
    shutil.copytree(ADDONS, wow / "Interface" / "AddOns")
    shutil.copytree(FIX / "wago", tmp_path / "cache" / "wago" / "1.0.0.1")
    deps = make_deps(wow_dir=wow)
    target = wow / "Interface" / "AddOns" / "RXPGuides" / "lang" / "Guides-frFR" / "forever" / "Test-Isle.lua"
    before = target.read_bytes()
    doc = translate_addons(deps, translator=Fake(broken="]] {1}"))
    assert doc["written"] == [] and doc["errors"]
    assert target.read_bytes() == before
