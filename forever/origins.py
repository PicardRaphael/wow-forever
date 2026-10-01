"""Origine déclarée de chaque valeur des données (`forever/data/<version>/origins.json`, T08b, bloc H, D4).

Chaque feuille d'un fichier de données (nombre, booléen, texte non vide) doit être couverte par une règle :
`file`, `paths` (pointeurs JSON, RFC 6901), `origin`, `source`, `certainty`, et `reason` pour une valeur écrite à
la main ou un paramètre. Six origines :

- `client` : décodée d'une table du client ; `journal` : mesurée dans les journaux ou relevée en jeu ;
  `addon` : addon de données (nom et version) ; `manuel` : écrite à la main (raison et source) ;
- `copie_figee` : copie figée du seed (`_seed_*.json`), lue en mode seed seulement, règle au niveau du fichier ;
- `parametre` : réglage de l'outil (graines, seuils, préréglages, règles de lecture), pas une valeur de jeu.

Plafond de certitude par origine : `client` et `journal` jusqu'à `certain`, `addon` et `manuel` au plus
`probable` ; `copie_figee` et `parametre` sans certitude. Les motifs (`*` : un segment, `**` : zéro ou plus) ne
sont permis que pour `client`, `journal`, `addon` et `copie_figee` : une valeur `manuel` est nommée par son chemin
exact (le chemin couvre son sous-arbre), une clé nouvelle n'est donc jamais couverte en silence. La règle la plus
précise l'emporte (plus de segments littéraux, puis moins de motifs).

Ne sont pas des valeurs : les clés de métadonnées (`metadata_keys`, à toute profondeur) et les chemins de
`not_game_values` (fichiers ou sous-arbres qui ne décrivent pas le jeu : journal des révisions, sources).

Certitude déclarée d'une valeur, comparée à celle de sa règle : champ `certainty` de l'entrée de `mechanics.json`
(`/values/<clé>/…`), sinon `field_certainty` du fichier dans `sources.json` (chemin pointé dont les segments se
suivent dans celui de la feuille). Une certitude déclarée plus haute que la règle est une erreur, sauf abaissement
prévu et daté dans `pending` (révision à venir) ; un abaissement prévu sans objet est une erreur."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forever.manifest import SOURCES_NAME, version_dirs

ORIGINS_NAME = "origins.json"
ORIGINS = ("client", "journal", "addon", "manuel", "copie_figee", "parametre")
CERTAINTY_RANK = {"suppose": 0, "probable": 1, "certain": 2}
CERTAINTY_CAP = {"client": "certain", "journal": "certain", "addon": "probable", "manuel": "probable"}
PATTERN_ORIGINS = frozenset({"client", "journal", "addon", "copie_figee"})
REASON_ORIGINS = frozenset({"manuel", "parametre"})
MECHANICS = "mechanics.json"
RULES_FILE = "decode_rules.json"

Segments = tuple[str, ...]


@dataclass(frozen=True)
class OriginIssue:
    kind: str
    version: str
    file: str
    path: str
    message: str


@dataclass
class OriginsReport:
    versions: list[str] = field(default_factory=list)
    issues: list[OriginIssue] = field(default_factory=list)
    leaves: dict[str, int] = field(default_factory=dict)
    by_origin: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class InventoryRow:
    file: str
    path: str
    certainty: str
    reason: str
    source: str
    registry: str
    leaves: int


@dataclass(frozen=True)
class PendingRow:
    file: str
    path: str
    declared: str
    target: str
    reason: str
    until: str


@dataclass(frozen=True)
class _Rule:
    index: int
    file: str
    origin: str
    pattern: Segments
    raw_path: str
    certainty: str | None
    doc: Mapping[str, Any]

    @property
    def specificity(self) -> tuple[int, int, int]:
        literal = sum(1 for s in self.pattern if s not in ("*", "**"))
        return (literal, -self.pattern.count("**"), -self.pattern.count("*"))


# --- Pointeurs et motifs -------------------------------------------------------------------------------------


def parse_pointer(pointer: str) -> Segments:
    """« /a/b~1c » -> ("a", "b/c") ; « ** » seul (fichier entier) -> ("**",)."""
    if pointer == "**":
        return ("**",)
    if not pointer.startswith("/"):
        raise ValueError(f"pointeur JSON attendu (commence par « / ») : {pointer!r}")
    return tuple(s.replace("~1", "/").replace("~0", "~") for s in pointer[1:].split("/"))


def format_pointer(segments: Segments) -> str:
    return "".join("/" + s.replace("~", "~0").replace("/", "~1") for s in segments)


def _match_prefix(pattern: Segments, path: Segments) -> bool:
    """Le motif couvre un préfixe du chemin (une règle couvre le sous-arbre qu'elle nomme)."""
    if not pattern:
        return True
    head, rest = pattern[0], pattern[1:]
    if head == "**":
        return any(_match_prefix(rest, path[i:]) for i in range(len(path) + 1))
    if not path:
        return False
    return (head == "*" or head == path[0]) and _match_prefix(rest, path[1:])


def _leaves(doc: Any, metadata: frozenset[str], path: Segments = ()) -> Iterator[tuple[Segments, Any]]:
    if isinstance(doc, dict):
        for key, value in doc.items():
            if key not in metadata:
                yield from _leaves(value, metadata, (*path, str(key)))
    elif isinstance(doc, list):
        for i, value in enumerate(doc):
            yield from _leaves(value, metadata, (*path, str(i)))
    elif doc is not None and doc != "":
        yield path, doc


def _contains_run(path: Segments, run: Segments) -> bool:
    n = len(run)
    return any(path[i : i + n] == run for i in range(len(path) - n + 1)) if n else False


# --- Contrôle ------------------------------------------------------------------------------------------------


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _retired(version_dir: Path) -> set[str]:
    rules_path = version_dir / RULES_FILE
    if not rules_path.is_file():
        return set()
    retired = _read(rules_path).get("retired_files", {})
    return set(retired) if isinstance(retired, dict) else set()


class _Checker:
    def __init__(self, data_dir: Path, version: str) -> None:
        self.version = version
        self.dir = data_dir / version
        self.issues: list[OriginIssue] = []
        self.leaf_count = 0
        self.by_origin: dict[str, int] = {}

    def issue(self, kind: str, file: str, path: str, message: str) -> None:
        self.issues.append(OriginIssue(kind, self.version, file, path, message))

    def run(self) -> None:
        path = self.dir / ORIGINS_NAME
        if not path.is_file():
            self.issue("schema", ORIGINS_NAME, "", f"{ORIGINS_NAME} absent de {self.version}")
            return
        doc = _read(path)
        metadata = frozenset(doc.get("metadata_keys", []))
        rules = self._rules(doc)
        not_values = self._not_values(doc)
        pending = self._pending(doc)
        sources = _read(self.dir / SOURCES_NAME) if (self.dir / SOURCES_NAME).is_file() else {}
        present = sorted(p.name for p in self.dir.glob("*.json") if p.name != ORIGINS_NAME)
        retired = _retired(self.dir)
        named = {r.file for r in rules} | {f for f, _ in not_values}
        for name in sorted(named - set(present)):
            if name not in retired:
                self.issue("fichier_absent", name, "", f"règle pour {name}, absent de {self.version}")
        used: set[int] = set()
        used_pending: set[int] = set()
        for name in present:
            file_rules = sorted(
                (r for r in rules if r.file == name), key=lambda r: (r.specificity, -r.index), reverse=True
            )
            skipped = [p for f, p in not_values if f == name]
            self._check_file(name, metadata, file_rules, skipped, pending, sources, used, used_pending)
        for r in rules:
            if r.file in present and r.index not in used:
                self.issue("regle_sans_effet", r.file, r.raw_path, f"aucune valeur sous {r.raw_path}")
        for i, (file, seg, _) in enumerate(pending):
            if i not in used_pending:
                self.issue("attente_sans_objet", file, format_pointer(seg), "abaissement prévu sans écart à couvrir")

    def _rules(self, doc: Mapping[str, Any]) -> list[_Rule]:
        rules: list[_Rule] = []
        for i, raw in enumerate(doc.get("rules", [])):
            file, origin = str(raw.get("file", "")), raw.get("origin")
            certainty = raw.get("certainty")
            paths = raw.get("paths") or []
            where = format_pointer(parse_pointer(paths[0])) if paths and paths[0] != "**" else "**"
            if origin not in ORIGINS:
                self.issue("schema", file, where, f"origine inconnue : {origin!r} ({', '.join(ORIGINS)})")
                continue
            if not raw.get("source"):
                self.issue("schema", file, where, "source absente")
            if origin in REASON_ORIGINS and not raw.get("reason"):
                self.issue("raison_absente", file, where, f"règle {origin} sans raison")
            cap = CERTAINTY_CAP.get(origin)
            if cap is None:
                if certainty is not None:
                    self.issue("schema", file, where, f"{origin} : pas de certitude propre")
            elif certainty not in CERTAINTY_RANK:
                self.issue("schema", file, where, f"certitude inconnue : {certainty!r}")
            elif CERTAINTY_RANK[certainty] > CERTAINTY_RANK[cap]:
                self.issue("certitude_plafond", file, where, f"{origin} : au plus {cap}, {certainty} déclaré")
            if origin == "copie_figee" and paths != ["**"]:
                self.issue("copie_figee_partielle", file, where, "copie figée : règle au niveau du fichier (**)")
            for p in paths:
                try:
                    seg = parse_pointer(p)
                except ValueError as err:
                    self.issue("schema", file, p, str(err))
                    continue
                if origin not in PATTERN_ORIGINS and any(s in ("*", "**") for s in seg):
                    self.issue("motif_interdit", file, p, f"{origin} : chemin exact attendu, motif refusé")
                    continue
                rules.append(_Rule(len(rules), file, origin, seg, p, certainty, raw))
        return rules

    def _not_values(self, doc: Mapping[str, Any]) -> list[tuple[str, Segments]]:
        out = []
        for raw in doc.get("not_game_values", []):
            if not raw.get("reason"):
                self.issue("raison_absente", str(raw.get("file")), "", "not_game_values sans raison")
            out += [(str(raw["file"]), parse_pointer(p)) for p in raw.get("paths", [])]
        return out

    def _pending(self, doc: Mapping[str, Any]) -> list[tuple[str, Segments, Mapping[str, Any]]]:
        out = []
        for raw in doc.get("pending", []):
            if not (raw.get("reason") and raw.get("until")):
                self.issue(
                    "schema", str(raw.get("file")), str(raw.get("path")), "abaissement prévu sans raison ni date"
                )
            out.append((str(raw["file"]), parse_pointer(str(raw["path"])), raw))
        return out

    def _declared(self, name: str, doc: Any, seg: Segments, field_cert: Mapping[str, str]) -> str | None:
        if name == MECHANICS and len(seg) >= 2 and seg[0] == "values":
            entry = doc.get("values", {}).get(seg[1])
            if isinstance(entry, dict) and isinstance(entry.get("certainty"), str):
                return str(entry["certainty"])
        best: tuple[int, str] | None = None
        for key, cert in field_cert.items():
            run = tuple(key.split("."))
            if _contains_run(seg, run) and (best is None or len(run) > best[0]):
                best = (len(run), cert)
        return best[1] if best else None

    def _check_file(
        self,
        name: str,
        metadata: frozenset[str],
        rules: Sequence[_Rule],
        skipped: Sequence[Segments],
        pending: Sequence[tuple[str, Segments, Mapping[str, Any]]],
        sources: Mapping[str, Any],
        used: set[int],
        used_pending: set[int],
    ) -> None:
        if any(s == ("**",) for s in skipped):
            return
        doc = _read(self.dir / name)
        entry = sources.get("files", {}).get(name, {}) if isinstance(sources, dict) else {}
        field_cert = entry.get("field_certainty", {}) if isinstance(entry, dict) else {}
        for seg, _value in _leaves(doc, metadata):
            if any(_match_prefix(s, seg) for s in skipped):
                continue
            self.leaf_count += 1
            rule = next((r for r in rules if _match_prefix(r.pattern, seg)), None)
            pointer = format_pointer(seg)
            if rule is None:
                self.issue("non_couverte", name, pointer, "valeur sans origine déclarée")
                continue
            used.add(rule.index)
            self.by_origin[rule.origin] = self.by_origin.get(rule.origin, 0) + 1
            declared = self._declared(name, doc, seg, field_cert)
            if rule.certainty is None or declared not in CERTAINTY_RANK:
                continue
            if CERTAINTY_RANK[declared] <= CERTAINTY_RANK[rule.certainty]:
                continue
            hit = next(
                (i for i, (f, p, _) in enumerate(pending) if f == name and _match_prefix(p, seg)),
                None,
            )
            if hit is not None:
                used_pending.add(hit)
                continue
            self.issue(
                "certitude_superieure",
                name,
                pointer,
                f"certitude déclarée {declared}, origine {rule.origin} au plus {rule.certainty}",
            )


def check_version(data_dir: Path, version: str) -> OriginsReport:
    checker = _Checker(data_dir, version)
    checker.run()
    return OriginsReport([version], checker.issues, {version: checker.leaf_count}, {version: checker.by_origin})


def check_all(data_dir: Path) -> OriginsReport:
    report = OriginsReport()
    for version in version_dirs(data_dir):
        one = check_version(data_dir, version)
        report.versions.append(version)
        report.issues += one.issues
        report.leaves.update(one.leaves)
        report.by_origin.update(one.by_origin)
    return report


# --- Inventaire des valeurs écrites à la main ----------------------------------------------------------------


def inventory(data_dir: Path, version: str) -> tuple[list[InventoryRow], list[PendingRow]]:
    """Valeurs `manuel` de la version (une ligne par chemin), et abaissements prévus ; triées par fichier et chemin."""
    vdir = data_dir / version
    doc = _read(vdir / ORIGINS_NAME)
    metadata = frozenset(doc.get("metadata_keys", []))
    cache: dict[str, list[Segments]] = {}
    rows: list[InventoryRow] = []
    for raw in doc.get("rules", []):
        if raw.get("origin") != "manuel":
            continue
        file = str(raw["file"])
        if file not in cache:
            cache[file] = [s for s, _ in _leaves(_read(vdir / file), metadata)] if (vdir / file).is_file() else []
        for p in raw.get("paths", []):
            seg = parse_pointer(p)
            n = sum(1 for leaf in cache[file] if _match_prefix(seg, leaf))
            rows.append(
                InventoryRow(
                    file,
                    p,
                    str(raw.get("certainty", "")),
                    str(raw.get("reason", "")),
                    str(raw.get("source", "")),
                    str(raw.get("registry", "")),
                    n,
                )
            )
    pending = [
        PendingRow(
            str(p["file"]),
            str(p["path"]),
            str(p["declared"]),
            str(p.get("target", "")),
            str(p["reason"]),
            str(p["until"]),
        )
        for p in doc.get("pending", [])
    ]
    rows.sort(key=lambda r: (r.file, r.path))
    pending.sort(key=lambda r: (r.file, r.path))
    return rows, pending


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_inventory(version: str, rows: Sequence[InventoryRow], pending: Sequence[PendingRow]) -> str:
    """Rendu Markdown déterministe (`docs/research/valeurs-ecrites-a-la-main.md`) ; aucune valeur de jeu."""
    by_cert: dict[str, int] = {}
    for r in rows:
        by_cert[r.certainty] = by_cert.get(r.certainty, 0) + 1
    lines = [
        "# Valeurs écrites à la main",
        "",
        f"Généré par `uv run forever origins inventory` sur la version {version} (ne pas éditer à la main : le test",
        "`tests/unit/test_origins_inventory.py` compare ce fichier au rendu de la commande). Chaque ligne est un chemin",
        f"de `forever/data/{version}/` dont l'origine déclarée dans `origins.json` est `manuel` : ni décodé du client,",
        "ni mesuré, ni lu dans un addon. Les valeurs elles-mêmes ne sont pas recopiées ici.",
        "",
        f"{len(rows)} chemins, {sum(r.leaves for r in rows)} valeurs ; "
        + ", ".join(f"{n} `{c}`" for c, n in sorted(by_cert.items())),
        "",
        "## Abaissements de certitude prévus",
        "",
    ]
    if pending:
        lines += [
            "| Fichier | Chemin | Déclarée | Visée | Raison | Échéance |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        lines += [
            f"| {p.file} | `{p.path}` | {p.declared} | {p.target} | {_cell(p.reason)} | {_cell(p.until)} |"
            for p in pending
        ]
    else:
        lines.append("Aucun.")
    lines += [
        "",
        "## Inventaire",
        "",
        "| Fichier | Chemin | Valeurs | Certitude | Registre | Raison | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {r.file} | `{r.path}` | {r.leaves} | {r.certainty} | {r.registry or '—'} | {_cell(r.reason)} | "
        f"{_cell(r.source)} |"
        for r in rows
    ]
    return "\n".join(lines) + "\n"


def inventory_payload(version: str, rows: Sequence[InventoryRow], pending: Sequence[PendingRow]) -> dict[str, Any]:
    return {
        "game_version": version,
        "leaves": sum(r.leaves for r in rows),
        "values": [r.__dict__ for r in rows],
        "pending": [p.__dict__ for p in pending],
    }


def render_report(report: OriginsReport) -> list[str]:
    lines = []
    for v in report.versions:
        counts = ", ".join(f"{o} {n}" for o, n in sorted(report.by_origin.get(v, {}).items()))
        lines.append(f"Origines {v} : {report.leaves.get(v, 0)} valeurs ({counts})")
    lines += [f"  ERREUR {i.version} {i.file} {i.path} [{i.kind}] : {i.message}" for i in report.issues]
    return lines


def main(argv: Sequence[str], data_dir: Path | None = None) -> int:
    """Contrôle en ligne de commande (`scripts/check_origins.py`) : 0 si chaque valeur a une origine valide."""
    from forever.config import PACKAGE_DIR

    report = check_all(data_dir or PACKAGE_DIR / "data")
    for line in render_report(report):
        print(line)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
