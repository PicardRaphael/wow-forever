"""Découverte des installations du client et choix de celle que forever lit (LN1, bloc A, décision 271).

Produits de fixture : `wow_classic_beta` (produit de `sources.json`, celui des données installées), `wow` (produit
public de la liste d'exclusion) et deux produits **manifestement fictifs** (`wow_fictif_finale`,
`wow_fictif_inconnu`) : le produit de la version finale n'est jamais écrit. En-tête réel de `.build.info` :
`tests/fixtures/installs/`."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import DATA_DIR, FIXTURES, PRODUCT

from forever.errors import InvalidArgumentError
from forever.installs import (
    NOT_FOREVER_PRODUCTS,
    ROLE_BETA,
    ROLE_FINAL,
    ROLE_OTHER,
    ROLE_UNKNOWN,
    assign_roles,
    beta_product,
    choose,
    discover,
    fixed_drives,
    parse_build_info,
    read_flavor,
    roots,
    survey,
)
from forever.pipeline.client_builds import (
    ClientBuild,
    adopt_product,
    adopted_products,
    forget_product,
    load_builds,
    record_build,
)

FIX = FIXTURES / "installs"
FINAL = "wow_fictif_finale"
UNKNOWN = "wow_fictif_inconnu"
BETA_V = "1.60.1.70374"
FINAL_V = "9.99.9.99999"
HEADER4 = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"
NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


def make_root(base: Path, rows, folders, *, name="World of Warcraft") -> Path:
    """Racine de fixture : `.build.info` (lignes produit, version) et dossiers {nom: (produit de .flavor.info ou
    None, exécutable ou None)}."""
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    lines = [HEADER4, *(f"us|1|{version}|{product}" for product, version in rows)]
    (root / ".build.info").write_bytes(("\n".join(lines) + "\n").encode())
    for folder, (flavor, exe) in folders.items():
        d = root / folder
        d.mkdir()
        if exe:
            (d / exe).write_bytes(b"")
        if flavor:
            (d / ".flavor.info").write_bytes(f"Product Flavor!STRING:0\n{flavor}\n".encode())
    return root


def beta_root(base: Path) -> Path:
    return make_root(base, [(PRODUCT, BETA_V)], {"_classic_beta_": (PRODUCT, "WowB.exe")})


def both_root(base: Path) -> Path:
    return make_root(
        base,
        [(PRODUCT, BETA_V), (FINAL, FINAL_V)],
        {"_classic_beta_": (PRODUCT, "WowB.exe"), "_fictif_": (FINAL, "WowF.exe")},
    )


def surveyed(tmp_path, environ, *, adopt=None, option=None, drives=()):
    cache = tmp_path / "cache"
    for folder in adopt or ():
        found = [i for i in discover([folder.parent]) if i.folder == folder]
        adopt_product(cache, found[0], NOW)
    return survey(environ, drives=lambda: list(drives), cache_dir=cache, data_dir=DATA_DIR, option=option)


# --- Lecture de .build.info et .flavor.info --------------------------------------------------------------------------


def test_real_header_is_read_by_column_name():
    rows = parse_build_info((FIX / "build_info_15.txt").read_text(encoding="utf-8"))
    assert [(r["Product"], r["Version"]) for r in rows] == [(PRODUCT, BETA_V)]


def test_permuted_columns_and_comment_lines():
    text = f"## seqn = 12\nProduct!STRING:0|Tags!STRING:0|Version!STRING:0\n{PRODUCT}|x|{BETA_V}\n# commentaire\n"
    assert [(r["Product"], r["Version"]) for r in parse_build_info(text)] == [(PRODUCT, BETA_V)]


def test_four_columns():
    rows = parse_build_info(f"{HEADER4}\nus|1|{FINAL_V}|{FINAL}\neu|1|{BETA_V}|{PRODUCT}\n")
    assert [r["Product"] for r in rows] == [FINAL, PRODUCT]


def test_flavor_info_gives_the_product(tmp_path):
    (tmp_path / ".flavor.info").write_bytes((FIX / "flavor_info.txt").read_bytes())
    assert read_flavor(tmp_path) == PRODUCT
    assert read_flavor(tmp_path / "absent") is None


def test_the_beta_product_comes_from_the_installed_data():
    assert beta_product(DATA_DIR) == PRODUCT


def test_the_exclusion_list_is_public_products_only():
    assert "wow" in NOT_FOREVER_PRODUCTS and PRODUCT not in NOT_FOREVER_PRODUCTS


# --- Racines ---------------------------------------------------------------------------------------------------------


def test_roots_in_order_without_duplicates(tmp_path):
    drive = tmp_path / "D"
    environ = {
        "FOREVER_WOW_DIR": str(tmp_path / "A" / "World of Warcraft" / "_classic_beta_"),
        "FOREVER_WOW_FORCE": str(tmp_path / "B" / "World of Warcraft" / "_fictif_"),
        "FOREVER_WOW_ROOTS": f"{tmp_path / 'R1'};{tmp_path / 'R2'};{tmp_path / 'R1'}",
    }
    found = roots(environ, [drive])
    assert found == [
        tmp_path / "A" / "World of Warcraft",
        tmp_path / "B" / "World of Warcraft",
        tmp_path / "R1",
        tmp_path / "R2",
        drive / "Program Files (x86)" / "World of Warcraft",
        drive / "Program Files" / "World of Warcraft",
        drive / "World of Warcraft",
        drive / "Games" / "World of Warcraft",
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="disques fixes réels sous Windows")
def test_no_fixed_drives_outside_windows():
    assert fixed_drives() == []


# --- Découverte ------------------------------------------------------------------------------------------------------


def test_an_installation_needs_an_executable(tmp_path):
    root = make_root(
        tmp_path,
        [(PRODUCT, BETA_V)],
        {"_classic_beta_": (PRODUCT, "WowB.exe"), "_vide_": (None, None), "_loader_": (None, "WowB_loader.exe")},
    )
    assert [i.folder.name for i in discover([root])] == ["_classic_beta_"]


def test_product_version_and_executable(tmp_path):
    root = both_root(tmp_path)
    found = {i.folder.name: i for i in discover([root])}
    beta, final = found["_classic_beta_"], found["_fictif_"]
    assert (beta.product, beta.version, beta.executable) == (PRODUCT, BETA_V, "WowB.exe")
    assert (final.product, final.version, final.executable) == (FINAL, FINAL_V, "WowF.exe")
    assert beta.product_source == ".flavor.info"


def test_without_flavor_the_single_line_is_used(tmp_path):
    root = make_root(tmp_path, [(PRODUCT, BETA_V)], {"_classic_beta_": (None, "WowB.exe")})
    [found] = discover([root])
    assert (found.product, found.version) == (PRODUCT, BETA_V)
    assert "ligne unique" in found.product_source


def test_two_lines_without_flavor_is_unreadable_never_guessed_from_the_folder(tmp_path):
    root = make_root(tmp_path, [(PRODUCT, BETA_V), ("wow", "12.0.1.70210")], {"_classic_beta_": (None, "WowB.exe")})
    [found] = discover([root])
    assert found.product is None and found.version is None


def test_a_public_product_is_found_by_its_known_folder(tmp_path):
    root = make_root(tmp_path, [(PRODUCT, BETA_V), ("wow", "12.0.1.70210")], {"_retail_": (None, "Wow.exe")})
    [found] = discover([root])
    assert (found.product, found.version) == ("wow", "12.0.1.70210")


def test_the_same_installation_seen_from_two_roots_is_counted_once(tmp_path):
    root = beta_root(tmp_path)
    environ = {"FOREVER_WOW_ROOTS": f"{root};{root}{os.sep}"}
    environ["FOREVER_WOW_DIR"] = str(root / "_classic_beta_")
    _, found = surveyed(tmp_path, environ)
    assert len(found) == 1


@pytest.mark.skipif(sys.platform != "win32", reason="casse des chemins ignorée sous Windows seulement")
def test_case_does_not_duplicate_an_installation(tmp_path):
    root = beta_root(tmp_path)
    environ = {"FOREVER_WOW_ROOTS": f"{root};{str(root).upper()}"}
    _, found = surveyed(tmp_path, environ)
    assert len(found) == 1


def test_program_files_x86_path_is_found_and_kept_intact(tmp_path):
    drive = tmp_path / "C"
    beta_root(drive / "Program Files (x86)")
    choice, found = surveyed(tmp_path, {}, drives=[drive])
    expected = drive / "Program Files (x86)" / "World of Warcraft" / "_classic_beta_"
    assert [i.folder for i in found] == [expected]
    assert choice.folder == expected


# --- Rôles et choix --------------------------------------------------------------------------------------------------


def test_beta_alone(tmp_path):
    root = beta_root(tmp_path)
    choice, found = surveyed(tmp_path, {"FOREVER_WOW_ROOTS": str(root)})
    assert [i.role for i in found] == [ROLE_BETA]
    assert choice.folder == root / "_classic_beta_"
    assert choice.reason == "bêta : aucune version finale adoptée"


def test_beta_and_adopted_final(tmp_path):
    root = both_root(tmp_path)
    choice, found = surveyed(tmp_path, {"FOREVER_WOW_ROOTS": str(root)}, adopt=[root / "_fictif_"])
    assert {i.folder.name: i.role for i in found} == {"_classic_beta_": ROLE_BETA, "_fictif_": ROLE_FINAL}
    assert choice.folder == root / "_fictif_"
    assert choice.reason == "version finale adoptée"


def test_final_alone_adopted(tmp_path):
    root = make_root(tmp_path, [(FINAL, FINAL_V)], {"_fictif_": (FINAL, "WowF.exe")})
    choice, _ = surveyed(tmp_path, {"FOREVER_WOW_ROOTS": str(root)}, adopt=[root / "_fictif_"])
    assert choice.folder == root / "_fictif_" and choice.install is not None
    assert choice.install.role == ROLE_FINAL


def test_unknown_product_is_listed_never_chosen(tmp_path):
    root = make_root(
        tmp_path,
        [(PRODUCT, BETA_V), (UNKNOWN, FINAL_V)],
        {"_classic_beta_": (PRODUCT, "WowB.exe"), "_inconnu_": (UNKNOWN, "WowX.exe")},
    )
    choice, found = surveyed(tmp_path, {"FOREVER_WOW_ROOTS": str(root)})
    assert {i.folder.name: i.role for i in found} == {"_classic_beta_": ROLE_BETA, "_inconnu_": ROLE_UNKNOWN}
    assert choice.folder == root / "_classic_beta_"


def test_a_public_product_is_other_and_never_chosen(tmp_path):
    root = make_root(tmp_path, [("wow", "12.0.1.70210")], {"_retail_": ("wow", "Wow.exe")})
    choice, found = surveyed(tmp_path, {"FOREVER_WOW_ROOTS": str(root)})
    assert [i.role for i in found] == [ROLE_OTHER]
    assert choice.folder is None and choice.reason == "aucune installation trouvée"


def test_force_wins_over_the_adopted_final(tmp_path):
    root = both_root(tmp_path)
    environ = {"FOREVER_WOW_ROOTS": str(root), "FOREVER_WOW_FORCE": str(root / "_classic_beta_")}
    choice, _ = surveyed(tmp_path, environ, adopt=[root / "_fictif_"])
    assert choice.folder == root / "_classic_beta_"
    assert choice.reason == "forcée par FOREVER_WOW_FORCE"


def test_the_command_option_wins_over_everything(tmp_path):
    root = both_root(tmp_path)
    environ = {"FOREVER_WOW_ROOTS": str(root), "FOREVER_WOW_FORCE": str(root / "_classic_beta_")}
    choice, _ = surveyed(tmp_path, environ, adopt=[root / "_fictif_"], option=root / "_fictif_")
    assert choice.folder == root / "_fictif_"
    assert choice.reason == "dossier donné par --wow-dir"


def test_the_most_recent_adopted_final_is_chosen(tmp_path):
    root = make_root(
        tmp_path,
        [(FINAL, FINAL_V), (UNKNOWN, "9.99.9.99998")],
        {"_fictif_": (FINAL, "WowF.exe"), "_inconnu_": (UNKNOWN, "WowX.exe")},
    )
    choice, _ = surveyed(tmp_path, {"FOREVER_WOW_ROOTS": str(root)}, adopt=[root / "_inconnu_", root / "_fictif_"])
    assert choice.folder == root / "_fictif_"


def test_forever_wow_dir_is_the_last_resort(tmp_path):
    folder = tmp_path / "ailleurs"
    folder.mkdir()
    choice = choose([], environ={"FOREVER_WOW_DIR": str(folder)})
    assert choice.folder == folder and "FOREVER_WOW_DIR" in choice.reason
    assert choose([], environ={}).folder is None


def test_roles_from_beta_product_and_adoptions(tmp_path):
    root = both_root(tmp_path)
    found = assign_roles(discover([root]), beta=PRODUCT, adopted={FINAL: {"role": "final"}})
    assert sorted(i.role for i in found) == [ROLE_BETA, ROLE_FINAL]


# --- Adoption --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rows", "folders"),
    [
        ([("wow", "12.0.1.70210")], {"_retail_": ("wow", "Wow.exe")}),
        ([(PRODUCT, BETA_V)], {"_classic_beta_": (PRODUCT, "WowB.exe")}),
        ([(PRODUCT, BETA_V), ("wow", "12.0.1.70210")], {"_x_": (None, "WowX.exe")}),
    ],
    ids=["public", "beta", "illisible"],
)
def test_adoption_is_refused(tmp_path, rows, folders):
    root = make_root(tmp_path, rows, folders)
    [found] = assign_roles(discover([root]), beta=PRODUCT, adopted={})
    with pytest.raises(InvalidArgumentError):
        adopt_product(tmp_path / "cache", found, NOW)
    assert adopted_products(tmp_path / "cache") == {}


def test_adoption_keeps_a_schema_1_journal(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    old = {
        "schema_version": 1,
        "builds": [
            {"build": BETA_V, "installed_at": "2026-10-13T08:00:00Z", "product": PRODUCT, "source": ".build.info"}
        ],
    }
    (cache / "client_builds.json").write_text(json.dumps(old), encoding="utf-8")
    root = both_root(tmp_path)
    final = next(i for i in discover([root]) if i.product == FINAL)
    adopt_product(cache, final, NOW)
    doc = json.loads((cache / "client_builds.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == 2
    assert doc["products"][FINAL] == {
        "role": "final",
        "adopted_at": "2026-11-04T09:00:00Z",
        "folder": str(root / "_fictif_"),
    }
    assert [b.build for b in load_builds(cache)] == [BETA_V]
    record_build(cache, ClientBuild(FINAL_V, NOW, FINAL))
    assert set(adopted_products(cache)) == {FINAL}


def test_forget_an_adoption(tmp_path):
    root = both_root(tmp_path)
    final = next(i for i in discover([root]) if i.product == FINAL)
    adopt_product(tmp_path / "cache", final, NOW)
    assert forget_product(tmp_path / "cache", FINAL) is True
    assert forget_product(tmp_path / "cache", FINAL) is False
    assert adopted_products(tmp_path / "cache") == {}
