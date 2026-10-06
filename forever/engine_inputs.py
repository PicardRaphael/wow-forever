"""Preuve d'entrées identiques par moteur, et rejeu ciblé (T08d, bloc B, décision 180, clause c).

Un moteur calculé (build du Mage, leveling du Mage, rendements décroissants des fiches PvP) ne lit qu'une partie des
données d'une version. Deux versions dont ces entrées sont identiques, hors métadonnées (source, dates de lecture,
reports de révision, provenance d'un correctif), donnent les mêmes résultats : aucune recommandation ne change, et
une installation peut se faire sans accord. C'est la méthode du rapport `docs/research/data-1.60.1.70170-r4.md`
(relevé instrumenté de `VersionData.read_json`, puis empreintes canoniques), devenue du code.

`ENGINES` déclare, pour chaque moteur, les fichiers lus en entier et les pointeurs lus dans un fichier partagé
(`classes.json`) ; la garde de complétude des tests vérifie que les lectures relevées pendant un cas réel y sont
incluses, pour que la preuve ne puisse pas devenir fausse en silence. Aucun chiffre de jeu ici."""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple
from unittest import mock

PROVENANCE_FILES = frozenset({"sources.json", "manifest.json", "origins.json", "revisions.json"})
CLASSES_FILE = "classes.json"
# Champs de provenance absents de `metadata_keys` d'origins.json mais jamais lus par un moteur (rapport de la
# révision 4 : `read_at` sous `source`, `carried_to` du plafond reporté).
EXTRA_METADATA = frozenset({"carried_from", "carried_to", "read_at"})


class EngineSpec(NamedTuple):
    """Moteur calculé : fichiers lus en entier, pointeurs lus par fichier partagé (`*` : toute clé), cas de rejeu."""

    name: str
    files: tuple[str, ...]
    pointers: Mapping[str, tuple[str, ...]]
    cases: tuple[str, ...]


class InputsDiff(NamedTuple):
    """Entrées d'un moteur comparées entre deux versions ; `items` : une ligne par fichier ou pointeur
    (`file`, `pointer`, `status` « identique » ou « différent », `before`, `after`, `leaves`)."""

    engine: str
    identical: bool
    items: list[dict[str, Any]]


# Relevé de l'étape 2 (capture_reads sur build_report leveling 20, simulate_leveling 20, pvp_report Mage contre
# Warlock) : les deux moteurs du Mage lisent les mêmes fichiers.
_MAGE_FILES = (
    "character_scaling.json",
    "decode_rules.json",
    "leveling.json",
    "mechanics.json",
    "meta.json",
    "monsters.json",
    "races.json",
    "respec.json",
    "spell_scaling.json",
    "spells.json",
    "talents.json",
)
_BUILD_CASES = tuple(
    f"{context}-{level}"
    for context in ("leveling", "dungeon", "raid", "pvp-bg", "pvp-world")
    for level in ((20, 30, 40, 60) if context == "leveling" else (20, 40, 60))
)  # cas de scripts/replay_builds.py

ENGINES: Mapping[str, EngineSpec] = {
    "mage_build": EngineSpec("mage_build", _MAGE_FILES, {CLASSES_FILE: ("/classes/Mage/spells",)}, _BUILD_CASES),
    "mage_leveling": EngineSpec(
        "mage_leveling", _MAGE_FILES, {CLASSES_FILE: ("/classes/Mage/spells",)}, ("sim-leveling-20", "sim-leveling-30")
    ),
    "pvp_dr": EngineSpec(
        "pvp_dr",
        ("pvp_items.json", "pvp_rules.json", "races.json"),
        {CLASSES_FILE: ("/classes/*",)},
        ("matchup-Mage-Warlock-20",),
    ),
}


class _TrackedClasses(dict[str, Any]):
    """`classes` de `classes.json` qui note chaque classe lue ; un parcours complet note `/classes`."""

    def __init__(self, data: Mapping[str, Any], reads: set[tuple[str, str | None]]) -> None:
        super().__init__(data)
        self._reads = reads

    def __getitem__(self, key: str) -> Any:
        self._reads.add((CLASSES_FILE, f"/classes/{key}"))
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        self._reads.add((CLASSES_FILE, f"/classes/{key}"))
        return super().get(key, default)

    def _all(self) -> None:
        self._reads.add((CLASSES_FILE, "/classes"))

    def __iter__(self) -> Iterator[str]:
        self._all()
        return super().__iter__()

    def items(self) -> Any:
        self._all()
        return super().items()

    def values(self) -> Any:
        self._all()
        return super().values()


def capture_reads(fn: Callable[[], Any]) -> set[tuple[str, str | None]]:
    """Lectures des données d'une version pendant `fn()` : (fichier, pointeur JSON ou None pour le fichier entier).

    Instruments : `VersionData.read_json` (avec suivi par classe dans `classes.json`), la lecture des sorts du Mage
    (`gamedata._mage_spells_cached`) et toute autre lecture texte d'un fichier d'un dossier de version."""
    from forever import gamedata, store

    reads: set[tuple[str, str | None]] = set()
    depth = [0]
    read_json = store.VersionData.read_json
    read_text = pathlib.Path.read_text
    cached = gamedata._mage_spells_cached

    def tracked_read_json(self: Any, name: str) -> Any:
        depth[0] += 1
        try:
            doc = read_json(self, name)
        finally:
            depth[0] -= 1
        if name == CLASSES_FILE and isinstance(doc, dict) and isinstance(doc.get("classes"), dict):
            return {**doc, "classes": _TrackedClasses(doc["classes"], reads)}
        reads.add((name, None))
        return doc

    def tracked_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if depth[0] == 0 and (self.parent / "sources.json").is_file():
            reads.add((self.name, None))
        return read_text(self, *args, **kwargs)

    def tracked_mage_spells(path: str, data_sha: str) -> dict[str, Any]:
        reads.add((CLASSES_FILE, "/classes/Mage/spells"))
        depth[0] += 1
        try:
            result: dict[str, Any] = cached.__wrapped__(path, data_sha)
            return result
        finally:
            depth[0] -= 1

    with (
        mock.patch.object(store.VersionData, "read_json", tracked_read_json),
        mock.patch.object(pathlib.Path, "read_text", tracked_read_text),
        mock.patch.object(gamedata, "_mage_spells_cached", tracked_mage_spells),
    ):
        fn()
    return reads


def metadata_keys(*version_dirs: Path) -> frozenset[str]:
    """Clés de métadonnées exclues de la comparaison (`value_diff.META`, `metadata_keys` d'`origins.json`…)."""
    from forever.pipeline.value_diff import META

    keys = set(META) | EXTRA_METADATA
    for folder in version_dirs:
        try:
            doc = json.loads((folder / "origins.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        keys |= {str(k) for k in doc.get("metadata_keys", [])} if isinstance(doc, dict) else set()
    return frozenset(keys)


def _strip(doc: Any, metadata: frozenset[str]) -> Any:
    if isinstance(doc, dict):
        return {k: _strip(v, metadata) for k, v in doc.items() if k not in metadata}
    if isinstance(doc, list):
        return [_strip(v, metadata) for v in doc]
    return doc


def _resolve(doc: Any, pointer: str) -> Any:
    node = doc
    for part in pointer.strip("/").split("/") if pointer.strip("/") else []:
        if isinstance(node, dict):
            node = node.get(part)
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return None
    return node


def _sha(obj: Any) -> str:
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha(doc: Any, pointers: Sequence[str] | None, metadata: frozenset[str]) -> str:
    """Empreinte du JSON trié, sans les clés de métadonnées, du document entier ou des pointeurs donnés."""
    if pointers is None:
        return _sha(_strip(doc, metadata))
    return _sha({p: _strip(_resolve(doc, p), metadata) for p in pointers})


def _matches(pattern: str, pointer: str) -> bool:
    want = pattern.strip("/").split("/")
    got = pointer.strip("/").split("/")
    return len(got) >= len(want) and all(w in ("*", g) for w, g in zip(want, got, strict=False))


def covered(spec: EngineSpec, read: tuple[str, str | None]) -> bool:
    """Vrai si la lecture `(fichier, pointeur)` est incluse dans la déclaration du moteur."""
    file, pointer = read
    if file in spec.files:
        return True
    if pointer is None:
        return False
    return any(_matches(p, pointer) for p in spec.pointers.get(file, ()))


def _leaves(doc: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from _leaves(v, f"{path}/{k}")
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from _leaves(v, f"{path}/{i}")
    else:
        yield path, doc


def _changed_leaves(a: Any, b: Any) -> int:
    la, lb = dict(_leaves(a)), dict(_leaves(b))
    return sum(1 for k in set(la) | set(lb) if k not in la or k not in lb or la[k] != lb[k])


def _expand(pattern: str, docs: Sequence[Any]) -> list[str]:
    """Pointeurs concrets d'un motif (`*` : chaque clé présente dans l'un des documents)."""
    out = [""]
    for part in pattern.strip("/").split("/"):
        nxt: list[str] = []
        for prefix in out:
            if part != "*":
                nxt.append(f"{prefix}/{part}")
                continue
            keys: set[str] = set()
            for doc in docs:
                node = _resolve(doc, prefix)
                if isinstance(node, dict):
                    keys |= {str(k) for k in node}
            nxt += [f"{prefix}/{k}" for k in sorted(keys)]
        out = nxt
    return out


def compare_inputs(before: Path, after: Path) -> dict[str, InputsDiff]:
    """Entrées de chaque moteur comparées entre deux dossiers de version."""
    metadata = metadata_keys(before, after)
    loaded: dict[tuple[Path, str], Any] = {}

    def load(folder: Path, name: str) -> Any:
        if (folder, name) not in loaded:
            try:
                loaded[folder, name] = json.loads((folder / name).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                loaded[folder, name] = None
        return loaded[folder, name]

    def item(file: str, pointer: str | None, a: Any, b: Any) -> dict[str, Any]:
        sa, sb = _strip(a, metadata), _strip(b, metadata)
        ha = None if a is None else _sha(sa)
        hb = None if b is None else _sha(sb)
        return {
            "file": file,
            "pointer": pointer,
            "status": "identique" if ha == hb else "différent",
            "before": ha,
            "after": hb,
            "leaves": 0 if ha == hb else _changed_leaves(sa, sb),
        }

    out: dict[str, InputsDiff] = {}
    for name, spec in ENGINES.items():
        items = [item(f, None, load(before, f), load(after, f)) for f in spec.files]
        for file, patterns in spec.pointers.items():
            a, b = load(before, file), load(after, file)
            for pattern in patterns:
                for pointer in _expand(pattern, [d for d in (a, b) if d is not None]):
                    items.append(item(file, pointer, _resolve(a, pointer), _resolve(b, pointer)))
        out[name] = InputsDiff(name, all(i["status"] == "identique" for i in items), items)
    return out


def cases_to_replay(diffs: Mapping[str, InputsDiff]) -> list[tuple[str, str]]:
    """(moteur, cas) à rejouer : seulement les moteurs dont une entrée change."""
    return [
        (name, case)
        for name, spec in ENGINES.items()
        if name in diffs and not diffs[name].identical
        for case in spec.cases
    ]


def targeted_replay(diffs: Mapping[str, InputsDiff], replay: Callable[[str, str], Any]) -> dict[str, dict[str, Any]]:
    """Rejoue les seuls cas des moteurs touchés par `replay(moteur, cas)` ; rend {moteur: {cas: résultat}}."""
    out: dict[str, dict[str, Any]] = {}
    for engine, case in cases_to_replay(diffs):
        out.setdefault(engine, {})[case] = replay(engine, case)
    return out
