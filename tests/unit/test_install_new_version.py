"""Installation d'une **nouvelle version** du jeu (T08a, bloc A, décision 134).

`forever install` de T06b n'écrit qu'une révision de plus dans la version courante. `forever install --new-version`
crée le dossier de la version de la candidate, en reportant ce que `forever decode` n'écrit pas : copies figées du
seed (`_seed_*.json`, `_source_gunba_mage_tree.json`), `confirmed_changes.json` et le journal des révisions.

Le critère d'acceptation vient du rapport `docs/research/data-1.60.1.70124.md` : `forever diff` entre les deux
versions installées ne doit montrer **aucun fichier retiré**, alors que la comparaison avec la candidate brute en
montre cinq.

Les règles de fusion ne changent pas : la base reste la version installée (talents et sorts déjà fusionnés en
révision 2), la candidate apporte la lecture du client. Une valeur changée hors `confirmed_changes.json` refuse
toujours l'installation."""

import json
import shutil

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, isolated_deps, read_json

from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.manifest import compute_manifest, load_manifest, version_files, write_manifest
from forever.pipeline.diff import diff_versions
from forever.pipeline.install import InstallRefusedError, apply_install, plan_install
from forever.store import load_version

NEW_VERSION = "1.60.1.70124"
# Fichiers que `forever decode` n'écrit pas dans une candidate : `forever diff 1.60.1.70009 <candidate>` les compte
# comme « fichiers retirés » (rapport du 2026-09-30).
CARRIED = (
    "_seed_spells.json",
    "_seed_talents.json",
    "_source_gunba_mage_tree.json",
    "confirmed_changes.json",
    "revisions.json",
)
# Fichiers hérités d'une version antérieure, écrits par `forever decode` avec `inherited_from` dans sources.json.
INHERITED = (
    "leveling.json",
    "mechanics.json",
    "meta.json",
    "monsters.json",
    "overrides.json",
    "racials.json",
    "respec.json",
)


@pytest.fixture
def installed(tmp_path):
    """Dépôt en l'état (1.60.1.70009 en révision 2), sur une copie."""
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    return isolated_deps(tmp_path, data)


@pytest.fixture
def newer(candidate, tmp_path):
    """Candidate de la session, relabellisée en version plus récente (aucun accès réseau)."""
    copy = tmp_path / "cand-70124"
    shutil.copytree(candidate.root, copy)
    (copy / LOCAL_VERSION).rename(copy / NEW_VERSION)
    sources = copy / NEW_VERSION / "sources.json"
    doc = read_json(sources)
    doc["game_version"] = NEW_VERSION
    sources.write_bytes(json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"))
    write_manifest(copy)
    return str(copy)


def test_new_version_creates_its_own_directory(installed, newer):
    before = sorted(p.name for p in installed.data_dir.iterdir() if p.is_dir())
    apply_install(installed, newer, motif="T08a", new_version=True)
    after = sorted(p.name for p in installed.data_dir.iterdir() if p.is_dir())
    assert after == sorted([*before, NEW_VERSION])
    # La version précédente n'est pas touchée.
    assert version_files(installed.data_dir / LOCAL_VERSION) == version_files(DATA_DIR / LOCAL_VERSION)


def test_the_new_version_has_every_file_of_the_previous_one(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    assert set(version_files(installed.data_dir / NEW_VERSION)) == set(version_files(DATA_DIR / LOCAL_VERSION))


def test_frozen_seed_copies_are_carried_unchanged(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    for name in ("_seed_talents.json", "_seed_spells.json", "_source_gunba_mage_tree.json"):
        assert (installed.data_dir / NEW_VERSION / name).read_bytes() == (DATA_DIR / LOCAL_VERSION / name).read_bytes()


def test_diff_between_the_two_installed_versions_has_no_removed_file(installed, newer):
    """Critère d'acceptation du bloc A : les 5 « fichiers retirés » de la comparaison avec la candidate brute
    disparaissent une fois la version installée."""
    raw = diff_versions(installed, LOCAL_VERSION, newer)
    assert sorted(c["key"] for c in raw if c["kind"] == "file") == sorted(CARRIED)
    apply_install(installed, newer, motif="T08a", new_version=True)
    installed_diff = diff_versions(installed, LOCAL_VERSION, NEW_VERSION)
    assert [c for c in installed_diff if c["kind"] == "file"] == []


def test_the_new_version_starts_at_revision_one(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    vdir = installed.data_dir / NEW_VERSION
    history = read_json(vdir / "revisions.json")
    assert history["version"] == NEW_VERSION
    assert [r["revision"] for r in history["revisions"]] == [1]
    assert history["revisions"][0]["motif"] == "T08a"
    sources = read_json(vdir / "sources.json")
    assert sources["revision"] == 1
    assert sources["game_version"] == NEW_VERSION
    assert sources.get("candidate") is not True


def test_confirmed_changes_are_carried_with_their_origin(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    before = read_json(DATA_DIR / LOCAL_VERSION / "confirmed_changes.json")
    after = read_json(installed.data_dir / NEW_VERSION / "confirmed_changes.json")
    assert after["version"] == NEW_VERSION
    assert after["carried_from"] == LOCAL_VERSION
    assert len(after["changes"]) == len(before["changes"])
    # La révision d'origine de chaque changement est gardée telle quelle.
    assert [c.get("applied_in_revision") for c in after["changes"]] == [
        c.get("applied_in_revision") for c in before["changes"]
    ]


def test_inherited_files_keep_their_origin_and_certainty(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    files = read_json(installed.data_dir / NEW_VERSION / "sources.json")["files"]
    for name in INHERITED:
        assert files[name]["inherited_from"] == LOCAL_VERSION, name


def test_manifest_points_to_the_new_version_and_keeps_the_old_one(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    manifest = load_manifest(installed.data_dir)
    assert manifest["game_version"] == NEW_VERSION
    assert set(manifest["versions"]) == {LOCAL_VERSION, NEW_VERSION}
    assert manifest == compute_manifest(installed.data_dir)


def test_nothing_changed_is_installed_anyway(installed, newer):
    """1.60.1.70124 ne change aucune valeur (22 tables identiques) : l'installation passe quand même, alors que
    `forever install` sans `--new-version` refuse une candidate qui ne change rien."""
    plan = plan_install(installed, newer, new_version=True)
    assert plan["changes"] == []
    assert plan["refused"] == []
    assert (plan["version_from"], plan["version_to"]) == (LOCAL_VERSION, NEW_VERSION)
    apply_install(installed, newer, motif="T08a", new_version=True)
    assert (installed.data_dir / NEW_VERSION / "talents.json").is_file()


def test_the_installed_values_are_those_of_the_previous_version(installed, newer):
    """Aucune valeur ne change : les fichiers fusionnés de la nouvelle version sont ceux de l'ancienne."""
    apply_install(installed, newer, motif="T08a", new_version=True)
    for name in ("talents.json", "spells.json"):
        assert read_json(installed.data_dir / NEW_VERSION / name) == read_json(DATA_DIR / LOCAL_VERSION / name)


def test_an_existing_version_directory_is_refused(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    before = version_files(installed.data_dir / NEW_VERSION)
    with pytest.raises(InvalidArgumentError):
        apply_install(installed, newer, motif="T08a", new_version=True)
    assert version_files(installed.data_dir / NEW_VERSION) == before


def test_a_candidate_of_the_current_version_is_refused_as_a_new_version(installed, candidate):
    with pytest.raises(InvalidArgumentError):
        plan_install(installed, str(candidate.root), new_version=True)


def test_plain_install_still_refuses_another_version(installed, newer):
    """Régression T06b : sans `--new-version`, une candidate d'une autre version reste refusée."""
    with pytest.raises(InvalidArgumentError):
        plan_install(installed, newer)


def test_a_value_outside_the_rules_is_still_refused(installed, newer, tmp_path):
    path = tmp_path / "cand-70124" / NEW_VERSION / "talents.json"
    doc = read_json(path)
    t = next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == "improvedFrostbolt")
    t["ranks"][0] = [9]
    path.write_bytes(json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))
    write_manifest(tmp_path / "cand-70124")
    plan = plan_install(installed, newer, new_version=True)
    assert [c["path"] for c in plan["refused"]] == ["improvedFrostbolt.ranks[1]"]
    with pytest.raises(InstallRefusedError):
        apply_install(installed, newer, motif="T08a", new_version=True)
    assert not (installed.data_dir / NEW_VERSION).exists()


def test_cli_new_version_without_consent_writes_nothing(installed, newer, capsys):
    code = main(["install", "--new-version", newer], deps=installed)
    capsys.readouterr()
    assert code != 0
    assert not (installed.data_dir / NEW_VERSION).exists()


def test_cli_new_version_dry_run_writes_nothing(installed, newer, capsys):
    code = main(["install", "--new-version", "--dry-run", newer], deps=installed)
    out = capsys.readouterr().out
    assert code == 0
    assert not (installed.data_dir / NEW_VERSION).exists()
    assert NEW_VERSION in out


def test_cli_new_version_yes_installs(installed, newer, capsys):
    code = main(["install", "--new-version", "--yes", newer], deps=installed)
    capsys.readouterr()
    assert code == 0
    assert (installed.data_dir / NEW_VERSION / "revisions.json").is_file()


def test_the_new_version_loads_and_verifies(installed, newer):
    apply_install(installed, newer, motif="T08a", new_version=True)
    version = load_version(isolated_deps(installed.cache_dir.parent, installed.data_dir))
    assert version.game_version == NEW_VERSION
