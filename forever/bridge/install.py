"""Installation de ForeverBridge dans le client (P06a) : copie de `addon/ForeverBridge`, fichiers de contrôle des
drapeaux (`ctl/`) et addon de sonde chargé à la demande (`ForeverBridge_Probe`). Le client ne voit que les fichiers
présents à son lancement : installer jeu fermé, puis le relancer.

Fichiers de contrôle (autotest `/fv diag`) : `empty` (vide, ne doit pas jouer), `valid` (son valide, doit jouer),
`flip` (vide à l'installation, rempli par `touch_probe` pendant que le jeu tourne), `late` (absent à l'installation,
créé par `touch_probe`) ; chacun en `.wav` (WAV silencieux) et en `.ogg` (copie d'un `.ogg` trouvé dans un autre addon
installé, aucun encodeur ici). `ForeverBridge_Probe/Probe.lua`, réécrit par `touch_probe`, dit si un addon chargé à
la demande relit son fichier modifié après le lancement.

Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : `bridge/install-slots.js`),
sous la licence suivante :

MIT License

Copyright (c) 2026 chelinho139

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "addon" / "ForeverBridge"
ADDON = "ForeverBridge"
PROBE_ADDON = "ForeverBridge_Probe"
INTERFACE = "16001"


class InstallError(Exception):
    """Installation impossible (dossier du client invalide, source absente, réserve hors bornes)."""


@dataclass
class InstallReport:
    actions: list[str] = field(default_factory=list)
    ogg_source: Path | None = None


def addons_dir(wow_dir: Path) -> Path:
    """`<wow_dir>/Interface/AddOns` ; InstallError s'il n'existe pas."""
    raise NotImplementedError


def find_ogg(addons: Path) -> Path | None:
    """Plus petit `.ogg` d'un addon installé autre que ForeverBridge (ordre des chemins à taille égale)."""
    raise NotImplementedError


def install_bridge(wow_dir: Path, slots: int = 0, *, dry_run: bool = False, source: Path = SOURCE) -> InstallReport:
    """Installe l'addon, `ctl/` et l'addon de sonde ; `dry_run` n'écrit rien et rend les opérations prévues."""
    raise NotImplementedError


def touch_probe(wow_dir: Path, now: datetime) -> list[str]:
    """Fichiers de la sonde modifiés pendant que le jeu tourne : `flip` rempli, `late` créé, `Probe.lua` réécrit."""
    raise NotImplementedError
