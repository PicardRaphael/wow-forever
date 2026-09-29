"""Installation d'une version candidate dans la version courante des données (T06b, décision D3) : révision
numérotée et journalisée de `forever/data/<version>/`, jamais une autre version.

Règles de fusion (seuls changements permis) :
- valeur d'un talent ou d'un sort changée : listée dans `confirmed_changes.json` (`confirmed`), ou valeur du client
  là où le dépôt avait `null` (`observation`, par exemple un coût en mana) ;
- certitude d'un talent passée à `FC-<build>` (`certainty`) ;
- champs du client ajoutés (`added_field`) : `name_fr`, `tooltip_values`, `source` ; `desc` et `spellIds` du dépôt
  gardés (gabarit `{i}` et identifiants par rang), ceux du client rangés dans `source` ;
- `duration_s` retiré (`removed_field`) quand la durée corrigée est la valeur du rang du client.
Tout autre écart (structure d'un talent, rang en plus ou en moins, valeur non confirmée) refuse l'installation."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict

from forever.config import Deps
from forever.errors import ForeverError, InvalidArgumentError
from forever.manifest import SOURCES_NAME, write_manifest
from forever.pipeline.diff import TALENT_FIELDS, Change, _rows
from forever.pipeline.sources import load_source
from forever.provenance import Provenance, data_revision_of, format_provenance_line, local_provenance, make_provenance
from forever.store import current_identity
from forever.timefmt import format_utc

TALENTS = "talents.json"
SPELLS = "spells.json"
CONFIRMED = "confirmed_changes.json"
REVISIONS = "revisions.json"
RULES = ("confirmed", "observation", "certainty", "added_field", "removed_field", "metadata")
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
    candidate: str
    candidate_sha: str
    revision_from: int
    revision_to: int
    changes: list[InstallChange]
    refused: list[InstallChange]
    counts: dict[str, int]
    provenance: Provenance


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
                if c is None:
                    self.add(TALENTS, key, t, None, source, "certain", "refused")
                    merged.append(t)
                    continue
                for f in TALENT_FIELDS:
                    if t.get(f) != c.get(f):
                        self.add(TALENTS, f"{key}.{f}", t.get(f), c.get(f), source, "certain", "refused")
                for ch in _rows("talent", key, t.get("ranks", []), c.get("ranks", []), None):
                    self.value(TALENTS, ch, source)
                if "tooltip_values" in t:
                    for ch in _rows(
                        "talent", key, t["tooltip_values"], c.get("tooltip_values", []), None, "tooltip_values"
                    ):
                        self.add(TALENTS, f"{key}.{ch['field']}", ch["old"], ch["new"], source, "certain", "refused")
                merged.append(self._talent(t, c, source))
            tree["talents"] = merged
        for key, extra in by_key.items():
            if key not in seen:
                self.add(TALENTS, key, None, extra, source, "certain", "refused")
        return doc

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


def _merge(deps: Deps, candidate: str) -> tuple[InstallPlan, dict[str, Any]]:
    identity = current_identity(deps.data_dir)
    src, cv = load_source(deps, candidate)
    if not src.candidate:
        raise InvalidArgumentError(
            f"{candidate} n'est pas une version candidate.", "donner le dossier écrit par `forever decode`"
        )
    _, rv = load_source(deps, identity.game_version)
    if cv.game_version != rv.game_version:
        raise InvalidArgumentError(
            f"Candidate {cv.game_version} ≠ version courante {rv.game_version} : une installation révise la version "
            "courante seulement.",
            "une nouvelle version de données passe par la chaîne de T08",
        )
    confirmed_doc = _json(rv.path / CONFIRMED)
    read_at = str(cv.sources.get("collected_at") or format_utc(deps.now())[:10])
    m = _Merge(rv.game_version, confirmed_doc["changes"], read_at)
    talents = m.talents(_json(rv.path / TALENTS), _json(cv.path / TALENTS))
    spells = m.spells(_json(rv.path / SPELLS), _json(cv.path / SPELLS))
    rev = data_revision_of(rv.sources)
    counts = {r: sum(1 for c in m.changes if c["rule"] == r) for r in RULES}
    counts["refused"] = len(m.refused)
    provenance = make_provenance(
        deps,
        game_version=rv.game_version,
        data_sha=rv.data_sha,
        freshness=local_provenance(deps)["freshness"],
        certainty="certain",
        assumptions=[f"candidate {candidate} (données {cv.data_sha}) sur la version {rv.game_version} r{rev}"],
    )
    plan: InstallPlan = {
        "version": rv.game_version,
        "candidate": candidate,
        "candidate_sha": cv.data_sha,
        "revision_from": rev,
        "revision_to": rev + 1,
        "changes": m.changes,
        "refused": m.refused,
        "counts": counts,
        "provenance": provenance,
    }
    docs = {"talents": talents, "spells": spells, "applied": m.applied, "observed": m.observed, "path": rv.path}
    return plan, docs


def plan_install(deps: Deps, candidate: str) -> InstallPlan:
    """Changements qu'écrirait l'installation de `candidate` (rien n'est écrit)."""
    return _merge(deps, candidate)[0]


class Revision(TypedDict):
    revision: int
    date: str
    motif: str
    command: str
    candidate: dict[str, str]
    report: str | None
    counts: dict[str, int]
    changes: list[InstallChange]


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
    files[REVISIONS] = {
        "source": "forever install : journal des révisions de la version (motif, commande, rapport, valeurs changées)",
        "certainty": "certain",
        "notes": ["chaque valeur changée porte sa source et sa certitude (champs source et certainty)"],
    }
    return doc


def apply_install(
    deps: Deps, candidate: str, *, motif: str, report: str | None = None, date: str | None = None
) -> Revision:
    """Écrit la révision suivante de la version courante (talents.json, spells.json, confirmed_changes.json,
    sources.json, revisions.json), puis le manifeste. Refuse tout écart hors règles (InstallRefusedError) et toute
    installation qui ne change rien (InvalidArgumentError)."""
    plan, docs = _merge(deps, candidate)
    if plan["refused"]:
        raise InstallRefusedError(plan["refused"])
    if not plan["changes"]:
        raise InvalidArgumentError(
            f"Rien à installer : la candidate ne change rien à {plan['version']} r{plan['revision_from']}.",
            "aucune action nécessaire",
        )
    day = date or format_utc(deps.now())[:10]
    n, version = plan["revision_to"], plan["version"]
    vdir: Path = docs["path"]
    confirmed = _confirmed(_json(vdir / CONFIRMED), docs, n, version, day)
    sources = _sources(_json(vdir / SOURCES_NAME), docs, n, version, day)
    revision: Revision = {
        "revision": n,
        "date": day,
        "motif": motif,
        "command": f"forever install {candidate} --yes",
        "candidate": {"path": candidate, "data_sha": plan["candidate_sha"]},
        "report": report,
        "counts": {k: v for k, v in plan["counts"].items() if k != "refused"},
        "changes": plan["changes"],
    }
    path = vdir / REVISIONS
    history: dict[str, Any] = (
        _json(path)
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
    _write(vdir / TALENTS, docs["talents"], 1)
    _write(vdir / SPELLS, docs["spells"], 1)
    _write(vdir / CONFIRMED, confirmed, 2)
    _write(vdir / SOURCES_NAME, sources, 2)
    _write(path, history, 1)
    write_manifest(deps.data_dir)
    return revision


LABELS = {
    "confirmed": "changement confirmé (confirmed_changes.json)",
    "observation": "valeur du client là où le dépôt avait null",
    "certainty": "certitude du talent",
    "added_field": "champ ajouté",
    "removed_field": "champ retiré",
    "metadata": "métadonnée",
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
    values = [c for c in plan["changes"] if c["rule"] in ("confirmed", "observation", "removed_field")]
    for title, rows in (("Valeurs changées", values), ("Écarts refusés", plan["refused"])):
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
