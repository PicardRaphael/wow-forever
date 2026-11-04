---
name: forever-routes
description: "Feuille de route de leveling de WoW Forever, toutes les classes : guide Polestar à suivre en jeu (addon installé, guide de ma race et de ma tranche de niveaux), puis aperçu calculé en recoupement : suite de quêtes, objectifs et rendus dans l'ordre, donjons placés à leur meilleur niveau, farm pour finir, temps et XP par heure jusqu'au niveau voulu, aperçu ajustable (enlever un donjon, exclure une quête, sans quêtes de classe) ; chaque route livrée pour Polestar et pour RestedXP. Déclencher pour « fais-moi une route du niveau 10 à 20 », « quel guide Polestar suivre », « feuille de route RestedXP », « quelles quêtes faire dans l'ordre », « enlève tel donjon de ma route ». Pas pour WoW retail ni WoW Classic hors Forever, ni la programmation."
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

## Polestar d'abord
L'addon Polestar est installé en jeu, avec les guides de toutes les races.
- Pars du guide Polestar de la race du joueur et de la tranche de niveaux demandée : nomme-le, à suivre en jeu
  (`/polestar` ouvre le hub de l'addon).
- Donne l'aperçu de `forever_route(action="plan")` (zones, donjons, heures) en recoupement, tel que l'outil le rend.
- Livre chaque route créée (ajustée ou non) dans les deux formats : RestedXP comme aujourd'hui
  (`forever_route(action="guide")`, « Valider et livrer ») et chaîne d'import Polestar (`/polestar import`).
- Tant que l'export Polestar n'existe pas, livre le RestedXP et dis que la version Polestar arrive avec la tranche
  suivante.

## Outil
- `forever_route(action="plan", class_name, faction, start_level, end_level, race, character, start_map, start_x,
  start_y, dungeons="auto", class_quests=True, exclude=[…], include=[…], professions=["Nom:rang:max"])` : `race` et
  `character` du profil toujours donnés (zone de départ de la race, quêtes déjà faites du personnage retirées),
  position si connue ; donjons avec leurs quêtes et quêtes de classe inclus par défaut. Réponse compacte par défaut :
  `hours`, `xp_h`, `zones` dans l'ordre, `dungeons` placés, `class_quests`, `rewards`, `first_stops` (cinq premiers
  arrêts : `text`, `zone`, `x`, `y`, `level`), `stops_total`, `preview`, `warnings` (les premiers, `warnings_total`),
  `basis` : la route livrée, notre calcul s'il ressemble au parcours gratuit de RestedXP de la race et de la classe,
  sinon ce parcours adapté (attribution à RestedXP, décision 279) ; `id` du plan. `detail=True` rend le plan entier
  (`stops` dans l'ordre : `kind` accept, objective, turnin, dungeon, dungeon_repeat, train, prof, grind ; `name`,
  `zone`, `x`, `y`, `level`, `xp`, `certainty`) : seulement si la question le demande, la réponse est longue.
- `forever_route(action="show", plan_id)` : relire un plan ; `forever_route(action="guide", plan_id)` : texte du guide
  RestedXP, nom stable « Forever · <personnage> · a-b » (livré en jeu par « Valider et livrer » sous l'aperçu ;
  `forever route rxp-clean`, jeu fermé, retire de RestedXP les routes livrées).

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
- Montée de métier optimisée (MT1), plan de réputation chiffré (RP1), suivi en direct (Polestar ou RestedXP le font) : dis
  « je ne sais pas » et la tranche.
