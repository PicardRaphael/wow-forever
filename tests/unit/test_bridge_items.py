"""Objets, équipement complet et liens cités (P06b, bloc A, décision 235) : chaîne d'objet du lien (enchantement,
gemmes, suffixe aléatoire, identifiant unique), `gear` à la forme `emplacement=chaîne=nom` (ancienne forme de P06a
encore lue), liens et infobulles de `links` (fixture construite `links_constructed.txt`), message type en deux
parties au plus."""

import pytest
from conftest import FIXTURES

from forever.bridge.context import ContextData, resolve
from forever.bridge.fragments import split_payload
from forever.bridge.items import (
    LINE_SEP,
    LINK_SEP,
    GameLink,
    ItemString,
    links_lines,
    parse_gear,
    parse_item_string,
    parse_links,
)
from forever.bridge.record import Record, build_payload, parse_payload

LINKS = (FIXTURES / "bridge" / "links_constructed.txt").read_text(encoding="utf-8").strip("\n")


def test_item_string_fields():
    expected = ItemString(item=7909, enchant=1883, gems=(), suffix=-12, unique=1234567, link_level=19, bonus=())
    assert parse_item_string("item:7909:1883:0:0:0:0:-12:1234567:19") == expected
    assert parse_item_string("7909:1883:0:0:0:0:-12:1234567:19") == expected
    assert parse_item_string("7909:1883:::::-12:1234567:19:::::") == expected


def test_item_string_gems_bonus_and_short_forms():
    assert parse_item_string("2") == ItemString(item=2)
    assert parse_item_string("2:0") == ItemString(item=2)
    full = parse_item_string("7909:0:3001:0:0:0:0:0:19:0:0:0:2:1500:1501")
    assert full.gems == (3001,) and full.bonus == (1500, 1501) and full.link_level == 19
    for bad in ("", "abc", "7909:x", ":12"):
        with pytest.raises(ValueError):
            parse_item_string(bad)


def test_gear_new_and_old_forms():
    pieces, bad = parse_gear("16=7909:1883:0:0:0:0:-12:1234567=Sword of the Bear;1=2:0")
    assert bad == []
    assert [(p.slot, p.item.item, p.item.enchant, p.item.suffix, p.name) for p in pieces] == [
        (16, 7909, 1883, -12, "Sword of the Bear"),
        (1, 2, 0, 0, ""),
    ]
    assert pieces[0].chain == "7909:1883:0:0:0:0:-12:1234567"
    old, bad = parse_gear("16:7909:Sword;3:1769")
    assert bad == [] and [(p.slot, p.item.item, p.name) for p in old] == [(16, 7909, "Sword"), (3, 1769, "")]
    pieces, bad = parse_gear("16=abc;xx:yy;;5=23456=Robe")
    assert bad == ["16=abc", "xx:yy"] and [p.slot for p in pieces] == [5]


def test_context_reads_both_forms_and_reports_bad_items():
    data = ContextData(talents={}, level_cap=None, races={})
    r = resolve(data, {"class": "MAGE", "gear": "16=7909:1883:0:0:0:0:-12:1234567=Sword of the Bear;16=abc"})
    assert r.gear == [("16", 7909, "Sword of the Bear")]
    assert [(p.slot, p.item.suffix) for p in r.pieces] == [(16, -12)]
    assert [(d.kind, d.value) for d in r.defects] == [("objet", "16=abc")]
    assert "objet mal formé" in r.defects[0].reason


def test_links_with_their_tooltip():
    links = parse_links(LINKS)
    assert [(link.kind, link.name) for link in links] == [("item", "Sword of the Bear"), ("spell", "Frostbolt")]
    assert links[0].body == "item:7909:1883:0:0:0:0:-12:1234567:19"
    assert links[0].tooltip[0] == "Sword of the Bear" and len(links[0].tooltip) == 4
    assert links[1].body == "spell:116" and links[1].tooltip[-1] == "Launches a bolt of frost at the enemy."
    assert parse_links("") == []
    assert parse_links(LINK_SEP.join(["item:2" + LINE_SEP + "Nom", "", LINE_SEP])) == [
        GameLink("item", "item:2", "Nom")
    ]


def test_links_lines_for_the_conversation():
    lines = links_lines(parse_links(LINKS))
    assert len(lines) == 2
    assert lines[0].startswith("[Sword of the Bear] (objet item:7909:1883:0:0:0:0:-12:1234567:19)")
    assert "Binds when equipped" in lines[0] and " / " in lines[0]
    assert lines[1].startswith("[Frostbolt] (sort spell:116)")


def test_links_survive_the_record():
    record = Record("abcd1234", 3, frozenset(), {"level": "19", "links": LINKS}, "Compare [Sword of the Bear]")
    assert parse_payload(build_payload(record)).context["links"] == LINKS


def test_typical_message_fits_in_two_parts():
    talents = ",".join(f"{105000 + i}:3" for i in range(51))
    gear = ";".join(f"{slot}=20{slot:03d}:1883:0:0:0:0:-12:1234567:19={'N' * 60}" for slot in range(1, 20))
    record = Record(
        "6ac884ce31ab", 40, frozenset({"b=talents"}),
        {"name": "Jen", "realm": "Classic Beta PvE 2", "level": "19", "class": "MAGE", "race": "Orc",
         "faction": "Horde", "zone": "The Barrens", "subzone": "The Crossroads", "map": "1413", "talents": talents,
         "gear": gear, "client": "1.60.1.70338"},
        "é" * 255, slot=12,
    )  # fmt: skip
    parts = split_payload(build_payload(record), session=record.session, message_id=record.message_id)
    assert len(parts) == 2
