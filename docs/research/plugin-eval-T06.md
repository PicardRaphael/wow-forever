# Évaluation du plugin forever (T06)

Suite : `plugin/evals/` (30 questions réelles, 20 voisines ; décision 96). Passages du 2026-09-29, Claude Code 2.1.284,
modèle par défaut de la session (Opus 5.5), vrai serveur MCP, un passage par cas :

```
claude plugin eval plugin --trust-plugin --mocks off --allow-tools "mcp__plugin_forever_forever__*" --runs 1 --ablation none -j 4 --judge-model opus --max-cost-usd 15 --no-publish --keep-temp --threshold 0 --json plugin/evals/results/passage-N.json
uv run python scripts/plugin_eval_report.py plugin/evals/results/passage-N.json
```

## Résultats

| Critère (seuil) | Passage 1 | Passage 2 | Passage 3 |
|---|---|---|---|
| Aiguillage, 50 cas (≥ 90 %) | 50/50 | 50/50 | 50/50 |
| Outil attendu appelé, 30 positifs (≥ 90 %) | 30/30 | 30/30 | 30/30 |
| Aucun chiffre inventé, 30 positifs (100 %) | **23/30** | 30/30 (hook en partie aveugle) | 30/30 |
| Certitude affichée, 30 positifs (100 %) | 30/30 | 30/30 | 30/30 |
| Provenance affichée, 30 positifs (≥ 90 %) | 30/30 | 30/30 | 30/30 |
| « Je ne sais pas » hors périmètre (3 sur 3) | 3/3 | 3/3 | **1/3** |
| Coût du passage | 6,44 $ | 6,31 $ | 6,43 $ |

Passage 2 : mesuré avec un hook qui lisait son entrée en cp1252 (relecture de la tranche : sans `PYTHONUTF8`,
« dégâts », « mètres » et « à » échappaient au contrôle ; l'environnement de l'évaluation est filtré). Il ne compte pas
pour le critère des chiffres. Passage 3 : entrée décodée en UTF-8 (commit `71ef7ec`), 129 chiffres de jeu dans les
réponses positives (dont 4 à unité accentuée), aucun signalé.

« Je ne sais pas » au passage 3 : le correcteur `regex` réussit 3/3 ; le juge `llm` (Haiku, trois votes) refuse les
réponses de `hors-butin-mortemines` et `hors-hotel-des-ventes`, qui disent pourtant « Je ne sais pas », citent DJ1 ou
EC1 et ne donnent aucune valeur (elles proposent ce que le projet sait déjà : niveau du donjon, recherche web
étiquetée). Rejeu des trois cas à trois exécutions (0,99 $) : regex 9/9, juge 8/9. Sur l'ensemble des passages, le juge
accepte 15 réponses sur 18 : variance du juge, question posée à l'utilisateur (`tasks/T06-corrections.md`).

Décision de l'utilisateur : critère `llm` des cas `hors-*` précisé (offres de ce que le projet couvre déjà et recherche
web étiquetée permises, toute valeur ou recommandation inventée interdite) et juge Opus (`--judge-model opus`). Rejeu
des trois cas à trois exécutions : « je ne sais pas » regex 9/9, juge 9/9, aucun chiffre inventé 9/9 (1,14 $).

Durée : environ 25 s par cas en moyenne, 90 s au plus (cas de `forever_build`, calcul d'environ une minute).
Le passage 2 suit deux corrections (commit `87acddc`) ; les 50 cas n'ont pas changé.

## Contrôle des chiffres : alertes et fausses alertes

Définitions : une **alerte** est un chiffre de jeu de la réponse que le hook Stop signale. Une **fausse alerte** est un
chiffre signalé qui figure bien dans un résultat d'outil forever de la session, à l'arrondi affiché près. Un chiffre
calculé par le modèle (somme, produit, formule appliquée à la main) est une vraie alerte, même quand il est juste : la
règle du projet veut que chaque chiffre soit recopié d'un outil.

**Passage 1** : 11 chiffres signalés dans 7 réponses.

| Cas | Chiffre signalé | Verdict | Explication |
|---|---|---|---|
| `respec-build-precis` | « 10,6 s » (de moins) | fausse alerte | `forever_build` rend −10,65 : écart négatif cité en valeur absolue, le signe dit en mots |
| `talent-niveau-24` | « 0,002 s » | fausse alerte | `forever_build` rend −0,0016 (même cause) |
| `build-pvp-bg-40` | « 31 points » | vraie (calcul juste) | somme des points du build faite par le modèle |
| `build-raid-60` | « 46 points », « 51 points » | vraies (calculs justes) | sommes faites par le modèle |
| `mecanique-arcane-blast` | « 41 % », « 67,5 % », « 94 % », « 120 % » | vraies | coûts calculés par le modèle à partir de la formule du registre |
| `mecanique-winters-chill` | « 10 % » | vraie | effet au maximum des cumuls calculé par le modèle |
| `build-givre-ou-feu` | « 0,7 s » | vraie | « environ 0,7 s » fond deux écarts du sous-agent (0,64 et 0,77) |

Taux de fausses alertes du passage 1 : **2 chiffres signalés sur 11 (18 %)**, soit 2 réponses sur 7 signalées à tort.

Corrections (commit `87acddc`) :
- valeur absolue d'une valeur d'outil acceptée comme source (test `tests/unit/test_numbers_eval_fixes.py`) ;
- consigne « aucun calcul » dans `format-reponse.md` et le routeur : ni somme, ni produit, ni formule appliquée, ni
  moyenne ; un écart négatif se dit en mots ;
- le rapport reprend le message du hook Stop dans la trace (le hook voit le transcript de la session ; recalculé sur
  la trace, qui contient aussi les résultats des sous-agents, le contrôle manquait deux alertes).

**Passage 2** : 117 chiffres de jeu, 0 alerte, mais hook en partie aveugle (voir plus haut) : non retenu.

**Passage 3** : 129 chiffres de jeu dans les 30 réponses positives, hook Stop exécuté dans les 30 sessions, **0 alerte,
donc 0 fausse alerte (0 %)**.

## Limites
- Un seul passage par cas : le déclenchement des skills et le respect de la consigne « aucun calcul » varient d'un
  passage à l'autre ; un passage à trois exécutions (`--runs 3`, environ 19 $) mesurerait cette variance.
- Le contrôle compare les nombres, pas leur unité ni leur champ : un chiffre juste attribué à la mauvaise grandeur, ou
  un nombre qui figure par hasard ailleurs dans un résultat d'outil, passe (faux négatif). Les résultats de
  `forever_build` contiennent plusieurs centaines de nombres, ce qui rend ces coïncidences possibles.
- La longueur des réponses (« courte par défaut », D3) n'est pas mesurée par un correcteur ; l'essai manuel du bloc E
  sur Ignite a donné une réponse détaillée sans demande de détail.
- Traces des passages supprimées après lecture (dossiers temporaires de l'évaluation) ; résultats JSON dans
  `plugin/evals/results/` (non versionné).

## Passage T06b (2026-09-29, plugin 0.2.0, 51 cas)

Même commande, `--json plugin/evals/results/passage-T06b.json` ; coût 5,99 $.

| Critère (seuil) | Passage T06b |
|---|---|
| Aiguillage, 51 cas (≥ 90 %) | 51/51 |
| Outil attendu appelé, 31 positifs (≥ 90 %) | **16/31** |
| Aucun chiffre inventé, 31 positifs (100 %) | **30/31** |
| Certitude affichée, 31 positifs (100 %) | **29/31** |
| Provenance affichée, 31 positifs (≥ 90 %) | 29/31 |
| « Je ne sais pas » hors périmètre (3 sur 3) | **2/3** |

- **Outil attendu : 15 échecs, tous par la règle « Données du joueur » (D6)**. Le profil est vide et la question ne
  donne ni la race, ni la faction, ni le build actuel. Le modèle appelle alors `forever_player_profile`, puis demande
  la donnée manquante avant tout calcul, avec la commande `forever profile set` (six tours, aucun outil de calcul).
  C'est le comportement demandé par la règle, mais les cas de T06 attendent un calcul dès le premier tour. Cas
  touchés : `build-donjon-50`, `build-givre-ou-feu`, `build-leveling-30`, `build-ordre-20`, `build-raid-60`,
  `leveling-repos-26`, `leveling-temps-18`, `leveling-xp-35`, les quatre `respec-*`, `talent-niveau-24`,
  `zone-donjon-18` et `zone-niveau-45`.
- **Chiffre signalé** (`talent-niveau-24`, « 14 points ») : le modèle compte lui-même les points du niveau précédent
  en demandant le build actuel. C'est une vraie alerte : un calcul, alors que l'outil rend ce total (`points.available`).
- **Certitude et provenance absentes** (`respec-troisieme`, `zone-donjon-18`) : réponses réduites à une question
  de précision, sans pied de réponse.
- **« Je ne sais pas »** : `hors-hotel-des-ventes` est refusé par le juge `sans-estimation` (déjà vu au passage 3).
- **Nouveau cas `talent-niveau-22`** (toutes les données dans la question) : réussi. `next_step` appelé avec
  `current`, Ice Lance recommandé, écart significatif de 6,1 s par monstre (intervalle 3,7 à 8,5 s), comparaison
  Monte Carlo contre Monte Carlo ; juge `mesure-et-modelise` satisfait.

Tranché par l'utilisateur le 2026-09-29 (option A, variante : profil de test rempli), voir le passage suivant. Options d'alors : garder la règle D6 et donner les données du joueur dans les
questions des cas touchés (ou accepter une question de précision comme bonne réponse), ou assouplir la règle
(calcul immédiat avec la valeur la plus probable, dite en tête de réponse).

## Passage T06b avec profil de test (2026-09-29, 53 cas)

Décision de l'utilisateur : garder la règle « Données du joueur » et faire tourner la suite avec un profil de test
rempli, comme à l'usage une fois le profil créé ; deux cas à profil vide vérifient que la donnée manquante est demandée.
`claude plugin eval` ne transmet au serveur MCP que les variables `EVAL_*` : `forever/profile.py` lit
`FOREVER_PROFILE`, sinon `EVAL_FOREVER_PROFILE`. Profil de test : `tests/fixtures/plugin_eval/profile-rempli.json`
(Mage Orc Horde, niveau 23, build Givre légal) ; cas `profil-vide-leveling-18` et `profil-vide-zone-18` (champ `env`
vers un fichier absent, juge `demande-la-donnee`).

```
$env:EVAL_FOREVER_PROFILE = "$PWD\tests\fixtures\plugin_eval\profile-rempli.json"
claude plugin eval plugin --trust-plugin --mocks off --allow-tools "mcp__plugin_forever_forever__*" --runs 1 --ablation none -j 4 --judge-model opus --max-cost-usd 15 --no-publish --keep-temp --threshold 0 --json plugin/evals/results/passage-T06b-profil.json
```

| Critère (seuil) | Passage avec profil |
|---|---|
| Aiguillage, 53 cas (≥ 90 %) | 53/53 |
| Outil attendu appelé, 33 positifs (≥ 90 %) | 31/33 |
| Aucun chiffre inventé, 33 positifs (100 %) | 32/33, puis 33/33 après correction du contrôle |
| Certitude affichée, 33 positifs (100 %) | 33/33 |
| Provenance affichée, 33 positifs (≥ 90 %) | 33/33 |
| « Je ne sais pas » hors périmètre (3 sur 3) | 3/3 |
| Coût | 7,81 $ (+ 0,47 $ de rejeu d'un cas) |

- **Outil attendu, deux échecs légitimes** : `respec-feu-vers-givre` et `respec-troisieme` posent la question à un
  autre niveau que celui du profil (32 et 36 contre 23) et sur un autre build ; le conseil de respec exige le build
  actuel, que le modèle demande (règle « la question prime sur le profil »). Attentes corrigées le 2026-09-29
  (décision 117) : demander le build actuel est la bonne réponse, outil attendu `forever_player_profile` et juge
  `demande-le-build` ; quatre cas ajoutés (questions générales et personnelles, dont une classe pas encore calculée),
  57 cas au total, à passer avec le modèle.
- **Chiffre signalé** (`build-givre-ou-feu`, « 11 153 XP/h ») : fausse alerte du contrôle. Le rapport du sous-agent
  `forever-sim-runner` écrit les XP/h avec une espace des milliers, que le contrôle lisait en deux nombres dans un
  résultat d'outil (11 et 153). Corrigé dans `forever/hooks.py` (test
  `tests/unit/test_review_t06b.py::test_hook_reads_thousands_in_tool_results`) ; contrôle rejoué sur la session du
  cas : aucun chiffre sans source ; cas rejoué seul : cinq correcteurs sur cinq.
- Les deux cas à profil vide et `talent-niveau-22` réussissent ; `talent-niveau-24` part désormais du build du profil
  (`next_step`).

