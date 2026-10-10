"""Boucle du pont en P06b, bloc D (décision 235) : l'export SimulationCraft collé (`k=simc`) est lu par le pont sans
le modèle ; la réponse liste les écarts avec le profil et une carte « Mettre à jour le profil » écrit, au clic, la
fiche (source `simulationcraft`) et les valeurs du contexte du même message (source `jeu`). Export réel de la sonde
G et son contexte (anonymisés)."""

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from conftest import FIXTURES
from test_bridge_loop import FakeCapture, events, make, slot_table
from test_bridge_loop_p06b import SESSION, RefusingAgent, part_bands, replies
from test_bridge_sonde_g import context

from forever.bridge.cards import CardSource
from forever.bridge.context import load_context_data
from forever.bridge.profile_gap import ProfileWatch
from forever.bridge.record import Record
from forever.profile import read_profile

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
REAL = (FIXTURES / "simc" / "mage19_sonde_g.txt").read_text(encoding="utf-8")


@pytest.fixture
def setup(tmp_path, make_deps):
    deps = replace(make_deps(), profile_path=tmp_path / "profil" / "profile.json")
    watch = ProfileWatch(data=load_context_data(deps), deps=deps,
                         store=tmp_path / "cache" / "bridge" / "profile_gaps.json", now=lambda: NOW)  # fmt: skip
    capture = FakeCapture()
    bridge, addons, _ = make(tmp_path, capture, RefusingAgent())
    bridge.profile = watch
    bridge.cards = CardSource(tmp_path / "cache", profile=watch)

    def send(record):
        for band in part_bands(record):
            capture.band = band
            bridge.step()
        return replies(addons)[-1]

    def cards():
        bridge.step()
        slot = slot_table(addons, 1)
        return [slot.cards[i] for i in range(1, len(slot.cards or {}) + 1)]

    return deps, send, cards


def test_real_export_is_read_and_proposed(setup, tmp_path):
    deps, send, cards = setup
    ctx = context("mage19_sonde_g_simc.txt")
    reply = send(Record(SESSION, 30, frozenset({"k=simc"}), ctx, REAL, slot=1))
    assert reply.text.startswith("Export SimulationCraft reçu (73 lignes, somme de contrôle juste) et lu")
    assert "fiche" in reply.text and "À valider" in reply.text
    assert "emplacement 18" in reply.text  # baguette absente de l'export, prise du contexte
    (card,) = cards()
    assert card.kind == "profile" and card.title == "Créer le personnage Personnage au profil"
    assert not deps.profile_path.exists()
    reply = send(Record(SESSION, 31, frozenset({f"a=profile_apply:{card.id}"}), ctx, "", slot=1))
    assert reply.text.startswith("Profil mis à jour")
    c = read_profile(deps)["character"]
    assert c["sheet"]["spell_power"]["frost"] == 29
    assert c["fields"]["sheet"]["source"] == "simulationcraft" and c["fields"]["level"]["source"] == "jeu"
    assert c["gear"]["18"]["item"] == 11288 and c["gear"]["5"]["enchant"] == 41
    (read,) = [e for e in events(tmp_path) if e["event"] == "simc_read"]
    assert read["gaps"] and read["warnings"]


def test_modified_export_is_not_read(setup):
    _, send, cards = setup
    record = Record(SESSION, 32, frozenset({"k=simc"}), context("mage19_sonde_g_simc.txt"),
                    REAL.replace("level=19", "level=18"), slot=1)  # fmt: skip
    reply = send(record)
    assert "export incomplet ou modifié : recopiez /simc" in reply.text
    assert cards() == []


def test_journal_keeps_no_name(setup, tmp_path):
    _, send, _ = setup
    ctx = {**context("mage19_sonde_g_simc.txt"), "name": "Jen"}
    send(Record(SESSION, 33, frozenset({"k=simc"}), ctx, REAL.replace("Personnage", "Jen"), slot=1))
    exports = [e for e in events(tmp_path) if e["event"] == "simc_export"]
    assert exports and 'mage=\\"Jen\\"' not in json.dumps(exports, ensure_ascii=False)
