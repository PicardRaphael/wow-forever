"""Cartes « À valider » des attentes de `forever update` (P06b, bloc B, décision 235) : texte rédigé par le pont à
partir des champs de l'attente (jamais par le modèle), Valider et Refuser seulement pour une attente approuvable à
l'état `en_attente`, « Expliquer » sur toutes ; attentes closes absentes. Résumé de mesure synthétique (valeurs de
`test_update_measures_summary.py`, aucun chiffre du jeu)."""

import pytest
from test_update_measures_summary import DETAILS, HP_LEVELS

from forever.bridge.actions import approvable
from forever.bridge.cards import card_lines, update_cards
from forever.update import measure_summary

VERSION = "1.60.1.70338"


def entry(kind, *, action="attente", state="en_attente", **extra):
    base = {"id": f"{kind}-{VERSION}", "kind": kind, "action": action, "version": VERSION, "state": state,
            "revision": None, "reasons": ["raison"], "commands": ["forever update approve x"]}  # fmt: skip
    return {**base, **extra}


def measures(state="en_attente"):
    builds = {"replayed": True, "changed": [{"engine": "leveling", "case": "leveling-20"}], "unchanged": 3}
    return entry("measures", state=state, summary=measure_summary(DETAILS, HP_LEVELS, builds))


@pytest.mark.parametrize(
    "item",
    [
        entry("install_version", revision=1),
        entry("install_revision", revision=2),
        measures(),
    ],
)
def test_approvable_entries(item):
    assert approvable(item)


@pytest.mark.parametrize(
    "item",
    [
        entry("install_version", action="bloqué", revision=1),
        entry("network"),
        entry("hotfixes_unread", until="2026-10-11T05:07:29Z"),
        entry("column_names"),
        entry("addon_data", addon="GearQuestForever"),
        entry("network_dbd"),
        measures("approuvée"),
        measures("rejetée"),
        measures("périmée"),
        measures("faite"),
    ],
)
def test_entries_that_cannot_be_approved(item):
    assert not approvable(item)


def test_measures_card_lines():
    lines = card_lines(measures())
    assert lines[0].startswith("PNJ ajoutés : Synthetic Boar")
    assert any(line.startswith("PNJ changés : Synthetic Wolf") for line in lines)
    assert any(line.startswith("PNJ nouvellement écartés : Synthetic Giant") for line in lines)
    assert any(line.startswith("PV par niveau : niv. 7 : 100 → 111") for line in lines)
    assert any(line == "Builds changés après rejeu : leveling leveling-20" for line in lines)


def test_names_are_listed_ten_at_most():
    details = {**DETAILS, "added": [{"npc_id": 900100 + i, "name": f"Boar {i}", "levels": {}} for i in range(12)]}
    summary = measure_summary(details, {}, {"replayed": False, "reason": "rejeu non fait"})
    (added,) = [line for line in card_lines(entry("measures", summary=summary)) if line.startswith("PNJ ajoutés")]
    assert "Boar 9" in added and "Boar 10" not in added and "… et 2 autre(s)" in added


def test_simple_card_lines():
    assert card_lines(entry("network")) == ["En attente du réseau : la mise à jour reprendra seule."]
    hotfix = entry("hotfixes_unread", until="2026-10-11T05:07:29Z")
    assert card_lines(hotfix) == ["Correctifs du serveur à lire jusqu'au 11/10/2026."]
    blocked = entry("install_version", action="bloqué", revision=1, commands=["uv run tasks.py verify"])
    assert card_lines(blocked)[-1] == "Une mise à jour attend une correction sur ton PC : ouvre une session Claude"
    install = entry("install_revision", revision=2, summary={"pvp": {"sentence": "fiches PvP : Warrior"}})
    assert card_lines(install)[:2] == [f"version {VERSION}, révision 2", "fiches PvP : Warrior"]


def test_update_cards_buttons_and_closed_entries():
    cards = update_cards([measures(), entry("network"), measures("faite"), measures("rejetée")])
    assert [c["id"] for c in cards] == [f"measures-{VERSION}", f"network-{VERSION}"]
    keys = [[b["key"] for b in c["buttons"]] for c in cards]  # « Masquer » : ajouté à la publication (CardSource)
    assert keys == [["approve", "reject", "explain"], ["explain"]]
    approve = cards[0]["buttons"][0]
    assert approve == {"key": "approve", "label": "Valider", "action": f"approve:measures-{VERSION}", "confirm": True}
    assert all(c["kind"] == "update" and c["title"] and c["lines"] for c in cards)
    approved = update_cards([measures("approuvée")])
    assert [b["key"] for b in approved[0]["buttons"]] == ["explain"]
    assert approved[0]["lines"][-1] == "Validée : sera installée à la prochaine mise à jour."
