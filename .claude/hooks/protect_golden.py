"""PreToolUse (Edit|Write|MultiEdit) : bloque l'écriture dans les zones protégées.
- tests/golden/ et le manifeste : seulement avec FOREVER_ALLOW_GOLDEN=1 (accord de l'utilisateur).
- seed/ : jamais (code de référence en lecture seule).
- fichiers listés dans tasks/.tests-verrouilles : pas pendant la phase verte d'une tranche."""

import json
import os
import pathlib
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)
cwd = data.get("cwd") or os.getcwd()
path = (data.get("tool_input") or {}).get("file_path") or ""
if not path:
    sys.exit(0)
rel = os.path.relpath(path, cwd).replace(os.sep, "/")


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


if rel.startswith("seed/"):
    block(
        f"Écriture refusée : {rel} est dans seed/, code de référence en lecture seule. "
        "Porte le code dans forever/ au lieu de modifier la source."
    )
if (rel.startswith("tests/golden/") or rel == "forever/data/manifest.json") and os.environ.get(
    "FOREVER_ALLOW_GOLDEN"
) != "1":
    block(
        f"Écriture refusée : {rel} est un fichier de référence. Montre à l'utilisateur l'écart attendu et sa cause, "
        "puis demande-lui de relancer Claude Code avec FOREVER_ALLOW_GOLDEN=1 s'il l'accepte. "
        "La justification ira dans le message de commit."
    )
locked = pathlib.Path(cwd, "tasks/.tests-verrouilles")
if locked.exists():
    files = {line.strip() for line in locked.read_text(encoding="utf-8").splitlines() if line.strip()}
    if rel in files:
        block(
            f"Écriture refusée : {rel} contient des tests committés en phase rouge. Implémente le code pour les faire passer ; "
            "si un test te semble faux, arrête-toi et explique pourquoi à l'utilisateur."
        )
sys.exit(0)
