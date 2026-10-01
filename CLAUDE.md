# forever-core

Système expert World of Warcraft: Forever : cœur de calcul Python (`forever/`), CLI, serveur MCP, données versionnées par version du jeu (`forever/data/`), plugin Claude Code léger (`plugin/`, sans logique de calcul).
À lire selon la tâche : spécification `docs/SPEC.md`, architecture `docs/ARCHITECTURE.md`, tranches `docs/ROADMAP.md`, mécaniques `docs/MECHANICS_REGISTRY.yaml`.

<!-- Mainteneurs : chaque ligne doit empêcher une erreur réelle de Claude. Ajouter une ligne quand l'erreur se répète ou qu'une revue l'attrape ; relire en PR comme du code. Propriétaire : Raphaël. Dernier élagage : 2026-09-26 (Opus 5.5). -->

## Commandes
- `uv run tasks.py test-fast` : tests unitaires rapides. `uv run tasks.py test` : tous les tests. Un seul test : `uv run pytest tests/<fichier>.py::<test> -q`.
- `uv run tasks.py verify` : lint + typage + tests + registre + contrôle des chiffres + origine des valeurs (`origins.json`). Une tâche n'est finie que si `uv run tasks.py verify` est vert (voir le skill `/verifier`).
- `uv run forever status` : fraîcheur des données.
- Dépendances et exécution via `uv` uniquement (`uv add`, `uv run`), jamais `pip`.

## Invariants du domaine
- IMPORTANT : aucun chiffre de jeu hors de `forever/data/` : ni dans `plugin/`, un skill, un prompt ou un commentaire. Un test prend ses valeurs dans `tests/fixtures/` ou cite sa source.
- Toute formule de combat vit dans `forever/engine/`, en fonctions pures. Simulateurs, optimiseurs, CLI et MCP l'appellent ; ils ne recalculent rien.
- Chaque résultat d'outil (CLI, MCP) porte un bloc `provenance` : version du jeu, empreinte des données, date, certitude (`certain`, `probable`, `suppose`).
- Toute mécanique ajoutée ou modifiée met à jour son entrée dans `docs/MECHANICS_REGISTRY.yaml` (statut, source, tests).
- Règle de jeu incertaine : ne pas deviner. Marquer `suppose` avec une note et ajouter la question dans `docs/OPEN_QUESTIONS.md`. Un comportement que Blizzard a reconnu comme bug (message officiel ou correctif annoncé) n'est jamais modélisé.
- Pas de réseau dans les tests (`tests/fixtures/` seulement). Les sources locales du client (journaux, addons, SavedVariables, dossier `FOREVER_WOW_DIR`) se lisent sur disque, jamais par le réseau, et jamais dans les tests. Seuls `forever status`, l'outil MCP `forever_status`, `forever builds`, `forever fetch`, `forever notes` (lancé à la main seulement, décision 148) et `forever api probe` (API Blizzard, décision 149) touchent Internet (via `forever/pipeline/`).

## Addon (`addon/`, règles détaillées dans `docs/ADDON.md`)
- SavedVariable initialisée dans le gestionnaire d'`ADDON_LOADED` ; jamais d'alias local au niveau du fichier.
- `pcall` autour de chaque `RegisterEvent` et de chaque API incertaine (talents, bonus des sorts, valeurs secrètes).
- Aucune fonction d'action (`CastSpell*`, `UseAction`, `RunMacro*`, `SendChatMessage` automatique) ; ni pixels, ni lecture d'écran, ni entrées simulées.
- Aucun abonnement au journal de combat (`COMBAT_LOG_EVENT*`) : l'analyse des combats se fait toujours hors du jeu, sur `WoWCombatLog-*.txt`.
- Contrôle : `uv run python scripts/check_addon.py` (et `tests/unit/test_addon_rules.py`).

## Zones protégées
- `tests/golden/` : ne jamais régénérer pour faire passer un test. Si un changement voulu les modifie, s'arrêter, expliquer pourquoi et demander l'accord ; la justification va dans le message de commit. Un hook bloque l'écriture.
- `seed/forever-mage/` et `seed/grimoire-engine/` : code de référence validé, à porter, en lecture seule.

## Façon de travailler
- Une tranche de `docs/ROADMAP.md` à la fois, dans l'ordre, via `/tranche Txx` : plan écrit directement dans `tasks/Txx-plan.md` (sans mode plan ni code), committé sur `main`, arrêt pour validation ; puis exécution dans une nouvelle session.
- Exécution dans le dépôt principal (pas de worktree) sur une branche `txx`. Fin de tranche : pousser la branche, attendre la CI verte sous Ubuntu et Windows, fusionner soi-même en fast-forward dans `main`, pousser `main`, supprimer la branche locale et distante.
- Tests d'abord : écrire les tests, constater l'échec, committer, puis implémenter jusqu'au vert sans modifier ces tests.
- Petits commits, message `Txx: <ce qui change>`.
- Continuer sans demander tant qu'une étape n'a pas besoin de moi. S'arrêter et demander avant : toucher `tests/golden/`, ajouter une dépendance, un accès réseau, supprimer des données, trancher une règle de jeu.
- Fin de tranche : `/verifier`, puis un résumé avec, dans l'ordre : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes, Angles morts (mécaniques absentes du registre qui influencent les résultats, avec leur effet estimé).

## Code
- Identifiants en anglais ; commentaires, docstrings, documentation et messages affichés à l'utilisateur en français.
