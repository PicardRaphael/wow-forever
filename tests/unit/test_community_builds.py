"""Comparaison avec les builds de la communauté (T05, bloc J) : fixture tirée de
docs/research/community-builds-mage.md (recherche du 2026-09-28, sous-agent de recherche web), nos builds de référence
par contexte et niveau, écart de chaque build calculé par le moteur, explication de chaque écart (concorde, mécanique
non modélisée avec son entrée du registre, source douteuse avec son motif). Aucune valeur communautaire n'entre dans
`forever/data/`."""

import datetime as dt
import hashlib
import json
import shutil

import pytest
from conftest import (
    DATA_DIR,
    FIXTURES,
    LOCAL_VERSION,
    RANK_VALUES_VERSION,
    REGISTRY_PATH,
    isolated_deps,
    read_json,
    rewind_to,
)

from forever.engine.talents import check_build
from forever.gamedata import load_game_data
from forever.manifest import write_manifest
from forever.registry import load
from forever.sim.community import community_gap

FIXTURE = FIXTURES / "community" / "mage_builds.json"
MONSTERS_COPY = FIXTURES / "community" / "monsters.json"  # PV des monstres de la comparaison (gelés)
KINDS = ("concorde", "mecanique_non_modelisee", "source_douteuse")
CONTEXTS = ("leveling", "dungeon", "raid", "pvp")


@pytest.fixture(scope="module")
def doc():
    return read_json(FIXTURE)


def test_fixture_comes_from_the_research(doc):
    assert doc["source"].startswith("docs/research/community-builds-mage.md")
    research = (FIXTURES.parent.parent / "docs" / "research" / "community-builds-mage.md").read_text(encoding="utf-8")
    ids = [b["id"] for b in doc["builds"]]
    assert len(ids) == len(set(ids)) == 55
    for b in doc["builds"]:
        assert b["source_url"] in research and f'"id": "{b["id"]}"' in research


def test_every_build_has_source_date_context_level(doc):
    for b in doc["builds"]:
        assert b["source_url"].startswith("https://")
        flags = " ".join(b["reliability_flags"])
        if b["author"] is None:  # page sans signature, signalée par la recherche
            assert "auteur inconnu" in flags, b["id"]
        if b["date"] is None:  # date inconnue, signalée par la recherche
            assert "date" in flags and "inconnue" in flags, b["id"]
        elif len(b["date"]) == 7:  # date au mois près, signalée par la recherche
            assert "imprécise" in flags, b["id"]
            dt.date.fromisoformat(b["date"] + "-01")
        else:
            dt.date.fromisoformat(b["date"])
        assert b["context"] in CONTEXTS and isinstance(b["level"], int) and 10 <= b["level"] <= 60
        assert b["points"]


def test_legality_is_recomputed(game_data, doc):
    for b in doc["builds"]:
        pts = {k: v for k, v in b["points"].items() if k in game_data.talents}
        known = len(pts) == len(b["points"])
        assert (known and check_build(game_data, pts, b["level"]) == []) == b["legal"], b["id"]


def test_every_gap_is_explained(game_data, doc):
    ids = {m.id for m in load(REGISTRY_PATH)}
    threshold = doc["concord_threshold"]
    assert (
        threshold
        == read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]["build.concord_threshold"]["value"]
    )
    for b in doc["builds"]:
        e = b["explanation"]
        assert e["kind"] in KINDS, b["id"]
        assert e["motif"], b["id"]
        if e["kind"] == "mecanique_non_modelisee":
            assert e["registry"] in ids, b["id"]
        if e["kind"] == "concorde":
            assert b["legal"] and abs(b["gap"]["analytic_rel"]) <= threshold, b["id"]
        if not b["legal"]:
            assert e["kind"] == "source_douteuse" and "illégal" in e["motif"], b["id"]


@pytest.fixture(scope="module")
def frozen_game_data(tmp_path_factory):
    """Données ramenées à RANK_VALUES_VERSION (version de la comparaison), PV des monstres remplacés par ceux de la
    comparaison (copie écrite par le script) : une nouvelle mesure des journaux (2026-10-02) ou une nouvelle version
    qui change les dégâts des rangs (1.60.1.70291) ne change pas les écarts attendus."""
    tmp = tmp_path_factory.mktemp("community")
    data = tmp / "data"
    shutil.copytree(DATA_DIR, data, ignore=shutil.ignore_patterns("__pycache__"))
    rewind_to(data, RANK_VALUES_VERSION)
    shutil.copyfile(MONSTERS_COPY, data / RANK_VALUES_VERSION / "monsters.json")
    write_manifest(data)
    return load_game_data(isolated_deps(tmp, data))


def test_frozen_monsters_are_the_ones_of_the_comparison(doc):
    assert hashlib.sha256(MONSTERS_COPY.read_bytes()).hexdigest() == doc["monsters_sha256"]
    assert read_json(MONSTERS_COPY)["game_version"] == doc["game_version"]


def test_gaps_are_computed_by_the_engine(frozen_game_data, doc):
    game_data = frozen_game_data
    refs = {(r["context"], r["level"]): r for r in doc["references"]}
    for b in doc["builds"]:
        if not b["legal"]:
            assert b["gap"] is None, b["id"]
            continue
        ref = refs[(b["context"], b["level"])]
        rel = community_gap(game_data, b["context"], b["level"], b["points"], ref["points"])
        assert rel == pytest.approx(b["gap"]["analytic_rel"], rel=1e-9, abs=1e-12), b["id"]


def test_references_are_legal_builds_of_the_optimizer(game_data, doc):
    pairs = {(b["context"], b["level"]) for b in doc["builds"]}
    assert pairs == {(r["context"], r["level"]) for r in doc["references"]}
    for r in doc["references"]:
        assert check_build(game_data, r["points"], r["level"]) == [], r
        assert r["preset"] in game_data.build.presets


def test_no_community_value_in_the_data(doc):
    blob = "\n".join(p.read_text(encoding="utf-8") for p in (DATA_DIR / LOCAL_VERSION).glob("*.json"))
    for b in doc["builds"]:
        assert b["source_url"] not in blob, b["id"]


def test_research_document_has_the_comparison(doc):
    research = (FIXTURES.parent.parent / "docs" / "research" / "community-builds-mage.md").read_text(encoding="utf-8")
    assert "## Comparaison avec nos builds (T05, bloc J)" in research
    for b in doc["builds"]:
        assert f"| {b['id']} |" in research.split("## Comparaison avec nos builds (T05, bloc J)")[1], b["id"]
    json.dumps(doc)
