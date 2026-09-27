---
name: verifier
description: Vérifie qu'une tâche est vraiment terminée dans forever-core (uv run tasks.py verify, registre, provenance) et en présente les preuves. À utiliser avant d'annoncer qu'un travail est fini.
---
# Vérification

1. Lancer `uv run tasks.py verify` et lire la sortie complète.
2. Si des mécaniques ont changé : vérifier leur entrée dans `docs/MECHANICS_REGISTRY.yaml` (statut, source, tests existants).
3. Si un outil CLI ou MCP a changé : lancer l'outil une fois et vérifier que le bloc `provenance` est complet.
4. Présenter les preuves, pas une affirmation : les dernières lignes de `uv run tasks.py verify`, le nombre de tests passés, la couverture du registre, et toute régression.
5. Si quelque chose échoue : le dire en premier, avec la prochaine action.
