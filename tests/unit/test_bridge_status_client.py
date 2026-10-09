"""Ligne d'état de la fenêtre (P06a, sonde en jeu E du 2026-10-09, point 6) : client plus récent que les données →
les deux versions et « mise à jour en attente » au lieu de « à jour » ; attentes dites en clair pour le joueur."""

from forever.bridge.status import status_line


def payload(**extra):
    return {"version": "1.60.1.70245", "freshness": "fresh", "pending": 0, "running": False, "integrity_ok": True,
            **extra}  # fmt: skip


def test_client_newer_than_the_data():
    line = status_line(payload(client="1.60.1.70291", pending=3))
    assert (
        line
        == "Données 1.60.1.70245 · client 1.60.1.70291 : mise à jour en attente · 3 mises à jour à valider sur le PC"
    )
    assert "à jour ·" not in line.replace("mise à jour", "")


def test_same_client_and_data():
    assert status_line(payload(client="1.60.1.70245")) == "Données 1.60.1.70245 · à jour"
    assert (
        status_line(payload(client=None, pending=1))
        == "Données 1.60.1.70245 · à jour · 1 mise à jour à valider sur le PC"
    )


def test_older_client_keeps_the_freshness():
    assert status_line(payload(client="1.60.1.70170")) == "Données 1.60.1.70245 · à jour"
