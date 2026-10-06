"""Bout en bout de `forever update` : une version nouvelle fictive installée par le clone, `verify` du clone compris
(demande de l'utilisateur du 2026-10-06, réponse 4 ; décision 192).

Cas réel : le 2026-10-06, `tasks.py verify` était rouge dans le clone pour 1.60.1.70235 parce que 85 tests figeaient
la version installée (`LOCAL_VERSION = "1.60.1.70170"`). Ce test installe une version fictive, plus récente que la
version installée du dépôt et de même contenu (copie de la version installée sous un nouveau numéro, comme 70235
dont les entrées des moteurs étaient identiques), par `run_update` : étape « jeu » sur un `.build.info` et une liste
de builds simulés, installation dans la copie de préparation, report à la main, preuve d'entrées, règle, puis
**`uv sync` et `uv run tasks.py verify` réels dans le clone**, commit, poussée et fusion dans un dépôt nu local
(`gh` simulé : CI verte). Seuls le téléchargement et le décodage sont remplacés par la candidate copiée : ils sont
couverts par `tests/unit/test_update_chain.py` sur les extraits. Une version figée dans un test rend ce test rouge.

Le dépôt nu est un clone du `HEAD` du dépôt (les changements non committés n'y sont pas). Long (le `verify` complet,
une douzaine de minutes) : lancé par `uv run tasks.py e2e` et par le job `e2e` de la CI, jamais par la suite par
défaut (sinon il tournerait aussi dans le `verify` du clone, sans fin). Aucun réseau : git local, `uv --offline`."""

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import DATA_DIR, LOCAL_VERSION, REPO_ROOT, FakeHttp, read_json

from forever.manifest import write_manifest
from forever.pipeline import decode
from forever.pipeline.builds import BUILDS_URL
from forever.pipeline.gitops import subprocess_runner
from forever.update import UpdateOptions, exit_code, run_update, update_dir

E2E_ENV = "FOREVER_E2E"
pytestmark = pytest.mark.skipif(
    os.environ.get(E2E_ENV) != "1", reason="bout en bout long : `uv run tasks.py e2e` (FOREVER_E2E=1)"
)

HEADER = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"
NOT_IN_CANDIDATE = ("revisions.json", "confirmed_changes.json")  # écrits par l'installation, pas par le décodage
NOT_IN_CANDIDATE_PREFIXES = ("_seed_", "_source_")  # copies figées gardées par l'installation


def fictive_version() -> str:
    head, build = LOCAL_VERSION.rsplit(".", 1)
    return f"{head}.{int(build) + 1}"


def candidate_of(version: str, root: Path) -> Path:
    """Candidate de `version` au contenu de la version installée (comme une sortie de `forever decode`)."""
    vdir = root / version
    vdir.mkdir(parents=True)
    for path in sorted((DATA_DIR / LOCAL_VERSION).iterdir()):
        if path.name in NOT_IN_CANDIDATE or path.name.startswith(NOT_IN_CANDIDATE_PREFIXES) or not path.is_file():
            continue
        shutil.copyfile(path, vdir / path.name)
    sources = read_json(vdir / "sources.json")
    sources.update(game_version=version, candidate=True)
    (vdir / "sources.json").write_bytes((json.dumps(sources, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    write_manifest(root)
    return root


def git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True)
    return out.stdout.strip()


class Runner:
    """git et `uv` réels ; `uv` sans FOREVER_E2E (le `verify` du clone saute ce test) ; `gh` simulé (CI verte)."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], int]] = []

    def __call__(self, args, cwd, timeout=None):
        args = list(args)
        assert not {"--force", "-f", "--force-with-lease"} & set(args), args
        if args[0] == "gh":
            out = self._gh(args, cwd)
        elif args[0] == "uv":
            env = {k: v for k, v in os.environ.items() if k != E2E_ENV}
            out = subprocess.run(
                args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                timeout=timeout, check=False,
            )  # fmt: skip
        else:
            out = subprocess_runner(args, cwd, timeout)
        self.calls.append((args, out.returncode))
        return out

    def _gh(self, args, cwd):
        if args[1:3] == ["run", "list"]:
            sha = git(cwd, "rev-parse", args[args.index("--branch") + 1])
            runs = [{"databaseId": 1, "headSha": sha, "status": "completed", "conclusion": "success", "url": "ci"}]
            return subprocess.CompletedProcess(args, 0, json.dumps(runs), "")
        if args[1:3] == ["run", "watch"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[1:3] == ["run", "view"]:
            jobs = [
                {"name": "verify (ubuntu)", "conclusion": "success"},
                {"name": "verify (windows)", "conclusion": "success"},
            ]
            return subprocess.CompletedProcess(args, 0, json.dumps({"jobs": jobs}), "")
        raise AssertionError(f"gh inattendu : {args}")


@pytest.fixture
def isolated_git(tmp_path, monkeypatch):
    config = tmp_path / "gitconfig"
    config.write_text(
        "[user]\n\tname = Test\n\temail = test@example.invalid\n[init]\n\tdefaultBranch = main\n"
        "[core]\n\tautocrlf = false\n\tlongpaths = true\n[commit]\n\tgpgsign = false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def test_a_new_version_is_installed_end_to_end_with_the_clone_verify(tmp_path, make_deps, monkeypatch, isolated_git):
    version = fictive_version()
    bare = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(REPO_ROOT), str(bare))
    head = git(bare, "rev-parse", "HEAD")
    if git(bare, "symbolic-ref", "--short", "HEAD") != "main":  # CI : branche de travail poussée sous main
        git(bare, "branch", "-f", "main", head)
        git(bare, "symbolic-ref", "HEAD", "refs/heads/main")
    wow = tmp_path / "World of Warcraft" / "_classic_beta_"
    wow.mkdir(parents=True)
    product = read_json(DATA_DIR / LOCAL_VERSION / "sources.json")["product"]
    (wow.parent / ".build.info").write_text(f"{HEADER}\nus|1|{version}|{product}\n", encoding="utf-8")
    builds = {product: [{"version": v, "created_at": "2026-10-06T00:00:00Z"} for v in (LOCAL_VERSION, version)]}
    deps = make_deps(
        cache_dir=tmp_path / "cache",
        wow_dir=wow,
        http=FakeHttp(routes={BUILDS_URL: json.dumps(builds).encode()}),
        now=datetime(2026, 10, 6, 12, 0, tzinfo=UTC),
    )
    (update_dir(deps.cache_dir)).mkdir(parents=True)
    (update_dir(deps.cache_dir) / "config.json").write_text(json.dumps({"repo_url": str(bare)}), encoding="utf-8")
    candidate = candidate_of(version, tmp_path / "candidate")
    monkeypatch.setattr("forever.update._fetch_version", lambda run, v, rules: None)  # téléchargement : simulé
    monkeypatch.setattr(decode, "decode_version", lambda *a, **k: SimpleNamespace(root=candidate))
    runner = Runner()
    lines: list[str] = []
    replay = lambda engine, case, data: {"rejoué": False}  # appelé seulement si une entrée change
    report = run_update(
        deps, UpdateOptions(only=frozenset({"jeu"})), runner=runner, replay=replay, progress=lines.append
    )
    journal = "\n".join(lines)
    assert [v["action"] for v in report["verdicts"]] == ["écrire"], journal
    verify = [code for args, code in runner.calls if args[0] == "uv" and "verify" in args]
    assert verify == [0], [p.get("log") for p in report["pending"]]  # verify réel du clone, vert
    assert [w["version"] for w in report["written"]] == [version], journal
    assert report["pending"] == [] and exit_code(report) == 0
    manifest = json.loads(git(bare, "show", "main:forever/data/manifest.json"))
    assert manifest["game_version"] == version and LOCAL_VERSION in manifest["versions"]
    assert git(bare, "rev-parse", "main") != head
