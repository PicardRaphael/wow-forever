"""Mesures écrites d'elles-mêmes (décision 230, puis décision 295 : plus d'accord).

- Une mesure des journaux qui change la table des monstres s'écrit toujours (plus de rejeu des builds depuis RB1,
  décision 299) ; ce qui change est noté (`notes`) pour la carte « Mis à jour », jamais une attente.
- Une mesure remplacée par une autre de la même version passe à « périmée ».
- Une mesure écrite est une révision de la version installée dont `revisions.json` garde les journaux mesurés.

Mesure simulée, journaux du dépôt de fixtures ; aucun chiffre du jeu."""

import json
import shutil

from conftest import LOCAL_VERSION
from test_update_chain import LOG, NEWER, logs, step  # noqa: F401  (fixture importée)
from test_update_measures_summary import PreviewMeasure

from forever.update import (
    UpdateOptions,
    _measure_revision,
    _revision,
    _written_logs,
    list_pending,
    record_pending,
    run_update,
)

JOURNALS = UpdateOptions(dry_run=True, only=frozenset({"journaux"}))
# attentes enregistrées, hors réseau : aucun clone, rien n'est poussé
RECORDED = UpdateOptions(only=frozenset({"journaux"}), network=False)


def measures(deps):
    return {e["id"]: e for e in list_pending(deps.cache_dir) if e.get("kind") == "measures"}


def add_log(deps, name):
    shutil.copyfile(LOG, deps.wow_dir / "Logs" / name)


def measure_verdict(report):
    (verdict,) = [v for v in report["verdicts"] if v["kind"] == "measures"]
    return verdict


def test_a_measure_is_written_alone(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    # révision installée lue avant le passage : 1 sur main, 2 sur une branche de données qui porte déjà la r2
    installed = _revision(deps.data_dir, LOCAL_VERSION)
    report = run_update(deps, JOURNALS, measure=PreviewMeasure(tmp_path))
    found = step(report, "journaux")
    assert found["status"] == "fait", found
    assert "écriture simulée" in found["detail"]
    assert report["pending"] == []
    verdict = measure_verdict(report)
    assert verdict["action"] == "écrire" and verdict["reasons"] == []
    assert verdict["revision"] == installed + 1


def test_a_measure_without_preview_never_waits(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])

    def measure(deps, data_dir, files):  # aucun aperçu : rien n'est comparé
        return {"changed": [{"file": "monsters.json", "pointer": "/npcs"}], "preview": None}

    report = run_update(deps, JOURNALS, measure=measure)
    assert report["pending"] == []
    assert step(report, "journaux")["status"] != "attente"


def test_a_replaced_measure_is_stale(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    record_pending(
        deps.cache_dir,
        {"id": "measures-x-old", "kind": "measures", "action": "écrire", "version": LOCAL_VERSION, "revision": None,
         "clauses": {}, "reasons": [], "created_at": "2026-10-09T06:00:00Z"},
    )  # fmt: skip
    report = run_update(deps, RECORDED, measure=PreviewMeasure(tmp_path))
    new = measure_verdict(report)
    found = measures(deps)
    assert found["measures-x-old"]["state"] == "périmée" and new["id"] in found["measures-x-old"]["stale_reason"]


def test_a_measure_of_a_version_no_longer_installed_is_stale(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    record_pending(
        deps.cache_dir,
        {
            "id": "measures-1.60.1.70000-aaaaaaaaaaaa",
            "kind": "measures",
            "action": "écrire",
            "version": "1.60.1.70000",
            "revision": None,
            "clauses": {},
            "reasons": ["synthétique"],
            "created_at": "2026-10-09T06:00:00Z",
        },
    )
    run_update(deps, RECORDED, measure=PreviewMeasure(tmp_path))
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
