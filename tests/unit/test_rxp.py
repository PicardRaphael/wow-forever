"""Guide RestedXP d'une feuille de route (RX1, bloc D) : `forever/rxp.py`, analyseur de test
`tests/fixtures/rxp/parser.py`, commande `forever route guide`, règles de `scripts/check_addon.py`.

Plan de fixture `tests/fixtures/rxp/plan.json` (valeurs inventées). Aucun chiffre de jeu ici."""

import importlib.util
import json
import re
import sys

from conftest import FIXTURES, REPO_ROOT, read_json

from forever.cli import main
from forever.rxp import encode_guide, guide_text

PLAN = read_json(FIXTURES / "rxp" / "plan.json")
NAME, GROUP = "Fixture Route", "Forever Routes"


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses du module : le module doit être connu
    spec.loader.exec_module(module)
    return module


parser = _module("rxp_parser", FIXTURES / "rxp" / "parser.py")
check_addon = _module("check_addon", REPO_ROOT / "scripts" / "check_addon.py")


def _guide():
    return encode_guide(PLAN, name=NAME, group=GROUP)


def test_guide_parses():
    text = _guide()
    guide = parser.parse(text)
    assert parser.errors(guide, text) == []
    assert guide.header["name"] == NAME and guide.header["group"] == GROUP and "forever" in guide.header
    assert guide.faction == "Horde"
    assert len(guide.steps) == len(PLAN["stops"])  # une étape par arrêt


def test_guide_roundtrip():
    guide = parser.parse(_guide())
    kinds = {"accept": "accept", "objective": "complete", "turnin": "turnin"}
    expected = [(kinds[s["kind"]], s["ref"]) for s in PLAN["stops"] if s["kind"] in kinds]
    read = [(c.name, int(c.args[0])) for step in guide.steps for c in step.commands if c.name in kinds.values()]
    assert read == expected
    gotos = [c.args for step in guide.steps for c in step.commands if c.name == "goto"]
    placed = [[str(s["map"]), f"{s['x']:.1f}", f"{s['y']:.1f}"] for s in PLAN["stops"] if s["map"] is not None]
    assert gotos == placed
    xp = [c.args for step in guide.steps for c in step.commands if c.name == "xp"]
    assert xp == [[str(PLAN["levels"]["to"])]]


def test_dungeon_step_names_the_dungeon():
    guide = parser.parse(_guide())
    dungeon = next(s for s in PLAN["stops"] if s["kind"] == "dungeon")
    assert any(dungeon["name"] in t for step in guide.steps for t in step.texts)


def test_guide_escaping():
    text = _guide()
    guide = parser.parse(text)
    odd = [s for s in PLAN["stops"] if "|" in (s["name"] or "")]
    assert odd
    accepts = [
        c for step in guide.steps for c in step.commands if c.name == "accept" and c.args == [str(odd[0]["ref"])]
    ]
    assert len(accepts) == 1  # un seul arrêt, une seule étape
    assert "Odd, Name" in accepts[0].text and ">>" in accepts[0].text
    assert not re.search(r"<<|--|\|", accepts[0].text)
    assert guide_text("a << b -- c | d\ne") == guide_text(guide_text("a << b -- c | d\ne"))  # idempotent
    assert "\n" not in guide_text("a\nb")


def test_guide_is_deterministic():
    assert _guide() == _guide()


def test_never_encrypted():
    for line in _guide().splitlines():
        assert not re.match(r"^\d+\|", line)
        assert not re.search(r"(-?\d+)(\D)([A-Za-z0-9+/=]{24,})%", line)
    for path in [*(REPO_ROOT / "addon").rglob("*.lua"), REPO_ROOT / "forever" / "rxp.py"]:
        code = path.read_text(encoding="utf-8")
        assert "ImportString" not in code and "RXPString" not in code, path


def test_no_rxpguides_text_in_fixtures():
    for path in FIXTURES.rglob("*"):
        if path.is_file() and path.suffix in (".lua", ".txt", ".json", ".md", ".py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            assert "#group RestedXP" not in text and 'RXPGuides.RegisterGuide("RestedXP' not in text, path


def test_check_addon_forbids_import_string(tmp_path):
    bad = tmp_path / "Bad.lua"
    bad.write_text("local function f(s)\n\tpcall(RXPGuides.guideImporter.ImportString, s)\nend\n", encoding="utf-8")
    assert any("ImportString" in e for e in check_addon.check_lua(bad))
    bad.write_text("local function f(s)\n\treturn loadstring(s)\nend\n", encoding="utf-8")
    assert any("loadstring" in e for e in check_addon.check_lua(bad))
    good = tmp_path / "Good.lua"
    good.write_text(
        "local function f(s)\n\tpcall(RXPGuides.ImportGuide, s)\n\tpcall(RXPGuides.RegisterGuide, s)\nend\n",
        encoding="utf-8",
    )
    assert check_addon.check_lua(good) == []


def _cache_with_plan(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    (cache / "routes").mkdir(parents=True)
    (cache / "routes" / f"{PLAN['id']}.json").write_text(json.dumps({**PLAN, "provenance": {}}), encoding="utf-8")
    monkeypatch.setenv("FOREVER_CACHE_DIR", str(cache))
    monkeypatch.setenv("FOREVER_OFFLINE", "1")
    return cache


def test_route_guide_cli(tmp_path, monkeypatch, capsys):
    _cache_with_plan(tmp_path, monkeypatch)
    out = tmp_path / "guide.txt"
    assert main(["route", "guide", PLAN["id"], "--out", str(out)]) == 0
    capsys.readouterr()
    text = out.read_text(encoding="utf-8")
    assert parser.errors(parser.parse(text), text) == []
    assert main(["route", "guide", PLAN["id"]]) == 0
    assert capsys.readouterr().out.strip() == text.strip()
