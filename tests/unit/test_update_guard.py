"""Plus de garde-fou de la première écriture de `forever update --auto` (décision 295, qui retire celui de la
décision 184) : la veille installe d'elle-même dès son premier passage automatique, sans aucune approbation, et
aucune attente d'accord d'avant la décision ne reste ouverte."""

from test_update_chain import DRY, montage, only_verdict  # noqa: F401  (fixture importée)

import forever.update as update_module
from forever.update import UpdateOptions, close_legacy_waits, list_pending, record_pending, run_update

AUTO_DRY = UpdateOptions(auto=True, dry_run=True)


def test_there_is_no_first_write_guard_anymore():
    assert not hasattr(update_module, "first_write_guard") and not hasattr(update_module, "GUARD_REASON")


def test_a_first_automatic_write_is_written(montage):  # noqa: F811
    deps, _ = montage()
    report = run_update(deps, AUTO_DRY)
    verdict = only_verdict(report)
    assert verdict["action"] == "écrire" and not any("garde-fou" in r for r in verdict["reasons"])
    assert report["pending"] == []


def test_waits_for_approval_from_before_the_decision_are_closed(make_deps):
    deps = make_deps()
    for pending_id, kind, action in (
        ("1.60.1.70450-r10-21a566d58007", "install_revision", "attente"),
        ("measures-1.60.1.70450-aaaaaaaaaaaa", "measures", "attente"),
        ("network-1.60.1.70450", "network", "attente"),  # se lève seule : gardée
        ("1.60.1.70450-r11-bbbbbbbbbbbb", "install_revision", "bloqué"),  # intégrité : gardée
    ):
        record_pending(deps.cache_dir, {"id": pending_id, "kind": kind, "action": action, "version": "1.60.1.70450"})
    closed = close_legacy_waits(deps.cache_dir, "2026-10-22T12:00:00Z")
    assert sorted(closed) == ["1.60.1.70450-r10-21a566d58007", "measures-1.60.1.70450-aaaaaaaaaaaa"]
    states = {e["id"]: e["state"] for e in list_pending(deps.cache_dir)}
    assert states["network-1.60.1.70450"] == "en_attente" and states["1.60.1.70450-r11-bbbbbbbbbbbb"] == "en_attente"
    assert states["1.60.1.70450-r10-21a566d58007"] == "périmée"
