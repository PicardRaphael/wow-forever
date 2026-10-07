---
name: forever-builds
description: "Builds de talents de WoW Forever pour les 9 classes : build calculé du Mage par contexte, builds populaires de Talents Forever et builds de la communauté pour les autres classes (Paladin, Démoniste, Prêtre, Chasseur, Chaman, Guerrier, Voleur, Druide) vérifiés sur les données du client (légalité, paliers, prérequis, effet des talents), lien Talents Forever du build calculé. Déclencher pour « meilleur build Paladin », « ce build de Voleur est-il légal », « que fait ce talent de Druide ». Pas pour WoW retail ni WoW Classic hors Forever, ni la programmation."
---

# Builds (WoW Forever, 9 classes)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé », forme de la réponse, règle
« je ne sais pas ». Aucun chiffre de mémoire : tout vient des outils forever.

## Noms du client

Le joueur lit les noms dans son client : sa langue est `game_locale`, rendue par `forever_player_profile`. Cite
chaque sort, talent, capacité, objet et zone **tel qu'il apparaît dans son client** (en anglais pour `enUS`), suivi du
nom français entre parenthèses quand l'outil le rend (`name_fr`, `name.fr`) ; le reste de la réponse reste en
français. Sans `game_locale` connue, cite le nom anglais du client et le nom français entre parenthèses.

## Mage : build calculé
- `forever_build(context, level, race, current, respecs)` : skill `forever-mage` pour le détail.
- Lien Talents Forever (bloc `export.talents_forever` de `forever_build`) : si `status` vaut `ok`, recopie tels quels
  `code`, `link` et `import` (commande `/tf import <code>` à coller en jeu) ; ne recompose jamais un code. Sinon
  dis la raison (`reason` : addon absent, export bloqué, format non pris en charge), jamais un code deviné. Cite
  `order_note` quand l'ordre n'est pas compris, la certitude du bloc (`probable` : pas encore relu en jeu) et la
  version de l'addon (`provenance.version`).
- Build populaire le plus proche (`export.talents_forever.closest_popular`) : rang, spécialisation, points du nôtre
  absents du sien (`missing_points`), points à ajouter, écart total, lien et date `asOf` ; certitude supposé
  (choix de joueurs).

## Autres classes : builds de la communauté vérifiés
- Le moteur ne calcule pas encore leurs dégâts (tranches de classe PA1 à DR1) : dis-le, certitude au mieux supposé
  pour le choix du build.
- Question personnelle : `forever_player_profile` d'abord (classe, niveau, talents du profil) ; question générale :
  rien à demander, hypothèse neutre annoncée.
- Builds populaires de Talents Forever d'abord : `forever_lookup(kind="tf_popular", name=<classe>)` (addon lu sur
  disque) : part de chaque spécialisation, date `asOf` et fenêtre, puis chaque build avec son lien, sa commande
  `import` et sa légalité déjà contrôlée sur le client (`légal`, `illégal`, ou `non vérifiable` avec le talent
  sans correspondance nommé). Certitude supposé (choix de joueurs) ; cite la date. Addon absent : dis-le.
- Builds de la communauté en plus (ou addon absent) : sous-agent `forever-web-researcher`, chaque build avec sa
  source, son type et sa date, présenté comme l'avis de cette source (section « Sources extérieures » de
  `format-reponse.md`).
- Vérifie chaque build : `forever_lookup(kind="build_check", name=<classe>, level=<niveau>,
  talents=<clé=rang,…>)` rend légal ou la liste des erreurs (paliers, prérequis, rangs, points au niveau) et la
  description des talents du client. Un build illégal se dit tel, avec les erreurs de l'outil.
- Effet d'un talent : `forever_lookup(kind="talent", name=<nom anglais ou clé>, class_name=<classe>)` : arbre,
  palier, prérequis, description du client (valeurs par rang non décodées pour ces classes : dis-le).
- Palier communautaire (probable) ou légalité non décidable (nœud hors grille) : répète ce que dit l'outil.

## Hors de ce skill
- PvP d'une classe (contrôles, défensifs, affrontement) : skill `forever-pvp`.
- Dégâts, rotations et leveling des autres classes : « je ne sais pas » + tranche de la classe.
