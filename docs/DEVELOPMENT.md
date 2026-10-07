# Développement

Comment ce projet avance. Pour l'usage du système, voir [../README.md](../README.md) et [USAGE.md](USAGE.md).

## Qui fait quoi

| Qui | Rôle |
|---|---|
| **claude.ai** (conversation) | Conçoit : cadre une tranche, discute une architecture, relit un plan ou un diff avec un regard neuf, sans accès au dépôt |
| **Claude Code** (sessions) | Exécute : écrit le plan dans `../tasks/`, les tests, le code, lance les contrôles, pousse et fusionne |
| **Moi** | Décide : valide chaque plan, tranche une règle de jeu, autorise une correction de test verrouillé, une dépendance, un accès réseau, une suppression de données |

Une seule chose ne se délègue pas : **vérifier en jeu** ce qui est marqué `suppose` ([OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)),
et repérer un chiffre absurde avec un œil de joueur.

## Cycle d'une tranche

Le travail avance par tranches verticales ([ROADMAP.md](ROADMAP.md)), dans l'ordre, **une à la fois**. Chaque tranche
traverse toutes les couches (données → moteur → outil → test) et se termine par un résultat utilisable.

### 1. Le plan

`/tranche Txx` dans une session neuve. Claude lit la section de la feuille de route, pose au plus cinq questions
décisives, puis **écrit directement** `../tasks/Txx-plan.md` : fichiers, interfaces, tests attendus avec leurs valeurs,
étapes, hors périmètre, risques.

- **Pas de mode plan.** Le plan est un fichier du dépôt, pas un état de l'interface : il se relit, se commente et se
  retrouve d'une session à l'autre.
- Il est committé sur `main`, avant toute branche. Puis la session **s'arrête** et attend ma validation.
- Relecture facultative dans une autre session, ou sur claude.ai : « relis ce plan comme un ingénieur qui devra le
  maintenir ; signale ce qui manque pour les critères de fin de la tranche, les risques non traités, ce qui est
  superflu, les tests absents ou faibles, tout écart aux invariants de `CLAUDE.md` ; propose les corrections en moins
  de 20 lignes ».

### 2. Les tests, rouges puis verrouillés

Nouvelle session, branche `txx` **dans le dépôt principal** (`git switch -c txx`).

1. Écrire les tests des critères de fin. Les lancer : ils doivent échouer **pour la bonne raison** (fonction absente,
   valeur fausse), pas sur une erreur de syntaxe.
2. Inscrire les tests attendus rouges dans `tasks/.rouge` et leurs fichiers dans `tasks/.tests-verrouilles` (les deux
   sont ignorés par git). Un hook interdit ensuite de les modifier.
3. Committer : « Txx: tests ».

### 3. Le vert

Implémenter jusqu'au vert, **sans toucher aux tests verrouillés**. Une tranche longue se découpe en blocs, un cycle
rouge → vert par bloc.

**Un test verrouillé qui se révèle faux ne se corrige pas tout seul.** Il ne bloque pas la tranche non plus : il est
noté dans `../tasks/Txx-corrections.md` (le test, la preuve tirée des données, le diff exact proposé), son bloc reste
sans commit « vert », et les blocs indépendants continuent. **Toutes les demandes de correction me sont présentées en
une seule fois**, avant le push final. Une fois l'accord donné, le fichier sort de la liste, le seul diff convenu est
appliqué, le fichier y revient, et la justification va dans le message de commit.

### 4. La fin

1. `/verifier` : `uv run tasks.py verify` (lint, typage, suite complète en parallèle réseau coupé, registre, contrôle
   des chiffres, origines) doit être vert, **lancé une seule fois, juste avant le push** (pendant le travail :
   `uv run tasks.py quick`, voir « Boucle de tests »). Une tâche n'est finie qu'à cette condition.
2. Mettre à jour [MECHANICS_REGISTRY.yaml](MECHANICS_REGISTRY.yaml) pour chaque mécanique touchée.
3. Pousser la branche, **attendre la CI verte sous Ubuntu et Windows** (`gh run watch`) — les fins de ligne et les
   chemins diffèrent assez pour qu'un vert local ne prouve rien.
4. Fusionner en **avance rapide** (`git merge --ff-only txx`), pousser `main`, supprimer la branche locale et
   distante. C'est Claude qui fusionne, pas moi.
5. Résumé final, dans cet ordre : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes, Angles
   morts (mécaniques absentes du registre qui influencent les résultats, avec leur effet estimé).

## Règles de séance

- **Une seule session à la fois.** Pas de tranches en parallèle : elles se croisent sur les mêmes données, le même
  registre et les mêmes comptes de tests.
- **Pas de worktree** (`worktree.bgIsolation` à `none`) : tout se passe dans le dépôt principal, sur une branche. Un
  worktree isolait le travail mais multipliait les allers-retours pour rien, à une session près.
- **Ne pas démarrer la tranche suivante dans la même session** : ouvrir une session neuve.
- **Petits commits**, message `Txx: <ce qui change>`.
- **Continuer sans demander** tant qu'une étape n'a pas besoin de moi. S'arrêter et demander avant de toucher
  `tests/golden/`, d'ajouter une dépendance ou un accès réseau, de supprimer des données, ou de trancher une règle de
  jeu.

### Boucle de tests : trois niveaux

| Niveau | Commande | Quand | Contenu |
|---|---|---|---|
| Travail | `uv run tasks.py quick` | en boucle, après chaque modification | lint, typage, tests rapides **concernés** par les fichiers modifiés depuis `main` (moins de 2 min) |
| Avant le push | `uv run tasks.py verify` | **une seule fois**, juste avant de pousser | lint, typage, **suite complète en parallèle** (`pytest -n auto`, tests `slow` compris), registre, chiffres, origines |
| Juge | CI (Ubuntu et Windows) | à chaque push | `verify` complet sur les deux systèmes, plus le job `e2e` |

- **`verify` ne se lance jamais en boucle** : un échec se corrige avec `quick` ou un test isolé
  (`uv run pytest tests/<fichier>.py::<test> -q`), puis `verify` une fois de plus avant le push.
- **Sélection de `quick`** (`scripts/select_tests.py`, analyse statique) : un module de `forever/` retient les tests
  qui l'importent (directement, par la fermeture des imports, ou par une fixture de `conftest.py`) ; un autre fichier
  (fixture, document, script, addon, plugin) retient les tests qui le nomment ; un fichier partagé (`conftest.py`,
  `pyproject.toml`, `uv.lock`, `tasks.py`) ou les données installées (`forever/data/`) : tous les tests rapides. La
  sélection est une approximation assumée : `verify` et la CI rattrapent ce qu'elle manque. Le hook de fin de tour
  lance la même sélection.
- **Tests lents** : un test qui dure plus de quelques secondes (Monte Carlo, rejeu, parité avec le seed, bout en
  bout) porte le marqueur `slow` (`pytestmark = pytest.mark.slow` en tête de fichier, ou sur le test) : hors de
  `quick`, toujours dans `verify` et la CI.
- **Tests parallélisables** : un test écrit seulement dans `tmp_path` (ou `tmp_path_factory`), jamais dans le dépôt,
  `~/.forever` ou un cache partagé ; aucun port fixe ; aucune dépendance à l'ordre des tests.
- **Clone de `forever update`** (décision 206) : quand une écriture ne change que des données (`forever/data/`,
  rapports `docs/research/data-*`, inventaire des valeurs écrites à la main), le clone lance
  `tasks.py verify --data --engines=<moteurs aux entrées changées>` : intégrité (`forever manifest --check`,
  `forever verify`), origines, registre, contrôle des chiffres, tests des données et tests des moteurs dont les
  entrées changent. Tout autre changement dans le clone : suite complète. La CI complète de la branche
  `data/<version>-r<N>` reste obligatoire avant la fusion.

### Deux fichiers qui s'appliquent à la main

Le mode auto de Claude Code refuse d'écrire dans `.github/workflows/` et `.claude/settings.json` : de là partiraient
une exécution en CI et une modification des permissions de l'agent. Un changement voulu dans ces fichiers est donc
livré en **patch**, et je l'applique moi-même :

```powershell
git apply tasks/<nom>.patch
```

Les patchs en attente vivent dans `../tasks/` ; celui qui a été appliqué est mentionné dans le message de commit de sa
tranche.

## Évaluation du plugin

Le plugin a son jeu de questions réelles et de questions voisines qui ne doivent **pas** le déclencher
(`plugin/evals/`). Deux niveaux :

- **En CI, sans modèle** : la structure de la suite est contrôlée à chaque validation (`tests/unit/test_plugin_evals.py`).
  Gratuit, lancé toujours.
- **À la main, avec le modèle** : `claude plugin eval`, vrai serveur MCP, juge Opus. Il mesure l'aiguillage, l'outil
  appelé, l'absence de chiffre inventé, la certitude et la provenance affichées.

**Ce passage coûte de l'argent** — de l'ordre de quelques dollars par passage complet, proportionnel au nombre de cas
et au nombre d'exécutions par cas ; `--max-cost-usd` sert de plafond dur. Il ne se lance donc pas à chaque tranche,
mais quand les skills ou le format de réponse changent. Commande exacte, seuils, résultats et coûts mesurés :
[USAGE.md](USAGE.md#évaluation) et [research/plugin-eval-T06.md](research/plugin-eval-T06.md).

## Zones protégées

- `tests/golden/` : **ne jamais régénérer pour faire passer un test**. Si un changement voulu les modifie, la session
  s'arrête, explique pourquoi et demande l'accord ; la justification va dans le message de commit. Un hook bloque
  l'écriture.
- `seed/forever-mage/` et `seed/grimoire-engine/` : code de référence validé, à porter, en lecture seule.

## Faire vivre CLAUDE.md

- **Quand Claude se trompe** : corriger, puis dire « mets à jour CLAUDE.md pour ne plus refaire cette erreur ».
  N'ajouter une ligne au fichier partagé que si l'erreur se répète ou qu'une revue l'attrape. Se demander où la
  mettre : `CLAUDE.md`, une règle de `.claude/rules/`, la section « Pièges » d'un skill, ou un hook si elle doit être
  garantie.
- **En revue de PR** : installer l'action GitHub avec `/install-github-action`, puis taguer `@claude` sur une PR pour
  qu'il ajoute la leçon au `CLAUDE.md` dans la PR même.
- **Contrôler** : `/context` pour voir ce qui est chargé, `/doctor` pour repérer les lignes à couper. Si une règle
  présente est ignorée, le fichier est trop long ou la règle ambiguë.
- **Élaguer** à chaque nouveau modèle ou tous les six mois : retirer les lignes de style et de procédure, les
  réintroduire seulement si l'erreur revient. **Ne jamais retirer les invariants du domaine** : ce sont des faits sur
  le projet, pas des béquilles pour le modèle.
- **Préférences personnelles** : dans `CLAUDE.local.md` (ignoré par Git) ou `~/.claude/CLAUDE.md`, jamais dans le
  fichier partagé.
