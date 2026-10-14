"""Suites de la relecture d'EX1 : refus en français d'une chaîne trop imbriquée (avant toute récursion), profil de
base EllesmereUI aux tables vides gardé tel quel, octets non UTF-8 et clés booléennes recopiés à l'identique,
bonus Legacy « Talented » transmis au code Naowh, lien typé « closest » sans repli sur un autre build.

Valeurs : fixtures de FA1 (`mage_builds.json`), données installées (`classes.json`, points par niveau du moteur) ;
octets et tables synthétiques."""

import json

import pytest
from talents_forever_data import load_fixture

from forever.bridge.agent import AgentResult
from forever.bridge.exports import typed_link
from forever.bridge.loop import Bridge
from forever.cli import main
from forever.exports.codec import ExportFormatError, deflate, encode_for_print, unpack
from forever.exports.ellesmere import (
    PREFIX,
    BaseProfile,
    ellesmere_deserialize,
    ellesmere_profile,
    ellesmere_serialize,
    read_ellesmere,
)
from forever.exports.talents import naowh_export

CASE = load_fixture("mage_builds.json")["cases"]["leveling-20"]
DEEP_NAOWH = "!NFB1!" + encode_for_print(deflate(b"\x01" + b"\x1a" * 5000 + b"\x01"))
DEEP_EUI = PREFIX + encode_for_print(deflate(b"{" * 5000 + b"}" * 5000))


def test_deep_naowh_string_is_refused_not_a_recursion_error(make_deps, capsys):
    with pytest.raises(ExportFormatError, match="profondeur"):
        unpack("!NFB1!", DEEP_NAOWH)
    assert main(["export", "read", DEEP_NAOWH, "--json"], make_deps()) == 2
    assert "profondeur" in json.loads(capsys.readouterr().out)["error"]["message"]


def test_deep_ellesmere_string_is_refused():
    with pytest.raises(ExportFormatError, match="profondeur"):
        read_ellesmere(DEEP_EUI)


def test_nan_in_a_profile_is_refused():
    with pytest.raises(ExportFormatError):
        ellesmere_deserialize(b"{Ks1:xnnan;}")


def test_empty_tables_of_the_base_are_kept():
    for addons in ([], {"EllesmereUIAuraBuffReminders": []}, {"EllesmereUIAuraBuffReminders": {"forever": []}}):
        base = BaseProfile(name="Base", data={"addons": addons, "fonts": []}, cdm={}, spec_key="1", source="sauvegarde")
        data = ellesmere_profile(base, spec_key="1", bars={"cooldowns": [1]}, buff_ids=[2])["data"]
        assert data["addons"]["EllesmereUIAuraBuffReminders"]["forever"]["customIDs"] == [2]
        assert data["fonts"] == []


def test_raw_bytes_and_boolean_keys_round_trip_identically():
    raw = b"{Ks2:\xff\xfes1:aKTn1;}"
    assert ellesmere_serialize(ellesmere_deserialize(raw)) == raw


def test_talented_bonus_reaches_the_naowh_code(make_deps):
    deps = make_deps()
    talents = {**CASE["talents"], "frostbite": CASE["talents"]["frostbite"] + 1}
    assert naowh_export(deps, "Mage", CASE["level"], talents)["status"] == "bloque"
    assert naowh_export(deps, "Mage", CASE["level"], talents, talented_bonus=1)["status"] == "ordre_genere"


def test_closest_link_never_borrows_another_build_s_naowh_code():
    other = [typed_link("talents_forever", "https://x/build"), typed_link("naowh_build", "!NFB1!autre")]
    result = AgentResult(text="", session_id=None, exports={"build": other})
    assert Bridge._typed_links(result, "closest", "https://x/closest") == [
        typed_link("talents_forever", "https://x/closest")
    ]
