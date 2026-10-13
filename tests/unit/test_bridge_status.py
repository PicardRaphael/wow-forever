"""État des données écrit par le pont pour la fenêtre du jeu (P06a, bloc D) : version, fraîcheur, attentes de
`forever update`, sans réseau (client HTTP simulé en échec), sans jamais lever."""

import json
import os

from forever.bridge.status import status_line, status_payload
from forever.update import update_dir


def write_pending(cache_dir):
    pending = update_dir(cache_dir) / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": "p1",
        "kind": "revision",
        "action": "attente",
        "version": "1.60.1.70291",
        "state": "en_attente",
        "created_at": "2026-10-09T08:00:00Z",
        "summary": {"pvp": {"sentence": "fiches PvP : Warrior"}},
    }
    (pending / "p1.json").write_text(json.dumps(entry), encoding="utf-8")


def test_payload_and_line_with_one_pending(make_deps):
    deps = make_deps()
    write_pending(deps.cache_dir)
    payload = status_payload(deps)
    assert payload["version"] and payload["freshness"] in {"fresh", "stale", "silent", "unknown"}
    assert payload["pending"] == 1 and payload["pending_labels"] == ["fiches PvP : Warrior"]
    line = status_line(payload)
    assert line.startswith(f"Données {payload['version']} · ")
    # P06b (décision 235) : « n à valider » ne compte que les attentes approuvables ; « p1 » (genre inconnu) attend
    assert line.endswith("1 en attente")
    assert payload["line"] == line


def test_line_without_pending(make_deps):
    payload = status_payload(make_deps())
    assert payload["pending"] == 0
    assert "attente" not in status_line(payload)


def test_never_raises(make_deps, tmp_path):
    payload = status_payload(make_deps(data_dir=tmp_path / "absent"))
    assert payload["version"] is None
    assert status_line(payload).startswith("Données : état illisible")


# --- P06b, bloc B (décision 235) ------------------------------------------------------------------------------------


def put(cache_dir, **entry):
    pending = update_dir(cache_dir) / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    doc = {"action": "attente", "state": "en_attente", "created_at": "2026-10-10T08:00:00Z", **entry}
    (pending / f"{entry['id']}.json").write_text(json.dumps(doc), encoding="utf-8")


def base(**extra):
    return {"version": "1.60.1.70338", "freshness": "fresh", "integrity_ok": True, "client": "1.60.1.70338", **extra}


def test_line_counts_approvable_and_waiting_entries(make_deps):
    deps = make_deps()
    put(deps.cache_dir, id="measures-1.60.1.70338-a", kind="measures", version="1.60.1.70338")
    put(deps.cache_dir, id="network-1.60.1.70338", kind="network", version="1.60.1.70338")
    put(deps.cache_dir, id="hotfixes-1.60.1.70338", kind="hotfixes_unread", version="1.60.1.70338")
    put(deps.cache_dir, id="measures-old", kind="measures", version="1.60.1.70291", state="périmée")
    payload = status_payload(deps)
    assert (payload["approvable"], payload["waiting"]) == (1, 2)
    line = status_line({**base(), "approvable": payload["approvable"], "waiting": payload["waiting"]})
    assert line == "Données 1.60.1.70338 · client 1.60.1.70338 · à jour · 1 à valider · 2 en attente"


def test_newer_client_is_shown_with_the_wait():
    line = status_line(base(version="1.60.1.70291", approvable=0, waiting=1))
    assert line == "Données 1.60.1.70291 · client 1.60.1.70338 : mise à jour en attente · 1 en attente"


def test_running_pass_and_its_step(make_deps):
    from forever.update import update_dir as folder

    deps = make_deps()
    lock = folder(deps.cache_dir) / "lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    started = "2026-09-27T11:59:00Z"
    lock.write_text(json.dumps({"pid": os.getpid(), "command": "forever update --auto", "started_at": started,
                                "heartbeat": started, "step": "correctifs"}), encoding="utf-8")  # fmt: skip
    payload = status_payload(deps)
    assert payload["update"]["running"] is True and payload["update"]["step"] == "correctifs"
    assert "mise à jour en cours (lecture des correctifs du serveur)" in status_line(
        {**base(), "running": True, "update": payload["update"]}
    )


def test_last_pass_is_carried(make_deps):
    from forever.update import update_dir as folder

    deps = make_deps()
    last = folder(deps.cache_dir) / "last.json"
    last.parent.mkdir(parents=True, exist_ok=True)
    last.write_text(json.dumps({"started_at": "2026-09-27T11:00:00Z", "finished_at": "2026-09-27T11:05:00Z",
                                "written": [{"version": "1.60.1.70338", "revision": 2}]}), encoding="utf-8")  # fmt: skip
    put(deps.cache_dir, id="measures-1.60.1.70338-a", kind="measures", version="1.60.1.70338")
    update = status_payload(deps)["update"]
    assert update["running"] is False
    assert update["last"] == {
        "finished_at": "2026-09-27T11:05:00Z",
        "written": 1,
        "approvable": 1,
        "text": "Mise à jour terminée en 5 min : données installées",
    }
