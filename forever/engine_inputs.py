"""Preuve d'entrées identiques par moteur, et rejeu ciblé (T08d, bloc B, décision 180, clause c, amendée par 198
et 207).

Un moteur calculé (build du Mage, leveling du Mage, rendements décroissants des fiches PvP) ne lit qu'une partie des
données d'une version. Deux versions dont ces entrées sont identiques, hors métadonnées (source, dates de lecture,
reports de révision, provenance d'un correctif), donnent les mêmes résultats : aucune recommandation ne change, et
une installation peut se faire sans accord. C'est la méthode du rapport `docs/research/data-1.60.1.70170-r4.md`
(relevé instrumenté de `VersionData.read_json`, puis empreintes canoniques), devenue du code.

`ENGINES` déclare, pour chaque moteur, les fichiers lus en entier et les pointeurs lus dans un fichier partagé
(`classes.json`) ; la garde de complétude des tests vérifie que les lectures relevées pendant un cas réel y sont
incluses, pour que la preuve ne puisse pas devenir fausse en silence. Chaque moteur déclare son mode (`calcule` ou
`recopie`, T08e) ; une entrée changée porte ses feuilles et leur origine déclarée avant et après (`ValueChange`),
et `hotfix_losses` relève les valeurs d'un correctif du serveur perdues. Aucun chiffre de jeu ici."""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple
from unittest import mock

from forever.errors import ForeverError

PROVENANCE_FILES = frozenset({"sources.json", "manifest.json", "origins.json", "revisions.json"})
CLASSES_FILE = "classes.json"
# Champs de provenance absents de `metadata_keys` d'origins.json mais jamais lus par un moteur (rapport de la
# révision 4 : `read_at` sous `source`, `carried_to` du plafond reporté).
EXTRA_METADATA = frozenset({"carried_from", "carried_to", "read_at"})
# Décision 230 : noms affichés, jamais lus par un moteur qui calcule (garde : `test_no_engine_reads_the_french_names`) ;
# une révision qui n'ajoute que des noms français laisse les entrées des moteurs identiques.
DISPLAY_KEYS = frozenset({"name_fr"})


ENGINE_MODES = ("calcule", "recopie")


class EngineSpec(NamedTuple):
    """Moteur : fichiers lus en entier, pointeurs lus par fichier partagé (`*` : toute clé), cas de rejeu, et mode
    (décision 207) : `calcule` (règles du modèle, rejeu des cas) ou `recopie` (fiches tirées du client, sans règle du
    modèle, sans cas de rejeu)."""

    name: str
    files: tuple[str, ...]
    pointers: Mapping[str, tuple[str, ...]]
    cases: tuple[str, ...]
    mode: str


class EngineDeclarationError(ForeverError):
    def __init__(self, message: str) -> None:
        super().__init__(
            "engine_declaration", message, "déclarer le mode du moteur dans ENGINES (forever/engine_inputs.py)"
        )


class _Absent:
    """Marqueur d'une feuille ajoutée (absente avant) ou retirée (absente après)."""

    def __repr__(self) -> str:
        return "ABSENT"


ABSENT: Any = _Absent()


class ValueChange(NamedTuple):
    """Feuille changée : pointeur complet dans le fichier, valeurs (`ABSENT` si ajoutée ou retirée), origine déclarée
    avant (version installée) et après (copie de préparation) ; `None` : feuille sans règle."""

    file: str
    pointer: str
    before: Any
    after: Any
    origin_before: str | None
    origin_after: str | None


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
    "mage_build": EngineSpec(
        "mage_build", _MAGE_FILES, {CLASSES_FILE: ("/classes/Mage/spells",)}, _BUILD_CASES, "calcule"
    ),
    "mage_leveling": EngineSpec(
        "mage_leveling",
        _MAGE_FILES,
        {CLASSES_FILE: ("/classes/Mage/spells",)},
        ("sim-leveling-20", "sim-leveling-30"),
        "calcule",
    ),
    "pvp_dr": EngineSpec(
        "pvp_dr",
        ("pvp_items.json", "pvp_rules.json", "races.json"),
        {CLASSES_FILE: ("/classes/*",)},
        (),  # fiches recopiées du client : contrôle par `verify --data --engines=pvp_dr`, pas de rejeu
        "recopie",
    ),
}


def check_engines(engines: Mapping[str, EngineSpec]) -> None:
    """Garde de complétude : chaque moteur déclare un mode connu (`ENGINE_MODES`)."""
    for name, spec in engines.items():
        mode = getattr(spec, "mode", None)
        if mode not in ENGINE_MODES:
            raise EngineDeclarationError(
                f"Moteur {name} : mode {mode!r} inconnu ({' ou '.join(ENGINE_MODES)} attendu, décision 207)."
            )


check_engines(ENGINES)


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
            yield from _leaves(v, f"{path}/{str(k).replace('~', '~0').replace('/', '~1')}")  # RFC 6901
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from _leaves(v, f"{path}/{i}")
    else:
        yield path, doc


def _changed_leaves(a: Any, b: Any) -> int:
    return len(_changed(a, b))


def _changed(a: Any, b: Any) -> list[tuple[str, Any, Any]]:
    """(chemin relatif, avant, après) de chaque feuille changée, `ABSENT` pour une feuille ajoutée ou retirée."""
    la, lb = dict(_leaves(a)), dict(_leaves(b))
    keys = [*la, *(k for k in lb if k not in la)]
    return [(k, la.get(k, ABSENT), lb.get(k, ABSENT)) for k in keys if k not in la or k not in lb or la[k] != lb[k]]


class _Origins:
    """Résolveurs d'origine des deux dossiers comparés, chargés à la demande."""

    def __init__(self, before: Path, after: Path) -> None:
        self.dirs = (before, after)
        self.loaded: list[Any] = []

    def __call__(self, file: str, pointer: str) -> tuple[str | None, str | None]:
        if not self.loaded:
            from forever.origins import OriginResolver

            self.loaded = [OriginResolver.load(d) for d in self.dirs]
        return self.loaded[0].origin(file, pointer), self.loaded[1].origin(file, pointer)


def _value_changes(file: str, pointer: str | None, a: Any, b: Any, origins: _Origins) -> list[ValueChange]:
    out = []
    for path, x, y in _changed(a, b):
        full = f"{pointer or ''}{path}"
        out.append(ValueChange(file, full, x, y, *origins(file, full)))
    return out


def _origin_counts(changes: Sequence[ValueChange]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in changes:
        origin = c.origin_after if c.after is not ABSENT else c.origin_before
        key = origin or "sans_règle"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


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
    """Entrées de chaque moteur comparées entre deux dossiers de version ; un item « différent » porte ses feuilles
    changées (`changes`, `ValueChange` avec l'origine déclarée avant et après) et leurs comptes par origine. Les noms
    affichés (`DISPLAY_KEYS`) ne comptent pas."""
    metadata = metadata_keys(before, after) | DISPLAY_KEYS
    origins = _Origins(before, after)
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
        out: dict[str, Any] = {
            "file": file,
            "pointer": pointer,
            "status": "identique" if ha == hb else "différent",
            "before": ha,
            "after": hb,
            "leaves": 0,
        }
        if ha != hb:
            changes = _value_changes(file, pointer, sa, sb, origins)
            out.update(leaves=len(changes), changes=changes, origins=_origin_counts(changes))
        return out

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
    """(moteur, cas) à rejouer : seulement les moteurs dont une entrée change (un moteur qui recopie n'a pas de
    cas)."""
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


def hotfix_losses(before: Path, after: Path) -> list[ValueChange]:
    """Valeurs d'origine `correctif_serveur` de la version installée (`before`) perdues dans la copie de préparation
    (`after`) : feuille changée, ajoutée ou retirée sous une règle `correctif_serveur` avant, dont l'origine après n'est
    pas `correctif_serveur` (décision 207). Tous les fichiers portant une telle règle, pas seulement les entrées des
    moteurs : une recherche lit aussi ces valeurs."""
    from forever.origins import ORIGINS_NAME, SERVER_ORIGIN

    try:
        doc = json.loads((before / ORIGINS_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    files = sorted({str(r.get("file")) for r in doc.get("rules", []) if r.get("origin") == SERVER_ORIGIN})
    metadata = metadata_keys(before, after)
    origins = _Origins(before, after)
    out: list[ValueChange] = []
    for name in files:
        docs = []
        for folder in (before, after):
            try:
                docs.append(_strip(json.loads((folder / name).read_text(encoding="utf-8")), metadata))
            except (OSError, ValueError):
                docs.append(None)
        for change in _value_changes(name, None, docs[0], docs[1], origins):
            if change.origin_before == SERVER_ORIGIN and change.origin_after != SERVER_ORIGIN:
                out.append(change)
    return out
