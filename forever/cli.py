"""Interface en ligne de commande : `forever status | lookup | explain-mechanic | manifest | builds | fetch | decode | diff | verify
| report | logs | questie | monsters | mcp`.

Sortie texte en français par défaut (dernière ligne : provenance), `--json` pour une sortie structurée.
Codes de sortie : 0 succès, 2 usage, 3 intégrité des données, 4 introuvable, 5 réseau."""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections.abc import Mapping
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, NoReturn

from forever.config import CHAIN_MAX_GAP_S, Deps, default_deps
from forever.errors import (
    EXIT_INTEGRITY,
    EXIT_OK,
    ForeverError,
    InvalidArgumentError,
    PathNotFoundError,
    UnsupportedKindError,
    UsageError,
)
from forever.explain import MechanicExplanation, explain_mechanic
from forever.gamedata import load_game_data
from forever.lookup import SpellLookup, SpellRank, lookup_spell
from forever.manifest import load_manifest, version_dirs, write_manifest
from forever.pipeline.addon_sv import LoggerDB, read_logger_db
from forever.pipeline.builds import list_builds
from forever.pipeline.combatlog import LogHeader, LogSummary, log_files, read_log, scan_logs
from forever.pipeline.decode import Candidate, decode_version
from forever.pipeline.diff import Change, VersionDiff, diff_versions
from forever.pipeline.fetch import DEFAULT_LOCALE, TableFetch, fetch_tables
from forever.pipeline.levels import CasterLevels, from_logger_db, from_questie_journey, logger_utc_offset
from forever.pipeline.measure import (
    Conflict,
    LogMeasures,
    MonsterObservation,
    find_mine,
    log_spell_sets,
    measure_log,
    monster_hp,
)
from forever.pipeline.monsters import build_monsters, write_monsters
from forever.pipeline.questie import read_questie
from forever.pipeline.report import render_report
from forever.pipeline.sources import load_source, source_provenance
from forever.pipeline.verify import VerifyReport, verify_version
from forever.provenance import (
    Certainty,
    Provenance,
    error_payload,
    format_provenance_line,
    local_provenance,
    min_certainty,
)
from forever.status import StatusReport, status_report
from forever.store import current_identity, ensure_integrity, read_sources
from forever.timefmt import format_utc

SCHOOLS_FR = {"frost": "givre", "fire": "feu", "arcane": "arcane", "frostfire": "givrefeu"}
FOREVER_FR = {"oui": "identique", "modifie": "modifié", "inconnu": "inconnu"}


class _Parser(argparse.ArgumentParser):
    """Une erreur d'usage devient une UsageError : `main` l'affiche avec la provenance, en texte ou en JSON."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(self.prog, message, self.format_usage())


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="forever", description="Système expert World of Warcraft: Forever.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    status = sub.add_parser("status", help="fraîcheur des données, intégrité, couverture du registre")
    status.add_argument("--offline", action="store_true", help="aucun appel réseau (cache seulement)")
    status.add_argument("--json", action="store_true", help="sortie JSON")

    lookup = sub.add_parser("lookup", help="consulter une entité du jeu")
    lookup.add_argument("kind", help="type d'entité (T01 : spell)")
    lookup.add_argument("name", help="nom anglais (casse, espaces et tirets ignorés)")
    lookup.add_argument("--rank", type=int, help="position du rang, à partir de 1")
    lookup.add_argument("--detail", action="store_true", help="champs complémentaires")
    lookup.add_argument("--limit", type=int, default=20, help="rangs par page")
    lookup.add_argument("--offset", type=int, default=0, help="premier rang de la page (à partir de 0)")
    lookup.add_argument("--json", action="store_true", help="sortie JSON")

    manifest = sub.add_parser("manifest", help="empreintes des données versionnées")
    mode = manifest.add_mutually_exclusive_group(required=True)
    mode.add_argument("--update", action="store_true", help="recalculer et écrire forever/data/manifest.json")
    mode.add_argument("--check", action="store_true", help="vérifier les empreintes")
    manifest.add_argument("--json", action="store_true", help="sortie JSON")

    explain = sub.add_parser("explain-mechanic", help="expliquer une mécanique du registre")
    explain.add_argument("mechanic_id", help="identifiant du registre (ex. A5, casse ignorée)")
    explain.add_argument("--json", action="store_true", help="sortie JSON")

    builds = sub.add_parser("builds", help="versions publiées du client (réseau)")
    builds.add_argument("--limit", type=int, default=10, help="nombre de versions affichées")
    builds.add_argument("--offline", action="store_true", help="refuser tout appel réseau")
    builds.add_argument("--json", action="store_true", help="sortie JSON")

    fetch = sub.add_parser("fetch", help="télécharger les tables du client d'une version (réseau)")
    fetch.add_argument("--version", required=True, help="version complète, ex. 1.60.1.70009")
    fetch.add_argument("--tables", help="tables séparées par des virgules (défaut : decode_rules.json)")
    fetch.add_argument("--locale", help="locales séparées par des virgules (défaut : enUS)")
    fetch.add_argument("--refresh", action="store_true", help="retélécharger même si le cache est conforme")
    fetch.add_argument("--offline", action="store_true", help="refuser tout appel réseau")
    fetch.add_argument("--json", action="store_true", help="sortie JSON")

    decode = sub.add_parser("decode", help="décoder les tables du client en version candidate (hors ligne)")
    decode.add_argument("--version", required=True, help="version complète, ex. 1.60.1.70009")
    decode.add_argument("--csv-dir", help="dossier des CSV (défaut : cache de forever fetch)")
    decode.add_argument("--out", help="dossier de la candidate (défaut : <cache>/candidates/<version>)")
    decode.add_argument("--force", action="store_true", help="remplacer une candidate existante")
    decode.add_argument("--json", action="store_true", help="sortie JSON")

    diff = sub.add_parser("diff", help="comparer deux versions de données (dépôt ou candidate)")
    diff.add_argument("a", help="version du dépôt ou chemin d'une candidate")
    diff.add_argument("b", help="version du dépôt ou chemin d'une candidate")
    diff.add_argument("--json", action="store_true", help="sortie JSON")

    verify = sub.add_parser("verify", help="vérifier une version de données (dépôt ou candidate)")
    verify.add_argument("source", nargs="?", help="version du dépôt ou chemin d'une candidate (défaut : locale)")
    verify.add_argument("--json", action="store_true", help="sortie JSON")

    report = sub.add_parser("report", help="rapport Markdown d'un changement de données")
    report.add_argument("a", help="version du dépôt ou chemin d'une candidate")
    report.add_argument("b", help="version du dépôt ou chemin d'une candidate")
    report.add_argument("--out", help="écrire le rapport dans ce fichier")
    report.add_argument("--json", action="store_true", help="sortie JSON")

    logs = sub.add_parser("logs", help="journaux de combat du client (lecture locale, sans réseau)")
    logs_sub = logs.add_subparsers(dest="logs_command", required=True, parser_class=_Parser)
    scan = logs_sub.add_parser("scan", help="lister les journaux WoWCombatLog-*.txt d'un dossier")
    scan.add_argument("--dir", help="dossier des journaux (défaut : <FOREVER_WOW_DIR>/Logs)")
    scan.add_argument("--json", action="store_true", help="sortie JSON")
    measure = logs_sub.add_parser("measure", help="mesurer un journal ou tous ceux d'un dossier")
    measure.add_argument("path", help="journal WoWCombatLog-*.txt ou dossier")
    measure.add_argument(
        "--max-gap", type=float, default=CHAIN_MAX_GAP_S, help="écart maximal (s) entre deux instantanés enchaînés"
    )
    measure.add_argument(
        "--addon-sv", help="SavedVariables de ForeverLogger (niveau du lanceur pour les touchés et ratés, priorité 1)"
    )
    measure.add_argument(
        "--questie-sv", help="SavedVariables de Questie : carnet des gains de niveau (repli, lecture locale seulement)"
    )
    measure.add_argument(
        "--utc-offset",
        type=float,
        help="décalage heure locale - UTC (h) pour le carnet de Questie (défaut : instantané ForeverLogger, sinon système)",
    )
    measure.add_argument("--caster-level", type=int, help="niveau du lanceur en dernier recours")
    measure.add_argument("--json", action="store_true", help="sortie JSON")

    questie = sub.add_parser("questie", help="base locale de l'addon Questie (communautaire, sans réseau)")
    questie_sub = questie.add_subparsers(dest="questie_command", required=True, parser_class=_Parser)
    info = questie_sub.add_parser("info", help="version et contenu de l'addon Questie installé")
    info.add_argument("--dir", help="dossier de l'addon (défaut : <FOREVER_WOW_DIR>/Interface/AddOns/Questie)")
    info.add_argument("--json", action="store_true", help="sortie JSON")

    monsters = sub.add_parser("monsters", help="table des monstres (PV mesurés, Questie en regard)")
    monsters_sub = monsters.add_subparsers(dest="monsters_command", required=True, parser_class=_Parser)
    build = monsters_sub.add_parser("build", help="construire monsters.json hors des données")
    build.add_argument("--logs", required=True, help="journal WoWCombatLog-*.txt ou dossier de journaux")
    build.add_argument("--questie", help="dossier de l'addon Questie (valeurs en regard, agrégat communautaire)")
    build.add_argument("--out", help="dossier de sortie (défaut : <cache>/monsters)")
    build.add_argument("--force", action="store_true", help="remplacer un monsters.json existant")
    build.add_argument(
        "--fit-exclude",
        type=int,
        action="append",
        default=[],
        metavar="NPC",
        help="PNJ écarté de l'ajustement de la correction Questie (répétable ; listé dans la table)",
    )
    build.add_argument("--json", action="store_true", help="sortie JSON")

    sub.add_parser("mcp", help="serveur MCP sur stdio")
    return parser


# --- Rendu texte ---------------------------------------------------------------------------------


def _num(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def _rank_parts(r: SpellRank) -> list[str]:
    parts = []
    if r["damage_max"]:
        dmg = r["damage_min"] if r["damage_min"] == r["damage_max"] else f"{r['damage_min']}-{r['damage_max']}"
        parts.append(f"{dmg} dégâts")
    if r["dot_total"]:
        parts.append(f"+{r['dot_total']} sur {_num(r['dot_duration_s'])} s")
    parts.append(f"incantation {_num(r['cast_time_s'])} s" if r["cast_time_s"] else "instantané")
    if r["mana"] is not None:
        parts.append(f"{r['mana']} mana")
    elif r["mana_pct_base"] is not None:
        parts.append(f"{_num(r['mana_pct_base'] * 100)} % de la mana de base")
    else:
        parts.append("mana inconnu")
    if r["cooldown_s"]:
        parts.append(f"recharge {_num(r['cooldown_s'])} s")
    return parts


def render_lookup(res: SpellLookup) -> list[str]:
    title = f"{res['id'].replace('_', ' ').title()} ({SCHOOLS_FR.get(res['school'], res['school'])})"
    reach = [f"portée {_num(res['range_yd'])} m"] if res["range_yd"] is not None else []
    if res["total"] == 1 and len(res["ranks"]) == 1:
        r = res["ranks"][0]
        lines = [f"{title} — rang {r['rank']}/{res['ranks_total']}, appris au niveau {r['level']}"]
        lines.append(" · ".join(_rank_parts(r) + reach))
    else:
        lines = [" — ".join([title, f"{res['ranks_total']} rangs", *reach])]
        lines += [f"rang {r['rank']} · niveau {r['level']} · " + " · ".join(_rank_parts(r)) for r in res["ranks"]]
        if res["next_offset"] is not None:
            lines.append(f"suite : --offset {res['next_offset']}")
    if res["details"]:
        lines.append("Détails : " + " · ".join(f"{k} {json.dumps(v)}" for k, v in res["details"].items()))
    return lines


def render_status(rep: StatusReport) -> list[str]:
    f, integ = rep["freshness"], rep["integrity"]
    if integ["ok"]:
        integrity = "intégrité ok"
    elif not integ["manifest_found"]:
        integrity = "intégrité ÉCHEC (manifeste absent)"
    elif integ["manifest_error"]:
        integrity = f"intégrité ÉCHEC (manifeste illisible : {integ['manifest_error']})"
    else:
        integrity = f"intégrité ÉCHEC ({len(integ['mismatched'] + integ['missing'] + integ['unexpected'])} écart(s))"
    lines = [f"Données locales {rep['local_version']} · {integrity}"]
    freshness = f"Fraîcheur {f['freshness']}"
    if f["latest_version"]:
        freshness += f" · dernière version publiée {f['latest_version']} ({f['latest_created_at']})"
    if f["checked_at"]:
        freshness += f" · vérifiée le {f['checked_at']} ({f['source']})"
    lines.append(freshness)
    for label, paths in (
        ("modifié", integ["mismatched"]),
        ("manquant", integ["missing"]),
        ("inattendu", integ["unexpected"]),
    ):
        lines += [f"  {label} : {p}" for p in paths]
    lines.append(f"Registre des mécaniques : {rep['registry_coverage']} couvertes")
    return lines


def render_explanation(res: MechanicExplanation) -> list[str]:
    lines = [
        f"{res['id']} — {res['description']}",
        f"Statut {res['status']} · certitude {res['certainty']} · Forever : {FOREVER_FR.get(res['forever'], res['forever'])}",
        f"Formule : {res['formula']}" if res["formula"] else "Formule : aucune (mécanique non modélisée)",
    ]
    if res["note"]:
        lines.append(f"Note : {res['note']}")
    if res["parameters"]:
        lines.append(f"Paramètres (version {res['provenance']['game_version']}) :")
        lines += [
            f"  {p['key']} = {json.dumps(p['value'], ensure_ascii=False)} ({p['certainty']}) — {p['source']}"
            for p in res["parameters"]
        ]
    else:
        lines.append("Paramètres : aucun")
    for label, values in (
        ("Implémentation", res["implementations"]),
        ("Sources", res["sources"]),
        ("Tests", res["tests"]),
    ):
        lines.append(f"{label} : {', '.join(values) if values else 'aucun'}")
    for proof in res["proofs"]:
        journals = proof["journal"] if isinstance(proof["journal"], list) else [proof["journal"]]
        gaps = [
            f"{label} {_num(proof[key])} s"
            for key, label in (("ecart_median_s", "écart médian"), ("ecart_min_s", "écart minimal"))
            if key in proof
        ]
        lines.append(
            f"Preuve de journal : {', '.join(journals)} ({proof['date']}, n = {proof['n']}"
            + "".join(f", {g}" for g in gaps)
            + f") : {proof['mesure']}"
        )
    return lines


def _emit(payload: Mapping[str, Any], lines: list[str], provenance: Provenance, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("\n".join([*lines, format_provenance_line(provenance)]))


def _emit_error(deps: Deps, err: ForeverError, as_json: bool) -> int:
    payload = error_payload(deps, err)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        lines = [f"Erreur ({err.code}) : {err.message}"]
        if err.suggestions:
            lines.append(f"Suggestions : {', '.join(err.suggestions)}")
        lines += [f"À faire : {err.action}", format_provenance_line(payload["provenance"])]
        print("\n".join(lines), file=sys.stderr)
    return err.exit_code


# --- Commandes -----------------------------------------------------------------------------------


def _cmd_status(deps: Deps, args: argparse.Namespace) -> int:
    rep = status_report(deps, allow_network=not args.offline)
    _emit(rep, render_status(rep), rep["provenance"], args.json)
    return EXIT_OK if rep["integrity"]["ok"] else EXIT_INTEGRITY


def _cmd_lookup(deps: Deps, args: argparse.Namespace) -> int:
    if args.kind != "spell":
        raise UnsupportedKindError(f"type « {args.kind} »", ["spell"])
    res = lookup_spell(deps, args.name, args.rank, detail=args.detail, limit=args.limit, offset=args.offset)
    _emit(res, render_lookup(res), res["provenance"], args.json)
    return EXIT_OK


def _cmd_explain(deps: Deps, args: argparse.Namespace) -> int:
    res = explain_mechanic(deps, args.mechanic_id)
    _emit(res, render_explanation(res), res["provenance"], args.json)
    return EXIT_OK


def _cmd_manifest(deps: Deps, args: argparse.Namespace) -> int:
    if args.update:
        path = write_manifest(deps.data_dir)
        action = "Manifeste écrit"
    else:
        path = deps.data_dir / "manifest.json"
        ensure_integrity(deps.data_dir)
        action = "Empreintes conformes"
    manifest = load_manifest(deps.data_dir) or {"versions": {}}
    versions = manifest["versions"]
    n_files = sum(len(v.get("files", {})) for v in versions.values())
    provenance = local_provenance(deps)
    summary = f"{action} : {path} ({len(versions)} version(s), {n_files} fichiers, données {provenance['data_sha']})"
    payload = {"manifest": str(path), "versions": sorted(versions), "files": n_files, "provenance": provenance}
    _emit(payload, [summary], provenance, args.json)
    return EXIT_OK


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _local_product(deps: Deps) -> tuple[str, str, str]:
    """(version locale, produit, préfixe) lus dans sources.json de la version la plus récente."""
    version = current_identity(deps.data_dir).game_version
    sources = read_sources(deps.data_dir, version) or {}
    product, prefix = sources.get("product"), sources.get("version_prefix")
    if not (isinstance(product, str) and isinstance(prefix, str)):
        raise InvalidArgumentError(
            f"Produit inconnu : sources.json absent ou incomplet pour {version}.",
            "vérifier forever/data/<version>/sources.json (champs product et version_prefix)",
        )
    return version, product, prefix


def _cmd_builds(deps: Deps, args: argparse.Namespace) -> int:
    if args.limit < 1:
        raise InvalidArgumentError(f"--limit doit être positif (reçu {args.limit}).", "donner --limit 1 ou plus")
    local, product, prefix = _local_product(deps)
    deps = replace(deps, offline=deps.offline or args.offline)
    builds = list_builds(deps, product, prefix)
    shown = builds[: args.limit]
    provenance = local_provenance(deps)
    payload = {
        "product": product,
        "prefix": prefix,
        "local_version": local,
        "latest": builds[0].version if builds else None,
        "total": len(builds),
        "builds": [
            {"version": b.version, "created_at": format_utc(b.created_at), "local": b.version == local} for b in shown
        ],
        "provenance": provenance,
    }
    lines = [f"Versions publiées ({product}, {prefix}x) : {len(builds)}, de la plus récente à la plus ancienne"]
    for i, b in enumerate(shown):
        marks = [m for m, on in (("dernière", i == 0), ("locale", b.version == local)) if on]
        lines.append(f"  {b.version} · {format_utc(b.created_at)}" + (f" · {', '.join(marks)}" if marks else ""))
    if not any(b.version == local for b in builds):
        lines.append(f"Version locale {local} absente de la liste publiée")
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def _fetch_defaults(deps: Deps) -> tuple[list[str], dict[str, list[str]]]:
    """Tables et tables localisées de decode_rules.json (version locale la plus récente qui en a un)."""
    for version in reversed(version_dirs(deps.data_dir)):
        path = deps.data_dir / version / "decode_rules.json"
        if path.is_file():
            rules = json.loads(path.read_text(encoding="utf-8"))
            localized = rules.get("localized_tables", {})
            return list(rules["tables"]), {k: list(v) for k, v in localized.items()}
    raise InvalidArgumentError(
        "Aucune liste de tables : --tables est obligatoire tant qu'aucune version locale n'a de decode_rules.json.",
        "donner --tables T1,T2,…",
    )


def _cmd_fetch(deps: Deps, args: argparse.Namespace) -> int:
    deps = replace(deps, offline=deps.offline or args.offline)
    results: list[TableFetch] = []
    if args.tables:
        locales = _split(args.locale) if args.locale else [DEFAULT_LOCALE]
        results = fetch_tables(deps, args.version, _split(args.tables), locales=locales, refresh=args.refresh)
    else:
        tables, localized = _fetch_defaults(deps)
        results = fetch_tables(deps, args.version, tables, refresh=args.refresh)
        for locale, names in localized.items():
            results += fetch_tables(deps, args.version, names, locales=[locale], refresh=args.refresh)
    provenance = local_provenance(deps)
    downloaded = sum(1 for r in results if not r["from_cache"])
    lines = [
        f"Tables de {args.version} : {len(results)} ({downloaded} téléchargée(s), {len(results) - downloaded} en cache)"
    ]
    lines += [
        f"  {r['locale']}/{r['table']} · {r['bytes']} octets · {'cache' if r['from_cache'] else 'téléchargée'}"
        for r in results
    ]
    payload = {"version": args.version, "tables": results, "provenance": provenance}
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def render_decode(c: Candidate) -> list[str]:
    lines = [
        f"Version candidate {c.version} : {c.root}",
        f"{c.talents} talents · {c.spells} sorts · {c.spell_ranks} rangs de sort",
    ]
    lines += [f"  observation : {o}" for o in c.observations]
    return lines


def _change_line(c: Change) -> str:
    what = {"talent": "talent", "spell": "sort", "file": "fichier"}[c["kind"]]
    if c["change"] == "added":
        return f"+ {what} ajouté : {c['key']}" + (f" ({c['field']})" if c["field"] else "")
    if c["change"] == "removed":
        return f"- {what} retiré : {c['key']}" + (f" ({c['field']})" if c["field"] else "")
    old, new = json.dumps(c["old"], ensure_ascii=False), json.dumps(c["new"], ensure_ascii=False)
    return f"~ {c['key']} : {c['field']} {old} -> {new}"


def render_diff(d: VersionDiff) -> list[str]:
    lines = [f"Comparaison {d['a']} -> {d['b']}"]
    lines += [_change_line(c) for c in d["changes"]]
    counts = ", ".join(f"{n} {k}" for k, n in d["counts"].items())
    lines.append(f"{len(d['changes'])} changement(s) ({counts})" if d["changes"] else "Aucun changement")
    return lines


def render_verify(r: VerifyReport) -> list[str]:
    lines = [f"Vérification de {r['source']} ({r['version']}) : {'ok' if r['ok'] else 'ÉCHEC'}"]
    lines += [f"  erreur : {e}" for e in r["errors"]]
    lines += [f"  avertissement : {w}" for w in r["warnings"]]
    if r["inherited"]:
        lines.append(f"Fichiers hérités : {', '.join(r['inherited'])}")
    return lines


def _cmd_decode(deps: Deps, args: argparse.Namespace) -> int:
    c = decode_version(
        deps,
        args.version,
        csv_dir=Path(args.csv_dir) if args.csv_dir else None,
        out=Path(args.out) if args.out else None,
        force=args.force,
    )
    src, v = load_source(deps, str(c.root))
    provenance = source_provenance(deps, src, v)
    payload = {
        "version": c.version,
        "root": str(c.root),
        "talents": c.talents,
        "spells": c.spells,
        "spell_ranks": c.spell_ranks,
        "observations": c.observations,
        "provenance": provenance,
    }
    _emit(payload, render_decode(c), provenance, args.json)
    return EXIT_OK


def _cmd_diff(deps: Deps, args: argparse.Namespace) -> int:
    d = diff_versions(deps, args.a, args.b)
    _emit(d, render_diff(d), d["provenance"], args.json)
    return EXIT_OK


def _cmd_verify(deps: Deps, args: argparse.Namespace) -> int:
    r = verify_version(deps, args.source)
    _emit(r, render_verify(r), r["provenance"], args.json)
    return EXIT_OK if r["ok"] else EXIT_INTEGRITY


def _cmd_report(deps: Deps, args: argparse.Namespace) -> int:
    d = diff_versions(deps, args.a, args.b)
    r = verify_version(deps, args.b)
    text = render_report(d, r)
    if args.out:
        Path(args.out).write_bytes(text.encode("utf-8"))
    lines = [f"Rapport écrit : {args.out}"] if args.out else [text.rstrip("\n")]
    payload = {"a": d["a"], "b": d["b"], "report": text, "out": args.out, "verify": r, "provenance": d["provenance"]}
    if args.json or args.out:
        _emit(payload, lines, d["provenance"], args.json)
    else:
        print(text.rstrip("\n"))  # la dernière ligne du rapport est déjà la provenance
    return EXIT_OK if r["ok"] else EXIT_INTEGRITY


def _wow_path(deps: Deps, given: str | None, *parts: str) -> Path:
    """Chemin donné, sinon `<wow_dir>/<parts>` (FOREVER_WOW_DIR)."""
    if given:
        return Path(given)
    if deps.wow_dir is None:
        raise InvalidArgumentError(
            "Dossier du client inconnu.", "donner le chemin explicitement ou définir FOREVER_WOW_DIR"
        )
    return deps.wow_dir.joinpath(*parts)


def _log_provenance(deps: Deps, headers: list[LogHeader], certainty: Certainty, notes: list[str]) -> Provenance:
    """Provenance des mesures : version locale dont le préfixe correspond au build du journal (le journal ne donne
    que `1.60.1`, sans numéro de build : hypothèse affichée)."""
    version = current_identity(deps.data_dir).game_version
    assumptions = list(notes)
    for build in sorted({h.build for h in headers}):
        if version.startswith(build + "."):
            assumptions.append(f"build du journal non précisé ({build}) : version locale {version} retenue")
        else:
            assumptions.append(f"build du journal {build} sans version locale correspondante (locale : {version})")
    return local_provenance(deps, certainty=certainty, assumptions=assumptions)


def _summary_json(s: LogSummary) -> dict[str, Any]:
    return {
        "name": s.name,
        "lines": s.lines,
        "events": s.events,
        "build": s.header.build if s.header else None,
        "start": s.start.isoformat() if s.start else None,
        "end": s.end.isoformat() if s.end else None,
        "mine": s.mine,
        "error": s.error,
    }


def _cmd_logs_scan(deps: Deps, args: argparse.Namespace) -> int:
    directory = _wow_path(deps, args.dir, "Logs")
    if not directory.is_dir():
        raise PathNotFoundError("Dossier des journaux", str(directory), "donner --dir ou définir FOREVER_WOW_DIR")
    summaries = scan_logs(directory)
    provenance = _log_provenance(deps, [s.header for s in summaries if s.header], "certain", [])
    lines = [f"Journaux de combat dans {directory} : {len(summaries)}"]
    for s in summaries:
        if s.error:
            lines.append(f"  {s.name} · {s.lines} ligne(s) · illisible : {s.error}")
        else:
            span = f"{s.start:%Y-%m-%d %H:%M:%S} → {s.end:%H:%M:%S}" if s.start and s.end else "aucun événement"
            who = ", ".join(s.mine) or "aucun joueur « à moi »"
            lines.append(f"  {s.name} · {s.lines} lignes · {span} · {who}")
    payload = {"dir": str(directory), "logs": [_summary_json(s) for s in summaries], "provenance": provenance}
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def render_measures(m: LogMeasures) -> list[str]:
    caster = m["caster"]["name"] if m["caster"] else "aucun joueur « à moi »"
    lines = [f"Journal {m['name']} · build {m['header']['build']} · {m['events']} événements · lanceur {caster}"]
    lines += [
        f"  PV : {o['name']} ({o['npc_id']}) niveau {o['level']} = {o['max_hp']} ({o['guids']} individu(s))"
        for o in m["monsters"]
    ]
    lines += [f"  CONFLIT de PV : PNJ {c['npc_id']} niveau {c['level']} : {c['values']}" for c in m["conflicts"]]
    if m["costs"]:
        lines.append("  Coûts relevés : " + " · ".join(f"sort {k} = {v}" for k, v in m["costs"].items()))
    gcd = m["gcd_intervals"]
    if gcd["values"]:
        values = ", ".join(_num(round(v, 3)) for v in gcd["values"])
        lines.append(f"  Intervalles entre instantanés enchaînés : {values} s (n = {gcd['n']})")
    for spell, times in m["cast_times"].items():
        lines.append(f"  Incantations du sort {spell} : " + ", ".join(_num(round(x, 3)) for x in times) + " s")
    lines += [f"  Critique du sort {c['spell_id']} : × {_num(round(c['ratio'], 4))}" for c in m["crits"]]
    lines += [
        f"  Touchés/ratés {h['school']} écart {h['level_diff']:+d} : {h['hits']} / {h['misses']}"
        for h in m["hit_tally"]
    ]
    if m["caster_level"] is not None:
        field = ", ".join(str(v) for v in m["player_level_field"]) or "absent"
        lines.append(f"  Niveau du lanceur au début : {m['caster_level']} ; dernier champ du bloc avancé : {field}")
    lines += [
        f"  Niveau du lanceur {c['level']} à {str(c['time']).replace('T', ' ')} ({c['source']})"
        for c in m["caster_level_changes"]
    ]
    if m["unknown_events"]:
        lines.append(f"  Événements inconnus gardés bruts : {', '.join(m['unknown_events'])}")
    return lines


def _caster_levels(
    args: argparse.Namespace, db: LoggerDB | None, caster: str, notes: list[str], name: str
) -> CasterLevels | None:
    """Niveau du lanceur par priorité (décision 3 du plan T04b) : ForeverLoggerDB, carnet de Questie, --caster-level."""
    timelines = []
    if db is not None:
        timelines.append(from_logger_db(db, caster))
    if args.questie_sv:
        offset = logger_utc_offset(db, caster) if db is not None else None
        if args.utc_offset is not None:
            offset = timedelta(hours=args.utc_offset)
        if offset is None:
            notes.append(f"{name} : carnet de Questie ramené à l'heure locale par le fuseau du système")
        timelines.append(from_questie_journey(Path(args.questie_sv), caster, utc_offset=offset))
    if not timelines and args.caster_level is None:
        return None
    sources = [t.source for t in timelines] + (["--caster-level"] if args.caster_level is not None else [])
    notes.append(f"{name} : niveau du lanceur par priorité {' > '.join(sources)}")
    return CasterLevels(tuple(timelines), args.caster_level)


def _cmd_logs_measure(deps: Deps, args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        raise PathNotFoundError("Journal", str(path), "donner un fichier WoWCombatLog-*.txt ou son dossier")
    files = log_files(path) if path.is_dir() else [path]
    notes: list[str] = [f"fenêtre d'enchaînement des instantanés : {_num(args.max_gap)} s (paramètre de mesure)"]
    results: list[LogMeasures] = []
    headers: list[LogHeader] = []
    db = read_logger_db(Path(args.addon_sv)) if args.addon_sv else None
    spells = log_spell_sets(load_game_data(deps))
    notes.append(
        "intervalles : sorts qui déclenchent la recharge globale (start_recovery_ms > 0) ; touchés et ratés : sorts "
        "de spell_scaling.json seulement (ni baguette, ni effets déclenchés)"
    )
    for file in files:
        try:
            header, events = read_log(file)
            evs = list(events)
        except ForeverError as err:
            if not path.is_dir():
                raise
            notes.append(f"{file.name} ignoré : {err.message}")
            continue
        headers.append(header)
        levels = _caster_levels(args, db, find_mine(evs) or "", notes, file.name)
        results.append(
            measure_log(header, evs, name=file.name, max_gap_s=args.max_gap, caster_level=levels, spells=spells)
        )
    for m in results:
        notes += [f"{m['name']} : {a}" for a in m["assumptions"]]
    stats = any(m["gcd_intervals"]["values"] or m["cast_times"] or m["crits"] for m in results)
    certainty: Certainty = "probable" if stats else "certain"
    if stats:
        notes.append("intervalles, incantations et critiques : statistiques sur un petit échantillon (probable)")
    provenance = _log_provenance(deps, headers, certainty, notes)
    lines = [line for m in results for line in render_measures(m)] or ["Aucun journal mesurable"]
    _emit({"logs": results, "provenance": provenance}, lines, provenance, args.json)
    return EXIT_OK


QUESTIE_NOTE = "licence amont de Questie à vérifier (docs/OPEN_QUESTIONS.md) : base lue localement, jamais copiée"


def _cmd_questie_info(deps: Deps, args: argparse.Namespace) -> int:
    db = read_questie(_wow_path(deps, args.dir, "Interface", "AddOns", "Questie"))
    info = db.info
    provenance = local_provenance(deps, certainty=db.certainty, assumptions=[f"données {db.source}", QUESTIE_NOTE])
    lines = [
        f"Questie {info.version} {info.title} · interface {info.interface} · {info.npc_count} PNJ · "
        + (f"{info.quest_count} quêtes" if info.quest_count is not None else "quêtes non comptées"),
        f"Source : {db.source} ; certitude {db.certainty}",
    ]
    payload = {**info._asdict(), "source": db.source, "certainty": db.certainty, "provenance": provenance}
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def _cmd_monsters_build(deps: Deps, args: argparse.Namespace) -> int:
    path = Path(args.logs)
    if not path.exists():
        raise PathNotFoundError("Journaux", str(path), "donner --logs : un fichier WoWCombatLog-*.txt ou son dossier")
    out = Path(args.out) if args.out else deps.cache_dir / "monsters"
    questie = read_questie(Path(args.questie)) if args.questie else None
    observations: list[MonsterObservation] = []
    conflicts: list[Conflict] = []
    headers: list[LogHeader] = []
    notes: list[str] = []
    names: list[str] = []
    for file in log_files(path) if path.is_dir() else [path]:
        try:
            header, events = read_log(file)
            found, clash = monster_hp(list(events), log=file.name)
        except ForeverError as err:
            if not path.is_dir():
                raise
            notes.append(f"{file.name} ignoré : {err.message}")
            continue
        headers.append(header)
        names.append(file.name)
        observations += found
        conflicts += clash
    version = current_identity(deps.data_dir).game_version
    table = build_monsters(
        observations, questie, version, conflicts=conflicts, logs=names, fit_exclude=args.fit_exclude
    )
    written = write_monsters(table, out, deps.data_dir, force=args.force)
    levels = table["hp_by_level"].values()
    certainty = min_certainty(v["certainty"] for v in levels)
    if questie is not None:
        notes += [f"valeurs en regard et agrégat : {questie.source}", QUESTIE_NOTE]
    provenance = _log_provenance(deps, headers, certainty, notes)
    payload = {
        "path": str(written),
        "logs": names,
        "npcs": len(table["npcs"]),
        "levels": len(table["hp_by_level"]),
        "conflicts": table["conflicts"],
        "questie_gaps": table["questie_gaps"],
        "provenance": provenance,
    }
    lines = [
        f"Table des monstres écrite : {written}",
        (
            f"{len(table['npcs'])} PNJ mesurés · {len(table['hp_by_level'])} niveaux dans l'agrégat · "
            f"{len(table['conflicts'])} conflit(s) · {len(table['questie_gaps'])} écart(s) avec Questie"
        ),
    ]
    lines += [
        f"  écart : PNJ {g['npc_id']} niveau {g['level']} mesuré {g['measured']}, Questie {g['questie']}"
        for g in table["questie_gaps"]
    ]
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def _cmd_logs(deps: Deps, args: argparse.Namespace) -> int:
    handlers = {"scan": _cmd_logs_scan, "measure": _cmd_logs_measure}
    return handlers[args.logs_command](deps, args)


def _use_utf8_output() -> None:
    """Sortie redirigée (tube, fichier) : UTF-8 quel que soit l'encodage local, pour les accents et le JSON."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper) and stream in (sys.__stdout__, sys.__stderr__) and not stream.isatty():
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None, deps: Deps | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        args = build_parser().parse_args(argv)
    except UsageError as err:
        # la ligne n'a pas été analysée : --json est cherché tel quel ; en texte, la ligne d'usage précède l'erreur
        as_json = "--json" in argv
        _use_utf8_output()
        if not as_json:
            sys.stderr.write(err.usage)
        return _emit_error(deps or default_deps(), err, as_json)
    except SystemExit as exc:  # --help : aide d'argparse, sans provenance
        return exc.code if isinstance(exc.code, int) else 2
    deps = deps or default_deps()
    if args.command == "mcp":
        from forever.mcp_server import build_server  # import tardif : le SDK MCP est lourd à charger

        build_server(deps).run()
        return EXIT_OK
    _use_utf8_output()
    handlers = {
        "status": _cmd_status,
        "lookup": _cmd_lookup,
        "explain-mechanic": _cmd_explain,
        "manifest": _cmd_manifest,
        "builds": _cmd_builds,
        "fetch": _cmd_fetch,
        "decode": _cmd_decode,
        "diff": _cmd_diff,
        "verify": _cmd_verify,
        "report": _cmd_report,
        "logs": _cmd_logs,
        "questie": _cmd_questie_info,
        "monsters": _cmd_monsters_build,
    }
    try:
        return handlers[args.command](deps, args)
    except ForeverError as err:
        return _emit_error(deps, err, getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
