"""SIM2 : Rust installé par rustup dans `<home>/.cargo/bin` est trouvé même quand ce dossier manque au PATH (cas des
commandes lancées par la veille), sans toucher au PATH s'il y est déjà ou si le dossier n'existe pas."""

import os

from forever.pipeline.mythicsim_build import path_with_cargo


def test_cargo_bin_is_added_when_missing(tmp_path):
    cargo = tmp_path / ".cargo" / "bin"
    cargo.mkdir(parents=True)
    path = path_with_cargo("C:\\Windows" + os.pathsep + "C:\\Go\\bin", home=tmp_path)
    assert path.split(os.pathsep) == ["C:\\Windows", "C:\\Go\\bin", str(cargo)]


def test_path_is_kept_when_cargo_is_there_or_absent(tmp_path):
    cargo = tmp_path / ".cargo" / "bin"
    assert path_with_cargo("C:\\Windows", home=tmp_path) == "C:\\Windows"  # pas de Rust installé
    cargo.mkdir(parents=True)
    with_cargo = "C:\\Windows" + os.pathsep + str(cargo)
    assert path_with_cargo(with_cargo, home=tmp_path) == with_cargo
