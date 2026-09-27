"""Interface en ligne de commande : `forever status | lookup | explain-mechanic | manifest | builds | fetch | mcp`.

Sortie texte en français par défaut (dernière ligne : provenance), `--json` pour une sortie structurée.
Codes de sortie : 0 succès, 2 usage, 3 intégrité des données, 4 introuvable, 5 réseau."""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, NoReturn

from forever.config import Deps, default_deps
from forever.errors import (
    EXIT_INTEGRITY,
    EXIT_OK,
    ForeverError,
    InvalidArgumentError,
    UnsupportedKindError,
    UsageError,
)
from forever.explain import MechanicExplanation, explain_mechanic
from forever.lookup import SpellLookup, SpellRank, lookup_spell
from forever.manifest import load_manifest, version_dirs, write_manifest
from forever.pipeline.builds import list_builds
from forever.pipeline.fetch import DEFAULT_LOCALE, TableFetch, fetch_tables
from forever.provenance import Provenance, error_payload, format_provenance_line, local_provenance
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
    }
    try:
        return handlers[args.command](deps, args)
    except ForeverError as err:
        return _emit_error(deps, err, getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
