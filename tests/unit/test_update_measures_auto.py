"""Mesures sans accord inutile (décision 230, point 1).

- Une mesure des journaux qui change la table des monstres s'écrit seule quand, après rejeu, aucun conseil des builds
  du Mage ne change (les règles d'écartement des PNJ sont automatiques) ; elle ne crée une attente que si un conseil
  change, ou si le rejeu n'a rien pu comparer.
- Une attente approuvée s'écrit au passage suivant (jusqu'ici, rien n'écrivait une mesure approuvée).
- Une approbation reste valable quand l'attente est remplacée par une version qui ne fait qu'ajouter des journaux sans
  changer aucun conseil (mêmes cas changés, même conseil après) ; l'attente remplacée passe à « périmée » au lieu de
  rester « approuvée ».
- Une mesure écrite est une révision de la version installée dont `revisions.json` garde les journaux mesurés.

Rejeu et mesure simulés, journaux du dépôt de fixtures ; aucun chiffre du jeu."""

import json
import shutil

from conftest import LOCAL_VERSION
from test_update_chain import LOG, NEWER, logs, step  # noqa: F401  (fixture importée)
from test_update_measures_summary import CHANGED_CASE, PreviewMeasure, SplitReplay

from forever.update import (
    UpdateOptions,
    _measure_revision,
    _written_logs,
    approve,
    list_pending,
    record_pending,
    run_update,
)

JOURNALS = UpdateOptions(dry_run=True, only=frozenset({"journaux"}))
RECORDED = UpdateOptions(only=frozenset({"journaux"}))  # attentes enregistrées (sans clone : rien n'est poussé)


class SameReplay:
    """Rejeu simulé : aucun conseil ne change."""

    def __init__(self):
        self.calls = []

    def __call__(self, engine, case, data_dir):
        self.calls.append((engine, case))
        return {"talents": "A"}


class AfterReplay(SplitReplay):
    """Comme SplitReplay, avec un conseil « après » donné."""

    def __init__(self, base, after="B"):
        super().__init__(base)
        self.after = after

    def __call__(self, engine, case, data_dir):
        result = super().__call__(engine, case, data_dir)
        if result["talents"] == "B":
            result["talents"] = self.after
        return result


def measures(deps):
    return {e["id"]: e for e in list_pending(deps.cache_dir) if e.get("kind") == "measures"}


def add_log(deps, name):
    shutil.copyfile(LOG, deps.wow_dir / "Logs" / name)


def test_a_measure_that_changes_no_advice_is_written_alone(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    report = run_update(deps, JOURNALS, replay=SameReplay(), measure=PreviewMeasure(tmp_path))
    found = step(report, "journaux")
    assert found["status"] == "fait", found
    assert "écriture simulée" in found["detail"]
    assert report["pending"] == []
    (verdict,) = [v for v in report["verdicts"] if v["kind"] == "measures"]
    assert verdict["action"] == "écrire" and verdict["approved"] is False
    assert verdict["revision"] == 2


def test_a_measure_that_changes_an_advice_waits(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    report = run_update(deps, JOURNALS, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path))
    assert step(report, "journaux")["status"] == "attente"
    (entry,) = report["pending"]
    assert entry["kind"] == "measures" and entry["action"] == "attente"
    assert any("conseil" in r for r in entry["reasons"])


def test_a_measure_without_replay_waits(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])

    def measure(deps, data_dir, files):  # aucun aperçu : rien n'est comparé
        return {"changed": [{"file": "monsters.json", "pointer": "/npcs"}]}

    report = run_update(deps, JOURNALS, replay=SameReplay(), measure=measure)
    assert step(report, "journaux")["status"] == "attente"


def test_an_approved_measure_is_written_at_the_next_pass(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    first = run_update(deps, RECORDED, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path))
    (entry,) = first["pending"]
    approve(deps, entry["id"], spawn=lambda args: None)
    report = run_update(deps, JOURNALS, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path / "2"))
    (verdict,) = [v for v in report["verdicts"] if v["kind"] == "measures"]
    assert verdict["id"] == entry["id"]
    assert verdict["action"] == "écrire" and verdict["approved"] is True
    assert step(report, "journaux")["status"] == "fait"


def test_an_approval_survives_a_new_log_that_changes_no_advice(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    first = run_update(deps, RECORDED, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path))
    (old,) = first["pending"]
    approve(deps, old["id"], spawn=lambda args: None)
    add_log(deps, "WoWCombatLog-092726_160000.anon.txt")
    report = run_update(deps, RECORDED, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path / "2"))
    (verdict,) = [v for v in report["verdicts"] if v["kind"] == "measures"]
    assert verdict["id"] != old["id"]
    assert verdict["action"] == "écrire" and verdict["approved"] is True
    assert verdict["approved_from"] == old["id"]
    assert measures(deps)[old["id"]]["state"] == "périmée"


def test_a_replaced_approval_is_stale_when_an_advice_changes(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    first = run_update(deps, RECORDED, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path))
    (old,) = first["pending"]
    approve(deps, old["id"], spawn=lambda args: None)
    add_log(deps, "WoWCombatLog-092726_160000.anon.txt")
    replay = AfterReplay(deps.data_dir, after="C")  # le même cas change, mais vers un autre conseil
    report = run_update(deps, RECORDED, replay=replay, measure=PreviewMeasure(tmp_path / "2"))
    assert step(report, "journaux")["status"] == "attente"
    (new,) = report["pending"]
    found = measures(deps)
    assert found[new["id"]]["state"] == "en_attente"
    assert found[old["id"]]["state"] == "périmée" and new["id"] in found[old["id"]]["stale_reason"]


def test_an_unapproved_replaced_measure_is_stale_too(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    first = run_update(deps, RECORDED, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path))
    (old,) = first["pending"]
    add_log(deps, "WoWCombatLog-092726_160000.anon.txt")
    report = run_update(deps, RECORDED, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path / "2"))
    (new,) = report["pending"]
    found = measures(deps)
    assert found[old["id"]]["state"] == "périmée" and found[new["id"]]["state"] == "en_attente"


def test_a_measure_of_a_version_no_longer_installed_is_stale(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    record_pending(
        deps.cache_dir,
        {
            "id": "measures-1.60.1.70000-aaaaaaaaaaaa",
            "kind": "measures",
            "action": "attente",
            "version": "1.60.1.70000",
            "revision": None,
            "clauses": {},
            "reasons": ["synthétique"],
            "created_at": "2026-10-09T06:00:00Z",
        },
    )
    run_update(deps, RECORDED, replay=SameReplay(), measure=PreviewMeasure(tmp_path))
    old = measures(deps)["measures-1.60.1.70000-aaaaaaaaaaaa"]
    assert old["state"] == "périmée" and LOCAL_VERSION in old["stale_reason"]


def test_the_written_measure_is_a_revision_that_keeps_its_logs(tmp_path, data_copy):
    preview = tmp_path / "apercu"
    shutil.copytree(data_copy, preview)
    shas = {LOG.name: "0" * 64}
    revision = _measure_revision(preview, LOCAL_VERSION, shas, date="2026-10-10", command="forever update --auto")
    sources = json.loads((preview / LOCAL_VERSION / "sources.json").read_text(encoding="utf-8"))
    assert sources["revision"] == revision
    history = json.loads((preview / LOCAL_VERSION / "revisions.json").read_text(encoding="utf-8"))
    last = history["revisions"][-1]
    assert last["revision"] == revision and last["sources"]["logs"] == shas
    assert "mesure" in last["motif"]
    assert _written_logs(tmp_path / "cache", preview, LOCAL_VERSION)[LOG.name] == {"0" * 64}


def test_the_replay_keeps_the_advice_after_for_changed_cases(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    report = run_update(deps, JOURNALS, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path))
    builds = report["pending"][0]["summary"]["measures"]["builds"]
    assert builds["after"] == {f"mage_build:{CHANGED_CASE}": {"talents": "B"}}
