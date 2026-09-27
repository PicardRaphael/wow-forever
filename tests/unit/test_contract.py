"""Contrat des sorties (critère 5) : chaque commande, succès et erreurs, porte une provenance complète.

En texte, la dernière ligne (stdout pour un résultat ou un rapport, stderr pour une erreur) contient les 7 champs.
En --json, l'objet renvoyé contient un bloc `provenance` valide."""

import json

import pytest
from conftest import LOCAL_VERSION, FakeHttp, tamper

from forever.cli import main
from forever.provenance import validate_provenance

LABELS = ["version ", "données ", "générée ", "fraîcheur ", "certitude ", "registre ", "hypothèses : "]

CASES = {
    "status": (["status"], 0, None),
    "status-offline": (["status", "--offline"], 0, None),
    "status-integrity": (["status"], 3, "tamper"),
    "lookup": (["lookup", "spell", "frostbolt", "--rank", "2"], 0, None),
    "lookup-all": (["lookup", "spell", "fireball", "--detail"], 0, None),
    "lookup-unknown-spell": (["lookup", "spell", "frostbollt"], 4, None),
    "lookup-unknown-rank": (["lookup", "spell", "frostbolt", "--rank", "12"], 4, None),
    "lookup-unsupported": (["lookup", "spell", "blink"], 4, None),
    "lookup-invalid-limit": (["lookup", "spell", "frostbolt", "--limit", "0"], 2, None),
    "lookup-integrity": (["lookup", "spell", "frostbolt"], 3, "tamper"),
    "lookup-no-manifest": (["lookup", "spell", "frostbolt"], 3, "no-manifest"),
    "manifest-check": (["manifest", "--check"], 0, None),
    "manifest-check-integrity": (["manifest", "--check"], 3, "tamper"),
    "manifest-check-no-manifest": (["manifest", "--check"], 3, "no-manifest"),
    "manifest-update": (["manifest", "--update"], 0, None),
}


def prepare(data_copy, alteration):
    if alteration == "tamper":
        tamper(data_copy / LOCAL_VERSION / "spells.json")
    elif alteration == "no-manifest":
        (data_copy / "manifest.json").unlink(missing_ok=True)


@pytest.mark.parametrize("case", CASES)
def test_text_output_ends_with_provenance(case, capsys, make_deps, data_copy):
    argv, expected_code, alteration = CASES[case]
    prepare(data_copy, alteration)
    code = main(argv, make_deps(data_dir=data_copy, http=FakeHttp.fixture("builds_fresh.json")))
    out, err = capsys.readouterr()
    assert code == expected_code
    stream = out if out.strip() else err  # un rapport (même en échec) sur stdout, une erreur seule sur stderr
    last = stream.rstrip("\n").splitlines()[-1]
    assert last.startswith("Provenance")
    for label in LABELS:
        assert label in last, label


@pytest.mark.parametrize("case", CASES)
def test_json_output_has_valid_provenance(case, capsys, make_deps, data_copy):
    argv, expected_code, alteration = CASES[case]
    prepare(data_copy, alteration)
    code = main([*argv, "--json"], make_deps(data_dir=data_copy, http=FakeHttp.fixture("builds_fresh.json")))
    out, _ = capsys.readouterr()
    assert code == expected_code
    data = json.loads(out)
    assert validate_provenance(data["provenance"]) == []
    if code != 0 and not case.startswith("status"):  # status en échec reste un rapport complet
        assert {"code", "message", "action"} <= set(data["error"])
