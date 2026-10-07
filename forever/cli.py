"""Interface en ligne de commande : `forever status | lookup | explain-mechanic | manifest | builds | fetch | decode | diff | verify
| report | logs | questie | monsters | mcp`.

Sortie texte en français par défaut (dernière ligne : provenance), `--json` pour une sortie structurée.
Codes de sortie : 0 succès, 2 usage, 3 intégrité des données, 4 introuvable, 5 réseau."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, NoReturn, cast

from forever import registry
from forever.addons import addons_status
from forever.addons import inventory as addons_inventory
from forever.build import CONTEXTS, build_report
from forever.chart import leveling_chart
from forever.config import CHAIN_MAX_GAP_S, FETCH_TIMEOUT, Deps, default_deps
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
from forever.gamedata import build_game_data, load_game_data
from forever.leveling import (
    DEFAULT_RACE,
    MAX_N,
    check_level,
    check_race,
    check_talents,
    damage_assumptions,
    level_cap,
    parse_talents,
    simulate_leveling,
)
from forever.lookup import (
    SpellLookup,
    SpellRank,
    TalentLookup,
    lookup_class_talent,
    lookup_spell,
    lookup_talent,
    lookup_zones,
)
from forever.lookup import check_talents as check_class_talents
from forever.manifest import load_manifest, version_dirs, write_manifest
from forever.origins import check_all as check_origins
from forever.origins import inventory as origins_inventory
from forever.origins import inventory_payload, render_inventory
from forever.origins import render_report as render_origins_report
from forever.pipeline import blizzard_api, dbcache, hotfixes
from forever.pipeline import notes as notes_mod
from forever.pipeline.addon_sv import LoggerDB, read_logger_db
from forever.pipeline.builds import list_builds
from forever.pipeline.client_builds import (
    current_builds,
    read_build_info,
    split_by_version,
    version_at,
)
from forever.pipeline.combatlog import LogHeader, LogSummary, log_files, read_log, scan_logs
from forever.pipeline.dbd import layouts_from_json
from forever.pipeline.decode import Candidate, decode_version, load_rules
from forever.pipeline.diff import Change, VersionDiff, diff_versions
from forever.pipeline.fetch import (
    DEFAULT_LOCALE,
    TableFetch,
    dbd_tables,
    fetch_dbd,
    fetch_gametables,
    fetch_tables,
    wago_dir,
)
from forever.pipeline.hotfix_overlay import HotfixSource, hotfix_source, hotfix_values, load_dbd_layouts
from forever.pipeline.install import InstallRefusedError, apply_install, plan_install, render_install_report
from forever.pipeline.levels import CasterLevels, from_logger_db, from_questie_journey, logger_utc_offset
from forever.pipeline.live_logs import split_live, writing_note
from forever.pipeline.measure import (
    Conflict,
    LogMeasures,
    MonsterObservation,
    find_mine,
    log_spell_sets,
    measure_log,
    monster_hp,
)
from forever.pipeline.monsters import MONSTERS_FILE, build_monsters, write_monsters
from forever.pipeline.questie import read_questie
from forever.pipeline.refresh import (
    RefreshSources,
    apply_refresh,
    collect_sources,
    compare,
    curve_candidates,
    curve_exclusions,
    read_snapshot,
    remeasure,
    snapshot_exists,
)
from forever.pipeline.report import render_report
from forever.pipeline.sources import load_source, source_provenance
from forever.pipeline.verify import VerifyReport, verify_version
from forever.profile import (
    ProfileView,
    check_locale,
    load_profile,
    normalize_class,
    read_profile,
    remove,
    resolve_path,
    set_character,
    set_game_locale,
    use,
)
from forever.profile_import import ImportPlan, apply_import, plan_import
from forever.provenance import (
    Certainty,
    Provenance,
    error_payload,
    format_provenance_line,
    local_provenance,
    min_certainty,
)
from forever.pvp import pvp_report
from forever.sim.leveling_mc import KillResult
from forever.status import StatusReport, status_report
from forever.store import current_identity, ensure_integrity, load_version, read_sources
from forever.talents_forever import TfAddon
from forever.timefmt import format_utc
from forever.watch import watch

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
    lookup.add_argument(
        "kind", help="type d'entité : spell (T01), zones (T04c), talent (T06) ; fiches PvP : forever pvp"
    )
    lookup.add_argument("name", nargs="?", help="nom anglais du sort ou du talent (casse, espaces et tirets ignorés)")
    lookup.add_argument("--level", type=int, help="zones : niveau du personnage")
    lookup.add_argument("--faction", choices=["horde", "alliance"], help="zones : faction (défaut : toutes)")
    lookup.add_argument("--questie", help="zones : dossier de l'addon Questie (défaut : dans FOREVER_WOW_DIR)")
    lookup.add_argument("--rank", type=int, help="position du rang, à partir de 1")
    lookup.add_argument("--class", dest="cls", help="talent : classe (défaut : Mage ; 9 classes depuis PV1)")
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
    explain.add_argument("--level", type=int, help="niveau des valeurs dérivées en mana (Arcane Blast)")
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
    fetch.add_argument(
        "--timeout", type=_positive_seconds, default=FETCH_TIMEOUT, help="délai d'une requête en secondes"
    )
    fetch.add_argument(
        "--gametables", action="store_true", help="GameTables de decode_rules.json (api/casc, T08b) au lieu des tables"
    )
    fetch.add_argument(
        "--dbd", action="store_true", help="définitions de structure des tables (WoWDBDefs, commit épinglé, T08c)"
    )
    fetch.add_argument("--dbd-commit", help="commit de WoWDBDefs à épingler (défaut : index du cache, sinon master)")
    fetch.add_argument("--offline", action="store_true", help="refuser tout appel réseau")
    fetch.add_argument("--json", action="store_true", help="sortie JSON")

    decode = sub.add_parser("decode", help="décoder les tables du client en version candidate (hors ligne)")
    decode.add_argument("--version", required=True, help="version complète, ex. 1.60.1.70009")
    decode.add_argument("--csv-dir", help="dossier des CSV (défaut : cache de forever fetch)")
    decode.add_argument("--out", help="dossier de la candidate (défaut : <cache>/candidates/<version>)")
    decode.add_argument("--force", action="store_true", help="remplacer une candidate existante")
    decode.add_argument(
        "--hotfixes",
        action="store_true",
        help="appliquer les correctifs du serveur de DBCache.bin (T08c, mode forever)",
    )
    decode.add_argument("--dbcache", help="DBCache.bin (défaut : <FOREVER_WOW_DIR>/Cache/ADB/enUS/DBCache.bin)")
    decode.add_argument(
        "--dbd-layouts",
        help="dispositions dérivées (JSON) au lieu du relevé de WoWDBDefs du cache (forever fetch --dbd)",
    )
    decode.add_argument("--json", action="store_true", help="sortie JSON")

    profile = sub.add_parser("profile", help="profil joueur hors du dépôt (FOREVER_PROFILE, ~/.forever)")
    psub = profile.add_subparsers(dest="profile_cmd", required=True)
    show = psub.add_parser("show", help="personnage actif (ou nommé)")
    show.add_argument("name", nargs="?", help="nom du personnage (défaut : actif)")
    show.add_argument("--json", action="store_true", help="sortie JSON")
    plist = psub.add_parser("list", help="personnages du profil")
    plist.add_argument("--json", action="store_true", help="sortie JSON")
    pset = psub.add_parser("set", help="créer ou mettre à jour un personnage (champs donnés seulement)")
    pset.add_argument("name", nargs="?", help="nom du personnage (absent : seulement --game-locale)")
    pset.add_argument("--game-locale", help="langue du client du joueur (enUS, frFR…), prioritaire sur Config.wtf")
    pset.add_argument("--class", dest="cls", help="classe (neuf classes, nom français ou anglais)")
    pset.add_argument("--race", help="race (Mage : races.json)")
    pset.add_argument("--faction", help="faction (jamais déduite)")
    pset.add_argument("--level", type=int, help="niveau")
    pset.add_argument("--talents", help="talents « clé=rang,… » (remplacent les précédents)")
    pset.add_argument("--profession", action="append", default=[], help="métier « Nom=compétence » (répétable)")
    pstate = pset.add_mutually_exclusive_group()
    pstate.add_argument(
        "--planned", dest="planned", action="store_const", const=True, help="personnage prévu, pas encore créé"
    )
    pstate.add_argument("--created", dest="planned", action="store_const", const=False, help="personnage créé en jeu")
    pset.add_argument("--json", action="store_true", help="sortie JSON")
    puse = psub.add_parser("use", help="rendre un personnage actif")
    puse.add_argument("name", help="nom du personnage")
    puse.add_argument("--json", action="store_true", help="sortie JSON")
    prm = psub.add_parser("remove", help="retirer un personnage")
    prm.add_argument("name", help="nom du personnage")
    prm.add_argument("--yes", action="store_true", help="retirer sans demander l'accord")
    prm.add_argument("--json", action="store_true", help="sortie JSON")
    pimp = psub.add_parser(
        "import", help="remplir le profil depuis ForeverLogger, Questie, Auctionator et les journaux (sans réseau)"
    )
    pimp.add_argument("--wtf", help="dossier SavedVariables (défaut : WTF/Account/*/SavedVariables du client)")
    pimp.add_argument("--logs", help="dossier des journaux de combat (défaut : Logs du client)")
    pimp.add_argument("--utc-offset", type=float, help="décalage de l'heure locale des journaux, en heures")
    pmode = pimp.add_mutually_exclusive_group()
    pmode.add_argument("--dry-run", action="store_true", help="lister les changements sans rien écrire")
    pmode.add_argument("--yes", action="store_true", help="écrire sans demander l'accord")
    pimp.add_argument("--json", action="store_true", help="sortie JSON")

    install = sub.add_parser(
        "install", help="installer une candidate en révision suivante de la version courante (T06b)"
    )
    install.add_argument("candidate", help="dossier de la candidate écrit par forever decode")
    install.add_argument(
        "--new-version",
        action="store_true",
        help="installer une nouvelle version du jeu (nouveau dossier) au lieu d'une révision (T08a)",
    )
    install.add_argument("--beta-level-cap", type=int, help="plafond de niveau de la bêta (T08b, avec sa source)")
    install.add_argument(
        "--beta-level-cap-source", help="source du plafond : adresse de la note officielle, ou « observation »"
    )
    mode = install.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="afficher les changements sans rien écrire")
    mode.add_argument("--yes", action="store_true", help="écrire sans demander l'accord")
    install.add_argument("--report", help="écrire aussi le rapport Markdown dans ce fichier (hors des données)")
    install.add_argument(
        "--motif", default="installation des valeurs décodées du client", help="motif noté dans revisions.json"
    )
    install.add_argument("--json", action="store_true", help="sortie JSON")

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

    notes = sub.add_parser("notes", help="notes officielles du forum de Blizzard (réseau, lancé à la main, D1)")
    notes.add_argument("--state-from-issues", help="état lu dans les issues (gh issue list --json number,body)")
    notes.add_argument("--post", help="lire un seul message officiel, SUJET/N (ex. 2360696/3), avec sa révision")
    notes.add_argument("--json", action="store_true", help="sortie JSON")
    api = sub.add_parser("api", help="API Blizzard (réseau)")
    api_sub = api.add_subparsers(dest="api_command", required=True, parser_class=_Parser)
    a_probe = api_sub.add_parser("probe", help="sonder les espaces de noms de Forever (point 10, décision 149)")
    a_probe.add_argument("--region", default="eu,us", help="régions séparées par des virgules (défaut : eu,us)")
    a_probe.add_argument("--env-file", default=".env", help="fichier des clés (défaut : .env ; variables d'abord)")
    a_probe.add_argument("--json", action="store_true", help="sortie JSON")

    w = sub.add_parser("watch", help="veille locale : client, addons, correctifs, journaux (hors ligne, rien lancé)")
    w.add_argument("--report", action="store_true", help="écrire le résumé dans le cache (tâche planifiée)")
    w.add_argument("--json", action="store_true", help="sortie JSON")

    up = sub.add_parser(
        "update", help="mise à jour automatique des données : jeu, correctifs, journaux, addons (T08d, réseau accordé)"
    )
    up.add_argument("--auto", action="store_true", help="passage automatique (hook de démarrage, tâche planifiée)")
    up.add_argument("--dry-run", action="store_true", help="tout calculer, ne rien écrire ni enregistrer")
    up.add_argument("--no-network", action="store_true", help="aucun accès réseau (ni wago, ni WoWDBDefs, ni git)")
    up.add_argument("--only", help="étapes : jeu,correctifs,journaux,addons (défaut : toutes)")
    up.add_argument("--json", action="store_true", help="sortie JSON")
    up_sub = up.add_subparsers(dest="update_command", required=False, parser_class=_Parser)
    u_status = up_sub.add_parser("status", help="attentes d'accord et dernier passage")
    u_status.add_argument("--json", action="store_true", help="sortie JSON")
    u_approve = up_sub.add_parser("approve", help="approuver une attente (base inchangée) et lancer un passage")
    u_approve.add_argument("id", help="identifiant de l'attente (forever update status)")
    u_approve.add_argument("--wait", action="store_true", help="passage dans ce processus au lieu d'un passage détaché")
    u_approve.add_argument("--json", action="store_true", help="sortie JSON")
    u_reject = up_sub.add_parser("reject", help="rejeter une attente")
    u_reject.add_argument("id", help="identifiant de l'attente")
    u_reject.add_argument("--reason", help="raison du rejet")
    u_reject.add_argument("--json", action="store_true", help="sortie JSON")

    addons = sub.add_parser("addons", help="addons de données installés (lecture locale)")
    addons_sub = addons.add_subparsers(dest="addons_command", required=True, parser_class=_Parser)
    a_status = addons_sub.add_parser("status", help="versions, empreintes et changements depuis le dernier relevé")
    a_status.add_argument("--dir", help="dossier des addons (défaut : <FOREVER_WOW_DIR>/Interface/AddOns)")
    a_status.add_argument("--save", action="store_true", help="enregistrer le relevé dans le cache")
    a_status.add_argument("--json", action="store_true", help="sortie JSON")
    a_inv = addons_sub.add_parser("inventory", help="métadonnées et empreintes d'un addon, sans aucune valeur (T08d)")
    a_inv.add_argument("folder", help="dossier de l'addon (nom dans le dossier des addons, ou chemin)")
    a_inv.add_argument("--dir", help="dossier des addons (défaut : <FOREVER_WOW_DIR>/Interface/AddOns)")
    a_inv.add_argument("--json", action="store_true", help="sortie JSON")

    hot = sub.add_parser("hotfixes", help="correctifs du serveur lus dans Logs/Hotfix.log (lecture locale)")
    hot.add_argument("--log", help="journal Hotfix.log (défaut : <FOREVER_WOW_DIR>/Logs/Hotfix.log)")
    hot.add_argument("--since-install", action="store_true", help="seulement depuis la révision installée")
    hot.add_argument("--dbcache", help="valeurs des correctifs (défaut : <FOREVER_WOW_DIR>/Cache/ADB/enUS/DBCache.bin)")
    hot.add_argument("--values", action="store_true", help="chaque valeur corrigée, avant et après (T08c)")
    hot.add_argument("--dbd-layouts", help="dispositions dérivées (JSON) au lieu du relevé de WoWDBDefs du cache")
    hot.add_argument("--csv-dir", help="dossier des CSV du build (défaut : cache de forever fetch)")
    hot.add_argument("--json", action="store_true", help="sortie JSON")

    origins = sub.add_parser("origins", help="origine déclarée de chaque valeur des données (hors ligne)")
    origins_sub = origins.add_subparsers(dest="origins_command", required=True, parser_class=_Parser)
    o_check = origins_sub.add_parser("check", help="contrôler les origines de toutes les versions installées")
    o_check.add_argument("--json", action="store_true", help="sortie JSON")
    o_inv = origins_sub.add_parser("inventory", help="inventaire des valeurs écrites à la main")
    o_inv.add_argument("--version", help="version du jeu (défaut : la plus récente)")
    o_inv.add_argument(
        "--markdown", action="store_true", help="rendu Markdown (docs/research/valeurs-ecrites-a-la-main.md)"
    )
    o_inv.add_argument("--json", action="store_true", help="sortie JSON")

    measures = sub.add_parser("measures", help="mesures tirées des journaux et SavedVariables")
    measures_sub = measures.add_subparsers(dest="measures_command", required=True, parser_class=_Parser)
    refresh = measures_sub.add_parser(
        "refresh", help="relancer toutes les mesures, afficher ce qui change, écrire après accord"
    )
    refresh.add_argument("--logs", help="dossier des journaux (défaut : <FOREVER_WOW_DIR>/Logs)")
    refresh.add_argument(
        "--sv", help="dossier SavedVariables (défaut : <FOREVER_WOW_DIR>/WTF/Account/*/SavedVariables)"
    )
    refresh.add_argument(
        "--questie", help="dossier de l'addon Questie (défaut : <FOREVER_WOW_DIR>/Interface/AddOns/Questie)"
    )
    refresh.add_argument(
        "--utc-offset", type=float, help="décalage horaire des journaux, en heures (niveaux du carnet)"
    )
    refresh.add_argument(
        "--fit-exclude",
        type=int,
        action="append",
        default=None,
        metavar="NPC",
        help="PNJ écarté de l'ajustement de la correction Questie (défaut : ceux de monsters.json installé)",
    )
    refresh.add_argument(
        "--curve-exclude",
        type=int,
        action="append",
        default=None,
        metavar="NPC",
        help="PNJ hors norme : mesuré, mais écarté des PV par niveau et de la correction (ajouté à ceux de "
        "monsters.json installé)",
    )
    refresh.add_argument("--curve-exclude-reason", help="raison des PNJ de --curve-exclude (obligatoire avec eux)")
    mode = refresh.add_mutually_exclusive_group()
    mode.add_argument("--yes", action="store_true", help="écrire sans demander")
    mode.add_argument("--dry-run", action="store_true", help="afficher sans jamais écrire")
    refresh.add_argument("--json", action="store_true", help="sortie JSON")

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

    sim = sub.add_parser("sim", help="simulateurs (leveling)")
    sim_sub = sim.add_subparsers(dest="sim_command", required=True, parser_class=_Parser)
    sim_leveling = sim_sub.add_parser("leveling", help="temps par monstre et XP par heure (Monte Carlo et analytique)")
    sim_leveling.add_argument("--level", type=int, required=True, help="niveau du personnage")
    _leveling_arguments(sim_leveling, n_default=1500)

    chart = sub.add_parser("chart", help="graphiques (leveling)")
    chart_sub = chart.add_subparsers(dest="chart_command", required=True, parser_class=_Parser)
    chart_leveling = chart_sub.add_parser("leveling", help="graphique PNG du leveling, niveau par niveau")
    chart_leveling.add_argument("--out", required=True, help="fichier PNG à écrire (hors de forever/data/)")
    chart_leveling.add_argument("--from", dest="level_from", type=int, default=10, help="premier niveau")
    chart_leveling.add_argument("--to", dest="level_to", type=int, default=30, help="dernier niveau")
    _leveling_arguments(chart_leveling, n_default=300)

    b = sub.add_parser("build", help="build du Mage par contexte : talents, ordre, raisons, sensibilité, respec")
    b.add_argument("context", choices=CONTEXTS, help="contexte : leveling, dungeon, raid, pvp-bg, pvp-world")
    b.add_argument("--level", type=int, help="niveau du build (défaut : niveau maximal des données)")
    b.add_argument("--race", help="race du personnage (défaut : Orc, signalé dans inputs)")
    b.add_argument("--current", default="", help="build actuel clé=rang,clé=rang (conseil de respec)")
    b.add_argument("--respecs", type=int, default=0, help="réinitialisations déjà faites (barème de respec)")
    b.add_argument("--sp", type=float, help="puissance des sorts de la fiche (remplace l'estimation)")
    b.add_argument("--crit", type=float, help="critique des sorts de la fiche, en fraction (0.1 = 10 %%)")
    b.add_argument("--preset", default="complet", help="préréglage de l'optimiseur : rapide ou complet (défaut)")
    b.add_argument("--seed", type=int, default=12345, help="graine du Monte Carlo (défaut : 12345)")
    b.add_argument("--rules", default="forever", choices=["forever", "seed"], help="règles (seed : leveling seulement)")
    b.add_argument(
        "--sensitivity", default="on", choices=["on", "off"], help="sensibilité aux hypothèses (défaut : on)"
    )
    b.add_argument(
        "--talented-bonus", type=int, default=0, help="points du bonus Legacy « Talented » (défaut : 0, hypothèse)"
    )
    b.add_argument("--json", action="store_true", help="sortie JSON")

    tal = sub.add_parser("talents", help="talents des 9 classes (savoir du client)")
    tal_sub = tal.add_subparsers(dest="talents_cmd", required=True)
    tal_check = tal_sub.add_parser("check", help="légalité d'un build : légal ou liste des erreurs")
    tal_check.add_argument("--class", dest="cls", required=True, help="classe (nom français ou anglais)")
    tal_check.add_argument("--level", type=int, required=True, help="niveau du personnage")
    tal_check.add_argument("points", nargs="*", help="talents « clé=rang » (clés de classes.json)")
    tal_check.add_argument("--json", action="store_true", help="sortie JSON")
    tal_tf = tal_sub.add_parser("tf", help="Talents Forever installé : recoupement, code de build, builds populaires")
    tf_sub = tal_tf.add_subparsers(dest="tf_cmd", required=True)
    tf_cross = tf_sub.add_parser("crosscheck", help="recoupement de nos arbres avec ceux de l'addon (écarts)")
    tf_cross.add_argument("--out", help="écrit aussi le rapport Markdown dans ce fichier")
    tf_cross.add_argument("--json", action="store_true", help="sortie JSON")

    pvp = sub.add_parser("pvp", help="fiches PvP fixes des 9 classes (savoir du client, sans calcul de combat)")
    pvp_sub = pvp.add_subparsers(dest="pvp_cmd", required=True)
    pvp_class = pvp_sub.add_parser("class", help="fiche d'une classe : contrôles, défensifs, ruptures, recharges")
    pvp_class.add_argument("cls", help="classe (nom français ou anglais)")
    pvp_class.add_argument("--level", type=int, help="niveau (défaut : rang le plus haut de chaque sort)")
    pvp_class.add_argument(
        "--talents", help="talents « clé=rang,… » (défaut : inconnus, sorts de talent « si talent »)"
    )
    pvp_class.add_argument("--json", action="store_true", help="sortie JSON")
    pvp_match = pvp_sub.add_parser("matchup", help="fiche d'affrontement : menaces, réponses, fenêtres")
    pvp_match.add_argument("cls", help="ma classe")
    pvp_match.add_argument("opponent", help="classe adverse")
    pvp_match.add_argument("--level", type=int, help="mon niveau")
    pvp_match.add_argument("--race", help="ma race (raciaux)")
    pvp_match.add_argument("--talents", help="mes talents « clé=rang,… »")
    pvp_match.add_argument("--opponent-level", type=int, help="niveau adverse (défaut : le mien)")
    pvp_match.add_argument("--json", action="store_true", help="sortie JSON")

    pets = sub.add_parser("pets", help="familiers du Chasseur : règles, familles, capacités, bêtes, guide (CH0)")
    pets_sub = pets.add_subparsers(dest="pets_cmd", required=True)
    pets_common = _Parser(add_help=False)
    pets_common.add_argument("--addon", help="dossier de Forever Bestiary (défaut : dans FOREVER_WOW_DIR)")
    pets_common.add_argument("--saved", help="sauvegarde ForeverBestiary.lua (défaut : dans FOREVER_WOW_DIR)")
    pets_common.add_argument("--questie", help="dossier de Questie (défaut : dans FOREVER_WOW_DIR)")
    pets_common.add_argument("--json", action="store_true", help="sortie JSON")
    pets_sub.add_parser("rules", parents=[pets_common], help="règles du système de familiers, avec leurs sources")
    pets_family = pets_sub.add_parser("family", parents=[pets_common], help="fiche d'une famille")
    pets_family.add_argument("name", help="famille (nom français ou anglais)")
    pets_ability = pets_sub.add_parser("ability", parents=[pets_common], help="fiche d'une capacité et de ses rangs")
    pets_ability.add_argument("name", help="capacité (nom français ou anglais)")
    pets_ability.add_argument("--rank", type=int, help="un seul rang")
    pets_ability.add_argument("--detail", action="store_true", help="bêtes qui enseignent chaque rang")
    pets_beast = pets_sub.add_parser("beast", parents=[pets_common], help="fiche d'une bête de Forever Bestiary")
    pets_beast.add_argument("name", help="bête (nom ou identifiant de PNJ)")
    pets_tame = pets_sub.add_parser("tame", parents=[pets_common], help="guide d'apprivoisement (zone et niveau)")
    target = pets_tame.add_mutually_exclusive_group(required=True)
    target.add_argument("--ability", help="capacité à apprendre")
    target.add_argument("--family", help="famille cherchée")
    target.add_argument("--beast", help="bête cherchée")
    pets_tame.add_argument("--rank", type=int, help="rang de la capacité (défaut : le plus haut atteignable)")
    pets_tame.add_argument("--zone", required=True, help="zone (nom français ou anglais)")
    pets_tame.add_argument("--level", type=int, help="niveau du Chasseur (obligatoire, jamais deviné)")
    pets_cross = pets_sub.add_parser("crosscheck", parents=[pets_common], help="écarts client ↔ addon ↔ Questie")
    pets_cross.add_argument("--markdown", help="écrire aussi le rapport Markdown dans ce fichier")
    pets_sub.add_parser("mine", parents=[pets_common], help="mes observations et mes familiers (ma sauvegarde)")
    pets_measure = pets_sub.add_parser(
        "measure", parents=[pets_common], help="relevés du familier de ForeverLogger comparés au client (hors ligne)"
    )
    pets_measure.add_argument("--addon-sv", required=True, help="SavedVariables ForeverLogger.lua")

    sub.add_parser("mcp", help="serveur MCP sur stdio")
    hook = sub.add_parser("hook", help="hooks du plugin Claude Code (entrée JSON sur stdin)")
    hook.add_argument(
        "hook_name",
        choices=["session-start", "check-numbers"],
        help="session-start : ligne de fraîcheur (dans le dépôt) ; check-numbers : chiffres sans source (hook Stop)",
    )
    return parser


def _leveling_arguments(p: argparse.ArgumentParser, *, n_default: int) -> None:
    p.add_argument("--race", help="race du personnage (défaut : Orc, signalé dans inputs)")
    p.add_argument("--rotation", default="frost", choices=["frost", "fire", "arcane"], help="rotation (défaut : frost)")
    p.add_argument(
        "--ab-stacks", type=int, help="rotation arcane : cumuls d'Arcane Blast avant la décharge (défaut : maximum)"
    )
    p.add_argument(
        "--ab-dump",
        choices=["frostbolt", "fireball", "arcane_missiles"],
        help="rotation arcane : sort de décharge (défaut : frostbolt)",
    )
    p.add_argument("--talents", default="", help="talents clé=rang,clé=rang (ex. improvedFrostbolt=3)")
    p.add_argument("--n", type=int, default=n_default, help=f"combats simulés par niveau (défaut : {n_default})")
    p.add_argument("--seed", type=int, default=12345, help="graine du Monte Carlo (défaut : 12345)")
    p.add_argument(
        "--mob-source",
        default="measured",
        choices=["measured", "seed"],
        help="PV du monstre : mesurés puis Questie corrigé (défaut) ou modèle du seed",
    )
    p.add_argument(
        "--spell-level",
        default="character",
        choices=["character", "rank"],
        help="dégâts des rangs au niveau du personnage (défaut) ou du rang (seed)",
    )
    p.add_argument(
        "--rules",
        default="forever",
        choices=["forever", "seed"],
        help="règles du simulateur : corrections de Forever (défaut) ou comportement du seed (parité)",
    )
    p.add_argument(
        "--armor",
        default="auto",
        choices=["auto", "frost", "mage"],
        help="armure portée : selon le niveau (défaut), Frost/Ice Armor ou Mage Armor",
    )
    p.add_argument("--level-diff", type=int, help="niveau du monstre - niveau du personnage (défaut des données)")
    p.add_argument("--nova", action="store_true", help="Frost Nova au contact")
    p.add_argument("--json", action="store_true", help="sortie JSON")
    p.add_argument(
        "--low-level-penalty",
        choices=["on", "off"],
        help="pénalité des sorts de bas niveau (défaut : coefficient.low_level_default des données ; off refusé "
        "avec --rules seed)",
    )


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


def _zone_line(z: Mapping[str, Any]) -> str:
    c = z["by_color"]
    quests = z["quest_levels"]
    npcs = z["npc_levels"]
    return (
        f"  {z['name']} : {z['useful_quests']} quête(s) utile(s) (vertes {c['green']}, jaunes {c['yellow']}, "
        f"orange {c['orange']}, grises {c['gray']}, rouges {c['red']}) · quêtes de niveau {quests[0]} à {quests[1]}"
        + (f" · PNJ {npcs[0]} à {npcs[1]}" if npcs else "")
    )


def render_zones(res: Mapping[str, Any]) -> list[str]:
    low, high = res["band"]
    lines = [
        (
            f"Niveau {res['level']} · faction {res['faction'] or 'toutes'} · quêtes utiles de niveau {low} à {high} "
            f"({res['certainty']}, {res['source']})"
        ),
        "Zones :",
    ]
    lines += [_zone_line(z) for z in res["zones"]] or ["  aucune"]
    lines.append("Donjons :")
    lines += [_zone_line(d) for d in res["dungeons"]] or ["  aucun"]
    return lines


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


def render_talent(res: TalentLookup) -> list[str]:
    head = f"{res['name']} (arbre {res['tree']}, palier {res['tier']}, {res['max_rank']} rang(s))"
    lines = [head]
    needs = [f"{res['required_tree_points']} points dans l'arbre"] if res["required_tree_points"] else []
    if res["prereq"] is not None:
        needs.append(f"{res['prereq']['name']} au maximum")
    if needs:
        lines.append("Exige : " + ", ".join(needs))
    if res["spell"] is not None:
        lines.append(f"Apprend le sort : {res['spell']} (forever lookup spell {res['spell']})")
    lines += [f"rang {r['rank']}/{res['max_rank']} : {r['description']}" for r in res["ranks"]]
    if res["duration_s"] is not None:
        lines.append(f"Durée corrigée d'après le client : {_num(res['duration_s'])} s")
    lines.append(f"Source des valeurs : {res['source']}")
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
    lines = [f"Données locales {rep['local_version']} r{rep['data_revision']} · {integrity}"]
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
            for key, label in (("ecart_median_s", "écart médian"), ("ecart_p10_s", "écart du 10e percentile"))
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
    if args.kind == "zones":
        zones = lookup_zones(
            deps, args.level, faction=args.faction, questie_dir=Path(args.questie) if args.questie else None
        )
        _emit(zones, render_zones(zones), zones["provenance"], args.json)
        return EXIT_OK
    if args.kind == "talent":
        if not args.name:
            raise InvalidArgumentError("Nom du talent manquant.", "écrire forever lookup talent <nom>")
        if args.cls and normalize_class(args.cls) != "Mage":
            other = lookup_class_talent(deps, args.cls, args.name)
            lines = [
                (
                    f"{other['name']} ({other['class']}, {other['tree']}, palier {other['tier'] or '?'}, "
                    f"colonne {other['col'] or '?'}, {other['max_rank']} rang(s))"
                ),
                f"Description : {other['description_template']}",
            ]
            lines += [f"Prérequis : {p['name']} ({p['kind']})" for p in other["prereqs"]]
            _emit(other, lines, other["provenance"], args.json)
            return EXIT_OK
        talent = lookup_talent(deps, args.name, args.rank)
        _emit(talent, render_talent(talent), talent["provenance"], args.json)
        return EXIT_OK
    if args.kind != "spell":
        raise UnsupportedKindError(f"type « {args.kind} »", ["spell", "talent", "zones", "pvp", "pets"])
    if not args.name:
        raise InvalidArgumentError("Nom du sort manquant.", "écrire forever lookup spell <nom>")
    res = lookup_spell(deps, args.name, args.rank, detail=args.detail, limit=args.limit, offset=args.offset)
    _emit(res, render_lookup(res), res["provenance"], args.json)
    return EXIT_OK


def _cmd_explain(deps: Deps, args: argparse.Namespace) -> int:
    res = explain_mechanic(deps, args.mechanic_id, args.level)
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


def _positive_seconds(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"durée invalide : « {text} »") from None
    if not value > 0:
        raise argparse.ArgumentTypeError(f"durée strictement positive attendue : « {text} »")
    return value


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
    if args.gametables:
        return _fetch_gametables(deps, args)
    if args.dbd:
        return _fetch_dbd(deps, args)
    if args.tables:
        locales = _split(args.locale) if args.locale else [DEFAULT_LOCALE]
        results = fetch_tables(
            deps, args.version, _split(args.tables), locales=locales, refresh=args.refresh, timeout=args.timeout
        )
    else:
        tables, localized = _fetch_defaults(deps)
        results = fetch_tables(deps, args.version, tables, refresh=args.refresh, timeout=args.timeout)
        for locale, names in localized.items():
            results += fetch_tables(
                deps, args.version, names, locales=[locale], refresh=args.refresh, timeout=args.timeout
            )
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


def _fetch_dbd(deps: Deps, args: argparse.Namespace) -> int:
    _, rules = load_rules(deps.data_dir)
    tables = _split(args.tables) if args.tables else dbd_tables(rules)
    res = fetch_dbd(deps, args.version, tables, commit=args.dbd_commit, refresh=args.refresh)
    provenance = local_provenance(deps)
    downloaded = sum(1 for f in res["files"] if not f["from_cache"])
    lic = res["license"] or {}
    licence = lic.get("first_line") or ("absente du dépôt" if lic.get("status") == "absent" else "non lue")
    lines = [
        (
            f"Définitions {res['repo']} au commit {res['commit'][:12]} : {len(res['files'])} table(s), "
            f"{downloaded} téléchargée(s) ; licence : {licence}"
        ),
        f"  index : {res['index']}",
    ]
    lines += [
        f"  {f['table']} · {f['bytes']} octets · {'cache' if f['from_cache'] else 'téléchargée'}" for f in res["files"]
    ]
    _emit({**res, "provenance": provenance}, lines, provenance, args.json)
    return EXIT_OK


def _fetch_gametables(deps: Deps, args: argparse.Namespace) -> int:
    _, rules = load_rules(deps.data_dir)
    gametables = rules.get("gametables")
    if not isinstance(gametables, dict) or not gametables:
        raise InvalidArgumentError(
            "Aucune GameTable dans decode_rules.json.", "ajouter gametables (nom -> identifiant de fichier)"
        )
    results = fetch_gametables(
        deps, args.version, {str(k): int(v) for k, v in gametables.items()}, refresh=args.refresh
    )
    provenance = local_provenance(deps)
    downloaded = sum(1 for r in results if not r["from_cache"])
    lines = [f"GameTables de {args.version} : {len(results)} ({downloaded} téléchargée(s))"]
    lines += [
        f"  {r['name']} ({r['file_id']}) · "
        + ("absente du build (réponse vide)" if r["absent"] else f"{r['bytes']} octets")
        + (" · cache" if r["from_cache"] else "")
        for r in results
    ]
    payload = {"version": args.version, "gametables": results, "provenance": provenance}
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def render_decode(c: Candidate) -> list[str]:
    lines = [
        f"Version candidate {c.version} : {c.root}",
        f"{c.talents} talents · {c.spells} sorts · {c.spell_ranks} rangs de sort",
    ]
    lines += [f"  observation : {o}" for o in c.observations]
    return lines


_CHANGE_WHAT = {
    "talent": "talent",
    "spell": "sort",
    "file": "fichier",
    "scaling": "valeur",
    "character": "valeur",
    "class": "entrée de classe",
    "pet": "capacité de familier",
    "pvp_item": "bijou PvP",
}


def _hotfix_note(c: Change) -> str:
    """Attribution d'une ligne de `forever diff` au correctif du serveur qui porte la valeur (T08c)."""
    fix = c.get("hotfix")
    if not fix:
        return ""
    pushes = ", ".join(str(p) for p in fix.get("pushes", []))
    seen = fix.get("first_logged_at")
    when = f"vu par le client le {str(seen)[:10]} {str(seen)[11:16]}" if seen else "date inconnue"
    return f" (correctif {pushes}, {when})"


def _change_line(c: Change) -> str:
    what = _CHANGE_WHAT.get(c["kind"], c["kind"])
    note = _hotfix_note(c)
    if c["change"] == "added":
        return f"+ {what} ajouté : {c['key']}" + (f" ({c['field']})" if c["field"] else "") + note
    if c["change"] == "removed":
        return f"- {what} retiré : {c['key']}" + (f" ({c['field']})" if c["field"] else "") + note
    old, new = json.dumps(c["old"], ensure_ascii=False), json.dumps(c["new"], ensure_ascii=False)
    return f"~ {c['key']} : {c['field']} {old} -> {new}" + note


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


def _locale_line(view: ProfileView) -> list[str]:
    loc = view.get("game_locale")
    if not loc:
        return ["Langue du client : inconnue (forever profile set --game-locale enUS, ou FOREVER_WOW_DIR)"]
    where = "WTF/Config.wtf" if loc["source"] == "client" else "donnée par le joueur"
    return [f"Langue du client : {loc['value']} ({where})"]


def render_profile(view: ProfileView) -> list[str]:
    c = view["character"]
    if c is None:
        return [
            f"Profil joueur {view['path']} : aucun personnage (forever profile set <nom> --class Mage …)",
            *_locale_line(view),
        ]
    active = " (actif)" if c["name"] == view["active"] else ""
    head = f"Profil : {c['name']}{active}, {c['class']} {c['race'] or 'race ?'}, {c['faction'] or 'faction ?'}"
    if c.get("planned"):
        head += ", personnage prévu (pas encore créé)"
    else:
        head += f", niveau {c['level'] if c['level'] is not None else '?'}"
    lines = [head]
    if c["talents"]:
        lines.append("Talents : " + ", ".join(f"{k} {v}" for k, v in c["talents"].items()))
    if c["professions"]:
        lines.append("Métiers : " + ", ".join(f"{k} {v}" for k, v in c["professions"].items()))
    if view["missing"]:
        lines.append("Manquant : " + ", ".join(view["missing"]))
    if view["stale"]:
        lines.append(f"Saisi sur {c['game_version']} : à revérifier sur les données actuelles")
    if not c["validated"]:
        lines.append("Classe non couverte par les calculs : valeurs gardées sans contrôle")
    return [*lines, *_locale_line(view)]


def _parse_professions(items: list[str]) -> dict[str, int] | None:
    if not items:
        return None
    out: dict[str, int] = {}
    for item in items:
        name, sep, value = item.partition("=")
        if not sep or not name.strip() or not value.strip().isdigit():
            raise InvalidArgumentError(f"Métier mal écrit « {item} ».", 'écrire --profession "Couture=150"')
        out[name.strip()] = int(value)
    return out


def _import_lines(plan: ImportPlan) -> list[str]:
    def shown(value: Any) -> str:
        text = json.dumps(value, ensure_ascii=False) if isinstance(value, dict | list) else str(value)
        return text if len(text) <= 80 else text[:77] + "…"

    lines = [f"Import du profil : {len(plan['changes'])} changement(s)"]
    for c in plan["changes"]:
        who = c["character"] if c["character"] is not None else f"royaume {c.get('realm')}"
        build = c["client_build"] or "inconnue"
        lines.append(
            f"  {who} · {c['field']} : {shown(c['old'])} → {shown(c['new'])} ({c['source']}, {c['at']}, client {build})"
        )
    lines += [
        f"  désaccord · {c['character']} · {c['field']} : gardé {shown(c['kept']['value'])} ({c['kept']['source']}), "
        f"autre {shown(c['other']['value'])} ({c['other']['source']})"
        for c in plan["conflicts"]
    ]
    lines += [f"  non créé · {s['name']} ({s['guid']}) : {s['reason']}" for s in plan["skipped"]]
    return lines


def _cmd_profile_import(deps: Deps, args: argparse.Namespace) -> int:
    sv_dir = Path(args.wtf) if args.wtf else _default_sv(deps)
    logs_dir = Path(args.logs) if args.logs else (deps.wow_dir / "Logs" if deps.wow_dir is not None else None)
    offset = timedelta(hours=args.utc_offset) if args.utc_offset is not None else None
    plan = plan_import(deps, sv_dir=sv_dir, logs_dir=logs_dir, utc_offset=offset)
    lines = _import_lines(plan)
    printed = False
    if not plan["changes"]:
        status = "aucun changement"
    elif args.dry_run:
        status = "simulation"
    elif args.yes:
        apply_import(deps, plan)
        status = "écrit"
    else:
        if deps.confirm is not None and not args.json:
            print("\n".join(lines))  # changements listés avant la demande d'accord
            printed = True
        if deps.confirm is not None and deps.confirm("Écrire ces changements dans le profil ? [o/N] "):
            apply_import(deps, plan)
            status = "écrit"
        else:
            status = "refusé"
    verdict = {
        "aucun changement": "Aucun changement : rien n'est écrit.",
        "simulation": "Import en simulation : rien n'est écrit (--yes pour écrire).",
        "écrit": f"Profil écrit : {resolve_path(deps)}.",
        "refusé": "Import refusé : rien n'est écrit.",
    }[status]
    payload = {key: value for key, value in plan.items() if key != "doc"} | {"status": status}
    _emit(payload, [*([] if printed else lines), verdict, *plan["notes"]], plan["provenance"], args.json)
    return EXIT_OK


def _pvp_value(v: Any) -> str:
    value = v["value"] if isinstance(v, dict) and "value" in v else v
    return "?" if value is None else str(value)


def _pvp_items(title: str, items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return [f"{title} : aucun"]
    lines = [f"{title} :"]
    for i in items:
        parts = [i["name"]]
        if i.get("conditional"):
            parts.append(str(i["conditional"]))
        if i.get("pet"):
            parts.append("familier")
        for field, label in (
            ("diminish_name", "catégorie"),
            ("duration_s", "durée s"),
            ("cooldown_s", "recharge s"),
            ("range_yd", "portée m"),
            ("lockout_s", "verrouillage s"),
        ):
            if field in i:
                parts.append(f"{label} {_pvp_value(i[field])}")
        lines.append("  " + " · ".join(parts))
    return lines


def render_pvp(report: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    if "threats" in report:
        mine, them = report["mine"], report["opponent"]
        lines.append(f"Affrontement : {mine['class']} contre {them['class']}")
        lines += _pvp_items("Ses recharges offensives", report["threats"]["bursts"])
        lines += _pvp_items("Ses contrôles", report["threats"]["controls"])
        lines += _pvp_items("Ses défensifs", report["threats"]["defensives"])
        lines += _pvp_items("Mes ruptures de contrôle", report["answers"]["cc_breaks"])
        lines += _pvp_items("Mes interruptions", report["answers"]["interrupts"])
        lines += _pvp_items("Ses ruptures de contrôle", report["their_answers"]["cc_breaks"])
        lines += [f"Fenêtre : {w['name']} (recharge {_pvp_value(w['cooldown_s'])} s)" for w in report["windows"]]
    else:
        lines.append(f"Fiche PvP : {report['class']}" + (f", niveau {report['level']}" if report["level"] else ""))
        for key, title in (
            ("controls", "Contrôles"),
            ("defensives", "Défensifs"),
            ("cc_breaks", "Ruptures de contrôle"),
            ("interrupts", "Interruptions"),
            ("dispels", "Dissipations"),
            ("mobility", "Mobilité"),
            ("bursts", "Recharges offensives"),
        ):
            lines += _pvp_items(title, report[key])
    lines += [f"Manquant : {m}" for m in report["missing"]]
    lines += [f"Limite : {x}" for x in report["limits"]]
    return lines


def _tf_addon(deps: Deps) -> TfAddon:
    from forever.talents_forever import ADDON_FOLDER, load_addon

    addon = load_addon(deps)
    if addon is None:
        where = deps.wow_dir / "Interface" / "AddOns" / ADDON_FOLDER if deps.wow_dir else "FOREVER_WOW_DIR non réglé"
        raise InvalidArgumentError(
            f"Talents Forever introuvable ({where}).", "installer l'addon Talents Forever ou régler FOREVER_WOW_DIR"
        )
    return addon


def _tf_provenance(deps: Deps, addon: TfAddon, certainty: Certainty) -> Provenance:
    a = addon.describe()
    return local_provenance(
        deps,
        certainty=certainty,
        assumptions=[
            (
                f"Talents Forever {a['version']} (Data.lua build {a['build']}, généré le {a['generated']}, codes "
                f"v{a['codeVersion']}, empreinte {a['fingerprint']}), lecture locale"
            )
        ],
    )


def _cmd_talents_tf(deps: Deps, args: argparse.Namespace) -> int:
    from forever.talents_forever import crosscheck_report, render_crosscheck

    addon = _tf_addon(deps)
    report = crosscheck_report(addon)
    text = render_crosscheck(report)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    t = report["totals"]
    lines = [
        (
            f"Talents Forever {report['addon']['version']} face aux données {report['game_version']} : nœuds numérotés "
            f"autrement {t['renumbered']}, sans correspondance {t['unmatched']}, prérequis {t['prereq']}, noms d'arbres "
            f"{t['tree_names']}"
        )
    ]
    for name, c in sorted(report["classes"].items()):
        label = {"possible": "possible", "bloque": "bloqué"}.get(c["export"], "format non pris en charge")
        lines.append(f"  {name} : {c['matched']}/{c['positions']} positions appariées, export {label}")
        if c["blocked"]:
            lines.append(f"    {c['blocked']}")
    if args.out:
        lines.append(f"Rapport écrit : {args.out}")
    payload = {**report, "provenance": _tf_provenance(deps, addon, "probable")}
    _emit(payload, lines, payload["provenance"], args.json)
    return EXIT_OK


def _cmd_talents(deps: Deps, args: argparse.Namespace) -> int:
    if args.talents_cmd == "tf":
        return _cmd_talents_tf(deps, args)
    points = parse_talents(",".join(args.points)) if args.points else {}
    report = check_class_talents(deps, args.cls, points, args.level)
    verdict = "légal" if report["legal"] else "illégal"
    lines = [
        (
            f"Build {report['class']} niveau {report['level']} : {verdict} "
            f"({report['points']['spent']}/{report['points']['available']} points)"
        )
    ]
    lines += [f"  erreur : {e}" for e in report["errors"]]
    lines += [f"  {t['name']} {t['rank']}/{t['max_rank']} : {t['description_template']}" for t in report["talents"]]
    _emit(report, lines, report["provenance"], args.json)
    return EXIT_OK


def _cmd_pets(deps: Deps, args: argparse.Namespace) -> int:
    from forever.pets import render_crosscheck_markdown
    from forever.pets_lookup import lookup_pets, pets_crosscheck, pets_measure, pets_mine, render_pets

    addon = Path(args.addon) if args.addon else None
    saved = Path(args.saved) if args.saved else None
    questie = Path(args.questie) if args.questie else None
    cmd = args.pets_cmd
    if cmd == "crosscheck":
        payload = pets_crosscheck(deps, addon_dir=addon, questie_dir=questie)
        if args.markdown:
            target = Path(args.markdown)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(render_crosscheck_markdown(payload).encode("utf-8"))
    elif cmd == "mine":
        payload = pets_mine(deps, saved_path=saved)
    elif cmd == "measure":
        payload = pets_measure(deps, Path(args.addon_sv))
    else:
        if cmd == "rules":
            name = None
        elif cmd == "tame":
            name = args.ability or args.family or args.beast
        else:
            name = args.name
        payload = lookup_pets(
            deps,
            name,
            rank=getattr(args, "rank", None),
            zone=getattr(args, "zone", None),
            level=getattr(args, "level", None),
            detail=getattr(args, "detail", False),
            addon_dir=addon,
            saved_path=saved,
            questie_dir=questie,
        )
    _emit(payload, render_pets(payload), payload["provenance"], args.json)
    return EXIT_OK


def _cmd_pvp(deps: Deps, args: argparse.Namespace) -> int:
    talents = parse_talents(args.talents) if args.talents else None
    if args.pvp_cmd == "class":
        report = pvp_report(deps, args.cls, level=args.level, talents=talents)
    else:
        report = pvp_report(
            deps,
            args.cls,
            opponent=args.opponent,
            level=args.level,
            race=args.race,
            talents=talents,
            opponent_level=args.opponent_level,
        )
    _emit(report, render_pvp(report), report["provenance"], args.json)
    return EXIT_OK


def _cmd_profile(deps: Deps, args: argparse.Namespace) -> int:
    cmd = args.profile_cmd
    if cmd == "import":
        return _cmd_profile_import(deps, args)
    name: str | None = getattr(args, "name", None)
    target = name or ""
    if cmd == "set" and args.game_locale is not None:
        check_locale(args.game_locale)
    if cmd == "set" and not name and args.game_locale is None:
        raise InvalidArgumentError("Nom du personnage manquant.", "donner un nom, ou --game-locale seulement")
    if cmd == "set" and args.game_locale is not None:
        set_game_locale(deps, args.game_locale)
    if cmd == "set" and name:
        set_character(
            deps,
            target,
            cls=args.cls,
            race=args.race,
            faction=args.faction,
            level=args.level,
            talents=parse_talents(args.talents) if args.talents is not None else None,
            professions=_parse_professions(args.profession),
            planned=args.planned,
        )
    elif cmd == "use":
        use(deps, target)
    elif cmd == "remove":
        if args.yes or (deps.confirm is not None and deps.confirm(f"Retirer {name} du profil ? [o/N] ")):
            remove(deps, target)
        else:
            view = read_profile(deps)
            _emit(view, [f"Retrait de {name} refusé : rien n'est écrit."], view["provenance"], args.json)
            return EXIT_OK
    view = read_profile(deps, name if cmd in ("show", "set") else None)
    if cmd == "list":
        lines = [f"Profil joueur {view['path']} :"]
        chars = load_profile(Path(view["path"]))["characters"]
        lines += [
            f"  {'* ' if n == view['active'] else '  '}{n}" + (" (prévu)" if chars[n].get("planned") else "")
            for n in view["characters"]
        ] or ["  (vide)"]
    else:
        lines = render_profile(view)
    _emit(view, lines, view["provenance"], args.json)
    return EXIT_OK


def _install_target(plan: Any) -> str:
    """Cible d'une installation : nouvelle version (T08a) ou révision de la version courante (T06b)."""
    if plan["new_version"]:
        return f"nouvelle version {plan['version_from']} → {plan['version_to']} r{plan['revision_to']}"
    return f"{plan['version']} r{plan['revision_from']} → r{plan['revision_to']}"


def _install_prompt(plan: Any) -> str:
    what = "cette nouvelle version" if plan["new_version"] else "cette révision"
    return f"Installer {what} ({_install_target(plan)}) ? [o/N] "


def _cmd_install(deps: Deps, args: argparse.Namespace) -> int:
    report_path = Path(args.report) if args.report else None
    if report_path is not None and report_path.resolve().is_relative_to(deps.data_dir.resolve()):
        raise InvalidArgumentError(
            f"Le rapport ne s'écrit jamais dans {deps.data_dir}.", "choisir un fichier --report hors des données"
        )
    cap_args = {"beta_level_cap": args.beta_level_cap, "beta_level_cap_source": args.beta_level_cap_source}
    plan = plan_install(deps, args.candidate, new_version=args.new_version, **cap_args)
    text = render_install_report(plan)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_bytes(text.encode("utf-8"))
    revision = None
    if plan["refused"]:
        raise InstallRefusedError(plan["refused"])
    if not plan["changes"] and not args.new_version:
        status = "rien à écrire"
    elif args.dry_run:
        status = "simulation"
    elif args.yes or (deps.confirm is not None and deps.confirm(_install_prompt(plan))):
        report_rel = args.report.replace("\\", "/") if args.report else None
        revision = apply_install(
            deps, args.candidate, motif=args.motif, report=report_rel, new_version=args.new_version, **cap_args
        )
        status = "écrit"
    else:
        status = "refusé"
    provenance = local_provenance(deps, assumptions=[f"installation : {status}"])
    payload = {"status": status, "plan": plan, "revision": revision, "provenance": provenance}
    counts = ", ".join(f"{k} {v}" for k, v in plan["counts"].items())
    lines = [f"Installation de {args.candidate} : {_install_target(plan)} : {status}", f"Changements : {counts}"]
    cap = (plan.get("game_state") or {}).get("beta_level_cap")
    if cap:
        how = f"reporté de la {cap['carried_from']}" if cap.get("carried") else "donné"
        lines.append(
            f"État du jeu : plafond de la bêta {cap.get('value')} ({how} ; source {cap.get('source')} ; {cap.get('certainty')})"
        )
    if report_path is not None:
        lines.append(f"Rapport : {report_path}")
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def _hotfix_source(deps: Deps, args: argparse.Namespace) -> HotfixSource | None:
    """Correctifs du serveur demandés par `--hotfixes` : DBCache.bin, dispositions de WoWDBDefs, journal du cache."""
    if not args.hotfixes:
        return None
    path = _dbcache_path(deps, args.dbcache)
    if path is None or not path.is_file():
        raise InvalidArgumentError(
            f"DBCache.bin introuvable ({path or 'FOREVER_WOW_DIR absent'}).",
            "donner --dbcache <chemin> ou définir FOREVER_WOW_DIR",
        )
    _, rules = load_rules(deps.data_dir)
    layouts, dbd = _dbd_layouts(deps, args.dbd_layouts, args.version, rules)
    journal = hotfixes.load_journal(deps.cache_dir)
    return hotfix_source(path, layouts, dbd, journal, args.version, rules, format_utc(deps.now()))


def _cmd_decode(deps: Deps, args: argparse.Namespace) -> int:
    c = decode_version(
        deps,
        args.version,
        csv_dir=Path(args.csv_dir) if args.csv_dir else None,
        out=Path(args.out) if args.out else None,
        force=args.force,
        hotfixes=_hotfix_source(deps, args),
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


def _client_builds(deps: Deps) -> list[Any]:
    """Journal des versions du client, complété du relevé courant quand le dossier du client est lisible (T08a)."""
    return current_builds(deps.cache_dir, deps.wow_dir)


def _summary_json(s: LogSummary, builds: list[Any]) -> dict[str, Any]:
    return {
        "name": s.name,
        "lines": s.lines,
        "events": s.events,
        # Entête du journal : tronquée (« 1.60.1 »), jamais utilisée pour attribuer une version (décision 135).
        "build": s.header.build if s.header else None,
        "client_version": version_at(builds, s.start) if s.start else None,
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
    builds = _client_builds(deps)
    provenance = _log_provenance(deps, [s.header for s in summaries if s.header], "certain", [])
    lines = [f"Journaux de combat dans {directory} : {len(summaries)}"]
    for s in summaries:
        if s.error:
            lines.append(f"  {s.name} · {s.lines} ligne(s) · illisible : {s.error}")
        else:
            span = f"{s.start:%Y-%m-%d %H:%M:%S} → {s.end:%H:%M:%S}" if s.start and s.end else "aucun événement"
            who = ", ".join(s.mine) or "aucun joueur « à moi »"
            seen = version_at(builds, s.start) if s.start else None
            lines.append(f"  {s.name} · {s.lines} lignes · {span} · {who} · client {seen or 'inconnu'}")
    payload = {
        "dir": str(directory),
        "logs": [_summary_json(s, builds) for s in summaries],
        "client_builds": [{"build": b.build, "installed_at": format_utc(b.installed_at)} for b in builds],
        "provenance": provenance,
    }
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


def _fmt_kill(label: str, k: KillResult) -> str:
    return (
        f"  {label} : total {_num(round(k['total'], 2))} s · combat {_num(round(k['combat'], 2))} s · "
        f"repos {_num(round(k['downtime'], 2))} s · mana {_num(round(k['mana'], 1))} · "
        f"dégâts subis {_num(round(k['taken'], 1))} · XP/h {_num(round(k['xp_h']))}"
    )


def _pct(x: float | None, digits: int = 1) -> str:
    return "?" if x is None else f"{x * 100:+.{digits}f} %".replace(".", ",")


def _dec(x: float, digits: int = 2) -> str:
    return _num(round(x, digits))


def _advantage(gap: Mapping[str, Any] | None, unit: str, higher_is_better: bool) -> str:
    """Écart brut (a - b) présenté comme avantage de a (positif = a fait mieux), intervalle compris."""
    if not gap:
        return "aucun"
    s = 1 if higher_is_better else -1
    lo, hi = sorted((s * gap["low"], s * gap["high"]))
    sig = "significatif" if gap["significant"] else "égalité statistique"
    return f"{_dec(s * gap['mean'])} {unit} [{_dec(lo)} ; {_dec(hi)}] ({sig})"


def render_build(rep: Mapping[str, Any]) -> list[str]:
    """Texte du rapport de build (français) : en-tête, talents par arbre, ordre, choix, métrique, raisons,
    alternative, stabilité, sensibilité, respec, angles morts, hypothèses. Écarts présentés comme avantage du build
    (positif = le build fait mieux) ; le JSON garde les écarts bruts (build - autre)."""
    mt = rep["metric"]
    unit, up = mt["unit"], mt["higher_is_better"]
    head = f"Build {rep['context']} niveau {rep['level']} · {rep['race']}"
    if rep["scenario"]["provisional"]:
        head += " · scénario provisoire · mana des combats longs non modélisée (T05b)"
    head += " · équipement : fiche de base par niveau"
    if not rep["verifiable_in_game"]:
        head += " · non vérifiable en jeu avant la sortie"
    p = rep["points"]
    spent = f"Talents : {p['total']} point(s) sur {p['available']}"
    if p["unspent"]:
        spent += f", {p['unspent']} non dépensé(s)"
    lines = [head, spent]
    for tree, pts in rep["talents_by_tree"].items():
        if pts:
            lines.append(f"  {tree} ({sum(pts.values())}) : " + ", ".join(f"{k} {v}" for k, v in pts.items()))
    if rep["order"]:
        lines.append("Ordre : " + ", ".join(f"{s['level']} {s['talent'] or '-'}" for s in rep["order"]))
        undecided = [f"{s['level']} {s['talent']}" for s in rep["order"] if s.get("decided_by") == "non_departage"]
        if undecided:
            lines.append("  Choix non départagés par le calcul : " + ", ".join(undecided))
        passages = [f"{s['level']} {s['talent']}" for s in rep["order"] if s.get("decided_by") == "passage_palier"]
        if passages:
            lines.append("  Points de passage vers un palier (effet non modélisé) : " + ", ".join(passages))
    ns = rep.get("next_step")
    if ns is not None:
        verdict = {
            "monte_carlo": "écart significatif au Monte Carlo",
            "modelise": "à égalité, talent modélisé préféré",
            "non_departage": "choix non départagé par le calcul",
            "seul_candidat": "seul candidat légal",
        }.get(ns["decided_by"], ns["decided_by"])
        lines.append(f"Prochain talent au niveau {ns['level']} depuis le build actuel : {ns['choice']} ({verdict})")
        for r in sorted(ns["candidates"], key=lambda r: r["mean"] * (1 if not up else -1)):
            g = r["gap"]
            mark = "" if r["modeled"] else " (effet non modélisé)"
            lines.append(
                f"  {r['talent']}{mark} : {_dec(r['mean'])} {unit}, écart au meilleur {_dec(g['mean'])} "
                f"[{_dec(g['low'])} ; {_dec(g['high'])}]" + ("" if g["significant"] or g["mean"] == 0 else " (égalité)")
            )
    for name, c in rep["choices"].items():
        extra = [f"{k} {c[k]}" for k in ("ab_stacks", "ab_dump", "hs_stacks", "aoe_filler") if c.get(k) is not None]
        lines.append(
            f"Choix ({name}) : rotation {c['rotation']}, armure {c['armor']}" + "".join(f", {x}" for x in extra)
        )
    sense = "plus grand vaut mieux" if up else "plus petit vaut mieux"
    mc_text = "profil déterministe" if mt["monte_carlo"] is None else f"Monte Carlo {_dec(mt['monte_carlo'])}"
    lines.append(f"Métrique : {mt['name']} ({unit}, {sense}) : {mc_text} · analytique {_dec(mt['analytic'])}")
    lines.append("Raisons (valeur d'un point : avantage sur le meilleur autre emplacement)")
    for r in rep["reasons"]:
        if r["marginal"] is None:
            lines.append(f"  {r['name']} {r['rank']} : aucun déplacement légal du point")
            continue
        conf = f" ; Monte Carlo : {_advantage(r['confirmed'], unit, up)}" if r["confirmed"] else ""
        verdict = "à sa place" if r["marginal"] >= 0 else f"mieux placé sur {r['moved_to']}"
        lines.append(
            f"  {r['name']} {r['rank']} : {_dec(r['marginal'], 3)} {unit} ({_pct(r['relative'])}) face à "
            f"{r['moved_to']}, {verdict}{conf}"
        )
    alt = rep["alternative"]
    diff = ", ".join(f"{k} {a}→{b}" for k, (a, b) in alt["diff"].items()) if alt["diff"] else "aucune"
    who = "le build" if alt.get("better") == "build" else "l'alternative"
    lines.append(
        f"Alternative la plus proche : {diff} ; avantage du build : {_advantage(alt['gap'], unit, up)} ; "
        f"retenu : {who} ({alt['decided_by']})"
    )
    st = rep["stability"]
    names = sorted(set(st["winners"]))
    if st["stable"] and names:
        lines.append(f"Stabilité : même gagnant ({names[0]}) sur les {len(st['seeds'])} graines {st['seeds']}")
    else:
        lines.append(f"Stabilité : gagnant différent selon la graine ({st['winners']}, graines {st['seeds']})")
    lines.append("Sensibilité" + ("" if rep["sensitivity"] else " : non calculée (--sensitivity off)"))
    for row in rep["sensitivity"]:
        verdict = "tient" if row["holds"] else f"bascule vers {row['winner']}"
        lines.append(f"  {row['assumption']} : {row['value']} → {row['variant']} : {verdict} ({row['source']})")
    rs = rep["respec"]
    if rs.get("verdict") is None:
        lines.append(f"Respec : coût {_num(rs['cost_gold'])} po ({rs['cost_certainty']}) ; {rs.get('note', '')}")
    elif "gain_hours" in rs:
        lines.append(
            f"Respec : {rs['verdict']}"
            + (f" au niveau {rs['level']}" if rs["level"] else "")
            + f" ; gain {_dec(rs['gain_hours'])} h, coût {_num(rs['cost_gold'])} po ({rs['cost_certainty']}), "
            f"bilan {_dec(rs['balance_gold'], 1)} po à {_num(rs['gold_per_hour'])} po/h (suppose)"
        )
    else:
        lines.append(
            f"Respec : {rs['verdict']} ; coût {_num(rs['cost_gold'])} po ({rs['cost_certainty']}) ; avantage sur le "
            f"build {rs['reference']} : {_advantage(rs['gap'], unit, up)}"
        )
    lines.append("Angles morts" + ("" if rep["blind_spots"] else " : aucun déclaré au registre pour ce build"))
    for bs in rep["blind_spots"]:
        eff = "non chiffré" if bs["effect_pct"] is None else f"borne haute {_dec(bs['effect_pct'], 1)} %"
        talents = f" ({', '.join(bs['talents'])})" if bs["talents"] else ""
        lines.append(f"  {bs['id']}{talents} : {bs['description']} — {eff}")
    lines.append(f"Certitude : {rep['certainty']}")
    lines.append("Hypothèses")
    lines += [f"  - {a}" for a in rep["assumptions"]]
    return lines


def _cmd_build(deps: Deps, args: argparse.Namespace) -> int:
    rep = build_report(
        deps,
        args.context,
        args.level,
        race=args.race,
        current=parse_talents(args.current) or None,
        respecs=args.respecs,
        sp=args.sp,
        crit=args.crit,
        preset=args.preset,
        seed=args.seed,
        rules=args.rules,
        sensitivity=args.sensitivity == "on",
        talented_bonus=args.talented_bonus,
    )
    _emit(rep, render_build(rep), rep["provenance"], args.json)
    return EXIT_OK


def _cmd_sim(deps: Deps, args: argparse.Namespace) -> int:
    rep = simulate_leveling(
        deps,
        args.level,
        race=args.race,
        rotation=args.rotation,
        talents=parse_talents(args.talents),
        n=args.n,
        seed=args.seed,
        mob_source=args.mob_source,
        spell_level=args.spell_level,
        level_diff=args.level_diff,
        nova=args.nova,
        rules=args.rules,
        armor=args.armor,
        ab_stacks=args.ab_stacks,
        ab_dump=args.ab_dump,
        low_level_penalty=None if args.low_level_penalty is None else args.low_level_penalty == "on",
    )
    hp = rep["mob_hp"]
    gap = f"{rep['analytic_gap'] * 100:+.1f}".replace(".", ",")
    lines = [
        (
            f"Leveling niveau {rep['level']} · {rep['race']} · {rep['rotation']} · monstre niveau {hp['level']} "
            f"({_num(hp['value'])} PV, {hp['certainty']})"
        ),
        _fmt_kill(f"Monte Carlo (n = {rep['n']}, graine {rep['seed']})", rep["monte_carlo"]),
        _fmt_kill("Analytique", rep["analytic"]),
        f"  Écart analytique / Monte Carlo : {gap} %",
    ]
    st = rep["monte_carlo_stats"]
    if st is not None:
        conf = _num(st["confidence"] * 100)
        lines.insert(
            2,
            f"  Temps par monstre : {_dec(st['mean'])} s, intervalle à {conf} % [{_dec(st['low'])} ; "
            f"{_dec(st['high'])}] s (écart type {_dec(st['sd'])} s)",
        )
    _emit(rep, lines, rep["provenance"], args.json)
    return EXIT_OK


def _cmd_chart(deps: Deps, args: argparse.Namespace) -> int:
    out = Path(args.out)
    if out.resolve().is_relative_to(deps.data_dir.resolve()):
        raise InvalidArgumentError(
            f"Le graphique ne s'écrit jamais dans {deps.data_dir}.", "choisir un fichier --out hors des données"
        )
    data = load_version(deps)
    gd = build_game_data(data, rules=args.rules)
    cap = level_cap(data)
    check_level(args.level_from, cap)
    check_level(args.level_to, cap)
    if args.level_from > args.level_to:
        raise InvalidArgumentError(
            f"Plage de niveaux vide ({args.level_from} > {args.level_to}).", "donner --from ≤ --to"
        )
    if not 1 <= args.n <= MAX_N:
        raise InvalidArgumentError(f"n = {args.n} hors de 1-{MAX_N}.", f"donner un nombre de combats de 1 à {MAX_N}")
    race = args.race or DEFAULT_RACE
    check_race(data, race)
    diff = args.level_diff if args.level_diff is not None else gd.leveling.default_level_diff
    check_level(args.level_from + diff, cap, "Niveau du monstre")
    check_level(args.level_to + diff, cap, "Niveau du monstre")
    pts = parse_talents(args.talents)
    check_talents(gd, pts, args.level_to)
    options: dict[str, Any] = {
        "mob_source": args.mob_source,
        "spell_level": args.spell_level,
        "nova": args.nova,
        "rules": args.rules,
        "armor": args.armor,
        "low_level_penalty": None if args.low_level_penalty is None else args.low_level_penalty == "on",
    }
    if args.ab_stacks is not None:
        options["ab_stacks"] = args.ab_stacks
    if args.ab_dump is not None:
        options["ab_dump"] = args.ab_dump
    if args.level_diff is not None:
        options["level_diff"] = args.level_diff
    try:
        res = leveling_chart(
            gd,
            range(args.level_from, args.level_to + 1),
            pts,
            race=race,
            rotation=args.rotation,
            n=args.n,
            seed=args.seed,
            options=options,
            out=out,
        )
    except ValueError as exc:
        raise InvalidArgumentError(f"{exc}.", "voir `forever chart leveling --help`") from exc
    certainties = [cast(Certainty, p["mob_hp_certainty"]) for p in res["levels"]]
    notes = [f"niveau {o['level']} omis : {o['reason']}" for o in res["omitted"]]
    notes += [
        f"mob_source {args.mob_source}, spell_level {args.spell_level}, n = {args.n} par niveau, graine {args.seed}",
        f"rules {args.rules}, armor {args.armor}",
        "constantes leveling.* du seed sim_leveling.py (EST, suppose) ; XP de monstre : règle Classic (T04c)",
        *damage_assumptions(options, gd.constants.coefficients.low_level_default),
    ]
    provenance = local_provenance(deps, certainty=min_certainty([*certainties, "suppose"]), assumptions=notes)
    payload = {**res, "provenance": provenance}
    lines = [f"Graphique écrit : {res['path']} ({len(res['levels'])} niveaux, {len(res['omitted'])} omis)"]
    lines += [
        f"  niveau {p['level']} : Monte Carlo {_num(round(p['mc_total'], 1))} s, analytique "
        f"{_num(round(p['analytic_total'], 1))} s, XP/h {_num(round(p['xp_h']))} (PV {p['mob_hp_certainty']})"
        for p in res["levels"]
    ]
    _emit(payload, lines, provenance, args.json)
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


def _cmd_notes_post(deps: Deps, args: argparse.Namespace) -> int:
    m = re.fullmatch(r"(\d+)/(\d+)", str(args.post).strip())
    if not m:
        raise InvalidArgumentError(f"--post attend SUJET/N (ex. 2360696/3), reçu : {args.post}", "Corriger l'argument.")
    post = notes_mod.read_post(deps, int(m.group(1)), int(m.group(2)))
    provenance = local_provenance(
        deps,
        certainty="suppose",
        assumptions=[
            (
                f"message officiel n° {post['post_number']} du sujet {post['topic_id']}, révision {post['version']}"
                f" du {post['updated_at'][:10]} ({post['url']})"
            ),
            "notes officielles : signal à vérifier, jamais une valeur (docs/DATA_SOURCES.md)",
            "lecture lancée à la main (décision 148)",
        ],
    )
    lines = [
        (
            f"{post['title']} : message n° {post['post_number']}, {post['author']}, créé le {post['created_at'][:10]},"
            f" révision {post['version']} du {post['updated_at'][:10]}"
        ),
        f"  {post['url']}",
        *[f"  {line}" for line in post["lines"]],
    ]
    if post["keywords"]:
        lines.append("  registre : " + ", ".join(f"{k['registry']} ({k['keyword']})" for k in post["keywords"]))
    _emit({"post": post, "provenance": provenance}, lines, provenance, args.json)
    return EXIT_OK


def _cmd_notes(deps: Deps, args: argparse.Namespace) -> int:
    if args.post:
        return _cmd_notes_post(deps, args)
    state = None
    if args.state_from_issues:
        issues = json.loads(Path(args.state_from_issues).read_text(encoding="utf-8"))
        state = notes_mod.state_from_issues(issues if isinstance(issues, list) else [])
    result = notes_mod.read_notes(deps, state=state)
    provenance = local_provenance(
        deps,
        certainty="suppose",
        assumptions=[
            "notes officielles : signal à vérifier, jamais une valeur (docs/DATA_SOURCES.md)",
            "lecture lancée à la main (décision 148)",
        ],
    )
    if result["skipped"]:
        lines = [f"Notes officielles déjà lues le {result['last_run']} : une lecture par jour au plus."]
    else:
        lines = [f"Notes officielles : {len(result['notes'])} nouvelle(s) ou révisée(s)"]
        for n in result["notes"]:
            flag = " · problèmes connus (bugs reconnus)" if n["known_issues"] else ""
            lines.append(f"  {n['change']} : {n['title']} ({n['updated_at'][:10]}, version {n['version']}){flag}")
            lines.append(f"    {n['url']}")
            if n["keywords"]:
                lines.append("    registre : " + ", ".join(f"{k['registry']} ({k['keyword']})" for k in n["keywords"]))
    _emit({**result, "provenance": provenance}, lines, provenance, args.json)
    return EXIT_OK


def _cmd_api(deps: Deps, args: argparse.Namespace) -> int:
    keys = blizzard_api.load_keys(os.environ, Path(args.env_file))
    regions = tuple(r.strip() for r in args.region.split(",") if r.strip())
    result = blizzard_api.probe(deps, keys, regions=regions)
    provenance = local_provenance(
        deps, certainty="certain", assumptions=["sonde de l'API Blizzard : réponses HTTP seulement"]
    )
    lines = [f"API Blizzard : {len(result['responding'])} espace(s) de Forever répondent"]
    lines += [f"  {r['region']} {r['namespace']} {r['route']} : {r['status']}" for r in result["results"]]
    lines += [f"  couverture : {k} {v}" for k, v in result["coverage"].items()]
    payload = {**result, "issue_body": blizzard_api.probe_issue_body(result), "provenance": provenance}
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def _cmd_watch(deps: Deps, args: argparse.Namespace) -> int:
    result = watch(deps, report=args.report)
    provenance = local_provenance(deps, assumptions=["veille locale : rien n'est lancé, actions proposées seulement"])
    lines = [f"Veille locale ({result['wow_dir'] or 'client absent'}) : {len(result['events'])} changement(s)"]
    for e in result["events"]:
        lines.append(f"  {e['kind']} : {e['detail']}")
        lines += [
            f"    proposé : {a['command']}" + (" (réseau, sur accord)" if a["network"] else "") for a in e["actions"]
        ]
    names = {"dbcache": "DBCache.bin", "hotfix_log": "Hotfix.log"}
    lines += [
        f"  archivé : {names.get(a['kind'], a['kind'])} {a['build']} (nouvelle copie)" for a in result["archived"]
    ]
    lines += [f"  archivage : {err}" for err in result["archive_errors"]]
    _emit({**result, "provenance": provenance}, lines, provenance, args.json)
    return EXIT_OK


def _update_progress(line: str) -> None:
    """Journal de `forever update` au fil de l'eau, sur la sortie d'erreur : la sortie standard garde le seul
    rapport final (JSON intact) ; un passage détaché l'écrit dans son `run-<horodatage>.log`."""
    print(line, file=sys.stderr, flush=True)


def _cmd_update(deps: Deps, args: argparse.Namespace) -> int:
    from forever import update

    provenance = local_provenance(deps, assumptions=["mise à jour automatique : attentes et passages (T08d)"])
    if args.update_command == "status":
        summary = update.update_summary(deps.cache_dir, deps.now())
        entries = update.list_pending(deps.cache_dir)
        last = summary["last"]
        lines = [
            f"Dernier passage : {last['finished_at'] if last else 'aucun'}"
            + (f" (en cours : {summary['running_step'] or 'début'})" if summary["running"] else "")
        ]
        lines += [f"  écrit : {update.written_text(w)}" for w in (last or {}).get("written") or []]
        for e in entries:
            lines.append(
                f"  {e['id']} · {e.get('kind')} · {e.get('action')} · {e.get('state')}"
                + (f" · {'; '.join(e.get('reasons') or [])}" if e.get("reasons") else "")
            )
            if update.summary_text(e.get("summary")):
                lines.append(f"    résumé : {update.summary_text(e.get('summary'))}")
            if e.get("kind") in update.SELF_CLEARING_KINDS:
                lines.append(f"    se lève seule : {update.SELF_CLEARING_HINT}")
        if not entries:
            lines.append("  aucune attente")
        _emit({**summary, "pending": entries, "provenance": provenance}, lines, provenance, args.json)
        return EXIT_OK
    if args.update_command == "approve":
        out = update.approve(deps, args.id, wait=args.wait, progress=_update_progress)
        _emit(
            {**out, "provenance": provenance},
            [f"{out['id']} : {out['state']} · {out['detail']}"],
            provenance,
            args.json,
        )
        return EXIT_OK
    if args.update_command == "reject":
        out = update.reject(deps.cache_dir, args.id, args.reason)
        _emit({**out, "provenance": provenance}, [f"{out['id']} : {out['state']}"], provenance, args.json)
        return EXIT_OK
    only = frozenset(_split(args.only)) if args.only else frozenset()
    unknown = sorted(only - set(update.ONLY))
    if unknown:
        raise InvalidArgumentError(f"Étape inconnue : {', '.join(unknown)}.", f"choisir parmi {', '.join(update.ONLY)}")
    options = update.UpdateOptions(
        auto=args.auto, dry_run=args.dry_run, network=not args.no_network and not deps.offline, only=only
    )
    report = update.run_update(deps, options, progress=_update_progress)
    lines = [f"Mise à jour{' (simulation)' if args.dry_run else ''} : {report['started_at']} → {report['finished_at']}"]
    lines += [f"  {s['name']} : {s['status']} · {s['detail']}" for s in report["steps"]]
    for v in report["verdicts"]:
        sentence = update.summary_text(v.get("summary"))
        lines.append(
            f"  verdict {v['version']} r{v['revision']} : {v['action']}" + (f" ({sentence})" if sentence else "")
        )
    lines += [f"  écrit : {update.written_text(w)}" for w in report["written"]]
    lines += [f"  attente {p['id']} ({p['kind']}, {p['action']})" for p in report["pending"]]
    if any(p["kind"] in update.SELF_CLEARING_KINDS for p in report["pending"]):
        lines.append(f"  correctifs du serveur à lire : {update.SELF_CLEARING_HINT}")
    if any(p["kind"] not in update.SELF_CLEARING_KINDS for p in report["pending"]):
        lines.append("  voir `forever update status`, puis `forever update approve <id>`")
    _emit(report, lines, report["provenance"], args.json)  # type: ignore[arg-type]
    return update.exit_code(report)


def _cmd_addons_inventory(deps: Deps, args: argparse.Namespace) -> int:
    root = Path(args.dir) if args.dir else (deps.wow_dir / "Interface" / "AddOns" if deps.wow_dir else None)
    folder = Path(args.folder)
    if not folder.is_dir() and root is not None:
        folder = root / args.folder
    if not folder.is_dir():
        raise InvalidArgumentError(
            f"Dossier d'addon introuvable : {args.folder}.", "donner le nom du dossier et --dir, ou un chemin"
        )
    report = addons_inventory(folder)
    provenance = local_provenance(
        deps, certainty="suppose", assumptions=["inventaire d'un addon : métadonnées et empreintes, aucune valeur"]
    )
    lic = report["license"]
    lines = [
        f"Inventaire de {report['folder']} {report['toc'].get('Version', '?')} (empreinte {report['fingerprint']})",
        f"  titre : {report['toc'].get('Title', '?')} ; interface : {report['toc'].get('Interface', '?')}",
        f"  licence : {lic['source'] + (' ' + lic['name'] if lic.get('name') else '') if lic else 'aucune'}",
        f"  SavedVariables : {', '.join(report['saved_variables']) or 'aucune'}",
        f"  fichiers de données : {report['files']['count']} ({report['files']['total_size']} octets)",
    ]
    lines += [f"    {f['path']} : {' / '.join(f['header'])}" for f in report["files"]["list"] if f["header"]]
    lines += [f"  table {name} : {len(keys)} clé(s)" for name, keys in report["globals"].items()]
    _emit({**report, "provenance": provenance}, lines, provenance, args.json)
    return EXIT_OK


def _cmd_addons(deps: Deps, args: argparse.Namespace) -> int:
    if args.addons_command == "inventory":
        return _cmd_addons_inventory(deps, args)
    report = addons_status(deps, save=args.save, addons_dir=Path(args.dir) if args.dir else None)
    provenance = local_provenance(
        deps, certainty="suppose", assumptions=["addons communautaires : versions et empreintes, lecture locale"]
    )
    lines = [
        f"Addons de données ({report['addons_dir'] or 'dossier absent'}){' : relevé enregistré' if args.save else ''}"
    ]
    for a in report["addons"]:
        if a["status"] == "absent":
            lines.append(f"  {a['name']} : absent")
            continue
        files = a["files"]
        detail = ", ".join(f"{k} {len(v)}" for k, v in files.items() if v)
        lines.append(
            f"  {a['name']} {a.get('version') or '?'} : {a['status']} (empreinte {a['fingerprint']}"
            + (f" ; fichiers {detail}" if detail else "")
            + ")"
        )
        if a.get("aggregates_diff"):
            lines.append(
                f"    agrégats changés : {len(a['aggregates_diff'])} ; dépendants : {', '.join(a.get('depends', []))}"
            )
        if a.get("content_version"):
            content = ", ".join(f"{k} {v}" for k, v in a["content_version"].items())
            lines.append(f"    contenu : {content}")
        export = (a.get("recheck") or {}).get("export")
        if export:
            blocked = [
                f"{n} ({', '.join(e['talents'])})" for n, e in sorted(export.items()) if e["status"] != "possible"
            ]
            possible = sum(1 for e in export.values() if e["status"] == "possible")
            lines.append(
                f"    export Talents Forever : possible pour {possible} classe(s)"
                + (f" ; bloqué : {', '.join(blocked)}" if blocked else "")
            )
        if a.get("proposal"):
            lines.append("    attente proposée (addon_data) : un agrégat du dépôt en dépend")
        if a["status"] == "changé" and a.get("action"):
            lines.append(f"    action proposée : {a['action']}")
    labels = {
        "interface": "interface seule",
        "pas_un_addon": "pas un addon",
        "non_inventorié": "non inventorié",
        "sauvegarde": "copie de sauvegarde, non lue",
    }
    for u in report.get("untracked", []):
        lines.append(
            f"  {u['folder']} {u.get('version') or ''} : {labels.get(u['status'], u['status'])}".replace("  :", " :")
            + (f" ({u['action']})" if u.get("action") else "")
        )
    payload = {**report, "provenance": provenance}
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def _cmd_hotfixes(deps: Deps, args: argparse.Namespace) -> int:
    log = Path(args.log) if args.log else (deps.wow_dir.joinpath(*hotfixes.HOTFIX_LOG) if deps.wow_dir else None)
    version = current_identity(deps.data_dir).game_version
    _, rules = load_rules(deps.data_dir)
    new: list[dict[str, Any]] = []
    if log is not None and log.is_file():
        build = read_build_info(deps.wow_dir) if deps.wow_dir else None
        lines = hotfixes.read_log(log)
        new = hotfixes.update_journal(
            deps.cache_dir, lines, hotfixes.tracked_tables(rules), build.build if build else None, deps.now()
        )
    entries = hotfixes.load_journal(deps.cache_dir)
    sources = read_sources(deps.data_dir, version) or {}
    since = str(sources.get("revised_at") or sources.get("collected_at") or "") if args.since_install else None
    kept = [e for e in entries if since is None or str(e["at"])[:10] >= since]
    summary = hotfixes.summarize(entries, since=since)
    csv_dir = wago_dir(deps.cache_dir, version) / DEFAULT_LOCALE
    entities = hotfixes.touched_entities(kept, csv_dir, deps.data_dir / version)
    notes = ["VALIDATION_RESULT_INVALID compté à part : sens non établi (docs/OPEN_QUESTIONS.md)"]
    if log is None or not log.is_file():
        notes.append(f"journal {log or 'Hotfix.log'} absent : journal du cache seulement")
    cache_path = _dbcache_path(deps, args.dbcache)
    cache_block: dict[str, Any] | None = None
    if cache_path is not None and cache_path.is_file():
        cache = dbcache.read_dbcache(cache_path)
        log_tables = {ln.table for ln in lines} if log is not None and log.is_file() else set()
        names = dbcache.table_names(dbcache.known_tables(rules) | log_tables)
        check = dbcache.crosscheck(cache.entries, names, entries, cache.build, hotfixes.tracked_tables(rules))
        cache_block = {
            "path": str(cache_path),
            **dbcache.summarize_cache(cache, names),
            "crosscheck": check._asdict(),
        }
        notes.append(
            f"valeurs de DBCache.bin lues (build {cache.build}), appliquées seulement par forever decode --hotfixes"
        )
        if not version.endswith(f".{cache.build}"):
            notes.append(f"DBCache.bin du build {cache.build}, version installée {version} : non applicable")
        elif args.values:
            layouts, dbd = _dbd_layouts(deps, args.dbd_layouts, version, rules)
            source = hotfix_source(cache_path, layouts, dbd, entries, version, rules, format_utc(deps.now()))
            values_dir = Path(args.csv_dir) if args.csv_dir else wago_dir(deps.cache_dir, version)
            cache_block["values"] = hotfix_values(source, values_dir, deps.data_dir / version)
    else:
        notes.append(f"DBCache.bin non lu ({cache_path or 'FOREVER_WOW_DIR absent'}) : valeurs des correctifs non lues")
    provenance = local_provenance(deps, certainty="probable", assumptions=notes)
    payload = {
        "log": str(log) if log else None,
        "new": len(new),
        "summary": summary,
        "entities": entities,
        "dbcache": cache_block,
        "provenance": provenance,
    }
    if cache_block is not None and "values" in cache_block:
        payload["values"] = cache_block.pop("values")
    head = f"Correctifs du serveur ({'depuis le ' + since if since else 'tous'}) : {summary['lines']} ligne(s), {len(new)} nouvelle(s)"
    lines_out = [head]
    lines_out += [
        f"  {t} : {s['valid']} VALID, {s['delete']} DELETE, plages {s['ranges'][:5]}"
        for t, s in summary["tables"].items()
    ]
    if summary["invalid"]:
        lines_out.append(
            "  INVALID (sens non établi) : " + ", ".join(f"{t} {n}" for t, n in summary["invalid"].items())
        )
    lines_out += [f"  touché : {e['kind']} {e['key']} (le {e['date']})" for e in entities]
    if cache_block is not None:
        cc = cache_block["crosscheck"]
        lines_out.append(
            f"DBCache.bin (build {cache_block['build']}, {cache_block['entries']} entrées, "
            f"sha256 {cache_block['sha256'][:12]}…) : poussées {cache_block['pushes']}"
        )
        lines_out += [
            f"  {t} : " + ", ".join(f"{n} {s}" for s, n in row.items()) for t, row in cache_block["tables"].items()
        ]
        lines_out.append(
            f"  recoupement avec le journal : {cc['matched']} ligne(s) concordante(s), "
            f"{len(cc['only_log'])} seulement dans le journal, {len(cc['only_cache'])} seulement dans DBCache.bin"
        )
        if cache_block["dbreply"] or cache_block["item_reply"]:
            lines_out.append(
                f"  réponses à la demande (jamais appliquées) : DBReply {sum(cache_block['dbreply'].values())}, "
                f"objets {sum(cache_block['item_reply'].values())}"
            )
        if cache_block["unknown_hash"]:
            lines_out.append(f"  tables hors du projet (hachage inconnu) : {len(cache_block['unknown_hash'])}")
    if "values" in payload:
        lines_out += _values_lines(cast(dict[str, Any], payload["values"]))
    _emit(payload, lines_out, provenance, args.json)
    return EXIT_OK


def _values_lines(values: Mapping[str, Any]) -> list[str]:
    lines = [f"Valeurs des correctifs (build {values['build']}) : {len(values['records'])} enregistrement(s)"]
    for r in values["records"]:
        seen = f"vu le {str(r['seen_at'])[:10]} {str(r['seen_at'])[11:16]}" if r["seen_at"] else "date inconnue"
        head = f"  {r['table']} {r['rec_id']} {r['status']} ({r['push']}, {seen})"
        if r["status"] == "DELETE":
            body = "ligne retirée"
        elif r["identical"]:
            body = "identique au build"
        elif r["new"]:
            body = "ligne ajoutée : " + ", ".join(f"{f['field']} {f['hotfix']}" for f in r["fields"][:6])
        else:
            body = ", ".join(f"{f['field']} {f['build']} → {f['hotfix']}" for f in r["fields"])
        who = f" · {', '.join(r['entities'][:3])}" if r["entities"] else ""
        lines.append(f"{head} : {body}{who}")
    listed = values["listed"]
    lines.append(
        f"  non appliqués : INVALID {len(listed['invalid'])}, NOTPUBLIC {len(listed['notpublic'])}, "
        f"DBReply {sum(listed['dbreply'].values())}, réponses d'objets {sum(listed['item_reply'].values())}, "
        f"hachages inconnus {len(listed['unknown_hash'])}, dispositions non validées {len(listed['unvalidated'])}, "
        f"tables non lues {', '.join(listed['not_loaded']) or 'aucune'}"
    )
    return lines


def _dbd_layouts(
    deps: Deps, option: str | None, version: str, rules: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Dispositions : fichier dérivé (`--dbd-layouts`) ou relevé de WoWDBDefs du cache (`forever fetch --dbd`)."""
    if option:
        doc = json.loads(Path(option).read_text(encoding="utf-8"))
        if doc.get("build") != version:
            raise InvalidArgumentError(
                f"Dispositions du build {doc.get('build')}, version demandée {version} : jamais un build voisin.",
                "donner les dispositions du même build, ou relever WoWDBDefs : forever fetch --dbd",
            )
        return layouts_from_json(doc), {"repo": doc.get("repo"), "commit": doc.get("commit"), "files": {}}
    return load_dbd_layouts(deps.cache_dir, version, dbd_tables(rules))


def _dbcache_path(deps: Deps, option: str | None) -> Path | None:
    """`--dbcache`, sinon `<FOREVER_WOW_DIR>/Cache/ADB/enUS/DBCache.bin` ; None sans dossier du client."""
    if option:
        return Path(option)
    if deps.wow_dir is None:
        return None
    return deps.wow_dir.joinpath(*(part.format(locale=DEFAULT_LOCALE) for part in dbcache.DBCACHE_PATH))


def _cmd_origins(deps: Deps, args: argparse.Namespace) -> int:
    provenance = local_provenance(deps)
    if args.origins_command == "check":
        report = check_origins(deps.data_dir)
        payload = {
            "ok": report.ok,
            "versions": report.versions,
            "leaves": report.leaves,
            "by_origin": report.by_origin,
            "issues": [i.__dict__ for i in report.issues],
            "provenance": provenance,
        }
        _emit(payload, render_origins_report(report), provenance, args.json)
        return EXIT_OK if report.ok else EXIT_INTEGRITY
    version = args.version or current_identity(deps.data_dir).game_version
    rows, pending = origins_inventory(deps.data_dir, version)
    if args.markdown and not args.json:
        print(render_inventory(version, rows, pending), end="")
        return EXIT_OK
    payload = {**inventory_payload(version, rows, pending), "provenance": provenance}
    lines = [
        (
            f"Valeurs écrites à la main ({version}) : {len(rows)} chemins, {payload['leaves']} valeurs, "
            f"{len(pending)} abaissement(s) de certitude prévu(s)"
        ),
        *[f"  attente  {p.file} {p.path} : {p.declared} -> {p.target} ({p.until})" for p in pending],
        *[f"  {r.certainty:<8} {r.file} {r.path} : {r.reason}" for r in rows],
    ]
    _emit(payload, lines, provenance, args.json)
    return EXIT_OK


def _default_sv(deps: Deps) -> Path | None:
    """Premier dossier `WTF/Account/*/SavedVariables` du client, s'il existe."""
    if deps.wow_dir is None:
        return None
    found = sorted((deps.wow_dir / "WTF" / "Account").glob("*/SavedVariables"))
    return found[0] if found else None


def _refresh_lines(sources: RefreshSources, diff: Mapping[str, Any], status: str) -> list[str]:
    logs, npcs, b1 = diff["logs"], diff["npcs"], diff["b1"]
    lines = [
        (
            f"Journaux : {len(sources.logs)} trouvés · nouveaux {', '.join(logs['new']) or 'aucun'} · modifiés "
            f"{', '.join(logs['modified']) or 'aucun'} · disparus {', '.join(logs['gone']) or 'aucun'}"
        ),
        f"SavedVariables : {', '.join(p.name for p in sources.saved_variables) or 'aucune'}",
        (
            f"PNJ : {len(npcs['added'])} ajoutés, {len(npcs['changed'])} changés, {len(npcs['kept'])} conservés "
            "(journal disparu)"
        ),
        f"PNJ retirés : {', '.join(npcs['removed']) or 'aucun'}",
        f"PV par niveau : {len(diff['hp_by_level'])} niveau(x) changé(s)",
    ]
    for level, change in sorted(diff["hp_by_level"].items(), key=lambda kv: int(kv[0])):
        lines.append(f"  niveau {level} : {change['before']} -> {change['after']}")
    corr = diff["questie_correction"]
    if corr["before"] != corr["after"]:
        lines.append(f"Correction Questie : {corr['before']} -> {corr['after']}")
    measured, proof = b1["measured"], b1["registry"]
    if measured.get("n", 0) >= 2:
        lines.append(
            f"B1 : n = {measured['n']}, médiane {_num(round(measured['median_s'], 4))} s, 10e percentile "
            f"{_num(round(measured['p10_s'], 4))} s ; registre n = {proof['n'] if proof else '?'} : "
            + ("identique" if b1["same"] else "écart, bloc proposé ci-dessous (à reporter à la main)")
        )
        if not b1["same"]:
            lines += ["  " + line for line in b1["proposed"].splitlines()]
    else:
        lines.append("B1 : pas assez d'intervalles")
    a3 = diff["a3"]["measured"]
    lines.append(
        f"A3 : {sum(r['hits'] for r in a3)} touchés, {sum(r['misses'] for r in a3)} ratés sur {len(a3)} écart(s) "
        f"({diff['a3']['note']})"
    )
    changed = diff["measures"]["changed"]
    if diff["measures"]["first_snapshot"]:
        lines.append("Coûts, incantations, critiques : premier instantané")
    else:
        lines.append(
            "Coûts, incantations, critiques : "
            + (" ; ".join(f"{k} {', '.join(v)}" for k, v in changed.items() if v) or "inchangés")
        )
    ignite = diff["ignite"]
    lines.append(f"Ignite (règle {ignite['rule']}) : {ignite['note']}")
    for e in ignite["episodes"]:
        lines.append(
            f"  {len(e['crits'])} critique(s), {len(e['ticks'])} tic(s), part {_num(round(e['part'], 3))} : écart "
            f"règle {_num(round(e['rolling']['max_time_gap_s'], 3))} s, variante "
            f"{_num(round(e['keep_timer']['max_time_gap_s'], 3))} s"
        )
    lines.append(f"Résultat : {status}")
    return lines


def _cmd_measures_refresh(deps: Deps, args: argparse.Namespace) -> int:
    logs_dir = _wow_path(deps, args.logs, "Logs")
    sv_dir = Path(args.sv) if args.sv else _default_sv(deps)
    questie_dir = Path(args.questie) if args.questie else None
    if questie_dir is None and deps.wow_dir is not None:
        default = deps.wow_dir / "Interface" / "AddOns" / "Questie"
        questie_dir = default if default.is_dir() else None
    sources = collect_sources(logs_dir, sv_dir)
    # Décision 205 : un journal que le jeu ouvert écrit encore n'est pas mesuré, il est reproposé au passage suivant.
    ready, writing = split_live(sources.logs, now=deps.now(), running=deps.game_running())
    sources = sources._replace(logs=tuple(ready))
    data = load_version(deps)
    gd = build_game_data(data)
    installed = data.read_json(MONSTERS_FILE)
    questie = read_questie(questie_dir) if questie_dir else None
    try:
        curve = curve_exclusions(installed, args.curve_exclude, args.curve_exclude_reason)
    except ValueError as exc:
        raise InvalidArgumentError(str(exc), "donner --curve-exclude-reason TEXTE") from exc
    excluded = (installed.get("questie_correction") or {}).get("excluded", [])
    fit_exclude = (
        args.fit_exclude
        if args.fit_exclude is not None
        else sorted({int(e["npc_id"]) for e in excluded} - set(curve))  # PNJ hors norme : liste à part
    )
    offset = timedelta(hours=args.utc_offset) if args.utc_offset is not None else None
    # Une mesure n'est jamais attribuée à une autre version du jeu (T08a, décision 135) : seuls les journaux écrits
    # sous la version installée sont mesurés, les autres attendent son installation.
    builds = _client_builds(deps)
    starts = {s.name: s.start for s in scan_logs(logs_dir)}
    keep, held, unknown = split_by_version(
        [(p.name, starts.get(p.name)) for p in sources.logs], builds, data.game_version, utc_offset=offset
    )
    sources = sources._replace(logs=tuple(p for p in sources.logs if p.name in keep))
    new = remeasure(
        gd,
        sources,
        questie,
        version=data.game_version,
        installed=installed,
        fit_exclude=fit_exclude,
        curve_exclude=curve,
        utc_offset=offset,
    )
    if unknown:
        new["notes"].append(
            f"version du client inconnue pour {len(unknown)} journal/journaux ({', '.join(unknown)}) : "
            "antérieurs au premier relevé de .build.info, mesurés sans garantie qu'ils viennent de la version "
            f"installée ({data.game_version})"
        )
    for h in held:
        new["notes"].append(f"{h.name} retenu : {h.reason}")
    previous = read_snapshot(deps.cache_dir)
    if previous is None and snapshot_exists(deps.cache_dir):
        new["notes"].append("instantané illisible (<cache>/measures/last.json) : traité comme un premier instantané")
    diff = compare(installed, registry.load(deps.registry_path), previous, new)
    diff["measures"]["held_back"] = [h._asdict() for h in held]
    diff["curve_candidates"] = curve_candidates(new["monsters"], questie)  # proposés, jamais écartés sans accord
    written: list[Path] = []
    if not diff["changed"]:
        status = "rien à écrire"
    elif args.dry_run:
        status = "simulation"
    elif args.yes or (deps.confirm is not None and deps.confirm("Écrire ces changements ? [o/N] ")):
        written = apply_refresh(new, deps.data_dir, deps.cache_dir, date=format_utc(deps.now())[:10])
        status = "écrit"
    else:
        status = "refusé"
    notes = [*new["notes"], "PV des monstres : bloc avancé des journaux (mesure) ; preuves du registre jamais écrites"]
    if writing:
        notes.append(writing_note(writing))
    if questie is not None:
        notes.append(QUESTIE_NOTE)
    provenance = local_provenance(deps, certainty="suppose" if questie is not None else "probable", assumptions=notes)
    payload = {
        "status": status,
        "sources": {
            "logs": [p.name for p in sources.logs],
            "saved_variables": [p.name for p in sources.saved_variables],
        },
        "diff": diff,
        "written": [str(p) for p in written],
        "writing": writing,
        "provenance": provenance,
    }
    lines = _refresh_lines(sources, diff, status)
    lines += [
        f"  {w['name']} en cours d'écriture · modifié il y a {w['age_s'] // 60} min, jeu ouvert · reproposé au "
        "passage suivant"
        for w in writing
    ]
    lines += [f"  {h.name} retenu · client {h.client_version} · {h.reason}" for h in held]
    for c in diff["curve_candidates"]:
        where = "absent de Questie" if c["spawn_points"] is None else f"{c['spawn_points']} point(s) d'apparition"
        levels = ", ".join(
            f"niveau {lv['level']} : {lv['max_hp']} PV (courbe {lv['curve'] if lv['curve'] is not None else '?'})"
            for lv in c["levels"]
        )
        lines.append(
            f"  candidat à l'écartement · {c['name']} ({c['npc_id']}) · {where} · {levels} · "
            "--curve-exclude après accord"
        )
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


def _cmd_hook(deps: Deps, args: argparse.Namespace) -> int:
    """Hook du plugin : entrée JSON sur stdin, sortie JSON (ou rien) sur stdout, toujours le code 0."""
    from forever.hooks import check_numbers_output, session_start_output

    try:
        # Octets décodés en UTF-8 : sous Windows, sys.stdin suit l'encodage local (cp1252) sans PYTHONUTF8.
        raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
        hook_input = json.loads(raw.decode("utf-8", errors="replace") or "{}")
    except (ValueError, OSError):
        hook_input = {}
    if not isinstance(hook_input, dict):
        hook_input = {}
    if args.hook_name == "session-start":
        from forever.spawn import spawn_detached
        from forever.update import update_dir

        stamp = "".join(c for c in format_utc(deps.now()) if c.isalnum())
        log = update_dir(deps.cache_dir) / f"run-{stamp}.log"
        out = session_start_output(hook_input, deps, os.environ, spawn=lambda args: spawn_detached(args, log))
    else:
        out = check_numbers_output(hook_input)
    if out is not None:
        print(json.dumps(out, ensure_ascii=False))
    return EXIT_OK


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
    if args.command == "hook":
        return _cmd_hook(deps, args)
    handlers = {
        "status": _cmd_status,
        "lookup": _cmd_lookup,
        "explain-mechanic": _cmd_explain,
        "manifest": _cmd_manifest,
        "builds": _cmd_builds,
        "fetch": _cmd_fetch,
        "decode": _cmd_decode,
        "install": _cmd_install,
        "profile": _cmd_profile,
        "pvp": _cmd_pvp,
        "pets": _cmd_pets,
        "talents": _cmd_talents,
        "diff": _cmd_diff,
        "verify": _cmd_verify,
        "report": _cmd_report,
        "logs": _cmd_logs,
        "questie": _cmd_questie_info,
        "origins": _cmd_origins,
        "hotfixes": _cmd_hotfixes,
        "addons": _cmd_addons,
        "watch": _cmd_watch,
        "update": _cmd_update,
        "notes": _cmd_notes,
        "api": _cmd_api,
        "monsters": _cmd_monsters_build,
        "measures": _cmd_measures_refresh,
        "sim": _cmd_sim,
        "chart": _cmd_chart,
        "build": _cmd_build,
    }
    try:
        return handlers[args.command](deps, args)
    except ForeverError as err:
        return _emit_error(deps, err, getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
