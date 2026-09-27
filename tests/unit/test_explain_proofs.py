"""`forever explain-mechanic` affiche les preuves de journal du registre (T04)."""

import json

from forever.cli import main


def test_explain_shows_log_proof(capsys, make_deps):
    assert main(["explain-mechanic", "B1", "--json"], make_deps()) == 0
    (proof,) = json.loads(capsys.readouterr().out)["proofs"]
    assert proof["n"] == 3 and proof["journal"].endswith(".anon.txt")
    assert main(["explain-mechanic", "B1"], make_deps()) == 0
    assert "Preuve de journal : tests/fixtures/combatlog/" in capsys.readouterr().out
