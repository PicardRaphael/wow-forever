"""Attentes de mesure d'une version qui n'est plus installée (décision 230) : `périmée` à chaque passage réel qui
atteint l'étape des journaux, même sans aucun nouveau journal à mesurer."""

from conftest import LOCAL_VERSION
from test_update_chain import logs  # noqa: F401  (fixture importée)

from forever.update import UpdateOptions, list_pending, record_pending, run_update

RECORDED = UpdateOptions(only=frozenset({"journaux"}), network=False)


def test_a_stale_measure_closes_even_without_a_new_log(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    for path in (deps.wow_dir / "Logs").iterdir():
        path.unlink()  # aucun journal : l'étape n'a rien à mesurer
    record_pending(
        deps.cache_dir,
        {
            "id": "measures-1.60.1.70000-bbbbbbbbbbbb",
            "kind": "measures",
            "action": "attente",
            "version": "1.60.1.70000",
            "revision": None,
            "clauses": {},
            "reasons": ["synthétique"],
            "created_at": "2026-10-09T06:00:00Z",
        },
    )
    run_update(deps, RECORDED)
    (entry,) = [e for e in list_pending(deps.cache_dir) if e["id"] == "measures-1.60.1.70000-bbbbbbbbbbbb"]
    assert entry["state"] == "périmée" and LOCAL_VERSION in entry["stale_reason"]
