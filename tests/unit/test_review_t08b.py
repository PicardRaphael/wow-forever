"""Relecture de T08b (2026-10-01) : correctifs jamais perdus par la veille, lignes `DBReply` datées, année d'une ligne
de décembre lue en janvier, plafond observé en jeu cohérent avec son origine, plafond reporté gardant sa date
d'origine, ratios hérités signalés, origine des utilitaires affichée, jeton masqué avant la coupe du message,
mot-clé entier dans les notes."""

import json
import os
import shutil
from datetime import UTC, datetime

from conftest import (
    CLASS_FIXTURE_VERSION,
    DATA_DIR,
    FIXTURES,
    LOCAL_VERSION,
    WAGO_70124,
    FakeHttp,
    isolated_deps,
    read_json,
)

import forever.watch as watch_mod
from forever.gamedata import build_game_data
from forever.leveling import ratio_assumption
from forever.manifest import write_manifest
from forever.origins import check_version
from forever.pipeline import hotfixes
from forever.pipeline.blizzard_api import candidate_namespaces, probe
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install
from forever.pipeline.notes import recognise
from forever.store import load_version

T = "\t"


def test_watch_does_not_record_the_log_when_rules_are_unreadable(tmp_path, make_deps, monkeypatch):
    root = tmp_path / "World of Warcraft" / "_classic_beta_"
    (root / "Logs").mkdir(parents=True)
    shutil.copyfile(FIXTURES / "hotfix" / "Hotfix.log", root / "Logs" / "Hotfix.log")
    deps = make_deps(wow_dir=root)
    monkeypatch.setattr(watch_mod, "_rules", lambda d: {})
    watch_mod.watch(deps)
    monkeypatch.undo()
    result = watch_mod.watch(deps)
    assert "hotfixes" in {e["kind"] for e in result["events"]}


def test_dbreply_on_another_day_is_a_new_entry(tmp_path):
    line = "{d} 07:44:05.333  " + T + "DBReply Table ItemSparse RecID 723 VALIDATION_RESULT_DELETE"
    tracked = {"ItemSparse"}
    seen = datetime(2026, 10, 1, tzinfo=UTC)
    first = hotfixes.update_journal(
        tmp_path, hotfixes.parse_hotfix_log(line.format(d="9/30"), 2026), tracked, None, seen
    )
    again = hotfixes.update_journal(
        tmp_path, hotfixes.parse_hotfix_log(line.format(d="9/30"), 2026), tracked, None, seen
    )
    later = hotfixes.update_journal(
        tmp_path, hotfixes.parse_hotfix_log(line.format(d="10/2"), 2026), tracked, None, seen
    )
    assert len(first) == 1 and again == [] and len(later) == 1


def test_december_line_read_in_january_is_dated_last_year(tmp_path):
    log = tmp_path / "Hotfix.log"
    log.write_text("12/31 23:59:00.000  " + T + "1 Table Curve RecID 1 VALIDATION_RESULT_VALID\n", encoding="utf-8")
    stamp = datetime(2027, 1, 1, 8, 0, tzinfo=UTC).timestamp()
    os.utime(log, (stamp, stamp))
    [line] = hotfixes.read_log(log)
    assert line.at.startswith("2026-12-31")


def test_observed_cap_is_certain_and_origins_stay_valid(data_at_class_fixture_version, make_deps, tmp_path):
    cand = decode_version(isolated_deps(tmp_path), CLASS_FIXTURE_VERSION, csv_dir=WAGO_70124, out=tmp_path / "c")
    data_copy, version = data_at_class_fixture_version, CLASS_FIXTURE_VERSION  # version des extraits
    deps = make_deps(data_dir=data_copy)
    cap = read_json(DATA_DIR / version / "meta.json")["game_state"]["beta_level_cap"]["value"]
    apply_install(deps, str(cand.root), motif="test", beta_level_cap=cap + 10, beta_level_cap_source="observation")
    state = read_json(data_copy / version / "meta.json")["game_state"]["beta_level_cap"]
    assert state["certainty"] == "certain"
    rule = next(r for r in read_json(data_copy / version / "origins.json")["rules"] if r["file"] == "meta.json")
    assert rule["origin"] == "journal"
    assert check_version(data_copy, version).ok


def test_carried_cap_keeps_its_original_date_and_revision(data_at_class_fixture_version, make_deps, tmp_path):
    cand = decode_version(isolated_deps(tmp_path), CLASS_FIXTURE_VERSION, csv_dir=WAGO_70124, out=tmp_path / "c")
    data_copy, version = data_at_class_fixture_version, CLASS_FIXTURE_VERSION  # version des extraits
    deps = make_deps(data_dir=data_copy)
    before = read_json(DATA_DIR / version / "meta.json")["game_state"]["beta_level_cap"]
    current = read_json(DATA_DIR / version / "sources.json")["revision"]
    apply_install(deps, str(cand.root), motif="test")
    state = read_json(data_copy / version / "meta.json")["game_state"]["beta_level_cap"]
    assert (state["date"], state["revision"]) == (before["date"], before["revision"])
    assert state["carried_to"] == current + 1


def test_inherited_ratios_are_named_as_inherited(data_copy, make_deps):
    path = data_copy / LOCAL_VERSION / "character_scaling.json"
    doc = read_json(path)
    doc["inherited_from"] = "1.60.1.70009"
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    write_manifest(data_copy)
    gd = build_game_data(load_version(make_deps(data_dir=data_copy)))
    assert "hérité" in ratio_assumption(gd) and "1.60.1.70009" in ratio_assumption(gd)


def test_utility_source_is_named_in_the_assumption(game_data):
    assert "classes.json" in ratio_assumption(game_data)


def test_token_is_hidden_before_the_message_is_cut(make_deps):
    token = "t" * 80
    ns = candidate_namespaces("eu")[0]

    def post(url, headers, data, timeout):
        return json.dumps({"access_token": token}).encode()

    http = FakeHttp(exc=OSError(f"erreur {token}"))
    result = probe(
        make_deps(http=http),
        {"BLIZZARD_CLIENT_ID": "a", "BLIZZARD_CLIENT_SECRET": "b"},
        regions=("eu",),
        http_post=post,
        sleep=lambda s: None,
    )
    assert ns in result["results"][0]["namespace"]
    assert all("tttttttttt" not in r["status"] for r in result["results"])


def test_keyword_is_a_whole_word():
    assert recognise("Respect the rules", [])[1] == []
    assert {k["registry"] for k in recognise("Free respec this week", [])[1]} == {"I5"}
