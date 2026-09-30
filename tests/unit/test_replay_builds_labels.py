"""Rejeu des builds : une étiquette absente du cache est refusée (T08a).

`scripts/replay_builds.py compare <avant> <après>` rendait « aucune recommandation changée » quand l'un des deux
passages n'existait pas : une comparaison contre rien passait pour une comparaison réussie. Constat du 2026-09-30,
en comparant le rejeu de T08a à celui de T06b, absent du cache (`docs/research/builds-T05.md`, section
« Rejeu T08a »).

Aucun calcul de build ici : seules la lecture du cache et la vérification des étiquettes sont exercées."""

import importlib.util
import json

import pytest
from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "replay_builds.py"


def replay_module():
    spec = importlib.util.spec_from_file_location("replay_builds", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def replay(tmp_path, monkeypatch):
    """Module chargé, dont le cache pointe vers un dossier temporaire."""
    mod = replay_module()
    monkeypatch.setattr(mod, "_dir", lambda label: tmp_path / "builds" / label)
    return mod


def write_pass(tmp_path, label):
    """Passage d'un seul cas, à la forme rendue par `build_report` (clés relevées sur un rejeu réel)."""
    out = tmp_path / "builds" / label
    out.mkdir(parents=True)
    report = {
        "context": "leveling",
        "level": 20,
        "talents": {"frostbolt": 5},
        "talents_by_tree": {"Frost": {"frostbolt": 5}},
        "points": {"by_tree": {"Arcane": 0, "Fire": 0, "Frost": 5}, "total": 5, "available": 5, "unspent": 0},
        "order": [{"level": 10, "talent": "frostbolt"}],
        "choices": [],
        "metric": {"analytic": 35.48, "monte_carlo": 34.9},
        "monte_carlo_stats": None,
        "alternative": {
            "talents": {"frostbolt": 4},
            "diff": "frostbolt -1",
            "gap": 0.45,
            "decided_by": "analytique",
            "better": "build",
        },
        "stability": {"seeds": 5, "stable": True, "winners": {"build": 5}},
        "sensitivity": [{"assumption": "mob_hp", "holds": True}],
    }
    (out / "leveling-20.json").write_text(
        json.dumps({"report": report, "duration_s": 1.0}, ensure_ascii=False), encoding="utf-8"
    )
    return out


def test_compare_refuses_a_missing_first_label(replay, tmp_path):
    write_pass(tmp_path, "apres")
    with pytest.raises(SystemExit) as info:
        replay.compare("absent", "apres")
    assert "absent" in str(info.value)


def test_compare_refuses_a_missing_second_label(replay, tmp_path):
    write_pass(tmp_path, "avant")
    with pytest.raises(SystemExit) as info:
        replay.compare("avant", "absent")
    assert "absent" in str(info.value)


def test_compare_names_both_missing_labels(replay):
    with pytest.raises(SystemExit) as info:
        replay.compare("ni-lun", "ni-lautre")
    message = str(info.value)
    assert "ni-lun" in message and "ni-lautre" in message


def test_the_message_says_where_it_looked_and_what_exists(replay, tmp_path):
    write_pass(tmp_path, "T08a")
    with pytest.raises(SystemExit) as info:
        replay.compare("T06b", "T08a")
    message = str(info.value)
    assert "T06b" in message
    assert "T08a" in message  # les passages disponibles sont listés
    assert "replay_builds.py run" in message  # comment en produire un


def test_an_empty_directory_is_refused_too(replay, tmp_path):
    """Un dossier présent mais vide ne vaut pas mieux qu'un dossier absent."""
    write_pass(tmp_path, "plein")
    (tmp_path / "builds" / "vide").mkdir(parents=True)
    with pytest.raises(SystemExit) as info:
        replay.compare("vide", "plein")
    assert "vide" in str(info.value)


def test_table_refuses_a_missing_label(replay):
    with pytest.raises(SystemExit) as info:
        replay.table("absent")
    assert "absent" in str(info.value)


def test_two_present_labels_still_compare(replay, tmp_path):
    write_pass(tmp_path, "avant")
    write_pass(tmp_path, "apres")
    out = replay.compare("avant", "apres")
    assert "aucune recommandation changée" in out


def test_a_real_change_is_still_seen(replay, tmp_path):
    write_pass(tmp_path, "avant")
    write_pass(tmp_path, "apres")
    path = tmp_path / "builds" / "apres" / "leveling-20.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["report"]["talents"] = {"frostbolt": 4}
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    out = replay.compare("avant", "apres")
    assert "frostbolt 5→4" in out
