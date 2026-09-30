"""Journal des versions du client installées sur ce poste (T08a, bloc C, décision 135).

`.build.info` et `WowB.exe` sont réécrits à chaque mise à jour du client : l'instant du changement est perdu s'il
n'est pas relevé. Ce journal, en ajout seulement, garde pour chaque build vu sa date d'installation ; chaque
**session** de journal de combat est ensuite attribuée à la version en vigueur à son début.

L'entête du journal de combat (`COMBAT_LOG_VERSION … BUILD_VERSION 1.60.1`) est tronquée, sans numéro de build :
elle ne distingue pas deux versions et n'est jamais utilisée pour attribuer (constat du 2026-09-30,
`docs/research/data-1.60.1.70124.md`).

Valeurs des fixtures : forme réelle de `.build.info` relevée le 2026-09-30 sur le client de l'utilisateur."""

from datetime import UTC, datetime, timedelta

import pytest

from forever.pipeline.client_builds import (
    ClientBuild,
    load_builds,
    read_build_info,
    record_build,
    version_at,
)

# Deux colonnes suffisent à l'attribution ; le fichier réel en porte quinze.
HEADER = "Branch!STRING:0|Active!DEC:1|Version!STRING:0|Product!STRING:0"
BETA = "1.60.1.70124"
OLD = "1.60.1.70009"


def build_info(tmp_path, version=BETA, product="wow_classic_beta", extra=""):
    root = tmp_path / "World of Warcraft"
    (root / "_classic_beta_").mkdir(parents=True, exist_ok=True)
    path = root / ".build.info"
    path.write_text(f"{HEADER}\nus|1|{version}|{product}\n{extra}", encoding="utf-8")
    return root / "_classic_beta_"


def test_build_info_is_read_next_to_the_client(tmp_path):
    wow_dir = build_info(tmp_path)
    found = read_build_info(wow_dir)
    assert found is not None
    assert found.build == BETA
    assert found.product == "wow_classic_beta"


def test_installed_at_is_the_file_date(tmp_path):
    wow_dir = build_info(tmp_path)
    when = datetime(2026, 9, 30, 5, 46, 26, tzinfo=UTC)
    path = wow_dir.parent / ".build.info"
    import os

    os.utime(path, (when.timestamp(), when.timestamp()))
    found = read_build_info(wow_dir)
    assert found is not None
    assert found.installed_at == when


def test_the_right_product_is_picked(tmp_path):
    wow_dir = build_info(tmp_path, extra="eu|1|12.0.1.70210|wow\n")
    found = read_build_info(wow_dir)
    assert found is not None and found.build == BETA


def test_a_missing_file_is_not_an_error(tmp_path):
    (tmp_path / "wow" / "_classic_beta_").mkdir(parents=True)
    assert read_build_info(tmp_path / "wow" / "_classic_beta_") is None


def test_an_unreadable_file_is_not_an_error(tmp_path):
    wow_dir = build_info(tmp_path)
    (wow_dir.parent / ".build.info").write_text("n'importe quoi", encoding="utf-8")
    assert read_build_info(wow_dir) is None


def entry(build, day, hour=8):
    return ClientBuild(build=build, installed_at=datetime(2026, 9, day, hour, tzinfo=UTC), product="wow_classic_beta")


def test_the_journal_only_ever_grows(tmp_path):
    record_build(tmp_path, entry(OLD, 25))
    record_build(tmp_path, entry(BETA, 30))
    assert [e.build for e in load_builds(tmp_path)] == [OLD, BETA]


def test_the_same_build_is_recorded_once(tmp_path):
    record_build(tmp_path, entry(OLD, 25))
    record_build(tmp_path, entry(OLD, 25))
    record_build(tmp_path, entry(OLD, 26))  # même build relu plus tard : la première date fait foi
    assert [(e.build, e.installed_at.day) for e in load_builds(tmp_path)] == [(OLD, 25)]


def test_the_journal_is_sorted_by_date(tmp_path):
    record_build(tmp_path, entry(BETA, 30))
    record_build(tmp_path, entry(OLD, 25))
    assert [e.build for e in load_builds(tmp_path)] == [OLD, BETA]


def test_an_empty_journal_reads_as_empty(tmp_path):
    assert load_builds(tmp_path) == []


def test_version_in_force_at_a_moment(tmp_path):
    journal = [entry(OLD, 25), entry(BETA, 30, hour=5)]
    assert version_at(journal, datetime(2026, 9, 29, 15, tzinfo=UTC)) == OLD
    assert version_at(journal, datetime(2026, 9, 30, 4, tzinfo=UTC)) == OLD
    assert version_at(journal, datetime(2026, 9, 30, 6, tzinfo=UTC)) == BETA
    # Exactement à l'instant de la mise à jour : la nouvelle version.
    assert version_at(journal, datetime(2026, 9, 30, 5, tzinfo=UTC)) == BETA


def test_before_the_first_entry_the_version_is_unknown(tmp_path):
    assert version_at([entry(OLD, 25)], datetime(2026, 9, 20, tzinfo=UTC)) is None


def test_a_naive_moment_is_read_as_local_time(tmp_path):
    """Les journaux de combat datent leurs événements en heure locale, sans fuseau."""
    journal = [entry(OLD, 25), entry(BETA, 30, hour=5)]
    paris = timedelta(hours=2)
    # 06:00 à Paris = 04:00 UTC, avant la mise à jour de 05:00 UTC ; 08:00 à Paris = 06:00 UTC, après.
    before = datetime(2026, 9, 30, 6, tzinfo=UTC).replace(tzinfo=None)
    after = datetime(2026, 9, 30, 8, tzinfo=UTC).replace(tzinfo=None)
    assert version_at(journal, before, utc_offset=paris) == OLD
    assert version_at(journal, after, utc_offset=paris) == BETA


def test_recording_reads_and_writes_in_one_call(tmp_path):
    wow_dir = build_info(tmp_path)
    found = read_build_info(wow_dir)
    assert found is not None
    record_build(tmp_path / "cache", found)
    assert [e.build for e in load_builds(tmp_path / "cache")] == [BETA]


def test_a_corrupt_journal_is_refused_not_silently_emptied(tmp_path):
    record_build(tmp_path, entry(OLD, 25))
    from forever.pipeline.client_builds import JOURNAL_NAME

    (tmp_path / JOURNAL_NAME).write_text("{cassé", encoding="utf-8")
    with pytest.raises(Exception, match="client_builds"):
        load_builds(tmp_path)
