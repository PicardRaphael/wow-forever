"""Garde-fou de la première écriture git de `forever update --auto` (T08d, demande de l'utilisateur du 2026-10-06).

Tant qu'aucun passage réel n'a été approuvé, une écriture que la règle d'automatisme permettrait reste en attente
de l'accord de l'utilisateur quand le passage est automatique ; un passage lancé à la main n'est pas concerné. Le
garde-fou tombe à la première approbation d'une installation."""

from test_update_chain import DRY, montage, only_verdict  # noqa: F401  (fixture importée)

from forever.update import UpdateOptions, approve, first_write_guard, record_pending, run_update

AUTO_DRY = UpdateOptions(auto=True, dry_run=True)


def test_the_guard_is_up_until_a_first_approval(montage):  # noqa: F811
    deps, _ = montage()
    assert first_write_guard(deps.cache_dir) is True


def test_an_automatic_write_waits_while_the_guard_is_up(montage):  # noqa: F811
    deps, _ = montage()
    report = run_update(deps, AUTO_DRY)
    verdict = only_verdict(report)
    assert verdict["rule_action"] == "écrire" and verdict["action"] == "attente"
    assert any("garde-fou" in r for r in verdict["reasons"])
    assert [p["kind"] for p in report["pending"]] == ["install_version"]


def test_a_manual_run_is_not_held_by_the_guard(montage):  # noqa: F811
    deps, _ = montage()
    assert only_verdict(run_update(deps, DRY))["action"] == "écrire"


def test_the_first_approval_lifts_the_guard(montage):  # noqa: F811
    deps, _ = montage()
    entry = run_update(deps, AUTO_DRY)["pending"][0]
    record_pending(deps.cache_dir, entry)
    approve(deps, entry["id"], spawn=lambda args: None)
    assert first_write_guard(deps.cache_dir) is False
    assert only_verdict(run_update(deps, AUTO_DRY))["action"] == "écrire"
