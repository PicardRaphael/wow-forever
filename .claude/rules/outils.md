---
paths:
  - "forever/cli.py"
  - "forever/mcp_server.py"
  - "forever/cli/**"
  - "forever/mcp/**"
  - "plugin/**"
---
# Outils exposés (CLI, MCP, plugin)
- Bloc `provenance` complet dans chaque réponse : `game_version`, `data_sha`, `generated_at`, `freshness`, `certainty`, `assumptions`, `registry_coverage`. Un test de contrat le vérifie pour chaque outil.
- Réponses compactes par défaut (`detail=false`), pagination pour les listes, messages d'erreur qui disent quoi faire.
- Le plugin appelle les outils MCP ; il ne calcule rien et ne contient aucun chiffre de jeu.
