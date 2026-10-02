"""Installation de la candidate du client dans la version courante (T06b, bloc B, décision D3) et données installées
en révision 2.

Les tests de `forever install` partent d'un état r1 reconstruit sur une copie des données (talents et sorts : copies
du seed, trace des révisions retirée) : ils restent valables une fois le dépôt en révision 2. Valeurs attendues :
`confirmed_changes.json` (15 écarts tranchés en T03), coûts `SpellPower.ManaCost` du client (constats du plan T06b),
estimation du seed `mana.talent_rank_cost` (0,75 × coût du premier rang publié)."""

import hashlib
import json
import shutil

import pytest
from conftest import (
    DATA_DIR,
    LOCAL_VERSION,
    PREVIOUS_VERSION,
    change_key,
    isolated_deps,
    read_json,
    seed_view,
)

from forever.cli import main, render_status
from forever.engine.buffs import hot_streak_rules
from forever.engine.character import character
from forever.engine.mana import mana_cost
from forever.errors import InvalidArgumentError
from forever.lookup import lookup_talent
from forever.manifest import compute_manifest, version_files, write_manifest
from forever.pipeline.diff import compare_data, diff_versions
from forever.pipeline.install import InstallRefusedError, apply_install, plan_install, render_install_report
from forever.provenance import make_provenance, validate_provenance
from forever.status import status_report
from forever.store import ensure_integrity, load_version

COUNTS = {"confirmed": 15, "observation": 3, "certainty": 49, "removed_field": 1, "refused": 0}
ADDED = {
    ("talents.json", "name_fr"): 54,
    ("talents.json", "tooltip_values"): 54,
    ("talents.json", "source"): 54,
    ("spells.json", "source"): 15,
}
COSTS = {"pyroblast": 125, "ice_lance": 45, "blast_wave": 215}  # SpellPower.ManaCost du client, rang 1
SEED_ESTIMATES = {"pyroblast": 112.5, "ice_lance": 41.25, "blast_wave": 202.5}  # 0,75 × premier rang publié
REPORT = "docs/research/data-1.60.1.70009-r2.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewind_to_r1(data):
    """État r1 sur une copie des données : talents.json et spells.json = copies du seed, confirmed_changes.json sans
    trace d'application ni observation installée, sources.json sans révision, pas de revisions.json."""
    v = data / PREVIOUS_VERSION
    shutil.copyfile(v / "_seed_talents.json", v / "talents.json")
    shutil.copyfile(v / "_seed_spells.json", v / "spells.json")
    confirmed = read_json(v / "confirmed_changes.json")
    confirmed["changes"] = [
        {k: x for k, x in c.items() if k != "applied_in_revision"} for c in confirmed["changes"] if c["old"] is not None
    ]
    (v / "confirmed_changes.json").write_bytes(json.dumps(confirmed, ensure_ascii=False, indent=1).encode("utf-8"))
    sources = read_json(v / "sources.json")
    sources.pop("revision", None)
    sources.pop("revised_at", None)
    (v / "sources.json").write_bytes(json.dumps(sources, ensure_ascii=False, indent=2).encode("utf-8"))
    (v / "revisions.json").unlink(missing_ok=True)
    write_manifest(data)


@pytest.fixture
def r1(tmp_path):
    """Dépôt ramené à 1.60.1.70009 en révision 1 : les versions plus récentes sont retirées, `forever install`
    (sans --new-version) révise la version courante et c'est celle-là qu'on teste ici (T06b)."""
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    for d in data.iterdir():
        if d.is_dir() and d.name != PREVIOUS_VERSION:
            shutil.rmtree(d)
    rewind_to_r1(data)
    write_manifest(data)
    return isolated_deps(tmp_path, data)


def cand(candidate):
    return str(candidate.root)


def test_plan_lists_exactly_the_allowed_changes(r1, candidate):
    plan = plan_install(r1, cand(candidate))
    assert {k: plan["counts"][k] for k in COUNTS} == COUNTS
    assert plan["counts"]["metadata"] == 0
    assert (plan["revision_from"], plan["revision_to"]) == (1, 2)
    added = {}
    for c in plan["changes"]:
        if c["rule"] == "added_field":
            key = (c["file"], c["path"].split(".", 1)[1])
            added[key] = added.get(key, 0) + 1
    assert added == ADDED
    confirmed = read_json(r1.data_dir / PREVIOUS_VERSION / "confirmed_changes.json")["changes"]
    wanted = {(c["kind"] + "s.json", f"{c['key']}.{c['field']}", json.dumps(c["new"])) for c in confirmed}
    got = {(c["file"], c["path"], json.dumps(c["after"])) for c in plan["changes"] if c["rule"] == "confirmed"}
    assert got == wanted
    costs = {c["path"]: c["after"] for c in plan["changes"] if c["rule"] == "observation"}
    assert costs == {f"{k}.ranks[1].mana": v for k, v in COSTS.items()}
    removed = [(c["path"], c["before"]) for c in plan["changes"] if c["rule"] == "removed_field"]
    assert removed == [("hotStreak.duration_s", 20)]
    assert all(c["source"] and c["certainty"] == "certain" for c in plan["changes"] if c["rule"] != "game_state")
    assert {c["path"] for c in plan["changes"] if c["rule"] == "game_state"} == {"values.build.beta_level_cap"}


def test_plan_writes_nothing(r1, candidate):
    before = version_files(r1.data_dir / PREVIOUS_VERSION)
    plan_install(r1, cand(candidate))
    assert version_files(r1.data_dir / PREVIOUS_VERSION) == before


def test_change_outside_the_rules_is_refused(r1, candidate, tmp_path):
    copy = tmp_path / "cand"
    shutil.copytree(candidate.root, copy)
    path = copy / PREVIOUS_VERSION / "talents.json"
    doc = read_json(path)
    t = next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == "improvedFrostbolt")
    t["ranks"][0] = [9]
    path.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    write_manifest(copy)
    plan = plan_install(r1, str(copy))
    assert [(c["path"], c["before"], c["after"]) for c in plan["refused"]] == [
        ("improvedFrostbolt.ranks[1]", [0.1], [9])
    ]
    before = version_files(r1.data_dir / PREVIOUS_VERSION)
    with pytest.raises(InstallRefusedError):
        apply_install(r1, str(copy), motif="test")
    assert version_files(r1.data_dir / PREVIOUS_VERSION) == before


def test_candidate_of_another_version_is_refused(r1, candidate, tmp_path):
    copy = tmp_path / "cand"
    shutil.copytree(candidate.root, copy)
    (copy / PREVIOUS_VERSION).rename(copy / "1.60.1.70150")
    write_manifest(copy)
    with pytest.raises(InvalidArgumentError):
        plan_install(r1, str(copy))


def test_apply_writes_revision_two(r1, candidate):
    seed_before = {n: sha(r1.data_dir / PREVIOUS_VERSION / n) for n in ("_seed_talents.json", "_seed_spells.json")}
    rev = apply_install(r1, cand(candidate), motif="valeurs du client", report=REPORT, date="2026-09-29")
    assert rev["revision"] == 2 and rev["report"] == REPORT
    ensure_integrity(r1.data_dir)
    v = r1.data_dir / PREVIOUS_VERSION
    history = read_json(v / "revisions.json")
    assert [r["revision"] for r in history["revisions"]] == [1, 2]
    assert history["revisions"][1]["counts"]["confirmed"] == 15
    sources = read_json(v / "sources.json")
    assert (sources["revision"], sources["revised_at"]) == (2, "2026-09-29")
    assert compute_manifest(r1.data_dir)["versions"][PREVIOUS_VERSION]["revision"] == 2
    assert {n: sha(v / n) for n in seed_before} == seed_before
    confirmed = read_json(v / "confirmed_changes.json")["changes"]
    assert len(confirmed) == 18 and all(c["applied_in_revision"] == 2 for c in confirmed)
    p = lookup_talent(r1, "Hot Streak")["provenance"]
    assert p["data_revision"] == 2 and validate_provenance(p) == []
    # Idempotence : la même candidate ne change plus rien.
    plan = plan_install(r1, cand(candidate))
    assert sum(plan["counts"].values()) == 0
    with pytest.raises(InvalidArgumentError):
        apply_install(r1, cand(candidate), motif="deux fois")


def test_report_is_markdown_with_every_value(r1, candidate):
    text = render_install_report(plan_install(r1, cand(candidate)))
    assert text.startswith(f"# data: {PREVIOUS_VERSION} r1 → r2")
    for path in ("impact.ranks[2]", "hotStreak.ranks[1]", "hotStreak.duration_s", "blast_wave.ranks[1].level"):
        assert path in text, path
    for key, cost in COSTS.items():
        assert f"| {key}.ranks[1].mana | — | `{cost}` |" in text, key
    assert text.rstrip().splitlines()[-1].startswith("Provenance")


def test_cli_dry_run_writes_only_the_report(r1, candidate, tmp_path, capsys):
    out = tmp_path / "rapport.md"
    before = version_files(r1.data_dir / PREVIOUS_VERSION)
    code = main(["install", cand(candidate), "--dry-run", "--report", str(out)], deps=r1)
    assert code == 0
    assert version_files(r1.data_dir / PREVIOUS_VERSION) == before
    assert out.read_text(encoding="utf-8").startswith(f"# data: {PREVIOUS_VERSION} r1 → r2")
    assert "simulation" in capsys.readouterr().out


def test_cli_without_consent_writes_nothing(r1, candidate, capsys):
    before = version_files(r1.data_dir / PREVIOUS_VERSION)
    assert main(["install", cand(candidate)], deps=r1) == 0
    assert version_files(r1.data_dir / PREVIOUS_VERSION) == before
    assert "refusé" in capsys.readouterr().out


def test_cli_yes_installs(r1, candidate, capsys):
    assert main(["install", cand(candidate), "--yes", "--json"], deps=r1) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "écrit" and payload["revision"]["revision"] == 2
    assert validate_provenance(payload["provenance"]) == []


def test_cli_report_never_goes_into_the_data(r1, candidate):
    target = r1.data_dir / PREVIOUS_VERSION / "rapport.md"
    assert main(["install", cand(candidate), "--dry-run", "--report", str(target)], deps=r1) != 0
    assert not target.exists()


# --- Données installées (dépôt en révision 2) ----------------------------------------------------------------


def test_repository_is_revision_two(make_deps):
    v = DATA_DIR / PREVIOUS_VERSION
    history = read_json(v / "revisions.json")
    assert [r["revision"] for r in history["revisions"]] == [1, 2]
    assert history["revisions"][1]["report"] == REPORT
    assert (DATA_DIR.parent.parent / REPORT).is_file()
    assert read_json(v / "sources.json")["revision"] == 2
    deps = make_deps()
    p = make_provenance(
        deps, game_version=LOCAL_VERSION, data_sha="0" * 12, freshness="fresh", certainty="certain", assumptions=[]
    )
    # T08a : la version installée est 1.60.1.70124 (une nouvelle version repart à 1) ; PV1 : révisions 2 et 3.
    assert p["data_revision"] == 1  # 1.60.1.70170 installée le 2026-10-02 (nouvelle version : révision 1)


def test_every_talent_is_certain(make_deps, game_data):
    # La certitude nomme le build où la valeur a été lue : relue en 1.60.1.70124 à l'installation (T08a).
    build = "FC-" + LOCAL_VERSION.rsplit(".", 1)[-1]
    for key in game_data.talents:
        res = lookup_talent(make_deps(), key)
        assert res["source"] == build, key
        assert res["provenance"]["certainty"] == "certain", key
        assert all("$" not in r["description"] for r in res["ranks"]), key


def test_hot_streak_lasts_twenty_seconds_everywhere(make_deps, game_data):
    assert game_data.talents["hotStreak"].duration_s is None
    assert hot_streak_rules(game_data, {"hotStreak": 1}) == (20.0, 0.25, 3)
    assert all(15 not in r for r in game_data.talents["hotStreak"].ranks)
    res = lookup_talent(make_deps(), "Hot Streak")
    assert res["ranks"][0]["values"][0] == 20
    assert not any("durée corrigée" in a for a in res["provenance"]["assumptions"])


def test_installed_client_values(game_data):
    t = game_data.talents
    assert [r[0] for r in t["impact"].ranks[1:]] == [7, 10]
    assert t["improvedScorch"].ranks[1] == (67,)
    assert t["improvedBlizzard"].ranks[1] == (25,)
    assert t["presenceOfMind"].ranks[0] == ()
    assert game_data.spells["blast_wave"].ranks[0].level == 30
    for key, cost in COSTS.items():
        assert game_data.spells[key].ranks[0].mana == cost, key


def test_forever_uses_client_costs_and_seed_keeps_its_estimate(game_data, seed_game_data):
    for key, cost in COSTS.items():
        forever = game_data.spells[key].ranks[0]
        assert mana_cost(game_data, key, forever, {}, character(game_data, forever.level)) == cost, key
        seed = seed_game_data.spells[key].ranks[0]
        assert seed.mana is None, key
        estimate = mana_cost(seed_game_data, key, seed, {}, character(seed_game_data, seed.level))
        assert estimate == pytest.approx(SEED_ESTIMATES[key], rel=1e-12), key


def test_client_decode_matches_the_installed_data(make_deps, candidate):
    d = diff_versions(make_deps(), PREVIOUS_VERSION, cand(candidate))
    assert [
        c for c in d["changes"] if c["kind"] != "file" and not (c["kind"] == "scaling" and c["change"] == "added")
    ] == []


def test_client_decode_against_the_seed_copies_is_the_confirmed_list(tmp_path, candidate):
    client = load_version(isolated_deps(tmp_path, candidate.root))
    changes = [c for c in compare_data(seed_view(tmp_path), client) if c["kind"] != "file"]
    confirmed = read_json(DATA_DIR / PREVIOUS_VERSION / "confirmed_changes.json")["changes"]
    assert len(confirmed) == 18
    assert sorted(map(change_key, changes)) == sorted(map(change_key, confirmed))


def test_status_shows_the_revision(make_deps):
    rep = status_report(make_deps(), allow_network=False)
    assert rep["data_revision"] == 1  # 1.60.1.70170 installée le 2026-10-02 (nouvelle version : révision 1)
    assert render_status(rep)[0].startswith(f"Données locales {LOCAL_VERSION} r1 ·")
