"""Installe un addon du dépôt dans le client (copie de `addon/<nom>/`, ForeverLogger par défaut).

    uv run python scripts/install_addon.py [--addon ForeverLogger|ForeverRappels] [--wow-dir <dossier du client>]
        [--dry-run] [--backups-only]

ForeverRappels (RA1) : `RappelsData.lua` de la copie installée est généré depuis les données de la version installée
(`forever.rappels`) ; le fichier du dépôt reste vide, sans identifiant de sort. Réinstaller après une mise à jour des
données.

Destination : `<wow-dir>/Interface/AddOns/ForeverLogger/` (défaut : FOREVER_WOW_DIR, sinon la bêta Forever trouvée
sous Program Files (x86) ou Program Files). Refuse une destination sans dossier `Interface/AddOns`. Seul le dossier
`ForeverLogger` est remplacé ; l'ancien contenu est déplacé dans le cache du projet,
`<cache>/addons/backups/ForeverLogger.bak-<date>` (décision 228 : plus aucune sauvegarde dans le dossier des addons),
avec les `ForeverLogger.bak-*` qu'y avaient laissés les installations précédentes. `--backups-only` déplace seulement
ces anciennes sauvegardes, sans réinstaller. `--dry-run` affiche les opérations sans rien écrire. Aucun accès réseau."""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forever.config import default_cache_dir, default_wow_dir

SOURCE = ROOT / "addon" / "ForeverLogger"
NAME = "ForeverLogger"
ADDONS = ("ForeverLogger", "ForeverRappels")


class InstallError(Exception):
    """Installation impossible (destination invalide, droits insuffisants)."""


def backups_dir(cache_dir: Path) -> Path:
    """Dossier des sauvegardes d'addons dans le cache du projet."""
    return cache_dir / "addons" / "backups"


def _free(path: Path) -> Path:
    """`path`, ou `path-2`, `path-3`… s'il existe déjà : une sauvegarde n'en écrase jamais une autre."""
    candidate, index = path, 1
    while candidate.exists():
        index += 1
        candidate = path.with_name(f"{path.name}-{index}")
    return candidate


def relocate_backups(addons: Path, name: str, backup_dir: Path, *, dry_run: bool = False) -> list[str]:
    """Déplace les dossiers `<name>.bak-*` du dossier des addons dans `backup_dir` ; renvoie les opérations."""
    prefix = "[simulation] " if dry_run else ""
    actions = []
    for folder in sorted(p for p in addons.glob(f"{name}.bak-*") if p.is_dir()):
        target = _free(backup_dir / folder.name)
        actions.append(f"{prefix}sauvegarde déplacée : {folder} -> {target}")
        if not dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(folder), str(target))
    return actions


def _addons_dir(wow_dir: Path) -> Path:
    addons = wow_dir / "Interface" / "AddOns"
    if not addons.is_dir():
        raise InstallError(f"destination invalide : {addons} n'existe pas (dossier Interface/AddOns du client attendu)")
    return addons


def rappels_data() -> str:
    """`RappelsData.lua` de ForeverRappels pour la version de données installée."""
    from forever.config import default_deps
    from forever.rappels import data_lua
    from forever.store import load_version

    return data_lua(load_version(default_deps()))


def install(
    src: Path,
    wow_dir: Path,
    *,
    dry_run: bool,
    now: datetime,
    backup_dir: Path,
    extra: dict[str, str] | None = None,
) -> list[str]:
    """Copie `src` dans `<wow_dir>/Interface/AddOns/<nom>`, l'ancien contenu et les anciennes sauvegardes déplacés
    dans `backup_dir`, puis écrit les fichiers générés `extra` (nom -> texte) par-dessus la copie ; renvoie les
    opérations (préfixées « [simulation] » en `dry_run`)."""
    addons = _addons_dir(wow_dir)
    if not (src / f"{src.name}.toc").is_file():
        raise InstallError(f"source invalide : {src / (src.name + '.toc')} absent")
    dest = addons / src.name
    prefix = "[simulation] " if dry_run else ""
    actions = relocate_backups(addons, src.name, backup_dir, dry_run=dry_run)
    if dest.exists():
        backup = _free(backup_dir / f"{src.name}.bak-{now:%Y%m%d-%H%M%S}")
        actions.append(f"{prefix}sauvegarde : {dest} -> {backup}")
        if not dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest), str(backup))
    files = sorted(p for p in src.rglob("*") if p.is_file())
    actions.append(f"{prefix}copie : {src} -> {dest} ({len(files)} fichier(s))")
    if not dry_run:
        shutil.copytree(src, dest)
    for name, text in sorted((extra or {}).items()):
        actions.append(f"{prefix}fichier généré : {dest / name}")
        if not dry_run:
            (dest / name).write_bytes(text.encode("utf-8"))
    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Installe un addon du dépôt dans le client.")
    parser.add_argument("--addon", choices=ADDONS, default=NAME, help="addon à installer (défaut : ForeverLogger)")
    parser.add_argument("--wow-dir", type=Path, default=default_wow_dir(), help="dossier du client")
    parser.add_argument("--dry-run", action="store_true", help="afficher les opérations sans rien écrire")
    parser.add_argument(
        "--backups-only",
        action="store_true",
        help="déplacer seulement les anciennes sauvegardes du dossier des addons dans le cache, sans réinstaller",
    )
    args = parser.parse_args(argv)
    backup_dir = backups_dir(default_cache_dir())
    try:
        if args.backups_only:
            actions = relocate_backups(_addons_dir(args.wow_dir), args.addon, backup_dir, dry_run=args.dry_run)
            print("\n".join(actions) or "aucune sauvegarde dans le dossier des addons")
            return 0
        now = datetime.now()  # noqa: DTZ005 : horodatage local du nom de sauvegarde
        extra = {"RappelsData.lua": rappels_data()} if args.addon == "ForeverRappels" else None
        source = ROOT / "addon" / args.addon
        actions = install(source, args.wow_dir, dry_run=args.dry_run, now=now, backup_dir=backup_dir, extra=extra)
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
