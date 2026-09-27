"""`forever sim leveling` et `forever chart leveling` (bloc F du plan T04b) : sorties texte et JSON, provenance,
codes de sortie, aucun appel réseau, `forever/data/` inchangé. PV du niveau 12 : `monsters.json` installé (272,
mesuré)."""

import hashlib
import json

import pytest
from conftest import FakeHttp

from forever.cli import main
from forever.provenance import validate_provenance
from forever.sim.leveling_analytic import kill_analytic
from forever.sim.leveling_mc import mc

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def tree_sha(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode() + p.read_bytes())
    return h.hexdigest()


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def test_sim_leveling_json(capsys, make_deps, data_copy, game_data):
    http = FakeHttp.failing()
    deps = make_deps(http=http, data_dir=data_copy)
    before = tree_sha(data_copy)
    argv = ["sim", "leveling", "--level", "12", "--talents", "improvedFrostbolt=3", "--n", "200", "--json"]
    code, out, _ = run(capsys, argv, deps)
    assert code == 0
    payload = json.loads(out)
    assert (payload["level"], payload["race"], payload["rotation"]) == (12, "Orc", "frost")
    assert payload["talents"] == {"improvedFrostbolt": 3}
    assert payload["mob_hp"] == {
        "level": 12,
        "value": 272,
        "certainty": "certain",
        "source": payload["mob_hp"]["source"],
    }
    assert payload["options"]["mob_source"] == "measured" and payload["options"]["spell_level"] == "character"
    expected = mc(game_data, 12, {"improvedFrostbolt": 3}, n=200)
    assert payload["monte_carlo"] == pytest.approx(expected, rel=1e-12)
    assert payload["analytic"] == pytest.approx(kill_analytic(game_data, 12, {"improvedFrostbolt": 3}), rel=1e-12)
    assert payload["analytic_gap"] == pytest.approx(payload["analytic"]["total"] / expected["total"] - 1, rel=1e-12)
    prov = payload["provenance"]
    assert validate_provenance(prov) == [] and prov["certainty"] == "suppose"
    assert any("mob_source measured" in a for a in prov["assumptions"])
    assert http.calls == [] and tree_sha(data_copy) == before


def test_sim_leveling_seed_mode_matches_the_simulators(capsys, make_deps, game_data):
    argv = ["sim", "leveling", "--level", "16", "--talents", "improvedFrostbolt=5,elementalPrecision=2"]
    argv += ["--n", "150", "--seed", "4", "--mob-source", "seed", "--spell-level", "rank", "--level-diff", "1"]
    code, out, _ = run(capsys, [*argv, "--json"], make_deps())
    assert code == 0
    payload = json.loads(out)
    pts = {"improvedFrostbolt": 5, "elementalPrecision": 2}
    options = {"mob_source": "seed", "spell_level": "rank", "level_diff": 1}
    assert payload["monte_carlo"] == pytest.approx(mc(game_data, 16, pts, n=150, seed=4, **options), rel=1e-12)
    assert payload["mob_hp"]["level"] == 17 and payload["mob_hp"]["certainty"] == "suppose"


def test_sim_leveling_text(capsys, make_deps):
    code, out, _ = run(capsys, ["sim", "leveling", "--level", "12", "--n", "50", "--nova"], make_deps())
    assert code == 0
    lines = out.rstrip().splitlines()
    assert lines[-1].startswith("Provenance") and any("Monte Carlo" in line for line in lines)


@pytest.mark.parametrize(
    ("argv", "code", "error"),
    [
        (["--level", "12", "--talents", "improvedFrostbolt=5"], 2, "invalid_argument"),  # 3 points au niveau 12
        (["--level", "12", "--talents", "improvedFrostbolt"], 2, "invalid_argument"),
        (["--level", "12", "--talents", "inconnu=1"], 2, "invalid_argument"),
        (["--level", "0"], 2, "invalid_argument"),
        (["--level", "12", "--n", "0"], 2, "invalid_argument"),
        (["--level", "60", "--level-diff", "40"], 2, "invalid_argument"),
    ],
)
def test_sim_leveling_errors(capsys, make_deps, argv, code, error):
    got, out, _ = run(capsys, ["sim", "leveling", *argv, "--json"], make_deps())
    assert got == code and json.loads(out)["error"]["code"] == error


def test_chart_leveling(capsys, make_deps, data_copy, tmp_path):
    http = FakeHttp.failing()
    deps = make_deps(http=http, data_dir=data_copy)
    before = tree_sha(data_copy)
    out_png = tmp_path / "leveling.png"
    argv = ["chart", "leveling", "--out", str(out_png), "--from", "10", "--to", "13", "--n", "30"]
    argv += ["--talents", "improvedFrostbolt=3", "--json"]
    code, out, _ = run(capsys, argv, deps)
    assert code == 0
    payload = json.loads(out)
    assert payload["path"] == str(out_png) and out_png.read_bytes().startswith(PNG_SIGNATURE)
    assert [p["level"] for p in payload["levels"]] == [12, 13]
    assert [o["level"] for o in payload["omitted"]] == [10, 11]  # 3 points de talent seulement au niveau 12
    assert validate_provenance(payload["provenance"]) == []
    assert any("niveau 10 omis" in a for a in payload["provenance"]["assumptions"])
    assert http.calls == [] and tree_sha(data_copy) == before


def test_chart_leveling_refuses_to_write_into_the_data(capsys, make_deps, data_copy):
    argv = ["chart", "leveling", "--out", str(data_copy / "x.png"), "--from", "12", "--to", "12", "--n", "5", "--json"]
    code, out, _ = run(capsys, argv, make_deps(data_dir=data_copy))
    assert code == 2 and json.loads(out)["error"]["code"] == "invalid_argument"


def test_chart_leveling_bad_range(capsys, make_deps, tmp_path):
    argv = ["chart", "leveling", "--out", str(tmp_path / "x.png"), "--from", "20", "--to", "10", "--json"]
    code, out, _ = run(capsys, argv, make_deps())
    assert code == 2 and json.loads(out)["error"]["code"] == "invalid_argument"
