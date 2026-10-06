"""Chaîne `forever update` (T08d, bloc E, décisions 178 à 180), hors ligne.

Montage (relevé pendant l'exécution du bloc, 2026-10-06) : une copie des données ramenée à la version des extraits des
9 classes (`CLASS_FIXTURE_VERSION`), sur laquelle une version fictive `1.60.1.79998` est installée depuis ces extraits
(`forever install --new-version`). Le client est à `1.60.1.79999`, publié par wago (`FakeHttp` à routes : liste des
builds, CSV et GameTables servis depuis `tests/fixtures/wago/1.60.1.70124/`). Mêmes tables : la version installée
après coup ne diffère que par ses métadonnées. La preuve d'entrées et le report à la main se font donc sur la
version **installée dans une copie de préparation**, jamais sur la candidate brute (qui porte la lecture du client
avant la fusion des talents et des sorts).

Deux changements de CSV, choisis par sonde : le coefficient de dégâts de Frostbolt (`SpellEffect`, sort 116) passe
l'installation et ne touche que les deux moteurs du Mage (une feuille de `spell_scaling.json`) ; son coût de mana
(`SpellPower`) est refusé par les règles de fusion de `forever install`. Aucune valeur de jeu n'est affirmée : les
tests comparent des comptes et des statuts."""

import csv
import io
import json
import os
import shutil
from datetime import UTC, datetime, timedelta

import pytest
from conftest import (
    CLASS_FIXTURE_VERSION,
    DATA_DIR,
    FIXTURES,
    LOCAL_VERSION,
    NOW,
    WAGO_70124,
    FakeHttp,
    isolated_deps,
    read_json,
    rewind_to,
)

from forever.cli import main
from forever.engine_inputs import ENGINES
from forever.errors import EXIT_PENDING
from forever.manifest import version_files, write_manifest
from forever.pipeline.builds import BUILDS_URL
from forever.pipeline.client_builds import ClientBuild, record_build
from forever.pipeline.decode import decode_version, load_rules
from forever.pipeline.fetch import gametable_url, table_url
from forever.pipeline.install import apply_install
from forever.update import STEPS, UpdateOptions, UpdateReport, acquire_lock, run_update, update_dir

BASE = "1.60.1.79998"
TARGET = "1.60.1.79999"
NEWER = "1.60.1.80000"
HEADER = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"
PRODUCT = "wow_classic_beta"
FIXTURE_VERSION = "1.60.1.70170"  # build des fixtures DBCache.bin, dispositions et tables (décision 192)
DRY = UpdateOptions(dry_run=True)
MAGE = {"mage_build", "mage_leveling"}


def set_build_info(wow, version):
    path = wow.parent / ".build.info"
    path.write_text(f"{HEADER}\nus|1|{version}|{PRODUCT}\n", encoding="utf-8")
    stamp = datetime(2026, 9, 26, 12, 0, tzinfo=UTC).timestamp()
    os.utime(path, (stamp, stamp))


def builds_body(*versions):
    return json.dumps({PRODUCT: [{"version": v, "created_at": "2026-09-26T00:00:00Z"} for v in versions]}).encode()


def perturb(body: bytes, spell: str, column: str) -> bytes:
    """Premier enregistrement du sort dont la colonne n'est pas nulle : valeur doublée (décimale) ou +1000 (entière)."""
    rows = list(csv.reader(io.StringIO(body.decode("utf-8"))))
    head = rows[0]
    key, col = head.index("SpellID"), head.index(column)
    for row in rows[1:]:
        if row[key] == spell and row[col] not in ("0", "0.0"):
            row[col] = str(float(row[col]) * 2) if "." in row[col] else str(int(row[col]) + 1000)
            break
    else:
        raise AssertionError(f"sort {spell} sans {column} non nul")
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().encode("utf-8")


def wago_routes(version, change=None):
    """Tables et GameTables de `version`, servies depuis l'extrait 70124 ; `change` : (table, sort, colonne)."""
    routes = {}
    for locale_dir in (d for d in WAGO_70124.iterdir() if d.is_dir() and d.name != "gametables"):
        for path in locale_dir.glob("*.csv"):
            body = path.read_bytes()
            if change and locale_dir.name == "enUS" and path.stem == change[0]:
                body = perturb(body, change[1], change[2])
            routes[table_url(path.stem, version, locale_dir.name)] = body
    rules = load_rules(DATA_DIR)[1]
    for name, file_id in rules["gametables"].items():
        routes[gametable_url(file_id, version)] = (WAGO_70124 / "gametables" / f"{name}.txt").read_bytes()
    return routes


@pytest.fixture
def montage(tmp_path, make_deps):
    """Fabrique : (deps, http) avec la base 79998 installée, le client à `client`, wago publiant `published`."""
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    rewind_to(data, CLASS_FIXTURE_VERSION)
    base_deps = isolated_deps(tmp_path, data)
    shutil.copytree(WAGO_70124, base_deps.cache_dir / "wago" / BASE)
    apply_install(base_deps, str(decode_version(base_deps, BASE).root), motif="montage", new_version=True)
    shutil.rmtree(base_deps.cache_dir / "wago" / BASE)
    shutil.rmtree(base_deps.cache_dir / "candidates")
    wow = tmp_path / "World of Warcraft" / "_classic_beta_"
    (wow / "Logs").mkdir(parents=True)

    def factory(client=TARGET, published=(BASE, TARGET), change=None, now=NOW):
        set_build_info(wow, client)
        routes = {BUILDS_URL: builds_body(*published)}
        for version in published:
            if version != BASE:
                routes.update(wago_routes(version, change))
        http = FakeHttp(routes=routes)
        return make_deps(data_dir=data, cache_dir=base_deps.cache_dir, wow_dir=wow, http=http, now=now), http

    return factory


def step(report, name):
    found = [s for s in report["steps"] if s["name"] == name]
    assert len(found) == 1, [s["name"] for s in report["steps"]]
    return found[0]


def only_verdict(report):
    assert len(report["verdicts"]) == 1, report["verdicts"]
    return report["verdicts"][0]


class Replay:
    """Rejeu simulé (aucun Monte Carlo) : garde chaque appel (moteur, cas, dossier des données)."""

    def __init__(self):
        self.calls = []

    def __call__(self, engine, case, data_dir):
        self.calls.append((engine, case, data_dir))
        return {"engine": engine, "case": case}


# --- Chaîne complète en simulation ----------------------------------------------------------------------------


def test_steps_come_in_order(montage):
    deps, _ = montage()
    report = run_update(deps, DRY, replay=Replay())
    assert [s["name"] for s in report["steps"]] == list(STEPS)
    assert set(report) == set(UpdateReport.__annotations__)
    assert report["schema_version"] == 1


def test_same_tables_give_identical_inputs_and_write(montage):
    deps, _ = montage()
    replay = Replay()
    report = run_update(deps, DRY, replay=replay)
    assert step(report, "jeu")["data"]["target"] == TARGET
    assert step(report, "nouvelle_version")["status"] == "fait"
    verdict = only_verdict(report)
    assert verdict["kind"] == "install_version" and verdict["version"] == TARGET
    assert verdict["action"] == "écrire"
    assert verdict["clauses"] == {"verify": True, "install": True, "manual": True, "inputs": True}
    assert verdict["carry"]["perdu"] == 0 and verdict["carry"]["remplacé"] == 0 and verdict["carry"]["gardé"] > 0
    assert all(e["identical"] for e in verdict["inputs"].values())
    assert set(verdict["inputs"]) == set(ENGINES)
    assert replay.calls == []  # aucun moteur touché : rien à rejouer
    assert report["pending"] == [] and report["written"] == []


def test_dry_run_writes_nothing_in_the_data_nor_in_the_pending(montage):
    deps, _ = montage(change=("SpellEffect", "116", "EffectBonusCoefficient"))
    before = version_files(deps.data_dir / BASE)
    manifest = (deps.data_dir / "manifest.json").read_bytes()
    report = run_update(deps, DRY, replay=Replay())
    assert report["pending"]  # rendue…
    assert not (update_dir(deps.cache_dir) / "pending").exists()  # … sans être enregistrée
    assert version_files(deps.data_dir / BASE) == before
    assert (deps.data_dir / "manifest.json").read_bytes() == manifest
    assert not (deps.data_dir / TARGET).exists()
    assert not (update_dir(deps.cache_dir) / "repo").exists()
    assert not (update_dir(deps.cache_dir) / "last.json").exists()


def test_a_mage_value_changed_by_the_client_waits_with_a_targeted_replay(montage):
    deps, _ = montage(change=("SpellEffect", "116", "EffectBonusCoefficient"))
    replay = Replay()
    report = run_update(deps, DRY, replay=replay)
    verdict = only_verdict(report)
    assert verdict["action"] == "attente"
    assert {k for k, ok in verdict["clauses"].items() if not ok} == {"inputs"}
    assert {e for e, d in verdict["inputs"].items() if not d["identical"]} == MAGE
    changed = [i for i in verdict["inputs"]["mage_build"]["items"] if i["status"] == "différent"]
    assert [(i["file"], i["leaves"]) for i in changed] == [("spell_scaling.json", 1)]
    assert step(report, "nouvelle_version")["status"] == "attente"
    # rejeu ciblé : chaque cas des deux moteurs du Mage, avant et après, aucun cas des rendements décroissants
    expected = {(e, c) for e in MAGE for c in ENGINES[e].cases}
    assert {(e, c) for e, c, _ in replay.calls} == expected
    assert len(replay.calls) == 2 * len(expected)
    assert set(verdict["replay"]) == MAGE
    (entry,) = report["pending"]
    assert entry["kind"] == "install_version" and entry["action"] == "attente"
    assert entry["id"].startswith(f"{TARGET}-r1-") and entry["clauses"] == verdict["clauses"]


def test_an_install_refused_by_the_merge_rules_is_blocked(montage):
    deps, _ = montage(change=("SpellPower", "116", "ManaCost"))
    report = run_update(deps, DRY, replay=Replay())
    verdict = only_verdict(report)
    assert verdict["action"] == "bloqué"
    assert verdict["clauses"]["install"] is False
    assert step(report, "nouvelle_version")["status"] == "arrêt"
    assert [e["action"] for e in report["pending"]] == ["bloqué"]


def test_client_build_missing_from_wago_waits_without_fetching(montage):
    deps, http = montage(published=(BASE,))
    report = run_update(deps, DRY, replay=Replay())
    game = step(report, "jeu")
    assert game["status"] == "rien" and "en attente de wago" in game["detail"]
    assert step(report, "nouvelle_version")["status"] == "rien"
    assert report["verdicts"] == []
    assert [url for url, _, _ in http.calls] == [BUILDS_URL]


def test_a_newer_wago_build_is_reported_but_the_client_build_is_the_target(montage):
    deps, _ = montage(published=(BASE, TARGET, NEWER))
    report = run_update(deps, DRY, replay=Replay())
    game = step(report, "jeu")
    assert game["data"]["target"] == TARGET
    assert game["data"]["newer_on_wago"] == NEWER
    assert NEWER in game["detail"]
    assert only_verdict(report)["version"] == TARGET


def test_no_network_skips_the_clone_and_the_game(montage):
    deps, http = montage()
    report = run_update(deps, UpdateOptions(dry_run=True, network=False), replay=Replay())
    assert step(report, "clone")["status"] == "rien"
    assert step(report, "jeu")["status"] == "rien"
    assert report["verdicts"] == []
    assert http.calls == []


def test_only_restricts_the_steps_that_run(montage):
    deps, http = montage()
    report = run_update(deps, UpdateOptions(dry_run=True, only=frozenset({"addons"})), replay=Replay())
    assert [s["name"] for s in report["steps"]] == list(STEPS)
    for name in ("jeu", "nouvelle_version", "correctifs", "journaux"):
        assert step(report, name)["status"] == "rien", name
    assert http.calls == []


# --- Verrou --------------------------------------------------------------------------------------------------


def test_a_live_lock_stops_the_run(montage):
    deps, http = montage()
    assert acquire_lock(deps, "forever update --auto") is None
    report = run_update(deps, DRY, replay=Replay())
    assert [s["name"] for s in report["steps"]] == ["verrou"]
    assert report["steps"][0]["status"] == "arrêt" and "déjà en cours" in report["steps"][0]["detail"]
    assert http.calls == []


def test_a_stale_lock_is_taken_over_and_released_at_the_end(montage):
    deps, _ = montage()
    old, _ = montage(now=NOW - timedelta(hours=4))
    assert acquire_lock(old, "forever update --auto") is None
    report = run_update(deps, DRY, replay=Replay())
    lock = step(report, "verrou")
    assert lock["status"] == "fait" and lock["data"]["stale"] is True
    assert [s["name"] for s in report["steps"]] == list(STEPS)
    assert acquire_lock(deps, "forever update") is None  # libéré en fin de passage


# --- CLI ------------------------------------------------------------------------------------------------------


def test_cli_json_exit_codes(montage, capsys):
    deps, _ = montage()
    assert main(["update", "--dry-run", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(UpdateReport.__annotations__) <= set(payload)
    assert payload["provenance"]["game_version"] == BASE
    assert payload["provenance"]["certainty"] in ("certain", "probable", "suppose")

    shutil.rmtree(deps.cache_dir / "wago" / TARGET)  # tables relevées au premier passage : jamais retéléchargées
    deps, _ = montage(change=("SpellEffect", "116", "EffectBonusCoefficient"))
    assert main(["update", "--dry-run", "--json", "--only", "jeu"], deps) == EXIT_PENDING
    assert json.loads(capsys.readouterr().out)["pending"]


def test_cli_text_names_the_verdict(montage, capsys):
    deps, _ = montage(change=("SpellEffect", "116", "EffectBonusCoefficient"))
    assert main(["update", "--dry-run"], deps) == EXIT_PENDING
    out = capsys.readouterr().out
    assert "attente" in out and TARGET in out and "forever update status" in out


# --- Correctifs du serveur (révision suivante) ----------------------------------------------------------------

DBCACHE = FIXTURES / "hotfix" / "DBCache.bin"


def without_hotfixes(data):
    rewind_to(data, FIXTURE_VERSION)  # DBCache.bin de la fixture : build 1.60.1.70170 (décision 192)
    path = data / FIXTURE_VERSION / "sources.json"
    sources = read_json(path)
    sources.pop("hotfixes", None)
    path.write_bytes((json.dumps(sources, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    write_manifest(data)
    return sources


@pytest.fixture
def client_70170(tmp_path, make_deps, data_copy):
    """Client 70170 dont le `DBCache.bin` (fixture) porte des correctifs absents de la révision installée."""
    from forever.pipeline import dbcache

    sources = without_hotfixes(data_copy)
    wow = tmp_path / "World of Warcraft" / "_classic_beta_"
    (wow / "Logs").mkdir(parents=True)
    set_build_info(wow, FIXTURE_VERSION)
    live = wow / "Cache" / "ADB" / "enUS" / "DBCache.bin"
    live.parent.mkdir(parents=True)
    live.write_bytes(DBCACHE.read_bytes())
    rules = load_rules(data_copy)[1]
    from forever.pipeline.hotfixes import pending_hotfixes

    expected = pending_hotfixes(dbcache.read_dbcache(DBCACHE), sources, rules)
    return make_deps(data_dir=data_copy, wow_dir=wow, http=FakeHttp.failing()), live, expected


def test_pending_hotfixes_match_the_watch_rule(client_70170):
    from forever.pipeline.dbcache import effective, known_tables, read_dbcache, table_names
    from forever.pipeline.tables import TABLES

    _, _, expected = client_70170
    rules = load_rules(DATA_DIR)[1]
    applicable = effective(read_dbcache(DBCACHE).entries, table_names(known_tables(rules))).applicable
    assert expected == sorted(k for k in applicable if k[0] in TABLES)
    assert len(expected) > 0


def test_hotfixes_of_the_archive_wait_for_layouts_without_network(client_70170):
    deps, live, expected = client_70170
    options = UpdateOptions(dry_run=True, network=False, only=frozenset({"correctifs"}))
    report = run_update(deps, options, replay=Replay())
    fixes = step(report, "correctifs")
    assert fixes["status"] == "attente" and fixes["data"]["pending"] == len(expected)
    assert [e["kind"] for e in report["pending"]] == ["network_dbd"]
    # les correctifs viennent de l'archive : un fichier vivant illisible ne change rien
    live.write_bytes(DBCACHE.read_bytes()[:100])
    again = run_update(deps, options, replay=Replay())
    assert step(again, "correctifs")["data"]["pending"] == len(expected)


# --- Journaux de combat --------------------------------------------------------------------------------------

LOG = FIXTURES / "combatlog" / "WoWCombatLog-092726_145346.anon.txt"


class Measure:
    def __init__(self, changed):
        self.changed = changed
        self.calls = []

    def __call__(self, deps, data_dir, logs):
        self.calls.append([p.name for p in logs])
        return {"changed": self.changed}


@pytest.fixture
def logs(tmp_path, make_deps, data_copy):
    """Client 70170 et un journal du 27/09 ; `journal` : versions du client relevées avant le passage."""
    wow = tmp_path / "World of Warcraft" / "_classic_beta_"
    (wow / "Logs").mkdir(parents=True)
    shutil.copyfile(LOG, wow / "Logs" / LOG.name)

    def factory(journal):
        deps = make_deps(data_dir=data_copy, wow_dir=wow)
        for build, day in journal:
            record_build(deps.cache_dir, ClientBuild(build, datetime(2026, 9, day, tzinfo=UTC), PRODUCT, "test"))
        set_build_info(wow, journal[-1][0])
        return deps

    return factory


JOURNALS = UpdateOptions(dry_run=True, only=frozenset({"journaux"}))


def test_logs_of_the_installed_version_are_measured_and_wait_when_an_engine_input_changes(logs):
    deps = logs([(LOCAL_VERSION, 1)])
    measure = Measure([{"file": "monsters.json", "pointer": "/hp_curve"}])
    report = run_update(deps, JOURNALS, replay=Replay(), measure=measure)
    assert measure.calls == [[LOG.name]]
    assert step(report, "journaux")["status"] == "attente"
    assert [e["kind"] for e in report["pending"]] == ["measures"]


def test_measures_outside_the_engine_inputs_do_not_wait(logs):
    deps = logs([(LOCAL_VERSION, 1)])
    measure = Measure([{"file": "pet_rules.json", "pointer": "/x"}])
    report = run_update(deps, JOURNALS, replay=Replay(), measure=measure)
    assert measure.calls == [[LOG.name]]
    assert step(report, "journaux")["status"] == "fait"
    assert report["pending"] == []


def test_logs_of_another_version_are_listed_and_never_measured(logs):
    deps = logs([(LOCAL_VERSION, 1), (NEWER, 20)])
    measure = Measure([{"file": "monsters.json", "pointer": "/hp_curve"}])
    report = run_update(deps, JOURNALS, replay=Replay(), measure=measure)
    journaux = step(report, "journaux")
    assert measure.calls == []
    assert [h["name"] for h in journaux["data"]["held_back"]] == [LOG.name]
    assert journaux["data"]["held_back"][0]["client_version"] == NEWER
    assert report["pending"] == []


# --- Addons de données ---------------------------------------------------------------------------------------


def test_a_changed_addon_with_depends_waits(tmp_path, make_deps):
    from forever.addons import addons_status

    wow = tmp_path / "World of Warcraft" / "_classic_beta_"
    addons = wow / "Interface" / "AddOns"
    addons.mkdir(parents=True)
    shutil.copytree(FIXTURES / "addons" / "TalentsForeverBook", addons / "TalentsForeverBook")
    deps = make_deps(wow_dir=wow)
    addons_status(deps, save=True)
    data = addons / "TalentsForeverBook" / "Data.lua"
    data.write_bytes(data.read_bytes() + b"\n-- changed by the test\n")
    report = run_update(deps, UpdateOptions(dry_run=True, only=frozenset({"addons"})), replay=Replay())
    assert step(report, "addons")["status"] == "attente"
    assert [(e["kind"], e["addon"]) for e in report["pending"]] == [("addon_data", "TalentsForeverBook")]
