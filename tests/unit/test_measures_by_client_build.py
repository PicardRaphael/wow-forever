"""Une mesure n'est jamais attribuée à une autre version du jeu (T08a, bloc C, décision 135).

`forever logs scan` relève la version du client (`.build.info`) et attribue chaque journal à la version en vigueur
à son début. `forever measures refresh` ne mesure que les journaux de la version installée et **liste** les autres
au lieu de les écrire en silence dans les données d'une version qui ne les a pas produits.

Les journaux de fixtures sont datés ; les dates de mise à jour du client sont inventées pour le test, de part et
d'autre de ces dates."""

import json
from datetime import UTC, datetime

from conftest import COMBATLOG, LOCAL_VERSION, PREVIOUS_VERSION, read_json

from forever.cli import main
from forever.pipeline.client_builds import JOURNAL_NAME, ClientBuild, load_builds, record_build

HEADER = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"


def wow_dir_with(tmp_path, version):
    """Faux dossier de client : `Logs/` avec les journaux de fixtures, `.build.info` à la racine."""
    root = tmp_path / "World of Warcraft"
    client = root / "_classic_beta_"
    logs = client / "Logs"
    logs.mkdir(parents=True, exist_ok=True)
    for path in sorted(COMBATLOG.glob("WoWCombatLog-*.txt")):
        (logs / path.name).write_bytes(path.read_bytes())
    (root / ".build.info").write_text(f"{HEADER}\nus|1|{version}|wow_classic_beta\n", encoding="utf-8")
    return client


def scan(deps, wow_dir, capsys, extra=()):
    code = main(["logs", "scan", "--dir", str(wow_dir / "Logs"), "--json", *extra], deps)
    out = capsys.readouterr().out
    assert code == 0, out
    return json.loads(out)


def test_scan_records_the_client_build(tmp_path, make_deps, capsys):
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir)
    scan(deps, wow_dir, capsys)
    assert [e.build for e in load_builds(deps.cache_dir)] == [LOCAL_VERSION]


def test_scan_gives_each_log_its_client_version(tmp_path, make_deps, capsys):
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir)
    # Le client est passé à la version installée bien après les journaux de fixtures.
    record_build(deps.cache_dir, ClientBuild(PREVIOUS_VERSION, datetime(2026, 9, 1, tzinfo=UTC), "wow_classic_beta"))
    payload = scan(deps, wow_dir, capsys)
    versions = {log["client_version"] for log in payload["logs"] if log["start"]}
    assert versions == {PREVIOUS_VERSION}


def test_a_log_written_before_any_reading_has_no_version(tmp_path, make_deps, capsys):
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir)
    # Première lecture : le client vient d'être relevé, les journaux lui sont antérieurs.
    payload = scan(deps, wow_dir, capsys)
    assert all(log["client_version"] is None for log in payload["logs"] if log["start"])


def test_the_truncated_header_is_never_used_to_attribute(tmp_path, make_deps, capsys):
    """L'entête dit « 1.60.1 » : ce n'est pas une version complète et elle ne doit jamais servir d'attribution."""
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir)
    payload = scan(deps, wow_dir, capsys)
    for log in payload["logs"]:
        if log["build"] is not None:
            assert log["build"] == "1.60.1"
            assert log["client_version"] != log["build"]


def test_refresh_refuses_logs_of_another_version(tmp_path, make_deps, capsys, data_copy):
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir, data_dir=data_copy)
    # Les journaux datent d'avant la version installée : ils appartiennent à la version précédente.
    record_build(deps.cache_dir, ClientBuild(PREVIOUS_VERSION, datetime(2026, 9, 1, tzinfo=UTC), "wow_classic_beta"))
    record_build(deps.cache_dir, ClientBuild(LOCAL_VERSION, datetime(2026, 9, 30, tzinfo=UTC), "wow_classic_beta"))
    code = main(["measures", "refresh", "--logs", str(wow_dir / "Logs"), "--dry-run", "--json"], deps)
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    held = payload["diff"]["measures"]["held_back"]
    assert held, payload["diff"]["measures"]
    assert {h["client_version"] for h in held} == {PREVIOUS_VERSION}
    assert all(LOCAL_VERSION in h["reason"] for h in held)


def test_refresh_measures_logs_of_the_installed_version(tmp_path, make_deps, capsys, data_copy):
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir, data_dir=data_copy)
    record_build(deps.cache_dir, ClientBuild(LOCAL_VERSION, datetime(2026, 9, 1, tzinfo=UTC), "wow_classic_beta"))
    code = main(["measures", "refresh", "--logs", str(wow_dir / "Logs"), "--dry-run", "--json"], deps)
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["diff"]["measures"]["held_back"] == []


def test_refresh_measures_a_log_of_unknown_version_and_says_so(tmp_path, make_deps, capsys, data_copy):
    """Journal antérieur au premier relevé de `.build.info` : on ne sait pas de quelle version il vient. Il est
    mesuré quand même — l'écarter serait aussi faux que l'attribuer — et l'incertitude est dite."""
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir, data_dir=data_copy)
    code = main(["measures", "refresh", "--logs", str(wow_dir / "Logs"), "--dry-run", "--json"], deps)
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["diff"]["measures"]["held_back"] == []
    notes = payload["provenance"]["assumptions"]
    assert any("version du client" in note for note in notes), notes


def test_a_measure_carried_from_another_version_keeps_its_origin(make_deps):
    """`monsters.json` reporté par l'installation d'une nouvelle version garde la version qui l'a mesuré."""
    sources = read_json(make_deps().data_dir / LOCAL_VERSION / "sources.json")
    entry = sources["files"]["monsters.json"]
    assert PREVIOUS_VERSION in json.dumps(entry, ensure_ascii=False)


def test_the_journal_lives_in_the_cache_not_in_the_data(tmp_path, make_deps, capsys):
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir)
    scan(deps, wow_dir, capsys)
    assert (deps.cache_dir / JOURNAL_NAME).is_file()
    assert not any(deps.data_dir.rglob(JOURNAL_NAME))


# --- Mesures d'une version antérieure acceptées, explicitement et avec trace (2026-10-09) ------------------------
# Demande de l'utilisateur : les journaux de 1.60.1.70245 (PNJ de Dun Morogh, Coldridge et Ragefire Chasm) passent dans
# 1.60.1.70291, la note du 08/10 ne touchant pas ces monstres. Option explicite, raison obligatoire, trace écrite.

REASON = "note officielle sans changement de ces monstres (test)"


def earlier_deps(tmp_path, make_deps, data_copy):
    wow_dir = wow_dir_with(tmp_path, LOCAL_VERSION)
    deps = make_deps(wow_dir=wow_dir, data_dir=data_copy)
    record_build(deps.cache_dir, ClientBuild(PREVIOUS_VERSION, datetime(2026, 9, 1, tzinfo=UTC), "wow_classic_beta"))
    record_build(deps.cache_dir, ClientBuild(LOCAL_VERSION, datetime(2026, 9, 30, tzinfo=UTC), "wow_classic_beta"))
    return deps, wow_dir


def test_accepting_an_earlier_version_needs_a_reason(tmp_path, make_deps, capsys, data_copy):
    deps, wow_dir = earlier_deps(tmp_path, make_deps, data_copy)
    args = ["measures", "refresh", "--logs", str(wow_dir / "Logs"), "--dry-run", "--accept-version", PREVIOUS_VERSION]
    assert main(args, deps) != 0
    assert "--accept-reason" in capsys.readouterr().err


def test_logs_of_the_accepted_earlier_version_are_measured_and_traced(tmp_path, make_deps, capsys, data_copy):
    deps, wow_dir = earlier_deps(tmp_path, make_deps, data_copy)
    code = main(
        [
            "measures",
            "refresh",
            "--logs",
            str(wow_dir / "Logs"),
            "--accept-version",
            PREVIOUS_VERSION,
            "--accept-reason",
            REASON,
            "--yes",
            "--json",
        ],
        deps,
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["diff"]["measures"]["held_back"] == []
    accepted = payload["diff"]["measures"]["accepted_earlier"]
    assert accepted and {a["client_version"] for a in accepted} == {PREVIOUS_VERSION}
    assert all(a["reason"] == REASON for a in accepted)
    assert set(payload["sources"]["logs"]) >= {a["name"] for a in accepted}
    if payload["status"] == "écrit":
        monsters = read_json(data_copy / LOCAL_VERSION / "monsters.json")
        assert any(PREVIOUS_VERSION in n and REASON in n for n in monsters["notes"])
        source = read_json(data_copy / LOCAL_VERSION / "sources.json")["files"]["monsters.json"]["source"]
        assert PREVIOUS_VERSION in source and REASON in source


def test_a_later_version_is_never_accepted(tmp_path, make_deps, capsys, data_copy):
    deps, wow_dir = earlier_deps(tmp_path, make_deps, data_copy)
    later = "1.60.1.99250"
    args = ["measures", "refresh", "--logs", str(wow_dir / "Logs"), "--dry-run", "--accept-version", later]
    assert main([*args, "--accept-reason", REASON], deps) != 0
    assert "antérieure" in capsys.readouterr().err
