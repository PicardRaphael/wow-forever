"""Contexte vérifié par le pont (retours de la sonde en jeu F du 2026-10-09, point 2) : tout élément envoyé par le jeu
que le pont ne sait pas relier à nos données (nœud de talent, classe, race, objet mal formé) est journalisé comme
défaut (`context_defect`), compté par `forever bridge status`, et retiré du message : la conversation « jeu » ne voit
jamais « non reconnu » et ne peut pas répondre « je ne reconnais pas ». L'équipement n'a pas encore de table dans les
données (T10a) : ses objets sont transmis par leur nom du client, annoncés non reliés, sans défaut."""

import json

from conftest import FIXTURES
from forever.bridge.plans import prepare_record

from forever.bridge.context import load_context_data, resolve
from forever.bridge.journal import Journal
from forever.bridge.prompt import message_text
from forever.bridge.record import Record
from forever.cli import main

REAL = FIXTURES / "bridge" / "contexts" / "mage19.txt"


def real() -> dict[str, str]:
    return dict(line.split("=", 1) for line in REAL.read_text(encoding="utf-8").splitlines() if "=" in line)


def test_unknown_node_is_a_defect_and_never_reaches_the_message(make_deps):
    data = load_context_data(make_deps())
    ctx = {**real(), "talents": "105778:5,105779:5,999999:2"}
    record = Record("s", 1, frozenset({"b=talents"}), ctx, "Quel est mon prochain talent ?")
    prepared = prepare_record(data, record)
    assert [(d.kind, d.value) for d in prepared.defects] == [("talent", "999999:2")]
    text = message_text(record, talents=prepared.notes, guide=prepared.guide)
    assert "999999" not in text.split("Question")[0].replace("talents=105778:5,105779:5,999999:2", "")
    assert "non reconnu" not in text and "ne reconna" not in text
    assert "elementalPrecision:5" in text


def test_unknown_class_race_and_malformed_item_are_defects(make_deps):
    data = load_context_data(make_deps())
    ctx = {
        **real(),
        "race": "Pandaren",
        "target": "MONK",
        "target_level": "??",
        "target_race": "Vulpera",
        "gear": "3:1769:Canvas Shoulderpads;xx:yy",
    }
    r = resolve(data, ctx)
    kinds = sorted((d.kind, d.value) for d in r.defects)
    assert kinds == [("classe", "MONK"), ("objet", "xx:yy"), ("race", "Pandaren"), ("race", "Vulpera")]
    assert r.race is None and r.target_class is None and r.target_level is None
    for d in r.defects:
        assert d.reason


def test_items_are_passed_by_name_without_defect(make_deps):
    data = load_context_data(make_deps())
    r = resolve(data, real())
    assert r.defects == []
    assert ("16", 15444, "Staff of Orgrimmar") in r.gear
    notes = prepare_record(data, Record("s", 1, frozenset(), real(), "Q ?")).notes
    assert "Staff of Orgrimmar" in notes and "T10a" in notes


def test_hidden_target_level_is_not_a_defect(make_deps):
    data = load_context_data(make_deps())
    r = resolve(data, {**real(), "target": "SHAMAN", "target_level": "??", "target_race": "Tauren"})
    assert r.defects == [] and r.target_level is None and r.target_class == "Shaman"


def test_bridge_journals_defects_and_status_counts_them(capsys, make_deps, tmp_path):
    from test_bridge_loop import FakeAgent, FakeCapture, events, make

    deps = make_deps()
    data = load_context_data(deps)
    bridge, _, _ = make(tmp_path, FakeCapture(), FakeAgent())
    bridge.prepare = lambda record: prepare_record(data, record)
    ctx = {**real(), "talents": "105778:5,105779:5,999999:2"}
    bridge._work(Record("s", 1, frozenset({"b=talents"}), ctx, "Quel est mon prochain talent ?"))
    defects = [e for e in events(tmp_path) if e["event"] == "context_defect"]
    assert [(e["kind"], e["value"]) for e in defects] == [("talent", "999999:2")]
    prompt = bridge.agent.calls[0][0]
    assert "non reconnu" not in prompt

    journal = Journal(deps.cache_dir / "bridge" / "journal", deps.now)
    journal.write("context_defect", id=1, kind="talent", value="999999:2", reason="nœud absent de classes.json")
    assert main(["bridge", "status", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr()[0])
    assert payload["context_defects"]["count"] == 1
    assert payload["context_defects"]["last"]["value"] == "999999:2"
    assert main(["bridge", "status"], deps) == 0
    assert "1 défaut de contexte" in capsys.readouterr()[0]
