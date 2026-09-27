# Audit du CLAUDE.md de forever-core au regard des pratiques de Boris Cherny et de la documentation officielle Claude Code

> Rapport de recherche du 27/09/2026 (claude.ai), recopié pour Claude Code. Le CLAUDE.md du dépôt a été réécrit d'après ce rapport. Sources principales en fin de fichier.

Le CLAUDE.md d'origine était globalement bon (court, spécifique, vérifiable, avec une boucle de vérification et des hooks). Défauts relevés : huit règles toutes « non négociables » (l'emphase ne distingue plus rien), règle du doute répétée, procédures qui relèvent d'un skill, donnée qui se périme (« 30 mécanismes testés »), exigence non outillée (« Typage partout »), conflit possible entre « committer les tests rouges » et le hook d'arrêt.

## TL;DR

- **Verdict** : fichier au-dessus de la moyenne (7/10), à alléger, désemphatiser et mieux articuler avec hooks, skills et règles à portée de chemin.
- **Boris Cherny** (fil du 2 janvier 2026) : CLAUDE.md d'équipe partagé dans Git, enrichi « chaque fois que Claude fait quelque chose de travers », environ 2,5k tokens. Depuis juillet 2026 : le supprimer périodiquement et ne réintroduire que ce qui manque. Documentation officielle : moins de 200 lignes, « Would removing this cause Claude to make mistakes? », emphase sur une seule ligne, hooks pour ce qui doit arriver sans exception.
- **Action** : version corrigée (≈ 35 lignes), règles `.claude/rules/` à portée de chemin, `/tranche` en skill, hook PostToolUse ruff, blocage de `seed/`, pytest-socket, contrôle de typage, hook d'arrêt compatible avec la phase rouge.

## 1. Ce que Boris Cherny a dit lui-même

- **Fil « how I use Claude Code » (2 janvier 2026)** : configuration « surprisingly vanilla » ; « There is no one correct way ». CLAUDE.md partagé et enrichi à chaque erreur ; tag `@claude` en revue de PR pour ajouter une leçon au CLAUDE.md (GitHub Action) ; la plupart des sessions commencent en mode plan ; commandes slash pour les boucles répétées ; sous-agents ; hook PostToolUse de formatage ; `/permissions` plutôt que `--dangerously-skip-permissions` (sauf bac à sable) ; « give Claude a way to verify its work … 2-3x the quality ».
- **Taille** : « Our checked in CLAUDE.md is 2.5k tokens » — c'est le fichier de l'équipe ; son CLAUDE.md personnel fait deux lignes. L'équivalence « ≈ 100 lignes » vient d'un article tiers.
- **Fil des conseils de l'équipe (31 janvier 2026)** : après chaque correction, « Update your CLAUDE.md so you don't make that mistake again » ; éditer impitoyablement ; transformer en skill ce qu'on fait plus d'une fois par jour ; faire relire le plan par un second Claude.
- **Podcast (février 2026)** : CLAUDE.md « pretty short » ; face à un fichier qui gonfle, le supprimer et repartir du minimum.
- **YC Startup School (juillet 2026)** : « every six months delete your Claude.md. Delete your skills. »

## 2. Documentation officielle (septembre 2026)

- **Best practices** : commandes bash, style, workflow, contexte que Claude ne peut pas déduire ; « Would removing this cause Claude to make mistakes? If not, cut it. » ; exclure ce que Claude déduit, les conventions standard, la doc d'API, l'information qui change souvent ; emphase sur une seule ligne ; hooks déterministes ; `/doctor` ; « If you could describe the diff in one sentence, skip the plan. »
- **Mémoire** : moins de 200 lignes ; imports `@chemin` chargés au lancement (n'économisent pas de contexte) ; règles `.claude/rules/*.md` avec `paths:` chargées seulement sur les fichiers visés ; commentaires HTML retirés avant injection ; ajouter une ligne quand l'erreur se répète ; pour bloquer une action, un hook PreToolUse.
- **« Steering Claude Code » (juin 2026)** : un propriétaire, relire les changements comme du code ; règles à portée de chemin ; procédures en skills ; les commandes sont fusionnées dans les skills.
- **Billet de juillet 2026 (Claude 5)** : plus de 80 % du prompt système supprimés sans perte ; « Keep your CLAUDE.md lightweight … spend most of the tokens on gotchas » ; une compétence de vérification référencée par CLAUDE.md.
- **Guide Opus 5.5 (septembre 2026)** : une règle sur quand continuer et quand s'arrêter ; format du résumé final ; supprimer les « think carefully ».

## 3. Divergences et évolutions (2025 → 2026)

| Sujet | Avant | Maintenant |
|---|---|---|
| Emphase | « IMPORTANT », « YOU MUST » pour l'adhérence | Une seule ligne emphatique |
| Touche `#` | Ajout rapide | Retirée (v2.0.70) : demander à Claude d'éditer |
| Croissance | Ajouter à chaque erreur | Ajouter à la récidive ; élaguer à chaque modèle |
| Mode plan | Presque toujours | Sauter si le diff tient en une phrase |
| Commandes slash | `.claude/commands/` | Fusionnées dans les skills |
| Imports | 5 sauts | 4 sauts, sans économie de contexte |

Attributions douteuses écartées : statistiques de « tokens gaspillés » attribuées à un podcast introuvable ; « moins de 100 instructions » (podcast tiers).

## 4. Principes retenus pour forever-core

- CLAUDE.md d'environ 35 lignes : commandes (`uv run tasks.py test-fast`, `verify`, un seul test), invariants du domaine (un seul IMPORTANT : aucun chiffre de jeu hors de `forever/data/`), zones protégées (`tests/golden/`, `seed/`), façon de travailler (une tranche à la fois via `/tranche`, tests d'abord, petits commits, quand s'arrêter et demander, format du résumé), langue du code.
- Règles à portée de chemin : `engine.md` (pureté, aucune constante de jeu, unités, citation du registre), `data.md` (versions immuables, sources, manifeste par commande), `outils.md` (provenance complète, réponses compactes, plugin sans calcul).
- Skills : `/tranche` (procédure TDD, section Pièges), `/verifier` (preuves), `/revue` (sous-agents relecteur et auditeur).
- Hooks : protection de `tests/golden/` et de `seed/`, tests verrouillés en phase verte, tests rapides avant l'arrêt (phase rouge tolérée via `tasks/.rouge`), formatage ruff.
- Outillage : pytest-socket (réseau coupé), mypy strict, contrôle des chiffres dans le plugin, contrôle du registre.

## 5. Faire vivre le fichier

1. Sur erreur : corriger, puis « Mets à jour CLAUDE.md pour ne plus refaire cette erreur » ; n'ajouter au fichier partagé qu'à la récidive ; choisir le bon endroit (CLAUDE.md, règle, piège de skill, hook).
2. En revue : `@claude` sur les PR via la GitHub Action.
3. Mesurer : `/context`, observer si le comportement change.
4. Élaguer : `/doctor` ; à chaque nouveau modèle, retirer style et procédure, **jamais les invariants du domaine**.
5. Préférences personnelles dans `CLAUDE.local.md` ou `~/.claude/CLAUDE.md`.

## Sources principales

- https://twitter-thread.com/t/2007179832300581177
- https://www.threads.com/@boris_cherny/post/DTCSBrFjvgk/our-checked-in-claude-md-is-k-tokens-it-covers-common-bash-commands-code-style
- https://x.com/bcherny/status/2017742741636321619
- https://www.threads.com/@boris_cherny/post/DUMZuyJkpSJ/invest-in-your-claude-md-after-every-correction-end-with-update-your-claude-md
- https://www.ycombinator.com/library/NJ-inside-claude-code-with-its-creator-boris-cherny
- https://www.ycombinator.com/library/UN-boris-cherny-building-claude-code
- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/skills
- https://www.anthropic.com/engineering/claude-code-best-practices
- https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
- https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/
- https://claude.dev/blog/getting-the-most-out-of-opus-5-5/
- https://github.com/anthropics/claude-code/issues/14868
- https://reporails.com/articles/opus-5-delete-your-claudemd
