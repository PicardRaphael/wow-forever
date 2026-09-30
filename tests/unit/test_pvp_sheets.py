"""Fiches PvP par classe et par affrontement (PV1, blocs D et G) : service de lecture, CLI, outil MCP.

Valeurs attendues lues dans les données (`classes.json`, `races.json`, `pvp_items.json`, `pvp_rules.json`) par le
chemin `from` de chaque valeur, jamais écrites dans le test. Paires fixées au plan : Mage contre Démoniste, Voleur
contre Paladin."""

import json
import re

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.cli import main
from forever.provenance import validate_provenance
from forever.pvp import LIMIT, class_sheet, matchup
from forever.store import load_version

CERTAINTIES = {"certain", "probable", "suppose"}
_STEP = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def values(node):
    """Toutes les valeurs tracées (`{value, from, certainty}`) d'une fiche, à toute profondeur."""
    if isinstance(node, dict):
        if set(node) == {"value", "from", "certainty"}:
            yield node
            return
        for v in node.values():
            yield from values(v)
    elif isinstance(node, list):
        for v in node:
            yield from values(v)


def resolve(path: str):
    file, _, inner = path.partition(":")
    node = read_json(DATA_DIR / LOCAL_VERSION / file)
    for name, index in _STEP.findall(inner):
        node = node[int(index)] if index else node[name]
    return node


@pytest.fixture
def data(make_deps):
    return load_version(make_deps())


def by_name(items, name):
    found = [i for i in items if i["name"] == name]
    assert found, name
    return found[0]


def test_matchup_is_deterministic(data):
    for mine, other in (("Mage", "Warlock"), ("Rogue", "Paladin")):
        me = {"class": mine, "level": 60, "race": "Orc" if mine == "Mage" else "Human", "talents": None}
        a = matchup(data, me, {"class": other, "level": 60})
        b = matchup(data, me, {"class": other, "level": 60})
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
        assert a["threats"]["controls"] and a["answers"]["cc_breaks"] is not None


def test_every_value_traces_to_the_data(data):
    sheet = matchup(data, {"class": "Mage", "level": 60, "race": "Orc", "talents": None}, {"class": "Warlock"})
    traced = list(values(sheet))
    assert len(traced) > 50
    for v in traced:
        assert resolve(v["from"]) == v["value"], v["from"]


def test_missing_values_are_flagged_not_invented(data):
    sheet = class_sheet(data, "Warlock", 60)
    for section in ("controls", "defensives", "interrupts", "cc_breaks", "dispels", "mobility", "bursts"):
        for item in sheet[section]:
            if item["range_yd"]["value"] is None:
                assert any(item["name"] in m and "portée" in m for m in sheet["missing"])
    assert any("talent" in m for m in sheet["missing"])  # talents inconnus
    assert sheet["unresolved"] and any(sheet["unresolved"][0] in m for m in sheet["missing"])


def test_talent_spells_marked_conditional_without_talents(data):
    unknown = class_sheet(data, "Rogue", 60)
    talent_items = [i for s in ("controls", "bursts", "defensives") for i in unknown[s] if i["talent"]]
    assert talent_items and all(i["conditional"] == "si talent" for i in talent_items)
    none = class_sheet(data, "Rogue", 60, talents={})
    assert not [i for s in ("controls", "bursts", "defensives") for i in none[s] if i["talent"]]
    key = talent_items[0]["talent"]
    given = class_sheet(data, "Rogue", 60, talents={key: 1})
    chosen = [i for s in ("controls", "bursts", "defensives") for i in given[s] if i["talent"] == key]
    assert chosen and all(i["conditional"] is None for i in chosen)


def test_provenance_and_certainty_per_field(data, make_deps, capsys):
    sheet = class_sheet(data, "Rogue", 60)
    assert {v["certainty"] for v in values(sheet)} <= CERTAINTIES
    kidney = by_name(sheet["controls"], "Kidney Shot")
    assert kidney["diminish"]["certainty"] == "certain" and kidney["diminish_name"]["certainty"] == "suppose"
    assert kidney["types"]["certainty"] == "probable"
    capsys.readouterr()
    assert main(["pvp", "class", "Voleur", "--level", "60", "--json"], make_deps()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert validate_provenance(payload["provenance"]) == []


def test_sheet_never_reads_the_profile(make_deps, capsys):
    deps = make_deps()
    deps.profile_path.parent.mkdir(parents=True, exist_ok=True)
    deps.profile_path.write_bytes(b"{ profil illisible")  # toute lecture du profil lèverait une erreur
    capsys.readouterr()
    assert main(["pvp", "matchup", "Mage", "Démoniste", "--level", "60", "--race", "Orc", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mine"] == {"class": "Mage", "level": 60, "race": "Orc", "talents_known": False}


def test_rogue_controls_listed_with_category(data):
    rules = read_json(DATA_DIR / LOCAL_VERSION / "pvp_rules.json")
    kidney = by_name(class_sheet(data, "Rogue", 60)["controls"], "Kidney Shot")
    bit = kidney["diminish"]["value"]
    assert bit and kidney["diminish_name"]["value"] == rules["categories"][str(bit)]["name"]


def test_paladin_defensive_cooldowns_listed(data):
    sheet = class_sheet(data, "Paladin", 60)
    shield = by_name(sheet["defensives"], "Divine Shield")
    assert shield["duration_s"]["value"] and resolve(shield["cooldown_s"]["from"]) == shield["cooldown_s"]["value"]


def test_warlock_pet_abilities_in_the_sheet(data):
    sheet = class_sheet(data, "Warlock", 60)
    assert by_name(sheet["controls"], "Seduction")["pet"] is True
    assert by_name(sheet["interrupts"], "Spell Lock")["pet"] is True


def test_pvp_class_cli(make_deps, capsys):
    capsys.readouterr()
    assert main(["pvp", "class", "Voleur", "--level", "60"], make_deps()) == 0
    out = capsys.readouterr().out
    assert "Kidney Shot" in out and "Provenance" in out


def test_pvp_matchup_cli_json(make_deps, capsys):
    capsys.readouterr()
    argv = ["pvp", "matchup", "Voleur", "Paladin", "--level", "60", "--race", "Human", "--json"]
    assert main(argv, make_deps()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["opponent"]["class"] == "Paladin" and payload["threats"]["defensives"]
    assert validate_provenance(payload["provenance"]) == []


def test_pvp_cli_prints_the_limit(make_deps, capsys):
    capsys.readouterr()
    assert main(["pvp", "matchup", "Mage", "Démoniste", "--level", "60"], make_deps()) == 0
    assert LIMIT in capsys.readouterr().out


# --- Outil MCP ------------------------------------------------------------------------------------------------


def call_lookup(deps, arguments):
    import asyncio

    from mcp import Client

    from forever.mcp_server import build_server

    async def go():
        async with Client(build_server(deps)) as client:
            return await client.call_tool("forever_lookup", arguments)

    return asyncio.run(go())


def test_lookup_pvp_kind(make_deps):
    deps = make_deps()
    r = call_lookup(deps, {"kind": "pvp", "name": "Voleur", "level": 60, "limit": 3})
    assert not r.is_error
    out = r.structured_content
    assert len(out["controls"]) <= 3 and out["totals"]["controls"] >= len(out["controls"])
    assert validate_provenance(out["provenance"]) == []
    assert all("from" not in json.dumps(item) for item in out["controls"])  # compact : sans chemins
    both = call_lookup(deps, {"kind": "pvp", "name": "Mage", "opponent": "Démoniste", "level": 60, "race": "Orc"})
    assert not both.is_error and both.structured_content["opponent"]["class"] == "Warlock"
    detailed = call_lookup(deps, {"kind": "pvp", "name": "Voleur", "level": 60, "detail": True, "limit": 1})
    item = detailed.structured_content["controls"][0]
    assert resolve(item["duration_s"]["from"]) == item["duration_s"]["value"]


def test_unsupported_kind_lists_pvp(make_deps, capsys):
    capsys.readouterr()
    assert main(["lookup", "objet", "x", "--json"], make_deps()) != 0
    err = json.loads(capsys.readouterr().out)["error"]
    assert err["code"] == "unsupported_kind" and "pvp" in err["suggestions"]


def test_windows_list_long_opponent_cooldowns(data):
    threshold = read_json(DATA_DIR / LOCAL_VERSION / "pvp_rules.json")["sheets"]["long_cooldown_s"]["value"]
    sheet = matchup(data, {"class": "Rogue", "level": 60, "race": "Human", "talents": None}, {"class": "Paladin"})
    assert sheet["windows"]
    cooldowns = [w["cooldown_s"]["value"] for w in sheet["windows"]]
    assert all(cd >= threshold for cd in cooldowns) and cooldowns == sorted(cooldowns, reverse=True)


def test_values_come_from_the_rank_known_at_the_level(data):
    """Relecture de PV1 : à un niveau donné, durée, durée PvP et recharge viennent du rang connu à ce niveau (pas du
    rang le plus haut), sauf pour un effet porté par un sort déclenché (`via`)."""
    low = min(
        r["level"]
        for s in data.read_json("classes.json")["classes"]["Paladin"]["spells"].values()
        if s["name"] == "Hammer of Justice"
        for r in s["ranks"]
        if r["level"]
    )
    sheet = class_sheet(data, "Paladin", low)
    hammer = by_name(sheet["controls"], "Hammer of Justice")
    assert (
        ".ranks[0]" in hammer["duration_s"]["from"]
        and resolve(hammer["duration_s"]["from"]) == hammer["duration_s"]["value"]
    )
    for section in ("controls", "defensives", "interrupts", "bursts"):
        for item in sheet[section]:
            if item.get("via") is None:
                for field in ("duration_s", "pvp_duration_s", "cooldown_s"):
                    assert ".ranks[" in item[field]["from"], (item["name"], field)


def test_dispels_are_matched_by_direction(data):
    """Relecture de PV1 : mes dissipations ennemies seules visent ses buffs ; ses dissipations amies seules
    retirent mes contrôles (Cleanse d'un Paladin ne dissipe pas le bouclier d'un Prêtre ennemi)."""
    me = {"class": "Paladin", "level": 60, "race": "Human", "talents": None}
    sheet = matchup(data, me, {"class": "Priest", "level": 60})
    assert "Power Word: Shield" not in {a["name"] for a in sheet["answers"]["dispellable_auras"]}
    mage = {"class": "Mage", "level": 60, "race": "Orc", "talents": None}
    against = matchup(data, mage, {"class": "Shaman", "level": 60})["their_answers"]["dispels_against_my_controls"]
    assert "Polymorph" not in {c["name"] for c in against}  # Purge vise un ennemi, pas un allié métamorphosé


def test_client_race_token_selects_the_racials(data):
    me = {"class": "Mage", "level": 60, "race": "Scourge", "talents": None}  # jeton du client (ForeverLogger)
    sheet = matchup(data, me, {"class": "Warlock", "level": 60})
    assert sheet["answers"]["racials"] and all(r["race"] == "Undead" for r in sheet["answers"]["racials"])
    unknown = matchup(data, {**me, "race": "Inconnue"}, {"class": "Warlock"})
    assert any("race" in m for m in unknown["missing"])


def test_totals_keep_each_list_apart(make_deps):
    from forever.pvp import compact, pvp_report

    report = pvp_report(make_deps(), "Voleur", opponent="Prêtre", level=60, race="Human")
    totals = compact(report)["totals"]
    assert totals["answers.cc_breaks"] == len(report["answers"]["cc_breaks"])
    assert totals["their_answers.cc_breaks"] == len(report["their_answers"]["cc_breaks"])
