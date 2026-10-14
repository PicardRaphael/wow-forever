---
name: forever-routes
description: "Feuille de route de leveling de WoW Forever, toutes les classes : suite de quêtes à prendre, objectifs et rendus dans l'ordre, donjons placés à leur meilleur niveau, farm pour finir, temps et XP par heure jusqu'au niveau voulu, aperçu ajustable (enlever un donjon, exclure une quête, sans quêtes de classe), guide RestedXP à importer ou livré dans RestedXP par le pont. Déclencher pour « fais-moi une route du niveau 10 à 20 », « feuille de route RestedXP », « quelles quêtes faire dans l'ordre », « enlève tel donjon de ma route ». Pas pour WoW retail ni WoW Classic hors Forever, ni la programmation."
---

# Feuilles de route (WoW Forever)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé », forme de la réponse, règle
« je ne sais pas ». Aucun chiffre de mémoire : niveaux, heures, XP par heure et XP des arrêts viennent de l'outil,
recopiés tels quels.

## Noms du client

Cite chaque quête, zone et donjon **tel qu'il apparaît dans le client du joueur** (`game_locale` de
`forever_player_profile` ; en anglais pour `enUS`) ; le reste de la réponse en français.

## Données du joueur

Question personnelle : `forever_player_profile` d'abord (classe, camp, niveau). Une donnée manquante se demande avant
le calcul (classe, camp, niveau de départ et d'arrivée), jamais devinée.

## Outil
- `forever_route(action="plan", class_name, faction, start_level, end_level, dungeons="auto", class_quests=True,
  exclude=[…], include=[…], professions=["Nom:rang:max"])` : plan et `preview` (niveaux, `hours`, `xp_h`, donjons placés, récompenses, bonus
  rappelés, certitude, nombre d'arrêts) ; `stops` : arrêts dans l'ordre (`kind` : accept, objective, turnin,
  dungeon, dungeon_repeat, train, prof, grind ; `name`, `zone`, `x`, `y`, `level`, `xp`, `certainty`) ; `warnings` : quêtes
  écartées et pourquoi ; `id` du plan.
- `forever_route(action="show", plan_id)` : relire un plan ; `forever_route(action="guide", plan_id)` : texte du guide
  RestedXP (à importer dans RestedXP, ou livré en jeu par le bouton « Livrer dans RestedXP » du pont).

- Métiers : `professions` (« Nom:rang:rang maximal » en anglais, lus dans `forever_player_profile` ou demandés) ;
  la route place une visite au maître quand le rang suivant est déjà ouvert ; elle ne monte pas la compétence.
- Comparer avec une route de Factoruide : commande `forever route compare <fichier.fgguide>` (CLI seulement).

## Lire le plan
- Montre d'abord l'aperçu : niveaux, temps, XP par heure, donjons et leur niveau, récompenses notables, certitude ;
  puis les premiers arrêts, pas toute la liste.
- **Ajuster** : « enlève Wailing Caverns » se traduit par `dungeons` sans lui (noms séparés par des virgules) ou
  `dungeons="none"` ; une quête à éviter va dans `exclude`, une quête voulue dans `include` ; relance `plan`.
- Certitude : la route est au mieux `suppose` (trajets et vitesses repris de Factoruide, position de départ et vols
  connus inconnus) ; dis-le avec les avertissements de l'outil.
- Quêtes « vues seulement chez Factoruide » : jamais placées ; ne les propose pas.

## Ce qui n'est pas couvert
- Montée de métier optimisée (MT1), plan de réputation chiffré (RP1), suivi en direct (RestedXP le fait) : dis
  « je ne sais pas » et la tranche.
