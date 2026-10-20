"""Bloc 4d, suite (plan de CJ1 ; décision 282) : la route d'équipement dit, objet par objet, d'où vient le taux de
butin (tes relevés d'abord : ForeverLogger et Naowh, puis les addons) et les écarts entre sources ; chaque donjon
visé donne une boucle avec le nombre de passages attendu et pour 9 chances sur 10 (registre I20), objets d'un même
donjon cumulés ; le partage du butin en groupe est dit. Une tranche de niveaux donne aussi sa route d'équipement
(`a=gear_route:<de>-<à>`), proposée sous la réponse de la tranche.

Valeurs : objets, taux, relevés, contexte et plan fabriqués ici ; l'optimiseur réel est remplacé par un plan
fabriqué. Aucun chiffre de jeu ici."""

from test_bridge_choices import setup_bridge
from test_gear_route_4d import DOC, LEVEL, WHO

from forever.bridge import gear_level
from forever.bridge.loop import gear_levels
from forever.gear_route import drop_text

RECORD = {"dungeon": "fixture_depths", "dungeon_name": "Fixture Depths", "boss": "Fixture Boss", "rate": 0.25,
          "source": "relevé", "certainty": "certain", "observed": {"drops": 3, "kills": 12},
          "others": [{"source": "forever_guide", "rate": 0.3}, {"source": "atlasloot", "rate": 0.25}]}  # fmt: skip
ADDON = {"dungeon": "fixture_depths", "dungeon_name": "Fixture Depths", "boss": "Fixture Boss", "rate": 0.3,
         "source": "forever_guide", "certainty": "suppose", "others": []}  # fmt: skip
ELSEWHERE = {"dungeon": "fixture_spire", "dungeon_name": "Fixture Spire", "boss": "Fixture Late Boss", "rate": 0.05,
             "source": "atlasloot", "certainty": "suppose", "others": []}  # fmt: skip
PLAN = {"id": "g", "class": "mage", "levels": {"from": 4, "to": LEVEL}, "hours": 1.0, "xp_h": 100.0,
        "certainty": "suppose", "rewards": [], "reminders": [], "warnings": [],
        "stops": [{"kind": "dungeon", "ref": "Fixture Depths", "name": "Fixture Depths", "text": "donjon Fixture Depths",
                   "zone": "Fixture Vale", "level": 8}],
        "dungeons": [{"name": "Fixture Depths"}],
        "request": {"character": "Go", "purpose": "équipement"}, "basis": {"kind": "calcul"}, "provenance": {}}  # fmt: skip


def test_my_records_come_first_with_their_counts():
    text = drop_text([RECORD])
    assert "25 %" in text and "ton relevé" in text and "3 sur 12" in text


def test_other_sources_disagreeing_are_shown():
    text = drop_text([RECORD])
    assert "écart" in text and "Forever Guide 30 %" in text
    assert "AtlasLoot" not in text  # même taux : pas un écart


def test_an_addon_rate_names_its_source_and_other_bosses_are_listed():
    text = drop_text([ADDON, ELSEWHERE], boss="Fixture Boss")
    assert "30 %" in text and "Forever Guide" in text
    assert "aussi" in text and "Fixture Late Boss" in text and "Fixture Spire" in text


def reply(monkeypatch, make_deps, level=LEVEL, doc=None):
    asked = []

    def fake_plan(deps_, request, **_kwargs):
        asked.append(request)
        return PLAN

    monkeypatch.setattr(gear_level, "plan_route", fake_plan)
    monkeypatch.setattr(gear_level, "_leveling", lambda deps_, context, lv, to_level=None: dict(doc or DOC))
    monkeypatch.setattr(gear_level, "_who", lambda deps_, context: dict(WHO))
    monkeypatch.setattr(gear_level, "_drops", lambda deps_: lambda item: [RECORD] if item == 980002 else [])
    text, _ = gear_level.gear_route_reply(make_deps(offline=True), {}, level)
    return text, asked


def test_route_reply_gives_the_dungeon_loop(monkeypatch, make_deps):
    text, _ = reply(monkeypatch, make_deps)
    lines = text.splitlines()
    head = next(i for i, line in enumerate(lines) if line.startswith("Boucles de donjon"))
    loop = next(line for line in lines[head:] if "Fixture Depths" in line)
    assert "passage" in loop and "9 chances sur 10" in loop and "Boss Choker" in loop
    choker = next(line for line in lines if "Boss Choker" in line and "ton relevé" in line)
    assert "écart" in choker
    assert any("groupe" in line for line in lines[head:])  # partage du butin dit


def test_route_for_a_level_range(monkeypatch, make_deps):
    segments = [{**p, "from": 6, "to": 12} for p in DOC["picks"]]
    text, asked = reply(monkeypatch, make_deps, level=(6, 12), doc={"segments": segments})
    assert asked and asked[0].end_level == 12 and asked[0].include == (980101,)
    assert "du niveau 6 au niveau 12" in text and "Valider et livrer" in text


def test_range_actions_are_accepted_for_the_route():
    assert gear_levels("gear_route", "6-12") == (6, 12)
    assert gear_levels("gear_route", "12-6") is None


def test_range_reply_offers_its_route(tmp_path, monkeypatch):
    (tmp_path / "bridge").mkdir()
    bridge, _addons, _agent, send, _cards = setup_bridge(tmp_path / "bridge")
    bridge.gearer = lambda context, level: ("## Équipement du niveau 6 au niveau 12\n- Mains : objet", [])
    reply_ = send(flags={"a=gear_level:6-12"}, text="")
    actions = [reply_.choices.buttons[i].action for i in range(1, len(reply_.choices.buttons) + 1)]
    assert actions == ["gear_route:6-12"]


def test_gear_screen_route_button_sends_the_range():
    import pytest

    pytest.importorskip("lupa")
    from test_bridge_send_lua import sent
    from test_bridge_window6_lua import click, opened

    game = opened()
    click(game, "ForeverBridgeNav_gear")
    click(game, "ForeverBridgeGearToUp")
    click(game, "ForeverBridgeGearToUp")
    click(game, "ForeverBridgeGearRoute")
    _, record = sent(game)
    assert record.flags == frozenset({"a=gear_route:19-21"}) and record.text == ""


def test_no_item_gives_no_route(monkeypatch, make_deps):
    # essai sur le contexte réel du 2026-10-20 (Gnome Mage niveau 1) : aucun objet, la route calculée était une
    # simple route de leveling avec « Objets rapportés : » vide et « Valider et livrer »
    text, asked = reply(monkeypatch, make_deps, doc={"picks": []})
    assert asked == [] and "Valider et livrer" not in text and "Aucun objet" in text


def test_random_drops_take_one_line(monkeypatch, make_deps):
    # essai sur le contexte réel du 2026-10-20 : la route d'une tranche alignait plus de 40 objets de butin aléatoire
    drops = [
        {"slot": "Back", "item": 981000 + i, "name": f"Drop {i}", "source": "world_drop", "drop_levels": [8, 12]}
        for i in range(12)
    ]
    doc = {"picks": [*DOC["picks"][:2], *drops]}
    text, _ = reply(monkeypatch, make_deps, doc=doc)
    lines = [line for line in text.splitlines() if "Drop " in line or "butin aléatoire" in line.lower()]
    assert len(lines) == 1 and "12" in lines[0]
    assert "Quest Gloves" in text and "Boss Choker" in text
