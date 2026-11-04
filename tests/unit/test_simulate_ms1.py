"""`forever_simulate` et `forever sims` après MS1 (décision 301) :

- `talents` (« clé=rang,… », nos clés) sur `action="compare"` : légalité contrôlée au niveau 60 sur les arbres du
  client, puis chaîne du moteur par identifiant de sort ; build illégal refusé sans combat ;
- `engine` : `wowsims` (par défaut), `mythicsim` ou `both` (deux colonnes et leur écart, sans moyenne ni choix ; un
  refus d'un moteur n'efface pas l'autre colonne) ;
- `action="builds"` : recherche locale sur un préréglage, confirmation sur 10 000 combats, verdict ;
- provenance de chaque sortie : moteur, commit, empreinte, certitude `suppose`.

Clones, binaires et exécuteurs fabriqués (`wowsims_fakes`, `mythicsim_fakes`) ; aucun réseau."""

import json
import shutil

from conftest import FIXTURES
from mythicsim_fakes import Both, Engine, install
from wowsims_fakes import Sim, clone

from forever.cli import main
from forever.errors import ForeverError
from forever.provenance import validate_provenance
from forever.sims.report import simulate

# build Mage légal au niveau 60, en nos clés (chaîne du préréglage « Fire » de wowsims, client 70707)
FIRE = (
    "improvedChanneling=5,arcaneSubtlety=2,arcaneConcentration=5,missileBarrage=2,arcaneBlast=1,arcaneMeditation=1,"
    "incineration=5,improvedFireball=5,ignite=5,pyroblast=1,wakeOfFire=2,improvedScorch=3,hotStreak=1,"
    "masterOfElements=3,criticalMass=3,firePower=3,combustion=1,elementalPrecision=3"
)
FIRE_CODE = "0502052001001-55500001230133031-003"


def _setup(tmp_path, monkeypatch, engine=None):
    from forever.pipeline import gitops

    clone(tmp_path)
    install(tmp_path)
    shutil.copy(FIXTURES / "sims" / "wowsims" / "proto" / "mage.proto",
                tmp_path / "third_party" / "wowsims" / "forever" / "proto")  # fmt: skip
    sim, eng = Sim(), engine or Engine()
    monkeypatch.setattr(gitops, "subprocess_runner", Both(sim, eng))
    return sim, eng


def _talents(req):
    return req["raid"]["parties"][0]["players"][0]["talentsString"]


def test_compare_with_chosen_talents(tmp_path, make_deps, monkeypatch):
    sim, _ = _setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path)
    out = simulate(deps, "compare", cases="mage/dps/Fire@Gnome", talents=FIRE)
    assert _talents(sim.requests[0]) == FIRE_CODE  # ordre du proto de wowsims
    assert out["rows"][0]["talents"]["source"] == "talents"
    assert validate_provenance(out["provenance"]) == []


def test_illegal_talents_are_refused_without_a_fight(tmp_path, make_deps, monkeypatch):
    sim, _ = _setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path)
    try:
        simulate(deps, "compare", cases="mage/dps/Fire@Gnome", talents="arcanePower=1")
    except ForeverError as err:
        assert err.code == "invalid_argument" and "arcanePower" in err.message
    else:
        raise AssertionError("build illégal accepté")
    assert sim.requests == []


def test_both_engines_give_two_columns_and_the_gap(tmp_path, make_deps, monkeypatch):
    sim, eng = _setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path)
    out = simulate(deps, "compare", cases="mage/dps/Fire@Gnome", talents=FIRE, engine="both")
    row = out["rows"][0]
    assert row["wowsims"]["dps"] == 101.0 and row["mythicsim"]["dps"] == 200.0 and row["gap"] == 99.0
    assert _talents(sim.requests[0]) == _talents(eng.requests[0])  # mêmes talents des deux côtés
    notes = " ".join(out["provenance"]["assumptions"])
    assert "wowsims/forever" in notes and "MythicSim" in notes and "b" * 12 in notes
    assert validate_provenance(out["provenance"]) == []


def test_a_mythicsim_refusal_keeps_the_wowsims_column(tmp_path, make_deps, monkeypatch):
    _setup(tmp_path, monkeypatch, Engine(refuse=("item", "unknown item 18727")))
    deps = make_deps(cache_dir=tmp_path)
    out = simulate(deps, "compare", cases="mage/dps/Fire@Gnome", engine="both")
    row = out["rows"][0]
    assert row["wowsims"]["dps"] == 101.0 and row["gap"] is None
    assert row["mythicsim"]["error"]["code"] == "mythicsim_refused"
    assert "unknown item 18727" in row["mythicsim"]["error"]["message"]


def test_mythicsim_alone_says_its_refusal(tmp_path, make_deps, monkeypatch):
    _setup(tmp_path, monkeypatch, Engine(refuse=("talents", "Incineration has 5 ranks")))
    deps = make_deps(cache_dir=tmp_path)
    try:
        simulate(deps, "compare", cases="mage/dps/Fire@Gnome", engine="mythicsim")
    except ForeverError as err:
        assert err.code == "mythicsim_refused" and "Incineration has 5 ranks" in err.message
    else:
        raise AssertionError("refus de MythicSim effacé")


def test_builds_search_confirms_on_ten_thousand_fights(tmp_path, make_deps, monkeypatch):
    sim, _ = _setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path)
    out = simulate(deps, "builds", preset="mage/dps/Fire", race="Gnome", talents=FIRE, iterations=50,
                   max_steps=1, popular=False)  # fmt: skip
    assert out["level"] == 60 and out["engine"] == "wowsims"
    assert {r["simOptions"]["iterations"] for r in sim.requests} == {50, 10000}
    best = out["results"][0]
    assert best["verdict"] in ("meilleur", "non départagé") and "threshold" in best
    assert best["start"]["code"] == FIRE_CODE  # même talents : dégâts égaux (fabriqués)
    assert best["verdict"] == "non départagé"
    assert any("10 000" in a or "10000" in a for a in out["provenance"]["assumptions"])
    assert validate_provenance(out["provenance"]) == []


def test_cli_compare_and_update_report_both_engines(tmp_path, make_deps, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch)
    deps = make_deps(cache_dir=tmp_path)
    args = ["sims", "compare", "--cases", "mage/dps/Fire@Gnome", "--talents", FIRE, "--engine", "both"]
    assert main([*args, "--json"], deps) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["rows"][0]["mythicsim"]["dps"] == 200.0 and validate_provenance(doc["provenance"]) == []
    assert main(args, deps) == 0
    assert "MythicSim" in capsys.readouterr().out
    ws = {"commit": "c" * 40, "committed_at": "2026-10-21T12:00:00+02:00", "sha256": "d" * 64, "status": "à jour",
          "binary": "wowsimcli-cccccccccccc.exe", "go": "go1.27.0", "protoc": "36.0"}  # fmt: skip
    ms = {"commit": "e" * 40, "committed_at": "2026-11-04T15:39:27+11:00", "sha256": "9" * 64, "status": "compilé",
          "binary": "forever-engine-eeeeeeeeeeee.exe", "toolchain": "1.99.1", "go_revision": "f" * 40}  # fmt: skip
    monkeypatch.setattr("forever.pipeline.wowsims_build.update_wowsims", lambda cache_dir, **_: ws)
    monkeypatch.setattr("forever.pipeline.mythicsim_build.update_mythicsim", lambda cache_dir, **_: ms)
    assert main(["sims", "update"], deps) == 0
    text = capsys.readouterr().out
    assert "cccccccccccc" in text and "eeeeeeeeeeee" in text


def test_veille_replays_the_reference_cases_through_mythicsim(tmp_path, make_deps, monkeypatch):
    from forever import update
    from forever.pipeline import mythicsim_build, wowsims_build
    from forever.update import UpdateOptions

    _setup(tmp_path, monkeypatch)
    ws, ms = wowsims_build.pinned(tmp_path), mythicsim_build.pinned(tmp_path)
    monkeypatch.setattr(
        "forever.pipeline.wowsims_build.update_wowsims", lambda cache_dir, **_: {**ws, "status": "à jour"}
    )
    monkeypatch.setattr("forever.pipeline.mythicsim_build.update_mythicsim",
                        lambda cache_dir, **_: {**ms, "status": "compilé"})  # fmt: skip
    deps = make_deps(cache_dir=tmp_path)
    step = update._step_simulators(update._Run(deps, UpdateOptions(), None, None, None, deps.data_dir))
    assert step.status == "fait" and "MythicSim" in step.detail
    report = json.loads((tmp_path / "third_party" / "mythicsim" / "veille.json").read_text(encoding="utf-8"))
    assert report["commit"] == "b" * 40 and report["cases"]["mage/dps/Fire"] > 0
