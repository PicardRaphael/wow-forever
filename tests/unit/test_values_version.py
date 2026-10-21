"""Plan « Sources d'abord », étape c (décision 291) : la suite lit une copie des données ramenée à `VALUES_VERSION`
(version où ses valeurs attendues ont été validées) ; une nouvelle version installée ne change aucune valeur lue par
les tests. Simulation : une version plus récente ajoutée à une copie du dépôt dans `tmp_path`."""

import json
import shutil

from conftest import DATA_DIR, LOCAL_VERSION, REPO_DATA_DIR, VALUES_VERSION, pinned_data_dir

from forever.manifest import write_manifest


def test_the_suite_reads_the_values_version():
    assert LOCAL_VERSION == VALUES_VERSION
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["game_version"] == VALUES_VERSION


def test_a_newer_installed_version_is_rewound_for_the_tests(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(REPO_DATA_DIR, repo, ignore=shutil.ignore_patterns("__pycache__"))
    from forever.pipeline.builds import version_key

    latest = max((d.name for d in repo.iterdir() if d.is_dir() and d.name[0].isdigit()), key=version_key)
    newer = latest.rsplit(".", 1)[0] + "." + str(int(latest.rsplit(".", 1)[1]) + 1)  # plus récente que tout
    shutil.copytree(repo / VALUES_VERSION, repo / newer)
    write_manifest(repo)
    assert json.loads((repo / "manifest.json").read_text(encoding="utf-8"))["game_version"] == newer
    pinned = pinned_data_dir(repo, VALUES_VERSION, tmp_path / "pinned")
    assert pinned != repo and not (pinned / newer).exists()
    assert json.loads((pinned / "manifest.json").read_text(encoding="utf-8"))["game_version"] == VALUES_VERSION
    assert pinned_data_dir(pinned, VALUES_VERSION) == pinned  # déjà à la bonne version : aucune copie
