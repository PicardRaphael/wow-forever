"""`forever explain-mechanic` affiche les preuves de journal du registre (T04)."""

import json

from forever.cli import main


def test_explain_shows_log_proof(capsys, make_deps):
    assert main(["explain-mechanic", "B1", "--json"], make_deps()) == 0
    (proof,) = json.loads(capsys.readouterr().out)["proofs"]
    # T04b : une preuve sur deux journaux (liste), écarts à la recharge globale déclarés
    assert proof["n"] == 50 and [j.rsplit(".anon.", 1)[1] for j in proof["journal"]] == ["txt", "txt.gz"]
    assert (proof["ecart_median_s"], proof["ecart_p10_s"]) == (0.011, 0.0431)
    assert main(["explain-mechanic", "B1"], make_deps()) == 0
    out = capsys.readouterr().out
    assert "Preuve de journal : tests/fixtures/combatlog/WoWCombatLog-092726_145346.anon.txt, tests/" in out
    assert "écart médian 0,011 s, écart du 10e percentile 0,0431 s" in out
