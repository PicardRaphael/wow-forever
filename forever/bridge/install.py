"""Installation de ForeverBridge dans le client (P06a) : copie de `addon/ForeverBridge`, fichiers de contrôle des
drapeaux (`ctl/`) et addon de sonde chargé à la demande (`ForeverBridge_Probe`). Le client ne voit que les fichiers
présents à son lancement : installer jeu fermé, puis le relancer.

Fichiers de contrôle (autotest `/fv diag`) : `empty` (vide, ne doit pas jouer), `valid` (son valide, doit jouer),
`flip` (vide à l'installation, rempli par `touch_probe` pendant que le jeu tourne), `late` (absent à l'installation,
créé par `touch_probe`) ; chacun en `.wav` (WAV silencieux) et en `.ogg` (copie d'un `.ogg` trouvé dans un autre addon
installé, aucun encodeur ici). `ForeverBridge_Probe/Probe.lua`, réécrit par `touch_probe`, dit si un addon chargé à
la demande relit son fichier modifié après le lancement ; `ForeverBridge_Probe2`, chargé seulement par `/fv poll`, dit
si le premier chargement sans `/reload` d'un fichier modifié après le lancement lit le nouveau contenu (chemin des
réponses, décision 212 amendée le 2026-10-09).

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

from forever.bridge.slots import SILENT_WAV, SLOTS, inbox_lua, slot_name
from forever.errors import EXIT_USAGE, ForeverError

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "addon" / "ForeverBridge"
ADDON = "ForeverBridge"
PROBE_ADDON = "ForeverBridge_Probe"
PROBE2_ADDON = "ForeverBridge_Probe2"
INTERFACE = "16001"
MIN_SLOTS = 8
# Fichiers d'attente de l'addon, réécrits par le pont : jamais remplacés par une réinstallation.
BRIDGE_WRITTEN = ("Inbox.lua", "Status.lua")


class InstallError(ForeverError):
    """Installation impossible (dossier du client invalide, source absente, réserve hors bornes)."""

    exit_code = EXIT_USAGE

    def __init__(self, message: str) -> None:
        super().__init__(
            "bridge_install", message, "donner le dossier du client (--wow-dir ou FOREVER_WOW_DIR), jeu fermé"
        )


@dataclass
class InstallReport:
    actions: list[str] = field(default_factory=list)
    ogg_source: Path | None = None


def addons_dir(wow_dir: Path) -> Path:
    """`<wow_dir>/Interface/AddOns` ; InstallError s'il n'existe pas."""
    addons = wow_dir / "Interface" / "AddOns"
    if not addons.is_dir():
        raise InstallError(f"dossier du client invalide : {addons} n'existe pas (dossier Interface/AddOns attendu)")
    return addons


def find_ogg(addons: Path) -> Path | None:
    """Plus petit `.ogg` d'un addon installé autre que ForeverBridge (ordre des chemins à taille égale)."""
    found = [
        p
        for p in addons.rglob("*")
        if p.suffix.lower() == ".ogg" and p.is_file() and not p.relative_to(addons).parts[0].startswith(ADDON)
    ]
    return min(found, key=lambda p: (p.stat().st_size, str(p))) if found else None


def _probe_toc(title: str = "sonde", command: str = "/fv diag", lua: str = "Probe.lua") -> str:
    return "\n".join(
        [
            f"## Interface: {INTERFACE}",
            f"## Title: ForeverBridge ({title})",
            f"## Notes: Sonde du pont de forever-core, chargée à la demande par {command} (P06a).",
            "## LoadOnDemand: 1",
            f"## Dependencies: {ADDON}",
            "",
            lua,
            "",
        ]
    )


def _probe_lua(value: str, variable: str = "ForeverBridge_ProbeValue") -> str:
    return f'{variable} = "{value}"\n'


def _probe2_lua(value: str) -> str:
    return _probe_lua(value, "ForeverBridge_Probe2Value")


class _Writer:
    """Écritures et suppressions, ou leur seule description en simulation."""

    def __init__(self, report: InstallReport, wow_dir: Path, dry_run: bool) -> None:
        self.report, self.wow_dir, self.dry_run = report, wow_dir, dry_run
        self.prefix = "[simulation] " if dry_run else ""

    def _name(self, path: Path) -> str:
        return path.relative_to(self.wow_dir).as_posix()

    def write(self, path: Path, content: bytes, what: str, *, quiet: bool = False) -> None:
        if not quiet:
            self.report.actions.append(f"{self.prefix}{what} : {self._name(path)} ({len(content)} octets)")
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    def remove(self, path: Path, what: str) -> None:
        if path.exists():
            self.report.actions.append(f"{self.prefix}{what} : {self._name(path)} retiré")
            if not self.dry_run:
                path.unlink()

    def note(self, text: str) -> None:
        self.report.actions.append(f"{self.prefix}{text}")


def _slot_toc(index: int) -> str:
    return "\n".join(
        [
            f"## Interface: {INTERFACE}",
            f"## Title: ForeverBridge (emplacement {index:03d})",
            "## Notes: Réponses du pont de forever-core, chargées à la demande (P06a).",
            "## LoadOnDemand: 1",
            f"## Dependencies: {ADDON}",
            "",
            "Inbox.lua",
            "",
        ]
    )


def _install_reserve(addons: Path, slots: int, out: _Writer) -> None:
    """Emplacements `ForeverBridge_S001`… : `.toc` réécrit, `Inbox.lua` d'attente seulement s'il manque."""
    waiting = inbox_lua(0, {}, [], []).encode("utf-8")
    inboxes = 0
    for index in range(1, slots + 1):
        folder = addons / slot_name(index)
        out.write(folder / f"{slot_name(index)}.toc", _slot_toc(index).encode("utf-8"), "emplacement", quiet=True)
        if not (folder / "Inbox.lua").is_file():
            out.write(folder / "Inbox.lua", waiting, "emplacement", quiet=True)
            inboxes += 1
    out.note(
        f"réserve : {slot_name(1)} à {slot_name(slots)} ({slots} .toc, {inboxes} Inbox.lua d'attente écrits, "
        "les autres gardés)"
    )


def install_bridge(wow_dir: Path, slots: int = SLOTS, *, dry_run: bool = False, source: Path = SOURCE) -> InstallReport:
    """Installe l'addon, sa réserve d'emplacements, `ctl/` et les addons de sonde ; `dry_run` n'écrit rien et rend
    les opérations prévues."""
    if not MIN_SLOTS <= slots <= SLOTS:
        raise InstallError(f"réserve de {slots} emplacements : de {MIN_SLOTS} à {SLOTS} (8 à 200)")
    addons = addons_dir(wow_dir)
    if not (source / f"{ADDON}.toc").is_file():
        raise InstallError(f"source invalide : {source / (ADDON + '.toc')} absent")
    report = InstallReport(ogg_source=find_ogg(addons))
    out = _Writer(report, wow_dir, dry_run)
    dest = addons / ADDON
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        target = dest / path.relative_to(source)
        if path.name in BRIDGE_WRITTEN and path.parent == source and target.is_file():
            continue
        out.write(target, path.read_bytes(), "addon")
    _install_reserve(addons, slots, out)
    ctl = dest / "ctl"
    for name, content in (("empty", b""), ("valid", SILENT_WAV), ("flip", b"")):
        out.write(ctl / f"{name}.wav", content, "contrôle")
    out.write(ctl / "empty.ogg", b"", "contrôle")
    out.write(ctl / "flip.ogg", b"", "contrôle")
    if report.ogg_source is not None:
        out.write(ctl / "valid.ogg", report.ogg_source.read_bytes(), f"contrôle (copie de {report.ogg_source.name})")
    else:
        out.note("aucun .ogg dans les addons installés : l'autotest .ogg de /fv diag échouera (seul le .wav sera jugé)")
    for name in ("late.wav", "late.ogg"):
        out.remove(ctl / name, "contrôle")
    probe = addons / PROBE_ADDON
    out.write(probe / f"{PROBE_ADDON}.toc", _probe_toc().encode("utf-8"), "sonde")
    out.write(probe / "Probe.lua", _probe_lua("installation").encode("utf-8"), "sonde")
    probe2 = addons / PROBE2_ADDON
    toc2 = _probe_toc("sonde de consultation", "/fv poll", "Probe2.lua")
    out.write(probe2 / f"{PROBE2_ADDON}.toc", toc2.encode("utf-8"), "sonde")
    out.write(probe2 / "Probe2.lua", _probe2_lua("installation").encode("utf-8"), "sonde")
    return report


def addon_outdated(addons: Path, *, source: Path = SOURCE) -> list[str]:
    """Fichiers de l'addon du dépôt absents ou différents dans l'addon installé (chemins relatifs, triés) ; les
    fichiers écrits par le pont (`Inbox.lua`, `Status.lua`) et `ctl/` ne comptent pas. Le `## Version:` du .toc n'est
    jamais changé : seule la comparaison des contenus dit si l'addon est à jour (sonde en jeu F)."""
    dest = addons / ADDON
    out = []
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = path.relative_to(source)
        if (rel.parent == Path(".") and path.name in BRIDGE_WRITTEN) or rel.parts[0] == "ctl":
            continue
        target = dest / rel
        try:
            same = target.read_bytes() == path.read_bytes()
        except OSError:
            same = False
        if not same:
            out.append(rel.as_posix())
    return out


def touch_probe(wow_dir: Path, now: datetime) -> list[str]:
    """Fichiers de la sonde modifiés pendant que le jeu tourne : `flip` rempli, `late` créé, `Probe.lua` réécrit."""
    addons = addons_dir(wow_dir)
    ctl = addons / ADDON / "ctl"
    probe = addons / PROBE_ADDON
    if not ctl.is_dir() or not probe.is_dir():
        raise InstallError("ForeverBridge n'est pas installé : lancer `forever bridge install`, puis relancer le jeu")
    report = InstallReport()
    out = _Writer(report, wow_dir, dry_run=False)
    out.write(ctl / "flip.wav", SILENT_WAV, "drapeau levé")
    out.write(ctl / "late.wav", SILENT_WAV, "fichier ajouté")
    valid_ogg = ctl / "valid.ogg"
    if valid_ogg.is_file():
        out.write(ctl / "flip.ogg", valid_ogg.read_bytes(), "drapeau levé")
        out.write(ctl / "late.ogg", valid_ogg.read_bytes(), "fichier ajouté")
    else:
        out.note("pas de ctl/valid.ogg : flip.ogg et late.ogg inchangés")
    out.write(probe / "Probe.lua", _probe_lua(f"modifié à {now:%H:%M:%S}").encode("utf-8"), "sonde réécrite")
    probe2 = addons / PROBE2_ADDON
    if probe2.is_dir():
        out.write(probe2 / "Probe2.lua", _probe2_lua(f"modifié à {now:%H:%M:%S}").encode("utf-8"), "sonde réécrite")
    else:
        out.note(f"{PROBE2_ADDON} absent : relancer `forever bridge install`, jeu fermé")
    return report.actions
