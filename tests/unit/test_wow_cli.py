"""`forever wow list|adopt|forget` et l'installation choisie dans `forever status` (LN1, bloc A, décision 271).

Racines de fixture dans `tmp_path` (voir `test_installs.py`), déclarées par `FOREVER_WOW_ROOTS` dans les dépendances
injectées : jamais le disque réel."""

import json
from dataclasses import replace
from pathlib import Path

from conftest import PRODUCT
from test_installs import BETA_V, FINAL, FINAL_V, beta_root, both_root, make_root

from forever.cli import main
from forever.config import FALLBACK_WOW_DIR, default_wow_dir
from forever.pipeline.client_builds import adopted_products
from forever.provenance import validate_provenance


def deps_with(make_deps, environ, *, drives=()):
    return replace(make_deps(), environ=environ, drives=lambda: list(drives))


def run(argv, deps, capsys):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def test_list_json(tmp_path, make_deps, capsys):
    root = both_root(tmp_path)
    code, out, _ = run(["wow", "list", "--json"], deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)}), capsys)
    assert code == 0
    data = json.loads(out)
    assert validate_provenance(data["provenance"]) == []
    by_folder = {Path(i["folder"]).name: i for i in data["installs"]}
    assert by_folder["_classic_beta_"]["role"] == "beta"
    assert by_folder["_classic_beta_"]["product"] == PRODUCT
    assert by_folder["_classic_beta_"]["version"] == BETA_V
    assert by_folder["_fictif_"]["role"] == "unknown"
    assert by_folder["_fictif_"]["executable"] == "WowF.exe"
    assert data["choice"]["folder"] == str(root / "_classic_beta_")
    assert data["reason"] == "bêta : aucune version finale adoptée"


def test_list_text_flags_an_unknown_product(tmp_path, make_deps, capsys):
    root = both_root(tmp_path)
    code, out, _ = run(["wow", "list"], deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)}), capsys)
    assert code == 0
    assert f"forever wow adopt {root / '_fictif_'}" in out
    assert out.rstrip().splitlines()[-1].startswith("Provenance")


def test_list_keeps_a_program_files_x86_path_intact(tmp_path, make_deps, capsys):
    drive = tmp_path / "C"
    beta_root(drive / "Program Files (x86)")
    _, out, _ = run(["wow", "list", "--json"], deps_with(make_deps, {}, drives=[drive]), capsys)
    folder = drive / "Program Files (x86)" / "World of Warcraft" / "_classic_beta_"
    assert json.loads(out)["choice"]["folder"] == str(folder)


def test_adopt_then_list_chooses_the_final(tmp_path, make_deps, capsys):
    root = both_root(tmp_path)
    deps = deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)})
    code, _, _ = run(["wow", "adopt", str(root / "_fictif_"), "--yes"], deps, capsys)
    assert code == 0
    assert set(adopted_products(deps.cache_dir)) == {FINAL}
    _, out, _ = run(["wow", "list", "--json"], deps, capsys)
    data = json.loads(out)
    assert data["choice"]["folder"] == str(root / "_fictif_")
    assert data["choice"]["version"] == FINAL_V
    assert data["reason"] == "version finale adoptée"


def test_adopt_without_agreement_writes_nothing(tmp_path, make_deps, capsys):
    root = both_root(tmp_path)
    deps = deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)})
    code, _, _ = run(["wow", "adopt", str(root / "_fictif_")], deps, capsys)
    assert code == 2
    assert adopted_products(deps.cache_dir) == {}


def test_adopt_of_a_public_product_is_refused(tmp_path, make_deps, capsys):
    root = make_root(tmp_path, [("wow", "12.0.1.70210")], {"_retail_": ("wow", "Wow.exe")})
    deps = deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)})
    code, _, err = run(["wow", "adopt", str(root / "_retail_"), "--yes"], deps, capsys)
    assert code == 2 and "Provenance" in err
    assert adopted_products(deps.cache_dir) == {}


def test_adopt_of_the_beta_is_refused(tmp_path, make_deps, capsys):
    root = beta_root(tmp_path)
    deps = deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)})
    code, _, _ = run(["wow", "adopt", str(root / "_classic_beta_"), "--yes"], deps, capsys)
    assert code == 2


def test_forget(tmp_path, make_deps, capsys):
    root = both_root(tmp_path)
    deps = deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)})
    run(["wow", "adopt", str(root / "_fictif_"), "--yes"], deps, capsys)
    code, _, _ = run(["wow", "forget", FINAL], deps, capsys)
    assert code == 0 and adopted_products(deps.cache_dir) == {}
    code, _, _ = run(["wow", "forget", FINAL], deps, capsys)
    assert code == 4


def test_status_shows_the_chosen_installation(tmp_path, make_deps, capsys):
    root = beta_root(tmp_path)
    code, out, _ = run(
        ["status", "--offline", "--json"], deps_with(make_deps, {"FOREVER_WOW_ROOTS": str(root)}), capsys
    )
    assert code == 0
    installation = json.loads(out)["installation"]
    assert installation == {
        "folder": str(root / "_classic_beta_"),
        "role": "beta",
        "product": PRODUCT,
        "version": BETA_V,
        "reason": "bêta : aucune version finale adoptée",
    }


# --- config.default_wow_dir ------------------------------------------------------------------------------------------


def test_default_wow_dir_follows_the_choice(tmp_path):
    root = both_root(tmp_path)
    environ = {"FOREVER_WOW_ROOTS": str(root), "FOREVER_WOW_FORCE": str(root / "_fictif_")}
    found = default_wow_dir(environ, drives=list, cache_dir=tmp_path / "cache")
    assert found == root / "_fictif_"


def test_default_wow_dir_falls_back_to_forever_wow_dir_then_the_old_default(tmp_path):
    assert default_wow_dir({"FOREVER_WOW_DIR": r"D:\Jeux\WoW"}, drives=list, cache_dir=tmp_path) == Path(r"D:\Jeux\WoW")
    assert default_wow_dir({}, drives=list, cache_dir=tmp_path) == FALLBACK_WOW_DIR
