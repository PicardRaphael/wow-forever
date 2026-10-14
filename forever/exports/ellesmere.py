"""Profils EllesmereUI par personnage et par rôle (EX1, bloc F, décision 267) : chaîne `!EUI_` (enveloppe version 3,
`type="full"`, `client="forever"`) construite sur un profil de base du joueur, lu en local dans la sauvegarde
`EllesmereUI.lua` (jamais écrite) ou collé (`!EUI_`). forever-core n'en remplit que les sorts du gestionnaire de
recharges (`cdmSpells`, clé de spécialisation du personnage) et les rappels de buffs (`customIDs`), tirés des sorts de
la classe appris au niveau ; tout le reste du profil de base est recopié tel quel (choix du joueur).

Format relevé dans EllesmereUI 9.5.4 (propriétaire, jamais recopié) : sérialiseur maison (`s<octets>:<texte>`,
`n<nombre>;`, `T`, `F`, `N`, table `{` partie tableau puis paires `K<clé><valeur>` `}`), puis `CompressDeflate` et
`EncodeForPrint` de LibDeflate (codec commun d'EX1). Ordre des clés fixé ici (trié) : sortie déterministe."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forever.config import Deps
from forever.engine.model import GameData

PREFIX = "!EUI_"
PAYLOAD_VERSION = 3
SAVED_VARIABLES = "EllesmereUI.lua"
ELLESMERE_VERSION = "9.5.4"
ROLE_LABELS = {"dps": "DPS", "heal": "Soins", "tank": "Tank"}
CDM_BARS = ("cooldowns", "utility")
BUFF_ADDON = "EllesmereUIAuraBuffReminders"


@dataclass(frozen=True)
class BaseProfile:
    """Profil de base du joueur : nom, données du profil (`profileData`), sorts du gestionnaire de recharges par clé
    de spécialisation, clé du personnage si EllesmereUI l'a gardée (`lastSpecByChar`), source, méta d'export."""

    name: str
    data: Mapping[str, Any]
    cdm: Mapping[str, Any]
    spec_key: str | None
    source: str
    meta: Mapping[str, Any] = field(default_factory=dict)


def ellesmere_serialize(value: Any) -> bytes:
    raise NotImplementedError


def ellesmere_deserialize(data: bytes) -> Any:
    raise NotImplementedError


def read_ellesmere(text: str) -> dict[str, Any]:
    raise NotImplementedError


def read_base_profile(wow_dir: Path, character_key: str, name: str | None = None) -> BaseProfile:
    raise NotImplementedError


def base_from_string(text: str, character_key: str | None = None) -> BaseProfile:
    raise NotImplementedError


def role_spells(
    gd: GameData, class_name: str, role: str, level: int, talents: Mapping[str, int] | None = None
) -> dict[str, list[int]]:
    raise NotImplementedError


def ellesmere_profile(
    base: BaseProfile, *, spec_key: str, bars: Mapping[str, Sequence[int]], buff_ids: Sequence[int]
) -> dict[str, Any]:
    raise NotImplementedError


def ellesmere_export(
    deps: Deps,
    character: str,
    realm: str,
    class_name: str,
    level: int,
    role: str,
    *,
    base_name: str | None = None,
    paste: str | None = None,
    spec_key: str | None = None,
    talents: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    raise NotImplementedError
