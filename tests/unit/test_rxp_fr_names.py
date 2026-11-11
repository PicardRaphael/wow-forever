"""FR1 : noms officiels français, par ordre de priorité (glossaire tiré des guides que RestedXP a traduits, tables
frFR du client, Questie frFR) ; un nom sans source reste en anglais et figure au rapport ; jamais inventé.

Valeurs : tables et addons inventés pour le test (`tests/fixtures/rxp_fr/`)."""

from pathlib import Path

from forever.rxp_fr.names import NameTable, client_layer, questie_layer, unique_map
from forever.rxp_fr.source import glossary

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "rxp_fr"
ADDONS = FIX / "AddOns"


def _table() -> NameTable:
    rxp = glossary(ADDONS)
    return NameTable(
        [
            ("restedxp", rxp.names),
            ("client", client_layer(FIX / "wago")),
            ("questie", questie_layer(ADDONS / "Questie")),
        ]
    )


def test_restedxp_glossary_wins_over_questie():
    names = _table()
    found = names.lookup("npc", "Brin Oakvale")
    assert found is not None and found.fr == "Brin Chênevaux" and found.source == "restedxp"
    quest = names.lookup("quest", 90001)
    assert quest is not None and quest.fr == "Un nouveau départ" and quest.source == "restedxp"


def test_npc_by_id_from_the_glossary():
    found = _table().lookup("npc", 900001)
    assert found is not None and found.fr == "Brin Chênevaux"


def test_client_tables_then_questie():
    names = _table()
    spell = names.lookup("spell", "Frost Spark")
    assert spell is not None and spell.fr == "Étincelle de givre" and spell.source == "client"
    item = names.lookup("item", "Boar Tusk")
    assert item is not None and item.source == "client"  # ItemSparse frFR avant Questie
    reed = names.lookup("item", "Marsh Reed")
    assert reed is not None and reed.fr == "Roseau des marais" and reed.source == "questie"
    crate = names.lookup("object", "Old Crate")
    assert crate is not None and crate.fr == "Vieille caisse"


def test_an_ambiguous_english_name_is_never_chosen():
    assert _table().lookup("zone", "Twin Hollow") is None
    assert unique_map([("a", "x"), ("a", "y"), ("b", "z"), ("b", "z")]) == {"b": "z"}


def test_a_missing_name_stays_english_and_is_reported():
    names = _table()
    assert names.lookup("npc", "Marsh Lurkers") is None
    assert ("npc", "Marsh Lurkers") in names.missing


def test_guide_names_and_titles_come_from_the_paired_headers():
    rxp = glossary(ADDONS)
    assert rxp.names["guide"]["10-12 Test Marsh"] == "10-12 Marais d’Essai"
    assert rxp.names["guide"]["5-10 Testing Isle"] == "5-10 Île d’Essai"
    assert rxp.phrases["titre|Speedrun Guide {1}-{2}"] == "Guide Speedrun {1}-{2}"
    assert rxp.phrases["titre|Test Forever Guide (A)"] == "Guide Test Forever (A)"


def test_phrases_of_the_glossary_keep_the_english_slot_numbers():
    rxp = glossary(ADDONS)
    assert rxp.phrases["{1}Talk to {2}"] == "{1}Parlez à {2}"
    assert rxp.phrases["Kill {1}. Loot them for their {2}"] == "Tuez les {1}. Dépouillez-les pour leurs {2}"
    assert rxp.phrases["Travel to Test Marsh"] == "Allez jusqu'au Marais d’Essai"


def test_a_name_with_brackets_or_codes_is_never_used():
    """Le client a des noms de développement (« [UNUSED] … ») : entre crochets ils donneraient `[[`, que le Lua 5.1
    du jeu refuse dans une chaîne longue (fichier entier rejeté, essai du 2026-11-11)."""
    assert unique_map([("Vial", "[INUTILISÉ] Fiole"), ("Ale", "Bière |cff00|r"), ("Bread", "Pain")]) == {
        "Bread": "Pain"
    }
    table = NameTable([("client", {"item": {"Vial": "[INUTILISÉ] Fiole"}})])
    assert table.lookup("item", "Vial") is None
