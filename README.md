# Kit de développement forever-core pour Claude Code

Ce kit se dépose à la racine d'un dépôt vide. Il donne à Claude Code un cadre de travail complet :
un `CLAUDE.md` court et vivant, des règles qui ne se chargent que dans les bons dossiers, des skills pour les
procédures, des hooks pour ce qui doit être garanti, une feuille de route en tranches vérifiables et du code de départ validé.

## Qui fait quoi
| Élément | Rôle | Garantie |
| --- | --- | --- |
| `CLAUDE.md` (~35 lignes) | Contexte permanent : commandes, invariants du domaine, zones protégées, façon de travailler | Consultatif |
| `.claude/rules/` | Règles chargées seulement quand Claude touche `forever/engine/`, `forever/data/` ou les outils | Consultatif, ciblé |
| `.claude/skills/` | Procédures : `/tranche` (TDD complet), `/verifier` (preuves de fin), `/revue` | Déclenchement manuel ou automatique |
| `.claude/agents/` | Relecteur et auditeur du registre, en lecture seule, avec un regard neuf | Contexte séparé |
| `.claude/hooks/` + `settings.json` | Zones protégées, tests verrouillés en phase verte, tests avant l'arrêt, formatage ruff, permissions | **Déterministe** |
| `tasks.py`, `scripts/`, CI | `uv run tasks.py verify` : lint, typage, tests (réseau coupé), registre, chiffres de jeu | **Déterministe** |
| `docs/` | Spécification, architecture, 13 tranches, registre de 97 mécaniques, sources, décisions, questions | Référence |
| `prompts/` | Cadrage, relecture du plan par un second Claude, nouvelle version du jeu | À coller |
| `seed/` | Skill Mage validé et moteur de raid vérifié, à porter (lecture seule) | Protégé |

## Prérequis
Claude Code à jour, Git, `uv` (il installe Python tout seul), un dépôt GitHub privé. Aucun `make` nécessaire : toutes les commandes passent par `uv run tasks.py <commande>` et fonctionnent sous Windows, macOS et Linux.

## Mode d'emploi
1. **Préparer** : crée le dépôt `forever-core`, décompresse le kit à la racine, `uv sync`, puis `uv run tasks.py verify` (vert sur un projet vide ; dans Claude Code : `!uv run tasks.py verify`), premier commit, push.
2. **Cadrer** : lance `claude`, mode plan (Maj+Tab deux fois), colle `prompts/00-cadrage.md`. Réponds à ses questions ; il écrit `tasks/T01-plan.md`.
3. **Faire relire le plan** : dans une autre session, colle `prompts/05-revue-plan.md`. Reporte les corrections utiles dans le plan.
4. **Exécuter** : nouvelle session, `/tranche T01`. Il écrit les tests, les committe en rouge, les verrouille, implémente jusqu'au vert, lance `/verifier`.
5. **Relire le code** : `/revue`. Tu fusionnes si c'est propre.
6. **Recommencer** avec T02, T03… Une tranche par session. Tranches indépendantes en parallèle : un `git worktree` et une session par tranche.

## Faire vivre CLAUDE.md
- **Quand Claude se trompe** : corrige, puis dis « mets à jour CLAUDE.md pour ne plus refaire cette erreur ». N'ajoute une ligne au fichier partagé que si l'erreur se répète ou qu'une revue l'attrape. Demande-toi où la mettre : CLAUDE.md, une règle de `.claude/rules/`, la section « Pièges » d'un skill, ou un hook si elle doit être garantie.
- **En revue de PR** : installe l'action GitHub avec `/install-github-action`, puis tague `@claude` sur une PR pour qu'il ajoute la leçon au CLAUDE.md dans la PR même.
- **Contrôler** : `/context` pour voir ce qui est chargé, `/doctor` pour repérer les lignes à couper. Si une règle présente est ignorée, le fichier est trop long ou la règle ambiguë.
- **Élaguer** à chaque nouveau modèle ou tous les six mois : retire les lignes de style et de procédure, réintroduis-les seulement si l'erreur revient. **Ne retire jamais les invariants du domaine** : ce sont des faits sur ton projet, pas des béquilles pour le modèle.
- **Préférences personnelles** : dans `CLAUDE.local.md` (ignoré par Git) ou `~/.claude/CLAUDE.md`, jamais dans le fichier partagé.

## Ce que toi seul fais
Valider chaque plan et chaque fusion, trancher le périmètre, vérifier en jeu les règles marquées `suppose` (`docs/OPEN_QUESTIONS.md`), exporter ta fiche de personnage, et repérer un chiffre absurde avec ton œil de joueur.
