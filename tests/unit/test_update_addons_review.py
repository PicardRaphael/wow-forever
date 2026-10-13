"""Suites des attentes vues en jeu après la remise à zéro du PC (décision 244) :

- garde-fou de la première écriture de `forever update --auto` : levé quand l'historique du dépôt porte déjà une
  révision écrite par un passage automatique (`revisions.json`, `automated`), même si le cache a été effacé (avant :
  état du cache seulement, réarmé par la remise à zéro : une mesure sans conseil changé attendait un accord) ;
- GitHub CLI absent : l'écriture s'arrête avant toute poussée, avec une raison claire (avant : erreur Windows obscure
  au moment d'attendre la CI, branche déjà poussée) ;
- cartes « Données d'addon » : ce qui a changé dans l'addon (version, fichiers), les données du dépôt qui en dépendent
  et pourquoi une session est nécessaire ;
- `forever update done <id> --note` : une relecture faite en session clôt son attente (`faite`, note gardée).

Données de fixtures, aucun chiffre du jeu."""

import json
import shutil

import pytest
from conftest import FIXTURES
from test_update_chain import DRY, montage, only_verdict  # noqa: F401  (fixture importée)
from test_update_publish import GAME, Recorder, done, isolated_git, origin  # noqa: F401  (fixtures importées)

from forever.bridge.cards import card_lines, update_cards
from forever.update import (
    UpdateOptions,
    first_write_guard,
    list_pending,
    record_pending,
    run_update,
    update_dir,
)

AUTO_DRY = UpdateOptions(auto=True, dry_run=True)


# --- garde-fou lu dans l'historique du dépôt ---------------------------------------------------------------------


def automated_history(data_dir):
    """Une révision écrite par un passage automatique dans l'historique d'une version du dépôt."""
    existing = sorted(p for p in data_dir.glob("*/revisions.json"))
    path = existing[-1] if existing else data_dir / "1.60.1.79997" / "revisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = json.loads(path.read_text("utf-8")) if path.is_file() else {"schema_version": 1, "revisions": []}
    doc["revisions"].append({"revision": len(doc["revisions"]) + 1, "automated": True})
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_the_guard_is_down_when_the_repo_already_holds_an_automated_write(tmp_path):
    cache, data = tmp_path / "cache", tmp_path / "data"
    data.mkdir()
    assert first_write_guard(cache, data) is True
    automated_history(data)
    assert first_write_guard(cache, data) is False  # cache vide (remise à zéro du PC) : l'historique suffit


def test_an_automatic_write_is_not_held_after_a_cache_reset(montage):  # noqa: F811
    deps, _ = montage()
    automated_history(deps.data_dir)
    verdict = only_verdict(run_update(deps, AUTO_DRY))
    assert verdict["action"] == "écrire"
    assert not any("garde-fou" in r for r in verdict.get("reasons", []))


# --- GitHub CLI absent -----------------------------------------------------------------------------------------


class NoGh(Recorder):
    def __call__(self, args, cwd, timeout=None):
        if list(args)[:1] == ["gh"]:
            self.calls.append(list(args))
            raise FileNotFoundError(2, "Le fichier spécifié est introuvable")
        return super().__call__(args, cwd, timeout)


@pytest.mark.slow
def test_a_missing_github_cli_stops_before_any_push(origin):  # noqa: F811
    montage_, _ = origin
    deps, _ = montage_()
    rec = NoGh()
    report = run_update(deps, GAME, runner=rec)
    assert rec.pushes() == [] and report["written"] == []
    (blocked,) = [p for p in report["pending"] if p.get("action") == "bloqué"]
    assert blocked["blocked_by"] == "gh"
    assert "GitHub CLI" in " ".join(blocked["reasons"])
    (card,) = update_cards([{**blocked, "state": "en_attente"}])
    assert card["lines"][0] == "GitHub CLI n'est pas installé sur ton PC : rien n'a été installé."


# --- cartes « Données d'addon » --------------------------------------------------------------------------------


def addon_entry(**extra):
    base = {
        "id": "addon-Questie-79dd5186dc66", "kind": "addon_data", "action": "attente", "state": "en_attente",
        "addon": "Questie", "version": "11.39.0 Forever-v28", "previous_version": "11.38.0 Forever-v27",
        "first": False, "files": {"added": ["a.lua"], "removed": [], "modified": ["b.lua", "c.lua"]},
        "uses": ["table des monstres (PV comparés à Questie)", "zones et quêtes conseillées"],
        "reasons": ["Questie changé"], "commands": ["forever measures refresh"],
    }  # fmt: skip
    return {**base, **extra}


def test_addon_card_says_what_changed_and_why_a_session_is_needed():
    lines = card_lines(addon_entry())
    text = "\n".join(lines)
    assert "11.38.0 Forever-v27 → 11.39.0 Forever-v28" in text
    assert "1 fichier(s) ajouté(s), 2 modifié(s)" in text
    assert "table des monstres (PV comparés à Questie)" in text
    assert "session" in text.lower() and "comparer" in text
    assert "forever" not in text.lower()


def test_addon_card_after_a_reset_says_there_was_no_previous_inventory():
    text = "\n".join(card_lines(addon_entry(first=True, previous_version=None, files=None)))
    assert "aucun relevé précédent" in text.lower() and "11.39.0 Forever-v28" in text


def test_the_pass_records_what_the_card_needs(make_deps, tmp_path):
    wow = tmp_path / "wow"
    shutil.copytree(FIXTURES / "questie" / "11.38.0", wow / "Interface" / "AddOns" / "Questie")
    deps = make_deps(wow_dir=wow)
    report = run_update(deps, UpdateOptions(only=frozenset({"addons"}), network=False))
    (entry,) = [p for p in report["pending"] if p["kind"] == "addon_data"]
    assert entry["first"] is True and entry["uses"] and entry["previous_version"] is None


# --- clôture d'une relecture -----------------------------------------------------------------------------------


def test_done_closes_an_addon_review_with_its_note(make_deps, capsys):
    from forever.cli import main

    deps = make_deps()
    record_pending(deps.cache_dir, addon_entry())
    assert main(["update", "done", "addon-Questie-79dd5186dc66", "--note", "relu : aucun changement"], deps) == 0
    (doc,) = list_pending(deps.cache_dir)
    assert doc["state"] == "faite" and doc["done_by"] == "relu : aucun changement"


def test_done_is_refused_for_an_entry_that_is_not_a_session_review(make_deps):
    from forever.cli import main

    deps = make_deps()
    record_pending(deps.cache_dir, addon_entry(id="m-1", kind="measures"))
    assert main(["update", "done", "m-1", "--note", "x"], deps) != 0
    assert json.loads((update_dir(deps.cache_dir) / "pending" / "m-1.json").read_text("utf-8"))["state"] == "en_attente"
