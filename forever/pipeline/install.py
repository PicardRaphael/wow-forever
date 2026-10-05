"""Installation d'une version candidate dans la version courante des données (T06b, décision D3) : révision
numérotée et journalisée de `forever/data/<version>/`, jamais une autre version.

Règles de fusion (seuls changements permis) :
- valeur d'un talent ou d'un sort changée : listée dans `confirmed_changes.json` (`confirmed`), ou valeur du client
  là où le dépôt avait `null` (`observation`, par exemple un coût en mana) ;
- certitude d'un talent passée à `FC-<build>` (`certainty`) ;
- champs du client ajoutés (`added_field`) : `name_fr`, `tooltip_values`, `source` ; `desc` et `spellIds` du dépôt
  gardés (gabarit `{i}` et identifiants par rang), ceux du client rangés dans `source` ;
- `duration_s` retiré (`removed_field`) quand la durée corrigée est la valeur du rang du client ;
- fichiers des 9 classes (PV1, `CLASS_FILES`) ajoutés (`added_file`) ou remplacés (`replaced_file`), seulement s'ils
  sont décodés des tables de cette version (jamais un fichier hérité, marqué `inherited_from`) ; de même pour
  `pets.json` (CH0 : familiers du Chasseur), jamais retiré quand la candidate ne le porte pas ;
- fichier retiré (`retired_file`) seulement s'il est déclaré dans `retired_files` de la candidate et que son
  remplaçant y est décodé ; sa copie figée (`frozen_copy`) est alors ajoutée. Aucun retrait n'est jamais déduit.
Tout autre écart (structure d'un talent, rang en plus ou en moins, valeur non confirmée) refuse l'installation."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError
from forever.manifest import SOURCES_NAME, write_manifest
from forever.pipeline.builds import version_key
from forever.pipeline.diff import TALENT_FIELDS, Change, _rows
from forever.pipeline.sources import load_source
from forever.pipeline.value_diff import character_lines, scaling_lines
from forever.provenance import Provenance, data_revision_of, format_provenance_line, local_provenance, make_provenance
from forever.store import current_identity
from forever.timefmt import format_utc

TALENTS = "talents.json"
SPELLS = "spells.json"
CONFIRMED = "confirmed_changes.json"
REVISIONS = "revisions.json"
META = "meta.json"
MECHANICS = "mechanics.json"
BETA_CAP_KEY = "build.beta_level_cap"  # retirée de mechanics.json par l'installation (T08b, D2)
RULES = (
    "confirmed",
    "observation",
    "certainty",
    "added_field",
    "removed_field",
    "metadata",
    "added_file",
    "replaced_file",
    "retired_file",
    "game_state",
    "value",
)
FILE_RULES = ("added_file", "replaced_file", "retired_file")
# Copies figées reportées d'une version à la suivante (forever decode ne les écrit pas).
CARRIED = ("_seed_talents.json", "_seed_spells.json", "_source_gunba_mage_tree.json", "_seed_racials.json")
CLASS_FILES = ("classes.json", "races.json", "pvp_items.json")
MAGE_CLASS = "Mage"  # moteur du Mage : ses clés de talents sont celles de talents.json
PETS_FILE = "pets.json"  # CH0 : familiers du Chasseur, ajouté ou remplacé comme les fichiers des 9 classes
# T08b, bloc C : fichiers décodés installés par une révision, avec la liste de leurs valeurs changées.
VALUE_FILES = ("spell_scaling.json", "character_scaling.json")
TALENT_TABLES = "tables Trait* et Spell* (wago.tools)"
SPELL_TABLES = "tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools)"


class InstallChange(TypedDict):
    file: str
    path: str
    before: Any
    after: Any
    source: str
    certainty: str
    rule: str


class InstallPlan(TypedDict):
    version: str
    version_from: str
    version_to: str
    new_version: bool
    candidate: str
    candidate_sha: str
    revision_from: int
    revision_to: int
    changes: list[InstallChange]
    refused: list[InstallChange]
    counts: dict[str, int]
    provenance: Provenance
    game_state: dict[str, Any]


class InstallRefusedError(ForeverError):
    def __init__(self, refused: Sequence[InstallChange]) -> None:
        shown = " ; ".join(f"{c['file']} {c['path']} {c['before']!r} -> {c['after']!r}" for c in refused[:5])
        more = f" (et {len(refused) - 5} autre(s))" if len(refused) > 5 else ""
        super().__init__(
            "install_refused",
            f"Installation refusée : {len(refused)} écart(s) hors des règles de fusion : {shown}{more}.",
            "trancher chaque écart (tasks/Txx-ecarts.md) et l'ajouter à confirmed_changes.json, ou corriger la candidate",
        )


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, doc: Any, indent: int) -> None:
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=indent) + "\n").encode("utf-8"))


def _key(kind: str, key: str, field: str | None, old: Any, new: Any) -> tuple[str, str, str, str, str]:
    return (kind, key, str(field), json.dumps(old, sort_keys=True), json.dumps(new, sort_keys=True))


class _Merge:
    def __init__(self, version: str, confirmed: Sequence[Mapping[str, Any]], read_at: str) -> None:
        self.build = version.rsplit(".", 1)[-1]
        self.version = version
        self.read_at = read_at
        self.confirmed = {_key(c["kind"], c["key"], c["field"], c["old"], c["new"]): c for c in confirmed}
        self.changes: list[InstallChange] = []
        self.refused: list[InstallChange] = []
        self.applied: list[Mapping[str, Any]] = []
        self.observed: list[Change] = []

    def add(self, file: str, path: str, before: Any, after: Any, source: str, certainty: str, rule: str) -> None:
        change: InstallChange = {
            "file": file,
            "path": path,
            "before": before,
            "after": after,
            "source": source,
            "certainty": certainty,
            "rule": rule,
        }
        (self.refused if rule == "refused" else self.changes).append(change)

    def value(self, file: str, c: Change, source: str) -> None:
        """Changement de valeur d'un rang : confirmé, observation (null du dépôt) ou refusé."""
        path = f"{c['key']}.{c['field']}"
        entry = self.confirmed.get(_key(c["kind"], c["key"], c["field"], c["old"], c["new"]))
        if entry is not None:
            self.applied.append(entry)
            self.add(file, path, c["old"], c["new"], f"{source} ; {entry['decision']}", "certain", "confirmed")
        elif c["change"] == "modified" and c["old"] is None and c["kind"] == "spell":
            self.observed.append(c)
            self.add(file, path, None, c["new"], source, "certain", "observation")
        else:
            self.add(file, path, c["old"], c["new"], source, "certain", "refused")

    def talents(self, repo: Mapping[str, Any], cand: Mapping[str, Any]) -> dict[str, Any]:
        by_key = {t["key"]: t for tree in cand["trees"] for t in tree["talents"]}
        seen: set[str] = set()
        doc = copy.deepcopy(dict(repo))
        source = f"client {self.version}, {TALENT_TABLES}"
        for tree in doc["trees"]:
            merged = []
            for t in tree["talents"]:
                key = t["key"]
                seen.add(key)
                c = by_key.get(key)
                rename = self._renamed(key, by_key) if c is None else None
                if c is None and rename is None:
                    self.add(TALENTS, key, t, None, source, "certain", "refused")
                    merged.append(t)
                    continue
                if rename is not None:
                    c = by_key[rename["new"]]
                    seen.add(rename["new"])
                    self.applied.append(rename)
                assert c is not None
                for f in TALENT_FIELDS:
                    if t.get(f) != c.get(f) and not (rename is not None and f == "name"):
                        self.add(TALENTS, f"{key}.{f}", t.get(f), c.get(f), source, "certain", "refused")
                for ch in _rows("talent", key, t.get("ranks", []), c.get("ranks", []), None):
                    self.value(TALENTS, ch, source)
                if "tooltip_values" in t:
                    for ch in _rows(
                        "talent", key, t["tooltip_values"], c.get("tooltip_values", []), None, "tooltip_values"
                    ):
                        self.value(TALENTS, ch, source)
                out = self._talent(t, c, source)
                if rename is not None:
                    self._rename(out, c, rename, source)
                merged.append(out)
            tree["talents"] = merged
        for key, extra in by_key.items():
            if key not in seen:
                self.add(TALENTS, key, None, extra, source, "certain", "refused")
        return doc

    def _renamed(self, key: str, by_key: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Renommage confirmé du talent `key` (`change` « renamed », champ `key`) vers une clé de la candidate."""
        for entry in self.confirmed.values():
            if (
                entry["kind"] == "talent"
                and entry.get("change") == "renamed"
                and entry["key"] == key
                and entry["field"] == "key"
                and entry["old"] == key
                and entry["new"] in by_key
            ):
                return entry
        return None

    def _rename(self, out: dict[str, Any], c: Mapping[str, Any], rename: Mapping[str, Any], source: str) -> None:
        """Talent renommé par le client : la clé du dépôt reste, les noms du client et le gabarit d'infobulle de la
        décision (`desc` de l'entrée confirmée) remplacent les anciens ; `source.client_key` garde la clé du client."""
        key, why = out["key"], f"{source} ; {rename['decision']}"
        old_name = out.get("name")
        if c.get("name") and old_name and old_name != c["name"]:
            former = [*out.get("former_names", []), old_name]
            self.add(TALENTS, f"{key}.former_names", out.get("former_names"), former, why, "certain", "confirmed")
            out["former_names"] = former
        for f, new in (("name", c.get("name")), ("name_fr", c.get("name_fr", "")), ("desc", rename.get("desc"))):
            if new is not None and out.get(f) != new:
                self.add(TALENTS, f"{key}.{f}", out.get(f), new, why, "certain", "confirmed")
                out[f] = new
        out["source"] = {**out["source"], "client_key": rename["new"]}

    def _talent(self, t: Mapping[str, Any], c: Mapping[str, Any], source: str) -> dict[str, Any]:
        key = t["key"]
        certainty = f"FC-{self.build}"
        out: dict[str, Any] = {}
        for f, v in t.items():
            if f == "duration_s":
                if [v, *c["ranks"][0][1:]] == list(c["ranks"][0]):
                    self.add(TALENTS, f"{key}.duration_s", v, None, source, "certain", "removed_field")
                    continue
                out[f] = v
                continue
            if f == "tooltip_values":  # un écart non confirmé est refusé plus haut : la valeur du client fait foi
                out[f] = c.get("tooltip_values", v)
                continue
            if f == "ranks":
                out[f] = c["ranks"]
                if "tooltip_values" not in t:
                    out["tooltip_values"] = c.get("tooltip_values", [])
                    self.add(
                        TALENTS, f"{key}.tooltip_values", None, out["tooltip_values"], source, "certain", "added_field"
                    )
                continue
            if f == "certainty":
                if v != certainty:
                    self.add(TALENTS, f"{key}.certainty", v, certainty, source, "certain", "certainty")
                out[f] = certainty
                continue
            out[f] = v
            if f == "name" and "name_fr" not in t:
                out["name_fr"] = c.get("name_fr", "")
                self.add(TALENTS, f"{key}.name_fr", None, out["name_fr"], source, "certain", "added_field")
        client = {
            "build": self.version,
            "tables": TALENT_TABLES,
            "read_at": self.read_at,
            "client_spell_ids": c.get("spellIds", []),
            "client_desc": c.get("desc", ""),
        }
        if t.get("source") != client:
            rule = "added_field" if "source" not in t else "metadata"
            self.add(TALENTS, f"{key}.source", t.get("source"), client, source, "certain", rule)
        out["source"] = client
        return out

    def spells(self, repo: Mapping[str, Any], cand: Mapping[str, Any]) -> dict[str, Any]:
        doc = copy.deepcopy(dict(repo))
        fields = list(repo.get("rank_format", []))
        source = f"client {self.version}, {SPELL_TABLES}"
        cand_spells = cand.get("spells", {})
        for key, s in doc["spells"].items():
            c = cand_spells.get(key)
            if c is None:
                self.add(SPELLS, key, s, None, source, "certain", "refused")
                continue
            for f in set(s) | set(c):
                if f in ("ranks", "source", "name", "name_fr", "spell_ids") or s.get(f) == c.get(f):
                    continue
                self.add(SPELLS, f"{key}.{f}", s.get(f), c.get(f), source, "certain", "refused")
            for ch in _rows("spell", key, s["ranks"], c["ranks"], fields):
                self.value(SPELLS, ch, source)
            s["ranks"] = [
                [a if a == b and (a is None) == (b is None) else b for a, b in zip(old, new, strict=True)]
                if len(old) == len(new)
                else old
                for old, new in zip(s["ranks"], c["ranks"], strict=False)
            ]
            client = {
                "build": self.version,
                "tables": SPELL_TABLES,
                "read_at": self.read_at,
                "rank_spell_ids": c.get("spell_ids", []),
                "mana": "SpellPower.ManaCost",
            }
            if s.get("mana_pct_base") is not None:
                client["mana_pct_base"] = "SpellPower.PowerCostPct"
            if s.get("source") != client:
                rule = "added_field" if "source" not in s else "metadata"
                self.add(SPELLS, f"{key}.source", s.get("source"), client, source, "certain", rule)
            s["source"] = client
        for key in cand_spells:
            if key not in doc["spells"]:
                self.add(SPELLS, key, None, cand_spells[key], source, "certain", "refused")
        return doc


def display_path(deps: Deps, path: str) -> str:
    """Chemin d'une candidate tel qu'il s'écrit dans la trace versionnée : `<cache>/…` sous le cache, `~/…` sous le
    dossier personnel, jamais un chemin personnel absolu (décision 99)."""
    p = Path(path).resolve()
    for root, label in ((deps.cache_dir, "<cache>"), (Path.home(), "~")):
        try:
            return f"{label}/{p.relative_to(Path(root).resolve()).as_posix()}"
        except ValueError:
            continue
    return Path(path).as_posix()


def _short_sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.is_file() else None


def _decoded(path: Path) -> bool:
    """Fichier de la candidate décodé des tables de sa version (pas une copie héritée d'une autre version)."""
    if not path.is_file():
        return False
    doc = _json(path)
    return isinstance(doc, dict) and "inherited_from" not in doc


def _file_changes(repo: Path, cand: Path, cand_sources: Mapping[str, Any], version: str) -> list[InstallChange]:
    """Fichiers ajoutés, remplacés ou retirés (règles `added_file`, `replaced_file`, `retired_file`)."""
    changes: list[InstallChange] = []
    source = f"Client {version} : fichier décodé par forever decode (candidate)"
    for name in VALUE_FILES:
        if not _decoded(cand / name):
            continue
        if not (repo / name).is_file():
            changes.append(
                {
                    "file": name,
                    "path": "*",
                    "before": None,
                    "after": _short_sha(cand / name),
                    "source": source,
                    "certainty": "certain",
                    "rule": "added_file",
                }
            )
            continue
        lines = (scaling_lines if name == VALUE_FILES[0] else character_lines)(_json(repo / name), _json(cand / name))
        changes += [
            {
                "file": name,
                "path": f"{key} · {field}" if field else key,
                "before": old,
                "after": new,
                "source": source,
                "certainty": "certain",
                "rule": "value",
            }
            for _, key, field, old, new in lines
        ]
    for name in (*CLASS_FILES, PETS_FILE):
        if not _decoded(cand / name):
            continue
        before, after = _short_sha(repo / name), _short_sha(cand / name)
        if before != after:
            rule = "added_file" if before is None else "replaced_file"
            changes.append(
                {
                    "file": name,
                    "path": "*",
                    "before": before,
                    "after": after,
                    "source": source,
                    "certainty": "certain",
                    "rule": rule,
                }
            )
    for old, spec in (cand_sources.get("retired_files") or {}).items():
        replacement = str(spec.get("replaced_by", ""))
        if not (repo / old).is_file() or replacement not in CLASS_FILES or not _decoded(cand / replacement):
            continue
        reason = f"retiré : remplacé par {replacement} ({spec.get('reason', 'retired_files')})"
        changes.append(
            {
                "file": old,
                "path": "*",
                "before": _short_sha(repo / old),
                "after": None,
                "source": reason,
                "certainty": "certain",
                "rule": "retired_file",
            }
        )
        frozen = spec.get("frozen_copy")
        if frozen and not (repo / frozen).is_file() and (cand / frozen).is_file():
            changes.append(
                {
                    "file": str(frozen),
                    "path": "*",
                    "before": None,
                    "after": _short_sha(cand / frozen),
                    "source": f"copie figée de {old} (mode seed)",
                    "certainty": "certain",
                    "rule": "added_file",
                }
            )
    return changes


def _game_state(
    repo: Path, rev: int, cap: int | None, source: str | None
) -> tuple[dict[str, Any], list[InstallChange]]:
    """Plafond de la bêta, fait d'installation (T08b, D2) : valeur donnée avec sa source (`probable` pour une note,
    `certain` pour une observation en jeu), sinon valeur précédente reportée (« reportée de la révision N »).
    L'ancienne clé de `mechanics.json` est retirée (règle `game_state`)."""
    if cap is not None and not source:
        raise InvalidArgumentError(
            "--beta-level-cap exige sa source.", "ajouter --beta-level-cap-source <adresse de la note | observation>"
        )
    meta = _json(repo / META) if (repo / META).is_file() else {}
    prev = (meta.get("game_state") or {}).get("beta_level_cap") if isinstance(meta, dict) else None
    mech = _json(repo / MECHANICS) if (repo / MECHANICS).is_file() else {}
    old = (mech.get("values") or {}).get(BETA_CAP_KEY) if isinstance(mech, dict) else None
    changes: list[InstallChange] = []
    if cap is not None:
        certainty = "certain" if source == "observation" else "probable"
        state: dict[str, Any] = {"value": cap, "source": source, "certainty": certainty, "carried": False}
        before = (prev or old or {}).get("value")
        changes.append(
            {
                "file": META,
                "path": "game_state.beta_level_cap",
                "before": before,
                "after": cap,
                "source": str(source),
                "certainty": certainty,
                "rule": "game_state",
            }
        )
    else:
        base = prev or old
        if not base:
            return {}, []
        state = {
            "value": base.get("value"),
            "source": base.get("source"),
            "certainty": base.get("certainty"),
            "carried": True,
            "carried_from": f"révision {rev}",
        }
        if prev and prev.get("date") and prev.get("revision") is not None:
            state |= {"date": prev["date"], "revision": prev["revision"]}  # date et révision d'origine gardées
    if old is not None:
        changes.append(
            {
                "file": MECHANICS,
                "path": f"values.{BETA_CAP_KEY}",
                "before": old.get("value"),
                "after": None,
                "source": "plafond de la bêta, fait d'installation : meta.json game_state (T08b, D2)",
                "certainty": str(state.get("certainty")),
                "rule": "game_state",
            }
        )
    return {"beta_level_cap": state}, changes


def _merge(
    deps: Deps,
    candidate: str,
    *,
    new_version: bool = False,
    beta_level_cap: int | None = None,
    beta_level_cap_source: str | None = None,
) -> tuple[InstallPlan, dict[str, Any]]:
    identity = current_identity(deps.data_dir)
    src, cv = load_source(deps, candidate)
    if not src.candidate:
        raise InvalidArgumentError(
            f"{candidate} n'est pas une version candidate.", "donner le dossier écrit par `forever decode`"
        )
    _, rv = load_source(deps, identity.game_version)
    if new_version:
        if cv.game_version == rv.game_version:
            raise InvalidArgumentError(
                f"Candidate {cv.game_version} = version courante : --new-version installe une version différente.",
                "installer une révision sans --new-version",
            )
        if version_key(cv.game_version) < version_key(rv.game_version):
            raise InvalidArgumentError(
                f"Candidate {cv.game_version} antérieure à la version courante {rv.game_version}.",
                "installer une version plus récente",
            )
    elif cv.game_version != rv.game_version:
        raise InvalidArgumentError(
            f"Candidate {cv.game_version} ≠ version courante {rv.game_version} : une installation révise la version "
            "courante seulement.",
            "installer une nouvelle version avec --new-version (T08a)",
        )
    confirmed_doc = _json(rv.path / CONFIRMED)
    read_at = str(cv.sources.get("collected_at") or format_utc(deps.now())[:10])
    # Les valeurs sont relues dans la candidate : leur certitude et leur bloc `source` nomment le build lu.
    m = _Merge(cv.game_version if new_version else rv.game_version, confirmed_doc["changes"], read_at)
    talents = m.talents(_json(rv.path / TALENTS), _json(cv.path / TALENTS))
    spells = m.spells(_json(rv.path / SPELLS), _json(cv.path / SPELLS))
    if not new_version:
        m.changes += _file_changes(rv.path, cv.path, cv.sources, rv.game_version)
    rev = data_revision_of(rv.sources)
    game_state, state_changes = _game_state(rv.path, rev, beta_level_cap, beta_level_cap_source)
    m.changes += state_changes
    counts = {r: sum(1 for c in m.changes if c["rule"] == r) for r in RULES}
    counts["refused"] = len(m.refused)
    target = cv.game_version if new_version else rv.game_version
    assumption = f"candidate {display_path(deps, candidate)} (données {cv.data_sha}) sur la version {rv.game_version}"
    provenance = make_provenance(
        deps,
        game_version=target,
        data_sha=rv.data_sha,
        freshness=local_provenance(deps)["freshness"],
        certainty="certain",
        assumptions=[assumption + (f" (nouvelle version {target})" if new_version else f" r{rev}")],
    )
    plan: InstallPlan = {
        "version": target,
        "version_from": rv.game_version,
        "version_to": target,
        "new_version": new_version,
        "candidate": display_path(deps, candidate),
        "candidate_sha": cv.data_sha,
        "revision_from": rev,
        "revision_to": 1 if new_version else rev + 1,
        "changes": m.changes,
        "refused": m.refused,
        "counts": counts,
        "provenance": provenance,
        "game_state": game_state,
    }
    docs = {
        "talents": talents,
        "spells": spells,
        "applied": m.applied,
        "observed": m.observed,
        "path": rv.path,
        "candidate_path": cv.path,
        "collected_at": cv.sources.get("collected_at"),
        "candidate_sources": cv.sources,
    }
    return plan, docs


def plan_install(
    deps: Deps,
    candidate: str,
    *,
    new_version: bool = False,
    beta_level_cap: int | None = None,
    beta_level_cap_source: str | None = None,
) -> InstallPlan:
    """Changements qu'écrirait l'installation de `candidate` (rien n'est écrit)."""
    return _merge(
        deps,
        candidate,
        new_version=new_version,
        beta_level_cap=beta_level_cap,
        beta_level_cap_source=beta_level_cap_source,
    )[0]


class Revision(TypedDict):
    revision: int
    date: str
    motif: str
    command: str
    candidate: dict[str, str]
    report: str | None
    counts: dict[str, int]
    changes: list[InstallChange]
    game_state: NotRequired[dict[str, Any]]
    renamed_in_classes: NotRequired[list[dict[str, str]]]
    hotfixes: NotRequired[list[int]]  # T08c : poussées des correctifs du serveur appliquées


def _mana_note(spells: Mapping[str, Any]) -> str:
    """Note de `sources.json` sur le champ mana, tirée des données installées."""
    pct = [k for k, s in spells["spells"].items() if s.get("mana_pct_base") is not None]
    col = list(spells["rank_format"]).index("mana")
    null = [k for k, s in spells["spells"].items() if any(r[col] is None for r in s["ranks"])]
    other = [k for k in null if k not in pct]
    note = "mana : SpellPower.ManaCost du client"
    if pct:
        note += f" ; null pour {', '.join(pct)} : coût en part du mana de base (mana_pct_base, SpellPower.PowerCostPct)"
    if other:
        note += f" ; null sans coût du client : {', '.join(other)} (estimation mana.talent_rank_cost)"
    return note


def _confirmed(doc: dict[str, Any], docs: Mapping[str, Any], n: int, version: str, day: str) -> dict[str, Any]:
    applied = {_key(c["kind"], c["key"], c["field"], c["old"], c["new"]) for c in docs["applied"]}
    for entry in doc["changes"]:
        if _key(entry["kind"], entry["key"], entry["field"], entry["old"], entry["new"]) in applied:
            entry.setdefault("applied_in_revision", n)
    known = {_key(c["kind"], c["key"], c["field"], c["old"], c["new"]) for c in doc["changes"]}
    for c in docs["observed"]:
        if _key(c["kind"], c["key"], c["field"], c["old"], c["new"]) in known:
            continue
        doc["changes"].append(
            {
                "kind": c["kind"],
                "key": c["key"],
                "change": c["change"],
                "field": c["field"],
                "old": c["old"],
                "new": c["new"],
                "reference_certainty": "certain (spells.json : null, valeur non publiée)",
                "nature": "client",
                "decision": "valeur du client là où la référence avait null (observation), installée par forever install",
                "applied_in_revision": n,
            }
        )
    stale = "Les fichiers de référence ne sont pas modifiés"
    doc["notes"] = [note for note in doc.get("notes", []) if not note.startswith(stale)]
    doc["notes"].append(
        f"Changements installés dans {version} en révision {n} (forever install, {day}) : champ applied_in_revision."
    )
    return doc


def _sources(doc: dict[str, Any], docs: Mapping[str, Any], n: int, version: str, day: str) -> dict[str, Any]:
    doc["revision"] = n
    doc["revised_at"] = day
    files = doc["files"]
    installed = f"installé en révision {n} (forever install, {day})"
    files[TALENTS] = {
        "source": f"Client {version} : {TALENT_TABLES} décodées par forever decode, {installed}",
        "certainty": "certain",
        "notes": [
            "rangs et tooltip_values : variables d'infobulle au niveau de base du sort (decode_rules.json)",
            "desc : gabarit du dépôt ({i}) ; gabarit brut et identifiants de sort du client dans source",
            f"certitude par talent FC-{version.rsplit('.', 1)[-1]} ; copie figée du seed : _seed_talents.json",
        ],
    }
    old = files.get(SPELLS, {})
    files[SPELLS] = {
        **old,
        "source": f"Client {version} : {SPELL_TABLES} décodées par forever decode, {installed}",
        "certainty": "certain",
        "field_notes": {**old.get("field_notes", {}), "mana": _mana_note(docs["spells"])},
        "notes": [
            "min et max des rangs issus d'un talent lus au niveau de base du sort (convention de la décision 39)",
            "copie figée du seed : _seed_spells.json",
        ],
    }
    cand_files = (docs.get("candidate_sources") or {}).get("files", {})
    for name in sorted(docs.get("value_files", [])):
        if name in cand_files:
            files[name] = {**cand_files[name], "notes": [*cand_files[name].get("notes", []), installed]}
    for change in docs.get("file_changes", []):
        if change["rule"] == "retired_file":
            files.pop(change["file"], None)
        elif change["file"] in cand_files:
            files[change["file"]] = {
                **cand_files[change["file"]],
                "notes": [*cand_files[change["file"]].get("notes", []), installed],
            }
    files[REVISIONS] = {
        "source": "forever install : journal des révisions de la version (motif, commande, rapport, valeurs changées)",
        "certainty": "certain",
        "notes": ["chaque valeur changée porte sa source et sa certitude (champs source et certainty)"],
    }
    return doc


def rename_class_talents(classes: dict[str, Any], confirmed: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, str]]:
    """Applique les renommages confirmés (`change` « renamed ») à l'arbre du Mage de `classes.json` : la clé du client
    devient celle du dépôt, gardée dans `client_key`. L'import du profil traduit les nœuds par ce fichier ; le moteur
    du Mage ne connaît que les clés de `talents.json`. Rend (classe, clé du client, clé du dépôt) par talent renommé."""
    renames = {
        e["new"]: e["old"]
        for e in confirmed
        if e["kind"] == "talent" and e.get("change") == "renamed" and e["field"] == "key"
    }
    done: list[tuple[str, str, str]] = []
    for tree in (classes.get("classes", {}).get(MAGE_CLASS) or {}).get("trees", []):
        for t in tree.get("talents", []):
            if t.get("key") in renames:
                new = t["key"]
                t["key"], t["client_key"] = renames[new], new
                done.append((MAGE_CLASS, new, t["key"]))
    return done


def _new_version_dir(deps: Deps, plan: InstallPlan, docs: Mapping[str, Any], day: str) -> Path:
    """Crée le dossier de la nouvelle version : fichiers décodés de la candidate, copies figées du seed et
    `confirmed_changes.json` repris de la version précédente. Les fichiers fusionnés (talents, sorts), `sources.json`
    et `revisions.json` sont écrits par l'appelant."""
    vdir = deps.data_dir / plan["version_to"]
    if vdir.exists():
        raise InvalidArgumentError(
            f"{plan['version_to']} est déjà installée ({vdir}).", "supprimer le dossier ou choisir une autre version"
        )
    previous: Path = docs["path"]
    cand: Path = docs["candidate_path"]
    vdir.mkdir(parents=True)
    for path in sorted(cand.iterdir()):  # décodés et hérités, hors fusionnés et sources.json
        if path.is_file() and path.name not in (TALENTS, SPELLS, SOURCES_NAME):
            shutil.copyfile(path, vdir / path.name)
    for name in CARRIED:  # copies figées du seed : le mode seed doit rendre les mêmes valeurs
        source = previous / name
        if source.is_file():
            shutil.copyfile(source, vdir / name)
    confirmed = _json(previous / CONFIRMED)
    confirmed["version"] = plan["version_to"]
    confirmed["carried_from"] = plan["version_from"]
    confirmed["notes"] = [
        *confirmed.get("notes", []),
        (
            f"Repris de {plan['version_from']} à l'installation de {plan['version_to']} "
            f"(forever install --new-version, {day}) : applied_in_revision garde la révision d'origine."
        ),
    ]
    _write(vdir / CONFIRMED, confirmed, 2)
    return vdir


def _new_version_sources(docs: Mapping[str, Any], plan: InstallPlan, day: str) -> dict[str, Any]:
    """`sources.json` de la nouvelle version : entrées de la version précédente, recouvertes par celles de la
    candidate (sources du client et marques `inherited_from`), révision remise à 1."""
    doc: dict[str, Any] = _json(Path(docs["path"]) / SOURCES_NAME)
    cand = _json(Path(docs["candidate_path"]) / SOURCES_NAME)
    doc["files"] = {**doc.get("files", {}), **cand.get("files", {})}
    doc["game_version"] = plan["version_to"]
    doc["collected_at"] = docs["collected_at"] or day
    doc["revision"] = 1
    doc["revised_at"] = day
    doc.pop("candidate", None)
    return doc


def apply_install(
    deps: Deps,
    candidate: str,
    *,
    motif: str,
    report: str | None = None,
    date: str | None = None,
    new_version: bool = False,
    beta_level_cap: int | None = None,
    beta_level_cap_source: str | None = None,
) -> Revision:
    """Écrit la révision suivante de la version courante (talents.json, spells.json, confirmed_changes.json,
    sources.json, revisions.json), puis le manifeste. Avec `new_version`, écrit le dossier d'une **nouvelle** version
    (T08a) : fichiers décodés de la candidate, copies figées du seed et changements confirmés repris de la version
    précédente, `revisions.json` en révision 1. Refuse tout écart hors règles (InstallRefusedError) et, sans
    `new_version`, toute installation qui ne change rien (InvalidArgumentError)."""
    plan, docs = _merge(
        deps,
        candidate,
        new_version=new_version,
        beta_level_cap=beta_level_cap,
        beta_level_cap_source=beta_level_cap_source,
    )
    if plan["refused"]:
        raise InstallRefusedError(plan["refused"])
    if not plan["changes"] and not new_version:
        raise InvalidArgumentError(
            f"Rien à installer : la candidate ne change rien à {plan['version']} r{plan['revision_from']}.",
            "aucune action nécessaire",
        )
    day = date or format_utc(deps.now())[:10]
    n, version = plan["revision_to"], plan["version"]
    vdir: Path = _new_version_dir(deps, plan, docs, day) if new_version else docs["path"]
    docs = {
        **docs,
        "file_changes": [c for c in plan["changes"] if c["rule"] in FILE_RULES],
        "value_files": {c["file"] for c in plan["changes"] if c["rule"] == "value"},
    }
    confirmed = _confirmed(_json(vdir / CONFIRMED), docs, n, version, day)
    base = _new_version_sources(docs, plan, day) if new_version else _json(vdir / SOURCES_NAME)
    sources = _sources(base, docs, n, version, day)
    revision: Revision = {
        "revision": n,
        "date": day,
        "motif": motif,
        "command": f"forever install{' --new-version' if new_version else ''} {plan['candidate']} --yes",
        "candidate": {"path": plan["candidate"], "data_sha": plan["candidate_sha"]},
        "report": report,
        "counts": {k: v for k, v in plan["counts"].items() if k != "refused"},
        "changes": plan["changes"],
    }
    if plan["game_state"]:
        revision["game_state"] = plan["game_state"]
    path = vdir / REVISIONS
    history: dict[str, Any] = (
        {"schema_version": 1, "version": version, "revisions": []}
        if new_version
        else _json(path)
        if path.is_file()
        else {
            "schema_version": 1,
            "version": version,
            "revisions": [
                {
                    "revision": plan["revision_from"],
                    "date": str(sources.get("collected_at")),
                    "motif": "état d'origine de la version, avant forever install",
                }
            ],
        }
    )
    history["revisions"].append(revision)
    for name in sorted({c["file"] for c in plan["changes"] if c["rule"] == "value"}):
        shutil.copyfile(Path(docs["candidate_path"]) / name, vdir / name)
    for change in docs["file_changes"]:
        if change["rule"] == "retired_file":
            (vdir / change["file"]).unlink()
        else:
            shutil.copyfile(Path(docs["candidate_path"]) / change["file"], vdir / change["file"])
    _write(vdir / TALENTS, docs["talents"], 1)
    _write(vdir / SPELLS, docs["spells"], 1)
    _write(vdir / CONFIRMED, confirmed, 2)
    _write(vdir / SOURCES_NAME, sources, 2)
    if carry_hotfix_provenance(vdir, Path(docs["candidate_path"])):
        revision["hotfixes"] = _json(vdir / SOURCES_NAME).get("hotfixes", {}).get("pushes", [])
    classes_path = vdir / "classes.json"
    if classes_path.is_file():
        classes = _json(classes_path)
        renamed = rename_class_talents(classes, confirmed["changes"])
        if renamed:
            _write(classes_path, classes, 1)
            revision["renamed_in_classes"] = [{"class": c, "client_key": n, "key": o} for c, n, o in renamed]
    _write(path, history, 1)
    if plan["game_state"]:
        _write_game_state(vdir, plan["game_state"], n, day)
    write_manifest(deps.data_dir)
    return revision


def carry_hotfix_provenance(vdir: Path, cand_vdir: Path) -> bool:
    """T08c : règles `correctif_serveur` d'`origins.json` et bloc `hotfixes` de `sources.json` de la candidate
    reportés dans la version installée (celles d'une révision précédente remplacées) ; rend True si la candidate en
    porte. Une candidate sans correctif retire ceux d'une révision précédente (ses fichiers les remplacent)."""
    from forever.origins import ORIGINS_NAME, SERVER_ORIGIN

    cand_origins = _json(cand_vdir / ORIGINS_NAME) if (cand_vdir / ORIGINS_NAME).is_file() else {}
    cand_sources = _json(cand_vdir / SOURCES_NAME) if (cand_vdir / SOURCES_NAME).is_file() else {}
    rules = [r for r in cand_origins.get("rules", []) if r.get("origin") == SERVER_ORIGIN]
    block = cand_sources.get("hotfixes")
    path = vdir / ORIGINS_NAME
    if path.is_file():
        doc = _json(path)
        kept = [r for r in doc.get("rules", []) if r.get("origin") != SERVER_ORIGIN]
        keys = list(doc.get("metadata_keys", []))
        new = {**doc, "rules": [*kept, *rules]}
        if rules and "hotfix" not in keys:
            new["metadata_keys"] = [*keys, "hotfix"]
        if new != doc:
            _write(path, new, 2)
    spath = vdir / SOURCES_NAME
    if spath.is_file():
        sources = _json(spath)
        updated = {k: v for k, v in sources.items() if k != "hotfixes"}
        if block is not None:
            updated["hotfixes"] = block
        if updated != sources:
            _write(spath, updated, 2)
    return bool(rules or block)


def _game_state_origin(vdir: Path, entries: Mapping[str, Any]) -> None:
    """Origine déclarée du plafond (`origins.json`) accordée à sa source : `journal` pour une observation en jeu
    (certain), `manuel` sinon (au plus probable)."""
    path = vdir / "origins.json"
    cap = entries.get("beta_level_cap")
    if not path.is_file() or not cap:
        return
    doc = _json(path)
    rule = next(
        (r for r in doc.get("rules", []) if r.get("file") == META and "/game_state" in r.get("paths", [])), None
    )
    if rule is None:
        return
    observed = cap.get("certainty") == "certain"
    rule["origin"] = "journal" if observed else "manuel"
    rule["certainty"] = "certain" if observed else "probable"
    rule["source"] = (
        "relevé en jeu par l'utilisateur (forever install --beta-level-cap-source observation)"
        if observed
        else "forever install --beta-level-cap (note officielle), sinon valeur reportée"
    )
    _write(path, doc, 2)


def _write_game_state(vdir: Path, state: Mapping[str, Any], n: int, day: str) -> None:
    """`meta.json` `game_state` (valeur, source, certitude, date, révision ; report signalé) et retrait de
    l'ancienne clé de `mechanics.json`."""
    meta = _json(vdir / META) if (vdir / META).is_file() else {}
    entries = {}
    for key, s in state.items():
        entry = {k: v for k, v in s.items() if k != "carried"}
        if s.get("carried") and "date" in entry and "revision" in entry:
            entries[key] = {**entry, "carried_to": n}
        else:
            entries[key] = {**entry, "date": day, "revision": n}
    meta["game_state"] = {**meta.get("game_state", {}), **entries}
    _write(vdir / META, meta, 1)
    _game_state_origin(vdir, entries)
    mech_path = vdir / MECHANICS
    if mech_path.is_file():
        mech = _json(mech_path)
        if BETA_CAP_KEY in mech.get("values", {}):
            del mech["values"][BETA_CAP_KEY]
            _write(mech_path, mech, 1)


LABELS = {
    "confirmed": "changement confirmé (confirmed_changes.json)",
    "observation": "valeur du client là où le dépôt avait null",
    "certainty": "certitude du talent",
    "added_field": "champ ajouté",
    "removed_field": "champ retiré",
    "metadata": "métadonnée",
    "added_file": "fichier ajouté (décodé du client)",
    "replaced_file": "fichier remplacé (décodé du client)",
    "retired_file": "fichier retiré (retired_files)",
    "game_state": "état du jeu (plafond de la bêta, meta.json game_state)",
    "value": "valeur d'un fichier décodé (spell_scaling.json, character_scaling.json)",
    "refused": "hors règles (refusé)",
}
CELL_MAX = 80


def _cell(value: object) -> str:
    if value is None:
        return "—"
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > CELL_MAX:
        text = text[: CELL_MAX - 1] + "…"
    return "`" + text.replace("|", "\\|") + "`"


def render_install_report(plan: InstallPlan) -> str:
    """Rapport Markdown d'une installation : résumé par règle, valeurs changées (fichier, chemin, avant, après,
    règle, source, certitude), certitudes, champs ajoutés, écarts refusés, provenance."""
    v, a, b = plan["version"], plan["revision_from"], plan["revision_to"]
    lines = [
        f"# data: {v} r{a} → r{b}",
        "",
        f"Candidate : `{plan['candidate']}` (données {plan['candidate_sha']}).",
        "",
    ]
    lines += ["| Règle | Changements |", "| --- | --- |"]
    lines += [f"| {LABELS[r]} | {plan['counts'].get(r, 0)} |" for r in (*RULES, "refused")]
    lines.append("")
    values = [c for c in plan["changes"] if c["rule"] in ("confirmed", "observation", "removed_field", "value")]
    files = [c for c in plan["changes"] if c["rule"] in FILE_RULES]
    for title, rows in (("Valeurs changées", values), ("Fichiers", files), ("Écarts refusés", plan["refused"])):
        if not rows:
            continue
        lines += [f"## {title}", "", "| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |"]
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        lines += [
            f"| {c['file']} | {c['path']} | {_cell(c['before'])} | {_cell(c['after'])} | {c['rule']} | "
            f"{c['source']} | {c['certainty']} |"
            for c in rows
        ]
        lines.append("")
    for key, s in (plan.get("game_state") or {}).items():
        label = {"beta_level_cap": "plafond de la bêta"}.get(key, key)
        how = f"reporté de la {s['carried_from']}" if s.get("carried") else "donné à l'installation"
        lines += [
            "## État du jeu",
            "",
            f"- {label} : {s.get('value')} ({how} ; source {s.get('source')} ; certitude {s.get('certainty')})",
            "",
        ]
    cert = [c for c in plan["changes"] if c["rule"] == "certainty"]
    if cert:
        befores = ", ".join(sorted({str(c["before"]) for c in cert}))
        lines += ["## Certitudes", "", f"{len(cert)} talent(s) : {befores} → {cert[0]['after']} :"]
        lines += ["", ", ".join(c["path"].split(".")[0] for c in cert), ""]
    added = [c for c in plan["changes"] if c["rule"] in ("added_field", "metadata")]
    if added:
        fields: dict[str, int] = {}
        for c in added:
            name = f"{c['file']} : {c['path'].split('.', 1)[1]}"
            fields[name] = fields.get(name, 0) + 1
        lines += ["## Champs ajoutés", ""]
        lines += [f"- {name} ({n})" for name, n in sorted(fields.items())]
        lines.append("")
    lines.append(format_provenance_line(plan["provenance"]))
    return "\n".join(lines) + "\n"
