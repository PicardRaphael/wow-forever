"""Un journal n'est noté comme mesuré qu'après l'écriture de sa mesure (T08d, demande de l'utilisateur du 2026-10-06).

Avant la correction, `forever update` inscrivait un journal dans `logs_measured` dès qu'il l'avait mesuré, avant tout
accord : une attente rejetée ou périmée ne le reproposait jamais. Désormais, un journal est déjà mesuré seulement si
sa mesure est écrite, c'est-à-dire si son empreinte actuelle figure dans l'instantané de `forever measures refresh`
(`<cache>/measures/last.json`, écrit avec les données) ou dans les sources d'une révision de la version installée ;
un journal qui a grossi depuis est reproposé."""

import hashlib
import json

from conftest import LOCAL_VERSION
from test_update_chain import LOG, Measure, Replay, logs, step  # noqa: F401  (fixture importée)

from forever.update import UpdateOptions, record_pending, reject, run_update

PASS = UpdateOptions(network=False, only=frozenset({"journaux"}))
ENGINE_CHANGE = [{"file": "monsters.json", "pointer": "/hp_curve"}]


def written(deps, name, sha, version=LOCAL_VERSION):
    """Instantané de `forever measures refresh` après écriture : journaux et empreintes."""
    path = deps.cache_dir / "measures" / "last.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"schema_version": 1, "game_version": version, "sources": {"logs": {name: sha}, "saved_variables": {}}}
    path.write_text(json.dumps(doc), encoding="utf-8")


def sha_of(deps):
    return hashlib.sha256((deps.wow_dir / "Logs" / LOG.name).read_bytes()).hexdigest()


def run(deps, measure):
    report = run_update(deps, PASS, replay=Replay(), measure=measure)
    for entry in report["pending"]:
        record_pending(deps.cache_dir, entry)
    return report


def test_a_waiting_measure_is_proposed_again_at_the_next_pass(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    measure = Measure(ENGINE_CHANGE)
    first = run(deps, measure)
    second = run(deps, measure)
    assert measure.calls == [[LOG.name], [LOG.name]]
    assert step(second, "journaux")["status"] == "attente"
    assert [p["id"] for p in second["pending"]] == [p["id"] for p in first["pending"]]


def test_a_rejected_measure_is_proposed_again(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    measure = Measure(ENGINE_CHANGE)
    entry = run(deps, measure)["pending"][0]
    reject(deps.cache_dir, entry["id"], "essai")
    run(deps, measure)
    assert measure.calls == [[LOG.name], [LOG.name]]


def test_a_log_whose_measure_is_written_is_not_measured_again(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    written(deps, LOG.name, sha_of(deps))
    measure = Measure(ENGINE_CHANGE)
    report = run(deps, measure)
    assert measure.calls == []
    assert step(report, "journaux")["status"] == "rien"


def test_a_log_that_grew_after_its_measure_is_proposed_again(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    written(deps, LOG.name, "0" * 64)  # empreinte d'une version plus courte du journal
    measure = Measure(ENGINE_CHANGE)
    run(deps, measure)
    assert measure.calls == [[LOG.name]]


def test_a_measure_written_for_another_version_does_not_count(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    written(deps, LOG.name, sha_of(deps), version="1.60.1.69999")
    measure = Measure(ENGINE_CHANGE)
    run(deps, measure)
    assert measure.calls == [[LOG.name]]
