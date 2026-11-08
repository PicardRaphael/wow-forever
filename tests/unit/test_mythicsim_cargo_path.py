"""SIM2 : Rust installé par rustup dans `<home>/.cargo/bin` est trouvé même quand ce dossier manque au PATH (cas des
commandes lancées par la veille), sans toucher au PATH s'il y est déjà ou si le dossier n'existe pas. Chemins pris
dans `tmp_path` : le séparateur du PATH change selon le système."""

import os

from forever.pipeline.mythicsim_build import path_with_cargo


def test_cargo_bin_is_added_when_missing(tmp_path):
    cargo = tmp_path / ".cargo" / "bin"
    cargo.mkdir(parents=True)
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    path = path_with_cargo(a + os.pathsep + b, home=tmp_path)
    assert path.split(os.pathsep) == [a, b, str(cargo)]


def test_path_is_kept_when_cargo_is_there_or_absent(tmp_path):
    cargo = tmp_path / ".cargo" / "bin"
    a = str(tmp_path / "a")
    assert path_with_cargo(a, home=tmp_path) == a  # pas de Rust installé
    cargo.mkdir(parents=True)
    with_cargo = a + os.pathsep + str(cargo)
    assert path_with_cargo(with_cargo, home=tmp_path) == with_cargo
