"""Essai CJ-6 du 2026-10-15, retour : « Mon équipement à ce niveau » au niveau 10 montrait encore des objets de
niveau 30. Cause lue dans la transcription de la conversation du pont : le modèle avait appelé deux fois
`forever_gear`, `action="leveling"` (sortie juste, filtrée au niveau 10) et `action="route"` (route d'équipement de la
liste BiS, sans niveau), puis mêlé les deux sorties. Le bouton de l'écran Équipement envoie désormais l'action
`a=gear_level:<N>`, traitée par le pont sans le modèle : un seul appel de l'outil (`leveling`, niveau N, classe, race,
camp et métiers du contexte) et une réponse rédigée à partir de sa seule sortie.

Bout en bout : bande de l'addon décodée par le pont (le bouton Lua est testé dans `test_bridge_window6_lua.py`),
appel de l'outil espionné, réponse publiée. Valeurs : addon GearQuest fabriqué dans `tmp_path`, contexte réel de
`tests/fixtures/bridge/contexts/mage19.txt` (Mage Orc, Horde). Aucun chiffre de jeu ici."""

import pytest
from test_bridge_choices import setup_bridge

from forever.bridge import gear_level

LEVEL = 10
ITEMS = {
    # objet : (emplacement, nom, faits de GearQuest) ; « Ok » : obtenable au niveau 10, « Haut » : jamais montré
    920001: ("Feet", "Ok Vendor Shoes", 'reqLevel=8,sourceType="vendor",instructions="Bought from Fixture Vendor."'),
    920002: ("Hands", "Haut Late Gloves", 'reqLevel=30,sourceType="vendor",instructions="Bought from Fixture Vendor."'),
    920003: (
        "Hands",
        "Ok Drop Gloves",
        'reqLevel=9,sourceType="world_drop",instructions="World drop around level 8-12."',
    ),
    920004: (
        "Back",
        "Haut Drop Cape",
        'reqLevel=9,sourceType="world_drop",instructions="World drop around level 25-30."',
    ),
    920005: ("Legs", "Haut Craft Pants", 'reqLevel=9,sourceType="profession",profession="Tailoring"'),
    920006: ("Head", "Aside Mystery Hat", 'reqLevel=1,sourceType="unsourced",instructions="Source not listed yet."'),
}


def wow_dir(tmp_path):
    folder = tmp_path / "wow" / "Interface" / "AddOns" / "GearQuestForever_MAGE"
    folder.mkdir(parents=True)
    facts = "\n".join(f'    [{i}]={{name="{n}",quality=2,{f}}},' for i, (_, n, f) in ITEMS.items())
    picks = "\n".join(
        f'    {{{i},"{slot}",{LEVEL - 2},{LEVEL + 2},{rank},"frost","Horde",1.0}},'
        for rank, (i, (slot, _, _)) in enumerate(ITEMS.items(), start=1)
    )
    text = f"local GQ = GearQuest\nGQ.Data.mageItemFacts = {{\n{facts}\n}}\nGQ.Data.magePicks = {{\n{picks}\n}}\n"
    (folder / "Data.Mage.generated.lua").write_text(text, encoding="utf-8")
    return tmp_path / "wow"


@pytest.fixture
def wired(tmp_path, make_deps, monkeypatch):
    deps = make_deps(wow_dir=wow_dir(tmp_path), offline=True)
    calls = []
    real = gear_level.gear_report

    def spy(deps_, action, **kwargs):
        calls.append((action, kwargs))
        return real(deps_, action, **kwargs)

    monkeypatch.setattr(gear_level, "gear_report", spy)
    (tmp_path / "bridge").mkdir()
    bridge, _addons, agent, send, _cards = setup_bridge(tmp_path / "bridge")
    bridge.gearer = lambda context, level: gear_level.gear_level_reply(deps, context, level)
    bridge.gear_router = lambda context, level: gear_level.gear_route_reply(deps, context, level)
    return send, agent, calls


def test_gear_screen_button_end_to_end(wired):
    send, agent, calls = wired
    before = len(agent.calls)
    reply = send(flags={f"a=gear_level:{LEVEL}"}, text="")
    assert len(agent.calls) == before  # sans le modèle
    assert len(calls) == 1
    action, kwargs = calls[0]
    assert action == "leveling" and kwargs["level"] == LEVEL
    assert kwargs["class_name"].upper() == "MAGE" and kwargs["faction"] == "horde" and kwargs["race"] == "Orc"
    text = reply.text
    assert "Ok Vendor Shoes" in text and "Ok Drop Gloves" in text
    assert "Haut" not in text  # aucun objet au-dessus du niveau demandé, ni hors de la sortie de l'outil
    assert "Aside Mystery Hat" in text and "mis à part" in text.lower()
    required = [int(part.split()[0]) for part in text.split("niveau requis ")[1:]]
    assert required and max(required) <= LEVEL


def test_gear_level_action_with_a_bad_level_is_refused(wired):
    send, _agent, calls = wired
    reply = send(flags={"a=gear_level:abc"}, text="")
    assert calls == [] and "refusée" in reply.text


def test_make_a_route_button_end_to_end(wired):
    """« En faire une route » (bloc 4c) : action `a=gear_route:<N>` sans le modèle, faite des seuls objets
    obtenables au niveau N (jamais la route de la liste BiS, sans niveau), regroupés par origine."""
    send, agent, calls = wired
    before = len(agent.calls)
    reply = send(flags={f"a=gear_route:{LEVEL}"}, text="")
    assert len(agent.calls) == before and [c[0] for c in calls] == ["leveling"]
    assert calls[0][1]["level"] == LEVEL
    text = reply.text
    assert f"Route d'équipement au niveau {LEVEL}" in text
    assert "Ok Vendor Shoes" in text and "Ok Drop Gloves" in text and "Haut" not in text


def test_gear_actions_with_a_bad_level_say_why(wired):
    send, _agent, calls = wired
    for flag in ("a=gear_route:abc", "a=gear_level:0"):
        reply = send(flags={flag}, text="")
        assert "niveau invalide" in reply.text
    assert calls == []
