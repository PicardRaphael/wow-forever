"""Fichiers du client rangés par langue (`Cache/ADB/<langue>/DBCache.bin`, `Cache/WDB/<langue>/questcache.wdb`),
lecture locale seulement. Le client n'écrit que dans le dossier de sa langue (enUS, frFR…), qui peut changer d'une
session à l'autre : le fichier est cherché à chaque lecture, jamais retenu. Aucun chiffre de jeu ici."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

DEFAULT_LOCALE = "enUS"
CLIENT_CONFIG = ("WTF", "Config.wtf")
LOCALE_RE = re.compile(r"^[a-z]{2}[A-Z]{2}$")
_TEXT_LOCALE = re.compile(r'^\s*SET\s+textLocale\s+"(?P<value>[^"]*)"', re.MULTILINE)


def text_locale(wow_dir: Path | None) -> str | None:
    """Langue du client lue dans `WTF/Config.wtf` (`SET textLocale "enUS"`) ; None sans fichier."""
    if wow_dir is None:
        return None
    try:
        m = _TEXT_LOCALE.search(wow_dir.joinpath(*CLIENT_CONFIG).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    return m["value"] if m and LOCALE_RE.fullmatch(m["value"]) else None


def locate(wow_dir: Path | None, parts: Sequence[str]) -> tuple[Path, str] | None:
    """Fichier `parts` (avec `{locale}`) du client et sa langue : celle de `Config.wtf` si son fichier existe, sinon
    le fichier le plus récent parmi les langues présentes ; None s'il n'y en a aucun."""
    if wow_dir is None:
        return None
    i = list(parts).index("{locale}")
    parent, rest = wow_dir.joinpath(*parts[:i]), parts[i + 1 :]
    try:
        found = [(d.joinpath(*rest), d.name) for d in parent.iterdir() if LOCALE_RE.fullmatch(d.name) and d.is_dir()]
    except OSError:
        return None
    found = [(p, loc) for p, loc in found if p.is_file()]
    if not found:
        return None
    wanted = text_locale(wow_dir)
    for path, loc in found:
        if loc == wanted:
            return path, loc
    return max(found, key=lambda f: (f[0].stat().st_mtime_ns, f[1]))


def locale_of(path: Path) -> str:
    """Langue d'un fichier donné à la main : son dossier s'il porte une langue, sinon l'anglais."""
    return path.parent.name if LOCALE_RE.fullmatch(path.parent.name) else DEFAULT_LOCALE
