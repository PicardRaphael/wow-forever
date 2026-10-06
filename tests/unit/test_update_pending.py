"""Approbation différée de `forever update` (T08d, bloc E, décision 180).

Une attente (`<cache>/update/pending/<id>.json`) porte sa base : `origin/main` du dernier passage et l'empreinte de
la préparation. `approve` contrôle que la base n'a pas bougé (sinon l'entrée devient `périmée` et le passage suivant
recalcule), la marque `approuvée` et lance un passage détaché (`spawn` simulé) ; `reject` garde la raison ; une
entrée `bloqué` (verify rouge, installation refusée, valeur perdue) n'est jamais approuvable. Le serveur MCP n'en
montre qu'un résumé en lecture seule."""

import asyncio
import json

import pytest
from mcp import Client

from forever.cli import main
from forever.errors import EXIT_NOT_FOUND, EXIT_USAGE, ForeverError
from forever.mcp_server import build_server
from forever.update import (
    approve,
    candidate_fingerprint,
    list_pending,
    record_pending,
    reject,
    save_report,
    update_dir,
    update_summary,
)

ORIGIN = "a" * 40
MOVED = "b" * 40
VERSION = "1.60.1.79999"


def report(origin_main=ORIGIN):
    return {
        "schema_version": 1,
        "started_at": "2026-10-06T08:00:00Z",
        "finished_at": "2026-10-06T08:05:00Z",
        "steps": [],
        "verdicts": [],
        "written": [],
        "pending": [],
        "origin_main": origin_main,
        "provenance": {},
    }


class Spawn:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, args):
        self.calls.append(list(args))
        if self.fail:
            raise OSError("lancement simulé en échec")


@pytest.fixture
def staged(tmp_path):
    root = tmp_path / "cache" / "update" / "stage-x" / "data" / VERSION
    root.mkdir(parents=True)
    (root / "talents.json").write_bytes(b'{"a": 1}\n')
    return root


def entry(staged, action="attente", ident=None):
    sha = candidate_fingerprint(staged)
    return {
        "id": ident or f"{VERSION}-r1-{sha}",
        "kind": "install_version",
        "action": action,
        "version": VERSION,
        "revision": 1,
        "clauses": {"verify": True, "install": True, "manual": True, "inputs": action == "écrire"},
        "reasons": ["moteurs aux entrées changées : mage_build"],
        "staged": str(staged),
        "staged_sha": sha,
        "base": {"origin_main": ORIGIN, "version": "1.60.1.79998", "revision": 1, "client_build": VERSION},
        "commands": ["forever update approve <id>"],
    }


def test_fingerprint_changes_with_any_file(staged):
    first = candidate_fingerprint(staged)
    assert len(first) == 12 and candidate_fingerprint(staged) == first
    (staged / "talents.json").write_bytes(b'{"a": 2}\n')
    assert candidate_fingerprint(staged) != first


def test_status_lists_the_entry(make_deps, staged, capsys):
    deps = make_deps()
    e = entry(staged)
    record_pending(deps.cache_dir, e)
    listed = list_pending(deps.cache_dir)
    assert [(x["id"], x["state"]) for x in listed] == [(e["id"], "en_attente")]
    assert main(["update", "status", "--json"], deps) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [x["id"] for x in payload["pending"]] == [e["id"]]
    assert payload["provenance"]["game_version"]


def test_recording_twice_keeps_an_approved_entry(make_deps, staged):
    deps = make_deps()
    e = entry(staged)
    save_report(deps.cache_dir, report())
    record_pending(deps.cache_dir, e)
    approve(deps, e["id"], spawn=Spawn())
    record_pending(deps.cache_dir, e)  # le passage suivant recalcule la même attente
    assert list_pending(deps.cache_dir)[0]["state"] == "approuvée"


def test_approve_with_an_unchanged_base_spawns_a_run(make_deps, staged):
    deps = make_deps()
    e = entry(staged)
    save_report(deps.cache_dir, report())
    record_pending(deps.cache_dir, e)
    spawn = Spawn()
    out = approve(deps, e["id"], spawn=spawn)
    assert out["state"] == "approuvée"
    assert len(spawn.calls) == 1
    assert "update" in spawn.calls[0] and "--auto" in spawn.calls[0]
    assert list_pending(deps.cache_dir)[0]["state"] == "approuvée"


def test_approve_survives_a_failing_spawn(make_deps, staged):
    deps = make_deps()
    e = entry(staged)
    save_report(deps.cache_dir, report())
    record_pending(deps.cache_dir, e)
    out = approve(deps, e["id"], spawn=Spawn(fail=True))
    assert out["state"] == "approuvée" and "forever update" in out["detail"]


def test_approve_after_main_moved_makes_the_entry_stale(make_deps, staged):
    deps = make_deps()
    e = entry(staged)
    record_pending(deps.cache_dir, e)
    save_report(deps.cache_dir, report(origin_main=MOVED))
    spawn = Spawn()
    out = approve(deps, e["id"], spawn=spawn)
    assert out["state"] == "périmée" and spawn.calls == []
    assert list_pending(deps.cache_dir)[0]["state"] == "périmée"


def test_approve_after_the_staging_was_rewritten_makes_the_entry_stale(make_deps, staged):
    deps = make_deps()
    e = entry(staged)
    save_report(deps.cache_dir, report())
    record_pending(deps.cache_dir, e)
    (staged / "talents.json").write_bytes(b'{"a": 3}\n')
    out = approve(deps, e["id"], spawn=Spawn())
    assert out["state"] == "périmée"


def test_reject_keeps_the_reason(make_deps, staged, capsys):
    deps = make_deps()
    e = entry(staged)
    record_pending(deps.cache_dir, e)
    out = reject(deps.cache_dir, e["id"], "valeur à vérifier en jeu")
    assert out["state"] == "rejetée" and out["reason"] == "valeur à vérifier en jeu"
    assert list_pending(deps.cache_dir)[0]["reason"] == "valeur à vérifier en jeu"


def test_a_blocked_entry_is_not_approvable(make_deps, staged, capsys):
    deps = make_deps()
    e = entry(staged, action="bloqué")
    save_report(deps.cache_dir, report())
    record_pending(deps.cache_dir, e)
    spawn = Spawn()
    with pytest.raises(ForeverError) as err:
        approve(deps, e["id"], spawn=spawn)
    assert err.value.exit_code == EXIT_USAGE and spawn.calls == []
    assert main(["update", "approve", e["id"]], deps) == EXIT_USAGE
    assert list_pending(deps.cache_dir)[0]["state"] == "en_attente"


def test_unknown_entry_is_not_found(make_deps, capsys):
    deps = make_deps()
    assert main(["update", "approve", "1.60.1.79999-r1-000000000000"], deps) == EXIT_NOT_FOUND
    assert main(["update", "reject", "1.60.1.79999-r1-000000000000"], deps) == EXIT_NOT_FOUND


def test_cli_reject(make_deps, staged, capsys):
    deps = make_deps()
    e = entry(staged)
    record_pending(deps.cache_dir, e)
    assert main(["update", "reject", e["id"], "--reason", "plus tard", "--json"], deps) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "rejetée"


# --- Rapport et résumé ----------------------------------------------------------------------------------------


def test_save_report_keeps_last_and_a_short_history(make_deps):
    deps = make_deps()
    for i in range(32):
        save_report(deps.cache_dir, {**report(), "started_at": f"2026-10-06T08:{i:02d}:00Z"})
    folder = update_dir(deps.cache_dir)
    assert json.loads((folder / "last.json").read_text(encoding="utf-8"))["started_at"] == "2026-10-06T08:31:00Z"
    history = json.loads((folder / "history.json").read_text(encoding="utf-8"))
    assert len(history) == 30 and history[-1]["started_at"] == "2026-10-06T08:31:00Z"


def test_summary_without_state(make_deps):
    summary = update_summary(make_deps().cache_dir)
    assert summary["last"] is None and summary["pending"] == [] and summary["running"] is False


def test_summary_counts_open_entries_only(make_deps, staged):
    deps = make_deps()
    save_report(deps.cache_dir, report())
    open_entry = entry(staged)
    closed = entry(staged, ident=f"{VERSION}-r2-000000000000")
    record_pending(deps.cache_dir, open_entry)
    record_pending(deps.cache_dir, closed)
    reject(deps.cache_dir, closed["id"], None)
    summary = update_summary(deps.cache_dir)
    assert [p["id"] for p in summary["pending"]] == [open_entry["id"]]
    assert summary["last"]["origin_main"] == ORIGIN and summary["last"]["finished_at"] == "2026-10-06T08:05:00Z"


def test_mcp_status_carries_a_read_only_update_block(make_deps, staged):
    deps = make_deps()
    save_report(deps.cache_dir, report())
    record_pending(deps.cache_dir, entry(staged))

    async def go():
        async with Client(build_server(deps)) as client:
            tools = await client.list_tools()
            result = await client.call_tool("forever_status", {"offline": True})
            return {t.name for t in tools.tools}, result

    names, result = asyncio.run(go())
    assert not result.is_error
    block = result.structured_content["update"]
    assert len(block["pending"]) == 1 and block["last"]["origin_main"] == ORIGIN
    assert not any("approve" in n or "update" in n for n in names)  # aucun outil MCP n'écrit ni n'approuve
