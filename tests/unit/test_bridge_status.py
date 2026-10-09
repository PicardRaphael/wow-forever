"""État des données écrit par le pont pour la fenêtre du jeu (P06a, bloc D) : version, fraîcheur, attentes de
`forever update`, sans réseau (client HTTP simulé en échec), sans jamais lever."""

import json

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
    assert line.endswith("1 mise à jour à valider sur le PC")  # texte demandé par l'utilisateur, sonde E (point 6)
    assert payload["line"] == line


def test_line_without_pending(make_deps):
    payload = status_payload(make_deps())
    assert payload["pending"] == 0
    assert "attente" not in status_line(payload)


def test_never_raises(make_deps, tmp_path):
    payload = status_payload(make_deps(data_dir=tmp_path / "absent"))
    assert payload["version"] is None
    assert status_line(payload).startswith("Données : état illisible")
