"""Construction de la table des monstres (`monsters.json`) : PV mesurés dans les journaux, Questie en regard.

Règles (décisions 2 et 3 du plan T04) :
- PV d'un PNJ à un niveau = valeur unique observée dans les journaux (`certain`) ; plusieurs valeurs → conflit listé,
  jamais moyenné. Seuls les PNJ observés sont écrits, avec la valeur Questie en regard (`questie_hp`) : la base
  Questie n'est jamais copiée.
- `hp_by_level` : par niveau, médiane des PV observés des PNJ normaux (rang Questie 0, ou rang inconnu), `certain` si
  plusieurs PNJ concordent, `probable` sinon (un PNJ seul, peut-être renforcé, n'établit pas la valeur du niveau) ;
  à défaut d'observation, médiane Questie des PNJ normaux (`suppose`, communautaire). Élites et rares à part.
- Écart entre une mesure et Questie : listé dans `questie_gaps`, la mesure prime.
Aucun chiffre de jeu : tout vient des journaux et de Questie."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import CandidateExistsError, InvalidArgumentError
from forever.pipeline.measure import Conflict, MonsterObservation
from forever.pipeline.questie import QuestieDB

MONSTERS_FILE = "monsters.json"
SCHEMA_VERSION = 1
NORMAL_RANK = 0  # rang cmangos « normal » dans Questie (format de la base)


def _median(values: Sequence[int]) -> int:
    return int(statistics.median_low(values))


def fit_questie_correction(npcs: Mapping[str, Any], *, exclude: Collection[int] = ()) -> dict[str, Any] | None:
    """Correction PV Questie -> Forever tirée des PNJ normaux mesurés (section `npcs` de `monsters.json`)."""
    raise NotImplementedError


def build_monsters(
    observations: Iterable[MonsterObservation],
    questie: QuestieDB | None,
    version: str,
    *,
    conflicts: Iterable[Conflict] = (),
    logs: Iterable[str] = (),
    fit_exclude: Collection[int] = (),
) -> dict[str, Any]:
    """Contenu de `monsters.json` pour la version `version`."""
    by_key: dict[tuple[int, int], list[MonsterObservation]] = defaultdict(list)
    for o in observations:
        by_key[(o["npc_id"], o["level"])].append(o)
    all_conflicts: list[Conflict] = list(conflicts)
    measured: dict[tuple[int, int], MonsterObservation] = {}
    for key, found in sorted(by_key.items()):
        values = sorted({o["max_hp"] for o in found})
        if len(values) > 1:
            logs_seen = sorted({o["log"] for o in found})
            all_conflicts.append({"npc_id": key[0], "level": key[1], "values": values, "log": ", ".join(logs_seen)})
        else:
            measured[key] = found[0]
    conflict_keys = {(c["npc_id"], c["level"]) for c in all_conflicts}
    measured = {k: v for k, v in measured.items() if k not in conflict_keys}

    npcs: dict[str, Any] = {}
    gaps: list[dict[str, int]] = []
    normal_by_level: dict[int, list[int]] = defaultdict(list)
    for (npc_id, level), o in sorted(measured.items()):
        q = questie.npc(npc_id) if questie else None
        questie_hp = q.hp_at(level) if q else None
        entry = npcs.setdefault(
            str(npc_id),
            {"name": o["name"], "zone_id": q.zone_id if q else None, "rank": q.rank if q else None, "levels": {}},
        )
        sources = sorted({x["log"] for x in by_key[(npc_id, level)]})
        entry["levels"][str(level)] = {
            "max_hp": o["max_hp"],
            "certainty": "certain",
            "source": f"journal {', '.join(sources)} (bloc avancé, {sum(x['guids'] for x in by_key[(npc_id, level)])} "
            "individu(s))",
            "questie_hp": questie_hp,
        }
        if questie_hp is not None and questie_hp != o["max_hp"]:
            gaps.append({"npc_id": npc_id, "level": level, "measured": o["max_hp"], "questie": questie_hp})
        if q is None or q.rank == NORMAL_RANK:
            normal_by_level[level].append(o["max_hp"])

    hp_by_level: dict[int, dict[str, Any]] = {}
    for level, values in normal_by_level.items():
        agree = len(set(values)) == 1 and len(values) > 1
        hp_by_level[level] = {
            "value": _median(values),
            "certainty": "certain" if agree else "probable",
            "source": "journaux : "
            + ("valeur commune" if agree else f"médiane de {sorted(values)}")
            + " des PNJ normaux observés",
            "n_npcs": len(values),
        }
    if questie is not None:
        community: dict[int, list[int]] = defaultdict(list)
        for q in questie.npcs().values():
            if q.rank != NORMAL_RANK or q.min_level < 1:
                continue
            for level in range(q.min_level, q.max_level + 1):
                hp = q.hp_at(level)
                if hp:
                    community[level].append(hp)
        for level, values in community.items():
            if level not in hp_by_level:
                hp_by_level[level] = {
                    "value": _median(values),
                    "certainty": "suppose",
                    "source": f"médiane des PNJ normaux de Questie ; {questie.source}",
                    "n_npcs": len(values),
                }
    return {
        "schema_version": SCHEMA_VERSION,
        "game_version": version,
        "source": "PV max lus dans le bloc avancé des journaux de combat du client ; Questie en regard",
        "logs": sorted(set(logs)),
        "questie_version": questie.info.version if questie else None,
        "questie_source": questie.source if questie else None,
        "npcs": npcs,
        "hp_by_level": {str(k): hp_by_level[k] for k in sorted(hp_by_level)},
        "conflicts": sorted(all_conflicts, key=lambda c: (c["npc_id"], c["level"])),
        "questie_gaps": gaps,
        "notes": [
            "npcs : PNJ observés seulement (jamais la base Questie) ; questie_hp : valeur de Questie au même niveau",
            "hp_by_level : médiane des PNJ normaux (rang Questie 0 ou inconnu) ; journal d'abord, sinon Questie",
            "créatures invoquées (propriétaire non nul dans le bloc avancé) exclues",
        ],
    }


def write_monsters(table: dict[str, Any], out: Path, data_dir: Path, *, force: bool = False) -> Path:
    """Écrit `out/monsters.json` hors de `data_dir` ; refuse d'écraser sans `force`."""
    if out.resolve().is_relative_to(data_dir.resolve()):
        raise InvalidArgumentError(
            f"La table des monstres ne s'écrit jamais dans {data_dir}.",
            "choisir un dossier --out hors des données, puis installer le fichier et lancer "
            "`uv run forever manifest --update`",
        )
    path = out / MONSTERS_FILE
    if path.exists() and not force:
        raise CandidateExistsError(str(path))
    out.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(table, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return path
