"""Ligne d'état de la fenêtre (P06a, sonde en jeu E du 2026-10-09, point 6 ; revue en P06b, décision 235) : version du
client toujours affichée ; client plus récent que les données → « mise à jour en attente » au lieu de la fraîcheur ;
« à valider » pour les attentes approuvables, « en attente » pour les autres."""

from forever.bridge.status import status_line


def payload(**extra):
    return {"version": "1.60.1.70245", "freshness": "fresh", "running": False, "integrity_ok": True,
            **extra}  # fmt: skip


def test_client_newer_than_the_data():
    line = status_line(payload(client="1.60.1.70291", approvable=3))
    assert line == "Données 1.60.1.70245 · client 1.60.1.70291 : mise à jour en attente · 3 à valider"
    assert "à jour ·" not in line.replace("mise à jour", "")


def test_same_client_and_data():
    assert status_line(payload(client="1.60.1.70245")) == "Données 1.60.1.70245 · client 1.60.1.70245 · à jour"
    assert status_line(payload(client=None, approvable=1)) == "Données 1.60.1.70245 · à jour · 1 à valider"


def test_older_client_keeps_the_freshness():
    assert status_line(payload(client="1.60.1.70170")) == "Données 1.60.1.70245 · client 1.60.1.70170 · à jour"
