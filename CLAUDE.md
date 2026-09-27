# forever-core

Système expert World of Warcraft: Forever : cœur de calcul Python (`forever/`), CLI, serveur MCP, données versionnées par version du jeu (`forever/data/`), plugin Claude Code léger (`plugin/`, sans logique de calcul).
À lire selon la tâche : spécification `docs/SPEC.md`, architecture `docs/ARCHITECTURE.md`, tranches `docs/ROADMAP.md`, mécaniques `docs/MECHANICS_REGISTRY.yaml`.

<!-- Mainteneurs : chaque ligne doit empêcher une erreur réelle de Claude. Ajouter une ligne quand l'erreur se répète ou qu'une revue l'attrape ; relire en PR comme du code. Propriétaire : Raphaël. Dernier élagage : 2026-09-26 (Opus 5.5). -->

## Commandes
- `uv run tasks.py test-fast` : tests unitaires rapides. `uv run tasks.py test` : tous les tests. Un seul test : `uv run pytest tests/<fichier>.py::<test> -q`.
- `uv run tasks.py verify` : lint + typage + tests + registre + contrôle des chiffres. Une tâche n'est finie que si `uv run tasks.py verify` est vert (voir le skill `/verifier`).
- `uv run forever status` : fraîcheur des données.
- Dépendances et exécution via `uv` uniquement (`uv add`, `uv run`), jamais `pip`.

## Invariants du domaine
- IMPORTANT : aucun chiffre de jeu hors de `forever/data/` : ni dans `plugin/`, un skill, un prompt ou un commentaire. Un test prend ses valeurs dans `tests/fixtures/` ou cite sa source.
- Toute formule de combat vit dans `forever/engine/`, en fonctions pures. Simulateurs, optimiseurs, CLI et MCP l'appellent ; ils ne recalculent rien.
- Chaque résultat d'outil (CLI, MCP) porte un bloc `provenance` : version du jeu, empreinte des données, date, certitude (`certain`, `probable`, `suppose`).
- Toute mécanique ajoutée ou modifiée met à jour son entrée dans `docs/MECHANICS_REGISTRY.yaml` (statut, source, tests).
- Règle de jeu incertaine : ne pas deviner. Marquer `suppose` avec une note et ajouter la question dans `docs/OPEN_QUESTIONS.md`. Un comportement que Blizzard a reconnu comme bug (message officiel ou correctif annoncé) n'est jamais modélisé.
- Pas de réseau dans les tests (`tests/fixtures/` seulement). Seuls `forever status`, l'outil MCP `forever_status`, `forever builds` et `forever fetch` touchent Internet (via `forever/pipeline/`).

## Zones protégées
- `tests/golden/` : ne jamais régénérer pour faire passer un test. Si un changement voulu les modifie, s'arrêter, expliquer pourquoi et demander l'accord ; la justification va dans le message de commit. Un hook bloque l'écriture.
- `seed/forever-mage/` et `seed/grimoire-engine/` : code de référence validé, à porter, en lecture seule.

## Façon de travailler
- Une tranche de `docs/ROADMAP.md` à la fois, dans l'ordre, via `/tranche Txx` : plan dans `tasks/Txx-plan.md`, puis exécution dans une nouvelle session.
- Tests d'abord : écrire les tests, constater l'échec, committer, puis implémenter jusqu'au vert sans modifier ces tests.
- Petits commits, message `Txx: <ce qui change>`.
- Continuer sans demander tant qu'une étape n'a pas besoin de moi. S'arrêter et demander avant : toucher `tests/golden/`, ajouter une dépendance, un accès réseau, supprimer des données, trancher une règle de jeu.
- Fin de tranche : `/verifier`, puis un résumé avec, dans l'ordre : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes.

## Code
- Identifiants en anglais ; commentaires, docstrings, documentation et messages affichés à l'utilisateur en français.
