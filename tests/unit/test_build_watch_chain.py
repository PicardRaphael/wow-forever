"""Chaîne de la veille quotidienne (T08a, bloc D, décision 134).

Le workflow `build-watch.yml` vit dans `tasks/T08a-build-watch.patch` : le mode auto n'écrit pas dans
`.github/workflows`, et il faut que l'utilisateur l'applique. Ce qu'il enchaîne est testé ici, hors ligne : une
version fictive plus récente est publiée, la chaîne la télécharge, la décode, la vérifie, la compare et rend un
rapport — **sans jamais écrire dans `forever/data/`**.

Réseau simulé (`FakeHttp`) : aucun appel réel, conformément à la règle des tests."""

import json
import shutil

import pytest
from conftest import FIXTURES, LOCAL_VERSION, WAGO_70009, FakeHttp, read_json

from forever.cli import main
from forever.manifest import version_files

# Version fictive, plus récente que la version installée : c'est le cas que la veille doit détecter.
PUBLISHED = "1.60.1.79999"


@pytest.fixture
def repo(tmp_path, make_deps, data_copy):
    """Dépôt sur copie, cache neuf, et les CSV du client déjà en cache pour la version fictive (le téléchargement
    est simulé plus bas ; ici on prépare ce que `forever fetch` aurait écrit)."""
    cache = tmp_path / "cache"
    wago = cache / "wago" / PUBLISHED
    shutil.copytree(WAGO_70009, wago)
    return make_deps(data_dir=data_copy, cache_dir=cache)


def builds_http(latest):
    payload = {"wow_classic_beta": [{"version": latest, "created_at": "2026-10-01T00:00:00Z"}]}
    return FakeHttp(body=json.dumps(payload).encode("utf-8"))


def run(deps, argv, capsys):
    code = main(argv, deps)
    out = capsys.readouterr().out
    assert code == 0, out
    return json.loads(out)


def test_no_new_version_means_nothing_to_do(make_deps, capsys):
    """Premier pas de la veille : la version publiée égale la version installée, le travail s'arrête."""
    payload = run(make_deps(http=builds_http(LOCAL_VERSION)), ["builds", "--json"], capsys)
    assert payload["latest"] == LOCAL_VERSION
    assert payload["local_version"] == LOCAL_VERSION


def test_a_newer_version_is_seen(make_deps, capsys):
    payload = run(make_deps(http=builds_http(PUBLISHED)), ["builds", "--json"], capsys)
    assert payload["latest"] == PUBLISHED and payload["local_version"] == LOCAL_VERSION
    assert payload["latest"] != payload["local_version"]


def test_the_chain_produces_a_report_and_writes_nothing_in_the_data(repo, tmp_path, capsys):
    """decode → verify → diff → report, comme le workflow, sur une version fictive plus récente."""
    before = version_files(repo.data_dir / LOCAL_VERSION)
    decoded = run(repo, ["decode", "--version", PUBLISHED, "--json"], capsys)
    candidate = decoded["root"]

    verified = run(repo, ["verify", candidate, "--json"], capsys)
    assert verified["ok"] is True

    diff = run(repo, ["diff", LOCAL_VERSION, candidate, "--json"], capsys)
    assert diff["b"] == candidate

    report = tmp_path / "rapport.md"
    run(repo, ["report", LOCAL_VERSION, candidate, "--out", str(report), "--json"], capsys)
    text = report.read_text(encoding="utf-8")
    assert text.startswith("# data: ")
    assert PUBLISHED in text

    # Le cœur de la veille : rien n'est installé.
    assert version_files(repo.data_dir / LOCAL_VERSION) == before
    assert not (repo.data_dir / PUBLISHED).exists()
    assert read_json(repo.data_dir / "manifest.json")["game_version"] == LOCAL_VERSION


def test_the_candidate_lives_in_the_cache_not_in_the_repository(repo, capsys):
    decoded = run(repo, ["decode", "--version", PUBLISHED, "--json"], capsys)
    root = decoded["root"]
    assert str(repo.cache_dir) in root
    assert str(repo.data_dir) not in root


def test_the_report_names_the_candidate_as_not_installed(repo, tmp_path, capsys):
    decoded = run(repo, ["decode", "--version", PUBLISHED, "--json"], capsys)
    report = tmp_path / "rapport.md"
    run(repo, ["report", LOCAL_VERSION, decoded["root"], "--out", str(report), "--json"], capsys)
    text = report.read_text(encoding="utf-8")
    assert "non installée" in text


def test_the_patch_adds_only_the_workflow_and_never_installs():
    """Contrôle du patch livré : il n'ajoute que le workflow, ne lance jamais `forever install` et vérifie
    lui-même que les données n'ont pas bougé."""
    patch = (FIXTURES.parent.parent / "tasks" / "T08a-build-watch.patch").read_text(encoding="utf-8")
    added = [line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")]
    body = "\n".join(added)
    assert patch.startswith("diff --git a/.github/workflows/build-watch.yml")
    assert patch.count("diff --git") == 1
    assert "forever install" not in body.replace("forever install --new-version <candidate>", "")
    assert "git diff --exit-code -- forever/data" in body
    for step in (
        "forever builds",
        "forever fetch",
        "forever decode",
        "forever verify",
        "forever diff",
        "forever report",
    ):
        assert step in body, step
