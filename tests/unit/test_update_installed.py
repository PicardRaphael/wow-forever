"""Historique des installations de la veille, carte « Mis à jour » et « Annuler » (décision 295).

La veille installe d'elle-même et prévient : une fiche par installation (`<cache>/update/installed/<id>.json`), dite
en mots de joueur (« build Mage donjon niveau 20 : Frostbite passe de 0 à 3 »), montrée par `forever update status`
et par une carte « Mis à jour » du pont, avec « Annuler » (`forever update undo <id>`, sans jeu ouvert). Aucune
attente d'accord ne peut plus bloquer une mise à jour : après un passage, les seules entrées ouvertes sont celles qui
se lèvent seules, celles qui demandent une session (intégrité cassée, pertes) et les rappels de relecture.

Fiches, rejeux et attentes fabriqués ; aucun chiffre du jeu."""

import sys
from datetime import UTC, datetime

from test_update_chain import Replay, montage  # noqa: F401  (fixture importée)

from forever.bridge.actions import ActionHandler, parse_action, update_argv
from forever.bridge.cards import CardSource, installed_cards
from forever.update import SELF_CLEARING_KINDS, SESSION_KINDS, UpdateOptions, record_pending, run_update
from forever.update_installed import (
    advice_changes,
    list_installed,
    notice_lines,
    notices,
    save_installed,
    undone,
    update_installed,
)

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
PYTHON = [sys.executable, "-u", "-m", "forever"]
NAMES = {"frostbite": "Frostbite", "iceShards": "Ice Shards"}


def record(record_id="1.60.1.70450-r11-abcdefabcdef", **extra):
    base = {
        "id": record_id, "kind": "install_revision", "version": "1.60.1.70450", "revision": 11,
        "installed_at": "2026-10-22T06:40:00Z", "sha": "0123456789abcdef", "state": "installée",
        "summary": "mage_build : classes.json /classes/Mage/spells, 1 autre valeur changée",
        "notes": ["moteurs aux entrées changées : mage_build"], "changes": [], "replay": "en cours",
        "undo": f"forever update undo {record_id}",
    }  # fmt: skip
    return {**base, **extra}


# --- conseils changés en mots de joueur ---------------------------------------------------------------------------


def test_advice_changes_name_the_build_the_level_and_the_talent():
    replayed = {
        "mage_build": {
            "dungeon-20": {
                "avant": {"talents": {"frostbite": 0, "iceShards": 5}, "choices": {}},
                "après": {"talents": {"frostbite": 3, "iceShards": 5}, "choices": {}},
            },
            "leveling-30": {"avant": {"talents": {"frostbite": 3}}, "après": {"talents": {"frostbite": 3}}},
            "raid-60": {"avant": {"rejoué": False, "raison": "x"}, "après": {"rejoué": False, "raison": "x"}},
        }
    }
    assert advice_changes(replayed, NAMES) == ["build Mage donjon niveau 20 : Frostbite passe de 0 à 3"]


def test_advice_changes_say_a_rotation_change():
    replayed = {
        "mage_build": {
            "dungeon-40": {
                "avant": {"talents": {}, "choices": {"dungeon_boss": {"rotation": "frost", "armor": "frost"}}},
                "après": {"talents": {}, "choices": {"dungeon_boss": {"rotation": "fire", "armor": "frost"}}},
            }
        }
    }
    assert advice_changes(replayed, NAMES) == ["build Mage donjon niveau 40 : rotation (boss) : frost → fire"]


def test_notice_lines_fall_back_on_the_summary_then_add_the_notes():
    assert notice_lines(record()) == [
        "conseils en cours de comparaison",
        "mage_build : classes.json /classes/Mage/spells, 1 autre valeur changée",
        "moteurs aux entrées changées : mage_build",
    ]
    lines = notice_lines(record(changes=["build Mage donjon niveau 20 : Frostbite passe de 0 à 3"], replay="fait"))
    assert lines[0] == "build Mage donjon niveau 20 : Frostbite passe de 0 à 3"


# --- historique -------------------------------------------------------------------------------------------------


def test_history_keeps_every_install_and_an_undone_one_is_known(tmp_path):
    for n in range(40):
        save_installed(tmp_path, record(f"1.60.1.70450-r{n}-aaaaaaaaaaaa", installed_at=f"2026-10-22T06:{n:02d}:00Z"))
    assert len(list_installed(tmp_path)) == 40  # jamais élagué
    assert list_installed(tmp_path)[0]["id"] == "1.60.1.70450-r39-aaaaaaaaaaaa"
    update_installed(tmp_path, "1.60.1.70450-r5-aaaaaaaaaaaa", state="annulée", undone_at="2026-10-22T07:00:00Z")
    assert undone(tmp_path, "1.60.1.70450-r5-aaaaaaaaaaaa") is not None
    assert undone(tmp_path, "1.60.1.70450-r6-aaaaaaaaaaaa") is None
    assert "1.60.1.70450-r5-aaaaaaaaaaaa" not in {r["id"] for r in notices(tmp_path)}


# --- carte « Mis à jour » et « Annuler » --------------------------------------------------------------------------


def test_the_updated_card_says_what_changed_and_offers_undo():
    (card,) = installed_cards([record(changes=["build Mage donjon niveau 20 : Frostbite passe de 0 à 3"])])
    assert card["title"] == "Mis à jour : données 1.60.1.70450 r11"
    assert "build Mage donjon niveau 20 : Frostbite passe de 0 à 3" in card["lines"]
    (undo,) = [b for b in card["buttons"] if b.get("key") == "undo"]
    assert undo == {"key": "undo", "label": "Annuler", "action": f"undo:{record()['id']}", "confirm": True}
    assert card["count"] == "info"  # rien n'attend le joueur
    assert parse_action(f"a={undo['action']}") == ("undo", record()["id"])


def test_the_bridge_publishes_the_updated_card(tmp_path):
    save_installed(tmp_path, record())
    cards = CardSource(tmp_path, now=lambda: 0.0).current()
    assert [c["title"] for c in cards] == ["Mis à jour : données 1.60.1.70450 r11"]
    assert any(b.get("key") == "hide" for b in cards[0]["buttons"])  # « Masquer » à la publication


def test_undo_launches_the_fixed_command_with_the_id_read_from_the_history(tmp_path):
    save_installed(tmp_path, record())
    launched = []
    handler = ActionHandler(cache_dir=tmp_path, now=lambda: NOW, spawn=lambda argv, log: launched.append(argv))
    result, text = handler.handle("undo", record()["id"])
    assert result == "lancée" and "Annulation lancée" in text
    assert launched == [[*PYTHON, "update", "undo", record()["id"], "--json"]]
    assert update_argv("undo", "x") == [*PYTHON, "update", "undo", "x", "--json"]
    assert handler.handle("undo", "inconnu")[0] == "refusée"
    offline = ActionHandler(cache_dir=tmp_path, now=lambda: NOW, offline=True, spawn=lambda argv, log: None)
    assert offline.handle("undo", record()["id"])[0] == "refusée"


def test_status_lists_what_was_updated_with_the_undo_command(make_deps, capsys):
    from forever.cli import main

    deps = make_deps()
    save_installed(deps.cache_dir, record(changes=["build Mage donjon niveau 20 : Frostbite passe de 0 à 3"]))
    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr().out
    assert "Mis à jour : données 1.60.1.70450 r11 le 2026-10-22 06:40" in out
    assert f"forever update undo {record()['id']}" in out
    assert "build Mage donjon niveau 20 : Frostbite passe de 0 à 3" in out


# --- aucune attente ne bloque plus une mise à jour ----------------------------------------------------------------


def test_no_wait_for_approval_is_left_after_a_pass(montage):  # noqa: F811
    """Après un passage où tout change (valeur du client, entrées de moteur), il ne reste aucune attente qu'un accord
    lèverait : seules restent possibles celles qui se lèvent seules, celles d'une session et les rappels de
    relecture ; une attente d'accord d'avant la décision est close."""
    deps, _ = montage(change=("SpellEffect", "116", "EffectBonusCoefficient"))
    record_pending(
        deps.cache_dir,
        {"id": "1.60.1.79999-r1-aaaaaaaaaaaa", "kind": "install_version", "action": "attente", "version": "x"},
    )
    report = run_update(deps, UpdateOptions(network=False), replay=Replay())
    allowed = {*SELF_CLEARING_KINDS, *SESSION_KINDS, "pass_error"}
    for entry in report["pending"]:
        assert entry["action"] != "attente" or entry["kind"] in allowed, entry
        assert not any("approve" in c for c in entry.get("commands") or []), entry
    from forever.update import list_pending

    for entry in list_pending(deps.cache_dir):
        if entry.get("state") == "en_attente":
            assert entry["action"] != "attente" or entry["kind"] in allowed, entry
