"""Valeurs des correctifs du serveur appliquées en mode forever (T08c, bloc C) : superposition sur les tables du build,
garde de build, refus d'une table sans disposition validée, décodage de la candidate avec la provenance de chaque
entité touchée (champ `hotfix`, bloc `hotfixes` de `sources.json`, origine `correctif_serveur` d'`origins.json`),
non-régression sans l'option et en mode seed, report à l'installation.

Fixtures : `tests/fixtures/hotfix/` (DBCache.bin extrait du fichier de l'utilisateur, journal du même build),
`tests/fixtures/dbd/` (dispositions dérivées), `tests/fixtures/wago/1.60.1.70170/` (tables du build)."""

import json
import re
import shutil
import struct

import pytest
from conftest import DATA_DIR, FIXTURES, LOCAL_VERSION, isolated_deps, read_json

from forever.cli import main
from forever.errors import HotfixBuildMismatchError, HotfixLayoutError
from forever.manifest import write_manifest
from forever.origins import CERTAINTY_CAP, ORIGINS, ORIGINS_NAME, check_version
from forever.pipeline.dbd import layouts_from_json
from forever.pipeline.decode import decode_version, load_class_tables, load_tables
from forever.pipeline.hotfix_overlay import HOTFIX_KEY, SERVER_ORIGIN, apply_hotfixes, hotfix_source
from forever.pipeline.hotfixes import JOURNAL_NAME
from forever.pipeline.install import carry_hotfix_provenance

HOTFIX = FIXTURES / "hotfix"
DBCACHE = HOTFIX / "DBCache.bin"
JOURNAL = read_json(HOTFIX / "hotfixes-70170.json")["entries"]
LAYOUTS_DOC = read_json(FIXTURES / "dbd" / "layouts-1.60.1.70170.json")
WAGO = FIXTURES / "wago" / "1.60.1.70170"
RULES = read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")
READ_AT = "2026-10-05T10:00:00Z"
DBD = {"repo": LAYOUTS_DOC["repo"], "commit": LAYOUTS_DOC["commit"], "files": {}}


def readme_sha() -> str:
    text = (HOTFIX / "README.md").read_text(encoding="utf-8")
    return json.loads(re.search(r"```json\n(.*?)\n```", text, re.DOTALL).group(1))["sha256"]


def source(layouts=None, version=LOCAL_VERSION, path=DBCACHE):
    lay = layouts_from_json(LAYOUTS_DOC) if layouts is None else layouts
    return hotfix_source(path, lay, DBD, JOURNAL, version, RULES, READ_AT)


def by_id(rows):
    return {int(r["ID"]): r for r in rows}


@pytest.fixture(scope="module")
def overlay():
    return apply_hotfixes(load_tables(WAGO, RULES), source(), WAGO)


@pytest.fixture(scope="module")
def decoded(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("t08c")
    with_fix = decode_version(isolated_deps(tmp), LOCAL_VERSION, csv_dir=WAGO, out=tmp / "avec", hotfixes=source())
    without = decode_version(isolated_deps(tmp), LOCAL_VERSION, csv_dir=WAGO, out=tmp / "sans")
    return with_fix.root / LOCAL_VERSION, without.root / LOCAL_VERSION


def warrior_talents(vdir):
    w = read_json(vdir / "classes.json")["classes"]["Warrior"]
    return {t["node_id"]: t for tree in w["trees"] for t in tree["talents"]}, w


# --- Superposition ---------------------------------------------------------------------------------------------


def test_valid_rows_replace_or_add(overlay):
    nodes = by_id(overlay.tables["TraitNode"])
    assert nodes[105928]["PosX"] == 5620 and nodes[105928]["PosY"] == 5130
    assert {113569, 113570} <= set(nodes)
    assert nodes[113569]["TraitTreeID"] == 1117
    assert by_id(overlay.tables["TraitDefinitionEffectPoints"])[25094]["CurveID"] == 111755
    assert 136735 in by_id(overlay.tables["TraitEdge"])


def test_delete_removes_rows(overlay):
    nodes = by_id(overlay.tables["TraitNode"])
    assert not {105929, 105936, 105973} & set(nodes)
    assert 124811 not in by_id(overlay.tables["TraitEdge"])


def test_delete_of_an_absent_row_is_listed(overlay):
    absent = {(d["table"], d["rec_id"]) for d in overlay.listed["delete_absent"]}
    assert ("TraitDefinitionEffectPoints", 25179) in absent
    assert ("SpellLevels", 999901) in absent  # entrée synthétique de la fixture


def test_applied_records_carry_before_after_and_date(overlay):
    rec = next(a for a in overlay.applied if (a.table, a.rec_id) == ("TraitNode", 105928))
    assert rec.status == "VALID" and rec.push_id == 112347
    assert rec.before["PosX"] == 6220 and rec.after["PosX"] == 5620
    assert rec.seen_at.startswith("2026-10-02T08:00:23")
    gone = next(a for a in overlay.applied if (a.table, a.rec_id) == ("TraitNode", 105929))
    assert gone.status == "DELETE" and gone.after is None and gone.before is not None


def test_invalid_notpublic_and_dbreply_add_nothing(tmp_path):
    tables = load_class_tables(WAGO, RULES)
    over = apply_hotfixes(tables, source(), WAGO)
    assert 315008 not in by_id(over.tables["SpellPower"])  # INVALID
    assert 73078 not in by_id(over.tables["SpellClassOptions"])  # NOTPUBLIC
    assert 15147 not in by_id(over.tables["Spell"])  # DBReply « absent »
    assert ("SpellPower", 315008) in {(i["table"], i["rec_id"]) for i in over.listed["invalid"]}


def test_untouched_tables_are_unchanged(overlay):
    tables = load_tables(WAGO, RULES)
    assert overlay.tables["SkillLineXTraitTree"] == tables["SkillLineXTraitTree"]
    assert overlay.tables["SpellCastTimes"] == tables["SpellCastTimes"]


def test_tables_not_read_by_the_pipeline_are_listed(overlay):
    assert {"Curve", "TraitNodeGroupXTraitNode"} <= set(overlay.listed["not_loaded"])


def test_every_applied_table_was_validated(overlay):
    for table in {a.table for a in overlay.applied}:
        assert overlay.checks[table].ok, overlay.checks[table].reason


# --- Gardes ----------------------------------------------------------------------------------------------------


def test_other_build_is_refused(tmp_path):
    with pytest.raises(HotfixBuildMismatchError):
        source(version="1.60.1.70124")
    raw = bytearray(DBCACHE.read_bytes())
    struct.pack_into("<I", raw, 8, 70124)
    other = tmp_path / "DBCache.bin"
    other.write_bytes(bytes(raw))
    with pytest.raises(HotfixBuildMismatchError):
        source(path=other)


def test_table_without_layout_hitting_read_rows_is_refused():
    layouts = layouts_from_json(LAYOUTS_DOC)
    del layouts["TraitNode"]
    with pytest.raises(HotfixLayoutError, match="TraitNode"):
        apply_hotfixes(load_tables(WAGO, RULES), source(layouts), WAGO)


# --- Candidate -------------------------------------------------------------------------------------------------


def test_candidate_has_the_new_warrior_talents(decoded):
    talents, warrior = warrior_talents(decoded[0])
    names = {t["name"] for t in talents.values()}
    assert {"Lingering Rage", "Furious Precision", "Gore Drinker"} <= names
    node = talents[113569]
    assert (node["tree"], node["tier"], node["col"], node["max"]) == ("Fury", 6, 3, 2)
    assert talents[105928]["col"] == 2  # Flurry déplacé
    assert 105929 not in talents
    assert warrior["unresolved_nodes"] == []
    booming = talents[105938]  # recoupement de la grille : PosX 5620, PosY 2130
    assert (booming["tier"], booming["col"]) == (1, 2)


def test_touched_entities_carry_their_hotfix(decoded):
    talents, _ = warrior_talents(decoded[0])
    for node_id in (113569, 105928):
        fix = talents[node_id][HOTFIX_KEY]
        assert fix["pushes"] == [112347]
        assert fix["first_logged_at"].startswith("2026-10-02T08:00:23")
        assert any(r.startswith("TraitNode ") for r in fix["rows"])
    untouched = talents[105938]
    assert HOTFIX_KEY not in untouched


def test_sources_carry_the_hotfix_block(decoded):
    block = read_json(decoded[0] / "sources.json")["hotfixes"]
    assert block["dbcache"]["build"] == 70170 and block["dbcache"]["sha256"] == readme_sha()
    assert block["dbcache"]["locale"] == "enUS" and "TactKey" not in json.dumps(block)
    assert 112347 in block["pushes"] and block["max_push"] == max(block["pushes"])
    assert block["dbd"]["commit"] == LAYOUTS_DOC["commit"]
    assert block["seen_at"]["112347"].startswith("2026-10-02T08:00:23")
    assert {"table": "TraitNode", "rec_id": 105928, "status": "VALID", "push": 112347} in [
        {k: a[k] for k in ("table", "rec_id", "status", "push")} for a in block["applied"]
    ]


def test_without_hotfixes_nothing_changes(decoded):
    with_fix, without = decoded
    assert HOTFIX_KEY not in json.dumps(read_json(without / "classes.json"))
    assert "hotfixes" not in read_json(without / "sources.json")
    for seed in sorted(p.name for p in without.glob("_seed_*.json")):
        assert (with_fix / seed).read_bytes() == (without / seed).read_bytes(), seed
    a, b = read_json(with_fix / "classes.json")["classes"], read_json(without / "classes.json")["classes"]
    for cls in b:
        if HOTFIX_KEY not in json.dumps(a[cls]):
            assert a[cls] == b[cls], cls


def test_origins_of_the_candidate(decoded):
    with_fix, _ = decoded
    doc = read_json(with_fix / ORIGINS_NAME)
    assert HOTFIX_KEY in doc["metadata_keys"]
    rules = [r for r in doc["rules"] if r["origin"] == SERVER_ORIGIN]
    assert rules and all(r["certainty"] == "certain" and r["pushes"] for r in rules)
    covered = {p for r in rules if r["file"] == "classes.json" for p in r["paths"]}
    assert any(p.startswith("/classes/Warrior/trees/") for p in covered)
    assert all("*" not in p for p in covered)
    assert check_version(with_fix.parent, LOCAL_VERSION).issues == []


# --- Origine propre --------------------------------------------------------------------------------------------


def test_server_origin_is_declared():
    assert SERVER_ORIGIN in ORIGINS and CERTAINTY_CAP[SERVER_ORIGIN] == "certain"


def test_server_origin_needs_pushes_and_date_and_exact_paths(decoded, tmp_path):
    root = tmp_path / "copie"
    shutil.copytree(decoded[0].parent, root)
    path = root / LOCAL_VERSION / ORIGINS_NAME
    doc = read_json(path)
    rule = next(r for r in doc["rules"] if r["origin"] == SERVER_ORIGIN)
    rule.pop("pushes")
    rule.pop("seen_at")
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    kinds = {i.kind for i in check_version(root, LOCAL_VERSION).issues}
    assert "schema" in kinds
    doc = read_json(path)
    rule = next(r for r in doc["rules"] if r["origin"] == SERVER_ORIGIN)
    rule["paths"] = ["/classes/*/trees"]
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    assert "motif_interdit" in {i.kind for i in check_version(root, LOCAL_VERSION).issues}


# --- Installation et commande ----------------------------------------------------------------------------------


def test_install_carries_origins_and_sources(decoded, data_copy):
    with_fix, _ = decoded
    vdir = data_copy / LOCAL_VERSION
    shutil.copyfile(with_fix / "classes.json", vdir / "classes.json")  # fichier remplacé par l'installation
    assert carry_hotfix_provenance(vdir, with_fix) is True
    doc = read_json(vdir / ORIGINS_NAME)
    assert HOTFIX_KEY in doc["metadata_keys"]
    assert any(r["origin"] == SERVER_ORIGIN for r in doc["rules"])
    assert read_json(vdir / "sources.json")["hotfixes"]["max_push"] >= 112347
    write_manifest(data_copy)
    assert check_version(data_copy, LOCAL_VERSION).issues == []
    assert carry_hotfix_provenance(vdir, with_fix) is True  # une seconde fois : règles remplacées, pas doublées
    again = read_json(vdir / ORIGINS_NAME)
    assert len([r for r in again["rules"] if r["origin"] == SERVER_ORIGIN]) == len(
        [r for r in doc["rules"] if r["origin"] == SERVER_ORIGIN]
    )


def test_cli_decode_with_hotfixes(tmp_path, make_deps, capsys):
    deps = make_deps()
    deps.cache_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HOTFIX / "hotfixes-70170.json", deps.cache_dir / JOURNAL_NAME)
    out = tmp_path / "cand"
    code = main(
        [
            "decode",
            "--version",
            LOCAL_VERSION,
            "--csv-dir",
            str(WAGO),
            "--out",
            str(out),
            "--hotfixes",
            "--dbcache",
            str(DBCACHE),
            "--dbd-layouts",
            str(FIXTURES / "dbd" / "layouts-1.60.1.70170.json"),
        ],
        deps,
    )
    text, _ = capsys.readouterr()
    assert code == 0, text
    assert "correctif" in text and "112347" in text
    assert "hotfixes" in read_json(out / LOCAL_VERSION / "sources.json")
