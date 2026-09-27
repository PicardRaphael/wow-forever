"""Ligne d'état : version des données du jeu et statut de fraîcheur (lit le cache de `forever status`)."""
import json
import os
import pathlib
import sys

sys.stdin.read()  # Claude Code envoie l'état de session ; il n'est pas utilisé ici
root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
manifest = root / "forever/data/manifest.json"
cache = pathlib.Path(os.path.expanduser("~/.cache/forever/status.json"))
version = json.loads(manifest.read_text(encoding="utf-8")).get("game_version", "?") if manifest.exists() else "données absentes"
status = json.loads(cache.read_text(encoding="utf-8")).get("freshness", "inconnu") if cache.exists() else "non vérifié"
icon = {"fresh": "OK", "stale": "MAJ DISPO", "unknown": "?", "silent": "SILENCE"}.get(status, status)
print(f"Forever {version} · {icon}")
