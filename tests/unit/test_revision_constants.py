"""Constantes de révision des tests (2026-10-02) : `LOCAL_REVISION`, `LOCAL_REVISED_AT` et `LOCAL_COLLECTED_AT` sont
lues dans le manifeste installé ; elles doivent concorder avec `sources.json` de la version installée et avec la
dernière entrée de `revisions.json`, faute de quoi les tests qui s'en servent ne prouveraient plus rien."""

from conftest import DATA_DIR, LOCAL_COLLECTED_AT, LOCAL_REVISED_AT, LOCAL_REVISION, LOCAL_VERSION, read_json


def test_manifest_revision_matches_sources_and_history():
    sources = read_json(DATA_DIR / LOCAL_VERSION / "sources.json")
    assert (sources["revision"], sources["revised_at"], sources["collected_at"]) == (
        LOCAL_REVISION,
        LOCAL_REVISED_AT,
        LOCAL_COLLECTED_AT,
    )
    last = read_json(DATA_DIR / LOCAL_VERSION / "revisions.json")["revisions"][-1]
    assert (last["revision"], last["date"]) == (LOCAL_REVISION, LOCAL_REVISED_AT)
