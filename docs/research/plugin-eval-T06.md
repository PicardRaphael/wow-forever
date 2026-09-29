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
