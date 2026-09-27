"""Contrat des sorties (critère 5) : chaque commande, succès et erreurs, porte une provenance complète.

En texte, la dernière ligne (stdout pour un résultat ou un rapport, stderr pour une erreur) contient les 7 champs.
En --json, l'objet renvoyé contient un bloc `provenance` valide.
Les erreurs d'usage d'argparse (code 2) sont couvertes comme les autres erreurs.
Exclusions : `--help` (aide d'argparse, code 0, ce n'est pas un résultat d'outil) et `forever mcp`
(serveur stdio, couvert par tests/integration/)."""

import json

import pytest
from conftest import (
    COMBATLOG,
    FIXTURES,
    LOCAL_VERSION,
    REAL_LOG,
    SYNTHETIC_LOGS,
    WAGO_70009,
    FakeHttp,
    corrupt_manifest,
    tamper,
)

from forever.cli import main
from forever.provenance import validate_provenance

QUESTIE = FIXTURES / "questie" / "11.38.0"

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
    "status-corrupt-manifest": (["status"], 3, "corrupt-manifest"),
    "lookup-corrupt-manifest": (["lookup", "spell", "frostbolt"], 3, "corrupt-manifest"),
    "manifest-check-corrupt-manifest": (["manifest", "--check"], 3, "corrupt-manifest"),
    "explain": (["explain-mechanic", "A5"], 0, None),
    "explain-absent": (["explain-mechanic", "A1"], 0, None),
    "explain-unknown": (["explain-mechanic", "Z9"], 4, None),
    "explain-integrity": (["explain-mechanic", "A5"], 3, "tamper"),
    "builds": (["builds"], 0, None),
    "builds-offline": (["builds", "--offline"], 5, None),
    "fetch-failed": (["fetch", "--version", LOCAL_VERSION, "--tables", "SpellName"], 5, None),
    "fetch-invalid-version": (["fetch", "--version", "1.60.x", "--tables", "SpellName"], 2, None),
    "usage-fetch-no-version": (["fetch"], 2, None),
    "decode": (["decode", "--version", LOCAL_VERSION, "--csv-dir", str(WAGO_70009)], 0, None),
    "decode-missing-csv": (["decode", "--version", LOCAL_VERSION], 4, None),
    "diff-same": (["diff", LOCAL_VERSION, LOCAL_VERSION], 0, None),
    "diff-unknown": (["diff", LOCAL_VERSION, "1.60.1.99999"], 4, None),
    "diff-integrity": (["diff", LOCAL_VERSION, LOCAL_VERSION], 3, "tamper"),
    "verify": (["verify"], 0, None),
    "verify-integrity": (["verify"], 3, "tamper"),
    "report": (["report", LOCAL_VERSION, LOCAL_VERSION], 0, None),
    "report-unknown": (["report", LOCAL_VERSION, "1.60.1.99999"], 4, None),
    "usage-diff-missing-args": (["diff"], 2, None),
    "usage-no-command": ([], 2, None),
    "usage-unknown-command": (["inconnu"], 2, None),
    "usage-lookup-missing-args": (["lookup"], 2, None),
    "usage-lookup-bad-rank": (["lookup", "spell", "frostbolt", "--rank", "deux"], 2, None),
    "usage-manifest-no-mode": (["manifest"], 2, None),
    "usage-explain-missing-id": (["explain-mechanic"], 2, None),
    "logs-scan": (["logs", "scan", "--dir", str(COMBATLOG)], 0, None),
    "logs-scan-missing": (["logs", "scan", "--dir", str(COMBATLOG / "absent")], 4, None),
    "logs-measure": (["logs", "measure", str(REAL_LOG)], 0, None),
    "logs-measure-unsupported": (["logs", "measure", str(SYNTHETIC_LOGS / "version21.txt")], 3, None),
    "logs-measure-truncated": (["logs", "measure", str(SYNTHETIC_LOGS / "truncated.txt")], 3, None),
    "usage-logs-no-subcommand": (["logs"], 2, None),
    "questie-info": (["questie", "info", "--dir", str(QUESTIE)], 0, None),
    "questie-info-missing": (["questie", "info", "--dir", str(COMBATLOG / "absent")], 4, None),
    "monsters-build": (
        ["monsters", "build", "--logs", str(COMBATLOG), "--questie", str(QUESTIE), "--out", "{tmp}/m", "--force"],
        0,
        None,
    ),
    "monsters-build-into-data": (["monsters", "build", "--logs", str(COMBATLOG), "--out", "{data}/x"], 2, None),
    "usage-monsters-no-logs": (["monsters", "build"], 2, None),
    # T04b : simulateur et graphique de leveling
    "sim-leveling": (["sim", "leveling", "--level", "12", "--n", "20"], 0, None),
    "sim-leveling-illegal": (["sim", "leveling", "--level", "12", "--talents", "improvedFrostbolt=5"], 2, None),
    "sim-leveling-integrity": (["sim", "leveling", "--level", "12", "--n", "5"], 3, "tamper"),
    "chart-leveling": (
        ["chart", "leveling", "--out", "{tmp}/c.png", "--from", "12", "--to", "13", "--n", "5"],
        0,
        None,
    ),
    "usage-sim-no-level": (["sim", "leveling"], 2, None),
    "usage-chart-no-out": (["chart", "leveling"], 2, None),
}


def expand(argv, data_copy):
    """Chemins de sortie propres au test : {tmp} (dossier temporaire) et {data} (copie des données)."""
    return [a.replace("{tmp}", str(data_copy.parent)).replace("{data}", str(data_copy)) for a in argv]


def prepare(data_copy, alteration):
    if alteration == "tamper":
        tamper(data_copy / LOCAL_VERSION / "spells.json")
    elif alteration == "no-manifest":
        (data_copy / "manifest.json").unlink(missing_ok=True)
    elif alteration == "corrupt-manifest":
        corrupt_manifest(data_copy)


@pytest.mark.parametrize("case", CASES)
def test_text_output_ends_with_provenance(case, capsys, make_deps, data_copy):
    argv, expected_code, alteration = CASES[case]
    prepare(data_copy, alteration)
    argv = expand(argv, data_copy)
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
    argv = expand(argv, data_copy)
    code = main([*argv, "--json"], make_deps(data_dir=data_copy, http=FakeHttp.fixture("builds_fresh.json")))
    out, _ = capsys.readouterr()
    assert code == expected_code
    data = json.loads(out)
    assert validate_provenance(data["provenance"]) == []
    if code != 0 and not case.startswith("status"):  # status en échec reste un rapport complet
        assert {"code", "message", "action"} <= set(data["error"])


def test_help_is_excluded(capsys, make_deps):
    """Exclusion documentée : l'aide d'argparse sort avec le code 0, sans ligne provenance."""
    assert main(["--help"], make_deps()) == 0
    assert "Provenance" not in capsys.readouterr().out
