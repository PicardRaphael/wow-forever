"""Temps par monstre d'une feuille de route (RX1, bloc F) : relevés du joueur d'abord, moteur du Mage (combat, repos,
course) à défaut, sinon estimation « combat seul ». Le moteur est remplacé ici par une valeur de test (aucune
simulation lancée) ; addons synthétiques de `tests/fixtures/addons/dungeons/`."""

import pytest
from conftest import FIXTURES, isolated_deps

from forever.route import RouteRequest, route_context

WOW = FIXTURES / "addons" / "dungeons"
ENGINE = {"seconds": 77.0, "low": 77.0, "high": 77.0, "certainty": "probable", "method": "moteur de test"}


@pytest.fixture
def deps(tmp_path):
    return isolated_deps(tmp_path)


def test_mage_uses_the_engine_without_measures(deps, monkeypatch):
    from forever.sim import objectives

    calls = []
    monkeypatch.setattr(objectives, "_engine_kill_time", lambda _deps, level, _race: calls.append(level) or ENGINE)
    ctx = route_context(deps, RouteRequest("mage", "horde", 10, 12, dungeons="none"), wow_dir=WOW)
    k = ctx.kill(10)
    assert (k.source, k.seconds, k.scope, k.certainty) == ("engine", 77.0, "total", "probable")
    assert 10 in calls


def test_other_classes_keep_the_estimate(deps, monkeypatch):
    from forever.sim import objectives

    monkeypatch.setattr(objectives, "_engine_kill_time", lambda *_a: pytest.fail("moteur appelé pour un Chasseur"))
    ctx = route_context(deps, RouteRequest("hunter", "horde", 10, 12, dungeons="none"), wow_dir=WOW)
    k = ctx.kill(10)
    assert k.source == "estimated" and k.scope == "combat"
