# forever-core

Système expert World of Warcraft: Forever : cœur de calcul Python (`forever/`), CLI, serveur MCP, données versionnées par version du jeu (`forever/data/`), plugin Claude Code léger (`plugin/`, sans logique de calcul).
À lire selon la tâche : vision `docs/VISION.md`, spécification `docs/SPEC.md`, architecture `docs/ARCHITECTURE.md`, tranches `docs/ROADMAP.md`, mécaniques `docs/MECHANICS_REGISTRY.yaml`.

<!-- Mainteneurs : chaque ligne doit empêcher une erreur réelle de Claude. Ajouter une ligne quand l'erreur se répète ou qu'une revue l'attrape ; relire en PR comme du code. Propriétaire : Raphaël. Dernier élagage : 2026-09-26 (Opus 5.5). -->

## Commandes
- `uv run tasks.py quick` pendant le travail (lint, typage, tests rapides concernés par les fichiers modifiés depuis `main`, moins de 2 min) ; `uv run tasks.py verify` **une seule fois avant chaque push, jamais en boucle** ; la CI (Ubuntu et Windows) juge. Un seul test : `uv run pytest tests/<fichier>.py::<test> -q`.
- `uv run tasks.py verify` : lint + typage + suite complète en parallèle (`-n auto`) + registre + contrôle des chiffres + origine des valeurs (`origins.json`). Une tâche n'est finie que s'il est vert (voir le skill `/verifier`).
- Test long (Monte Carlo, rejeu, parité, bout en bout, plus de quelques secondes) : marqueur `slow` (hors de `quick`, toujours dans `verify` et la CI). Un test écrit dans `tmp_path`, jamais dans le dépôt ni un cache partagé (suite parallèle).
- `uv run tasks.py e2e` : bout en bout de `forever update`, CI simulée du clone comprise (long ; job `e2e` de la CI, hors de `verify`).
- `uv run forever status` : fraîcheur des données.
- Dépendances et exécution via `uv` uniquement (`uv add`, `uv run`), jamais `pip`.

## Invariants du domaine
- IMPORTANT : aucun chiffre de jeu hors de `forever/data/` : ni dans `plugin/`, un skill, un prompt ou un commentaire. Un test prend ses valeurs dans `tests/fixtures/` ou cite sa source.
- Toute formule de combat vit dans `forever/engine/`, en fonctions pures. Simulateurs, optimiseurs, CLI et MCP l'appellent ; ils ne recalculent rien.
- Chaque résultat d'outil (CLI, MCP) porte un bloc `provenance` : version du jeu, empreinte des données, date, certitude (`certain`, `probable`, `suppose`).
- Toute mécanique ajoutée ou modifiée met à jour son entrée dans `docs/MECHANICS_REGISTRY.yaml` (statut, source, tests).
- Règle de jeu incertaine : ne pas deviner. Marquer `suppose` avec une note et ajouter la question dans `docs/OPEN_QUESTIONS.md`. Un comportement que Blizzard a reconnu comme bug (message officiel ou correctif annoncé) n'est jamais modélisé.
- Pas de réseau dans les tests (`tests/fixtures/` seulement). Les sources locales du client (journaux, addons, SavedVariables, dossier `FOREVER_WOW_DIR`) se lisent sur disque, jamais par le réseau, et jamais dans les tests. Seuls `forever status`, l'outil MCP `forever_status`, `forever builds`, `forever fetch`, `forever notes` (lancé à la main seulement, décision 148) `forever api probe` (API Blizzard, décision 149), `forever hotfixes --raidbots` (caches vérifiés de Raidbots, lecture seule, décision 290), `forever route polestar` (clone des guides de Polestar en cache, lecture seule, décision 289), `forever sims update` (clone de wowsims/forever en cache et modules Go téléchargés par `go`, lecture seule, compilé tel quel, décisions 293 et 294) et `forever update` (wago.tools, WoWDBDefs, git et `gh` du clone dédié, décision 179 ; mise à jour du clone de Polestar s'il existe, décision 289 ; recompilation de wowsims/forever s'il a déjà été compilé, décisions 293 et 294) touchent Internet (via `forever/pipeline/`). Le pont de P06a (`forever bridge`) lance `claude`, qui parle à l'API d'Anthropic ; forever lui-même n'ouvre aucune connexion. Depuis P06b, le pont lance aussi `git` en local, sans réseau (sous-commandes `init`, `add`, `commit`, `status`, `diff`, `log`, `rev-parse`), dans le seul dossier de la conversation « addons », et les commandes fixées de `forever update` sur un clic en jeu (décision 235).

## Addon (`addon/`, règles détaillées dans `docs/ADDON.md`)
- SavedVariable initialisée dans le gestionnaire d'`ADDON_LOADED` ; jamais d'alias local au niveau du fichier.
- `pcall` autour de chaque `RegisterEvent` et de chaque API incertaine (talents, bonus des sorts, valeurs secrètes).
- Aucune fonction d'action (`CastSpell*`, `UseAction`, `RunMacro*`, `CreateMacro`, `SendChatMessage` automatique) ; ni pixels, ni lecture d'écran, ni entrées simulées, sauf la bande du pont de P06a (décision 194). Macros : texte à importer par le joueur seulement (décision 195).
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
- Avant tout chantier (décision 288), deux questions écrites dans le plan : « qui maintient déjà ça mieux que nous ? » et « que se passe-t-il au prochain patch ? ». Si tout casse au prochain patch, ne pas le construire : lire et alimenter ce qui existe (client, addons, simulateur de la communauté, parcours maintenus) ; notre calcul ne sert qu'en recoupement et pour combler les trous ; une nouvelle version donne un rapport des valeurs qui changent, à valider, pas des tests rouges.
- IMPORTANT : Forever seulement (décision 294). Tout calcul se base uniquement sur ce qui est fait pour WoW Forever : rien de Season of Discovery ni de la Classic, ni données ni mécanismes, aucun rapprochement ; une source qui ne couvre pas Forever n'est pas prise.
- Calculs réutilisés (décision 293) : les calculs viennent de ce qui existe et est maintenu par d'autres (simulateurs de la communauté), par des adaptateurs minces, épinglés et mis à jour automatiquement ; aucun nouveau code de calcul qui recopie une mécanique du jeu ; le code redondant est retiré ou gelé.
- Mise à jour automatique complète (décision 295) : la veille installe tout d'elle-même et prévient (carte « Mis à jour », `forever update status`, « Annuler » : `forever update undo <id>`) ; seules exceptions, dites : intégrité cassée, source injoignable, valeur écrite à la main ou correctif du serveur perdus.
- Mes addons d'abord (décision 272) : avant de construire une fonction, regarder si un addon installé la fait déjà ; si oui, s'en servir (lecture locale, agrégats) et l'alimenter par des exports, sans refaire son interface ni ses données.
- Rien n'est fini sans mon essai en jeu (décision 273) : chaque bloc qui touche au jeu se termine par une courte procédure d'essai, et une tranche ne se ferme qu'avec mon accord. Exception pour les feuilles de route (décision 279) : acceptées automatiquement si elles ressemblent au parcours gratuit de RestedXP de la même race et classe (Polestar au-delà), sinon refusées avec l'écart expliqué.
- Mon interface est la mienne (décision 274) : rien ne modifie EllesmereUI sans demande explicite.
- Fin de tranche : `/verifier`, puis un résumé avec, dans l'ordre : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes, Angles morts (mécaniques absentes du registre qui influencent les résultats, avec leur effet estimé).

## Code
- Identifiants en anglais ; commentaires, docstrings, documentation et messages affichés à l'utilisateur en français.
