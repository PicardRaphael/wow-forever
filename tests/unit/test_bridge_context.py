"""Talents envoyés par le jeu reliés aux clés de forever (P06a, sonde en jeu E du 2026-10-09, point 1) : le jeu envoie
les identifiants de nœud (`C_Traits`), que `classes.json` relie aux talents (tables TraitNode et TraitNodeEntry du
client) ; contexte réel de la sonde."""

from conftest import FIXTURES
from forever.bridge.context import describe_talents, talent_table, talents_line

from forever.bridge.prompt import message_text
from forever.bridge.record import Record, parse_payload

REAL = (FIXTURES / "bridge" / "context_sonde_e.txt").read_text(encoding="utf-8")


def real_context() -> dict[str, str]:
    return dict(line.split("=", 1) for line in REAL.splitlines() if "=" in line)


def test_real_talents_of_the_probe_are_recognized(make_deps):
    table = talent_table(make_deps())
    reading = describe_talents(table, "MAGE", real_context()["talents"])
    assert [(t.key, t.rank, t.max) for t in reading.known] == [
        ("elementalPrecision", 5, 5),
        ("improvedFrostbolt", 5, 5),
    ]
    assert [t.name for t in reading.known] == ["Elemental Precision", "Improved Frostbolt"]
    assert reading.unknown == []
    assert talents_line(reading) == (
        "elementalPrecision:5 (Elemental Precision 5/5), improvedFrostbolt:5 (Improved Frostbolt 5/5)"
    )


def test_unknown_nodes_and_other_classes(make_deps):
    table = talent_table(make_deps())
    reading = describe_talents(table, "MAGE", "105779:3,999999:2,abc")
    assert [t.key for t in reading.known] == ["improvedFrostbolt"]
    assert reading.unknown == ["999999:2", "abc"]
    assert "nœuds non reconnus : 999999:2, abc" in talents_line(reading)
    assert describe_talents(table, "WARLOCK", "").known == []
    assert {"MAGE", "WARLOCK", "HUNTER", "PALADIN", "PRIEST", "ROGUE", "SHAMAN", "WARRIOR", "DRUID"} <= set(table)
    assert describe_talents(table, "UNKNOWN", "105779:3").unknown == ["105779:3"]


def test_message_gives_the_keys_for_forever_build(make_deps):
    record = Record("6ac884ce31ab", 4, frozenset({"b=talents"}), real_context(), "Quel est mon prochain talent ?")
    table = talent_table(make_deps())
    text = message_text(record, talents=talents_line(describe_talents(table, "MAGE", record.context["talents"])))
    assert "talents=105778:5,105779:5" in text
    assert "Talents actuels (clés de forever, pour `current` de forever_build) : elementalPrecision:5" in text
    assert "race=Orc" in text and text.rstrip().endswith("Quel est mon prochain talent ?")


def test_real_context_survives_the_band():
    from forever.bridge.record import build_payload

    record = Record("6ac884ce31ab", 4, frozenset(), real_context(), "Q ?", slot=13)
    assert parse_payload(build_payload(record)).context == real_context()
