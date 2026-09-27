---
paths:
  - "forever/data/**"
---
# Données versionnées
- Un dossier par version du jeu (`forever/data/<version>/`) ; ne jamais modifier les fichiers d'une version passée : une correction crée une nouvelle version de données avec sa justification.
- Chaque fichier porte ses sources (table du client, URL, date) et sa certitude.
- Après toute modification, recalculer les empreintes du manifeste avec `uv run forever manifest --update` (commande créée en T01), jamais à la main.
- Les données communautaires (PV des monstres, quêtes, butin) sont marquées comme telles et ne remplacent jamais une donnée du client.
