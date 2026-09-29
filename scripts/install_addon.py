"""Installe l'addon ForeverLogger du dépôt dans le client (copie de `addon/ForeverLogger/`).

    uv run python scripts/install_addon.py [--wow-dir <dossier du client>] [--dry-run]

Destination : `<wow-dir>/Interface/AddOns/ForeverLogger/` (défaut : FOREVER_WOW_DIR, sinon la bêta Forever trouvée
sous Program Files (x86) ou Program Files). Refuse une destination sans dossier `Interface/AddOns`. Seul le dossier
`ForeverLogger` est remplacé ; l'ancien contenu est renommé `ForeverLogger.bak-<date>` (ignoré par le client : le nom du dossier ne correspond plus au .toc).
`--dry-run` affiche les opérations sans rien écrire. Aucun accès réseau."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_wow_dir

SOURCE = ROOT / "addon" / "ForeverLogger"
NAME = "ForeverLogger"


class InstallError(Exception):
    """Installation impossible (destination invalide, droits insuffisants)."""


def install(src: Path, wow_dir: Path, *, dry_run: bool, now: datetime) -> list[str]:
    """Copie `src` dans `<wow_dir>/Interface/AddOns/<nom>` ; renvoie les opérations (préfixées « [simulation] » en
    `dry_run`)."""
    addons = wow_dir / "Interface" / "AddOns"
    if not addons.is_dir():
        raise InstallError(f"destination invalide : {addons} n'existe pas (dossier Interface/AddOns du client attendu)")
    if not (src / f"{src.name}.toc").is_file():
        raise InstallError(f"source invalide : {src / (src.name + '.toc')} absent")
    dest = addons / src.name
    prefix = "[simulation] " if dry_run else ""
    actions = []
    if dest.exists():
        backup = addons / f"{src.name}.bak-{now:%Y%m%d-%H%M%S}"
        actions.append(f"{prefix}sauvegarde : {dest} -> {backup}")
        if not dry_run:
            dest.rename(backup)
    files = sorted(p for p in src.rglob("*") if p.is_file())
    actions.append(f"{prefix}copie : {src} -> {dest} ({len(files)} fichier(s))")
    if not dry_run:
        shutil.copytree(src, dest)
    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Installe l'addon ForeverLogger dans le client.")
    parser.add_argument("--wow-dir", type=Path, default=default_wow_dir(), help="dossier du client")
    parser.add_argument("--dry-run", action="store_true", help="afficher les opérations sans rien écrire")
    args = parser.parse_args(argv)
    try:
        actions = install(SOURCE, args.wow_dir, dry_run=args.dry_run, now=datetime.now())  # noqa: DTZ005
    except InstallError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
    except PermissionError as exc:
        print(
            f"Erreur : droits insuffisants ({exc}). Relancer dans un terminal administrateur : "
            "uv run python scripts/install_addon.py",
            file=sys.stderr,
        )
        return 1
    print("\n".join(actions))
    if not args.dry_run:
        print("Addon installé : relancer le jeu ou taper /reload.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
