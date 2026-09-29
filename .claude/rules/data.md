---
paths:
  - "forever/data/**"
---
# Données versionnées
- Un dossier par version du jeu (`forever/data/<version>/`) ; ne jamais modifier les fichiers d'une version passée : une correction crée une nouvelle version de données avec sa justification.
- La version courante se révise seulement par révision numérotée et journalisée (`forever install`, décision 98) : `--dry-run` d'abord, accord de l'utilisateur, `revisions.json` et `sources.json.revision` tenus par la commande, rapport de diff dans `docs/research/`. Les copies du seed (`_seed_*.json`) ne changent jamais.
- Chaque fichier porte ses sources (table du client, URL, date) et sa certitude.
- Après toute modification, recalculer les empreintes du manifeste avec `uv run forever manifest --update` (commande créée en T01), jamais à la main.
- Les données communautaires (PV des monstres, quêtes, butin) sont marquées comme telles et ne remplacent jamais une donnée du client.
