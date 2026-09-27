"""Interface en ligne de commande : `forever status | lookup | explain-mechanic | manifest | mcp`.

Sortie texte en français par défaut (dernière ligne : provenance), `--json` pour une sortie structurée.
Codes de sortie : 0 succès, 2 usage, 3 intégrité des données, 4 introuvable."""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections.abc import Mapping
from typing import Any, NoReturn

from forever.config import Deps, default_deps
from forever.errors import EXIT_INTEGRITY, EXIT_OK, ForeverError, UnsupportedKindError, UsageError
from forever.explain import MechanicExplanation, explain_mechanic
from forever.lookup import SpellLookup, SpellRank, lookup_spell
from forever.manifest import load_manifest, write_manifest
from forever.provenance import Provenance, error_payload, format_provenance_line, local_provenance
from forever.status import StatusReport, status_report
from forever.store import ensure_integrity

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
    }
    try:
        return handlers[args.command](deps, args)
    except ForeverError as err:
        return _emit_error(deps, err, getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
