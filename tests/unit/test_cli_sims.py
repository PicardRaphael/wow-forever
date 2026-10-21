"""Commande `forever sims` (plan des simulateurs §7) : `update` compile et épingle wowsims/forever, `presets` liste les
préréglages du dépôt épinglé, `races` compare les races au niveau 60 sur un préréglage ; chaque sortie porte la
provenance (commit et empreinte du binaire, certitude `suppose`). Clone, binaire et exécuteur fabriqués (voir
`test_wowsims_run`) ; aucun réseau."""

import json

from test_wowsims_run import Sim, clone

from forever.cli import main


def test_presets_and_races(tmp_path, make_deps, monkeypatch, capsys):
    from forever.pipeline import gitops

    clone(tmp_path)
    monkeypatch.setattr(gitops, "subprocess_runner", Sim())
    deps = make_deps(cache_dir=tmp_path)
    assert main(["sims", "presets", "--json"], deps) == 0
    keys = [p["key"] for p in json.loads(capsys.readouterr().out)["presets"]]
    assert "mage/dps/Fire" in keys and "shaman/elemental/testing" in keys
    assert (
        main(["sims", "races", "--preset", "mage/dps/Fire", "--races", "Human,Gnome,High Order Skyborne", "--json"])
        == 0
    )
    out = json.loads(capsys.readouterr().out)
    assert [r["race"] for r in out["races"]] == ["RaceHighOrderSkyborne", "RaceGnome", "RaceHuman"]
    assert out["provenance"]["certainty"] == "suppose"
    assert any("wowsims/forever" in a and "a" * 12 in a for a in out["provenance"]["assumptions"])


def test_update_reports_the_pin(tmp_path, make_deps, monkeypatch, capsys):
    pin = {"commit": "c" * 40, "committed_at": "2026-10-21T12:00:00+02:00", "sha256": "d" * 64, "status": "compilé",
           "binary": "wowsimcli-cccccccccccc.exe", "go": "go1.27.0", "protoc": "36.0"}  # fmt: skip
    monkeypatch.setattr("forever.pipeline.wowsims_build.update_wowsims", lambda cache_dir, **_: pin)
    deps = make_deps(cache_dir=tmp_path)
    assert main(["sims", "update"], deps) == 0
    assert "cccccccccccc" in capsys.readouterr().out
