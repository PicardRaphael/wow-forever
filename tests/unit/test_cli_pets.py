"""`forever pets …` (CH0, bloc D) : chaque sous-commande rend le code 0, un texte terminé par la provenance et un
JSON avec son bloc `provenance` ; aucun réseau (client HTTP en échec).

Dossier du jeu construit dans le test avec les fixtures `tests/fixtures/bestiary/` et `tests/fixtures/questie/`."""

import json
import shutil

import pytest
from conftest import FIXTURES

from forever.cli import main
from forever.provenance import validate_provenance


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    addons = root / "Interface" / "AddOns"
    shutil.copytree(FIXTURES / "bestiary" / "ForeverBestiary", addons / "ForeverBestiary")
    shutil.copytree(FIXTURES / "questie" / "11.38.0", addons / "Questie")
    sv = root / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    shutil.copyfile(FIXTURES / "bestiary" / "ForeverBestiary.lua", sv / "ForeverBestiary.lua")
    return root


COMMANDS = [
    ["pets", "rules"],
    ["pets", "family", "Loup"],
    ["pets", "ability", "Bite", "--rank", "3", "--detail"],
    ["pets", "beast", "Prowler of the Test"],
    ["pets", "tame", "--ability", "Bite", "--rank", "3", "--zone", "Les Tarides", "--level", "10"],
    ["pets", "tame", "--family", "wolf", "--zone", "The Barrens", "--level", "10"],
    ["pets", "crosscheck"],
    ["pets", "mine"],
]


@pytest.mark.parametrize("argv", COMMANDS, ids=lambda a: " ".join(a[1:3]))
def test_text_ends_with_provenance(argv, make_deps, wow, capsys):
    assert main(argv, make_deps(wow_dir=wow)) == 0
    out = capsys.readouterr().out
    assert out.rstrip().splitlines()[-1].startswith("Provenance")


@pytest.mark.parametrize("argv", COMMANDS, ids=lambda a: " ".join(a[1:3]))
def test_json_carries_provenance(argv, make_deps, wow, capsys):
    assert main([*argv, "--json"], make_deps(wow_dir=wow)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert validate_provenance(payload["provenance"]) == []


def test_crosscheck_markdown_file(make_deps, wow, tmp_path, capsys):
    target = tmp_path / "recoupement.md"
    assert main(["pets", "crosscheck", "--markdown", str(target)], make_deps(wow_dir=wow)) == 0
    text = target.read_text(encoding="utf-8")
    assert text.startswith("# ") and b"\r\n" not in target.read_bytes()


def test_tame_without_level_is_a_usage_error(make_deps, wow, capsys):
    code = main(["pets", "tame", "--ability", "Bite", "--zone", "Les Tarides", "--json"], make_deps(wow_dir=wow))
    assert code == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] in ("invalid_argument", "usage")
