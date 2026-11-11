"""FR1 : le fichier français généré se charge sous Lua (client frFR simulé) et enregistre autant de guides que le
fichier anglais ; en enUS il ne charge rien.

Valeurs : mini-addon inventé pour le test (`tests/fixtures/rxp_fr/`)."""

import shutil
from pathlib import Path

from forever.rxp_fr.run import translate_addons
from lupa import LuaRuntime

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "rxp_fr"


class Fake:
    def translate(self, items):
        return {p: "FR " + p for p in items}


def _load(text: str, locale: str) -> list[str]:
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(
        f"""
        guides = {{}}
        function GetLocale() return "{locale}" end
        function UnitFactionGroup() return "Alliance" end
        RXP = {{enabledLocale = {{frFR = true}}}}
        RXPGuides = {{RegisterGuide = function(text) table.insert(guides, text) end}}
        """
    )
    lua.execute(text)
    return list(lua.eval("guides").values())


def test_generated_file_registers_every_guide_in_french(make_deps, tmp_path):
    wow = tmp_path / "wow"
    shutil.copytree(FIX / "AddOns", wow / "Interface" / "AddOns")
    shutil.copytree(FIX / "wago", tmp_path / "cache" / "wago" / "1.0.0.1")
    deps = make_deps(wow_dir=wow)
    doc = translate_addons(deps, translator=Fake())
    assert doc["written"] == ["Test-Isle.lua"], doc
    target = wow / "Interface" / "AddOns" / "RXPGuides" / "lang" / "Guides-frFR" / "forever" / "Test-Isle.lua"
    text = target.read_bytes().decode("utf-8")
    guides = _load(text, "frFR")
    assert len(guides) == 3
    assert "#name 5-10 Île d’Essai" in guides[1]
    assert _load(text, "enUS") == []
