"""Inventaire des valeurs écrites à la main (T08b, bloc H) : `forever origins inventory` et
`docs/research/valeurs-ecrites-a-la-main.md`, rendu committé de la commande."""

import json

from conftest import DATA_DIR, LOCAL_VERSION, REPO_ROOT

from forever.cli import main
from forever.origins import ORIGINS_NAME, inventory, inventory_payload, render_inventory

DOC = REPO_ROOT / "docs" / "research" / "valeurs-ecrites-a-la-main.md"


def manual_paths(version: str) -> set[tuple[str, str]]:
    origins = json.loads((DATA_DIR / version / ORIGINS_NAME).read_text(encoding="utf-8"))
    return {(r["file"], p) for r in origins["rules"] if r["origin"] == "manuel" for p in r["paths"]}


def test_inventory_lists_each_manual_value_once():
    rows, _ = inventory(DATA_DIR, LOCAL_VERSION)
    keys = [(r.file, r.path) for r in rows]
    assert len(keys) == len(set(keys))
    assert set(keys) == manual_paths(LOCAL_VERSION)
    assert all(r.reason and r.source and r.certainty and r.leaves > 0 for r in rows)


def test_inventory_has_no_certain_value():
    rows, _ = inventory(DATA_DIR, LOCAL_VERSION)
    assert {r.certainty for r in rows} <= {"probable", "suppose"}


def test_inventory_is_sorted_and_deterministic():
    rows, pending = inventory(DATA_DIR, LOCAL_VERSION)
    assert [(r.file, r.path) for r in rows] == sorted((r.file, r.path) for r in rows)
    assert render_inventory(LOCAL_VERSION, rows, pending) == render_inventory(
        LOCAL_VERSION, *inventory(DATA_DIR, LOCAL_VERSION)
    )


def test_pending_lowerings_come_first():
    rows, pending = inventory(DATA_DIR, LOCAL_VERSION)
    text = render_inventory(LOCAL_VERSION, rows, pending)
    assert pending
    first_pending = text.index(f"`{pending[0].path}`")
    first_row = text.index(f"`{rows[0].path}`")
    assert first_pending < first_row


def test_committed_inventory_is_up_to_date():
    rows, pending = inventory(DATA_DIR, LOCAL_VERSION)
    assert DOC.read_text(encoding="utf-8") == render_inventory(LOCAL_VERSION, rows, pending)


def test_payload_counts():
    rows, pending = inventory(DATA_DIR, LOCAL_VERSION)
    payload = inventory_payload(LOCAL_VERSION, rows, pending)
    assert payload["game_version"] == LOCAL_VERSION
    assert len(payload["values"]) == len(rows) and len(payload["pending"]) == len(pending)
    assert payload["leaves"] == sum(r.leaves for r in rows)


def test_cli_origins_inventory_json(capsys, make_deps):
    code = main(["origins", "inventory", "--json"], make_deps())
    out, _ = capsys.readouterr()
    assert code == 0
    data = json.loads(out)
    assert data["game_version"] == LOCAL_VERSION
    assert data["provenance"]["game_version"] == LOCAL_VERSION
    assert {(v["file"], v["path"]) for v in data["values"]} == manual_paths(LOCAL_VERSION)


def test_cli_origins_check_text(capsys, make_deps):
    code = main(["origins", "check"], make_deps())
    out, _ = capsys.readouterr()
    assert code == 0
    assert "Origines" in out and LOCAL_VERSION in out
