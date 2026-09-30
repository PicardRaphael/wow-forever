---
name: forever-builds
description: "Builds de talents de WoW Forever pour les 9 classes : build calculé du Mage par contexte, builds de la communauté pour les autres classes (Paladin, Démoniste, Prêtre, Chasseur, Chaman, Guerrier, Voleur, Druide) vérifiés sur les données du client (légalité, paliers, prérequis, effet des talents). Déclencher pour « meilleur build Paladin », « ce build de Voleur est-il légal », « que fait ce talent de Druide ». Pas pour WoW retail ni WoW Classic hors Forever, ni la programmation."
---

# Builds (WoW Forever, 9 classes)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé », forme de la réponse, règle
« je ne sais pas ». Aucun chiffre de mémoire : tout vient des outils forever.

## Mage : build calculé
- `forever_build(context, level, race, current, respecs)` : skill `forever-mage` pour le détail.

## Autres classes : builds de la communauté vérifiés
- Le moteur ne calcule pas encore leurs dégâts (tranches de classe PA1 à DR1) : dis-le, certitude au mieux supposé
  pour le choix du build.
- Question personnelle : `forever_player_profile` d'abord (classe, niveau, talents du profil) ; question générale :
  rien à demander, hypothèse neutre annoncée.
- Builds : sous-agent `forever-web-researcher`, chaque build avec sa source, son type et sa date, présenté comme
  l'avis de cette source (section « Sources extérieures » de `format-reponse.md`).
- Vérifie chaque build : `forever_lookup(kind="build_check", name=<classe>, level=<niveau>,
  talents=<clé=rang,…>)` rend légal ou la liste des erreurs (paliers, prérequis, rangs, points au niveau) et la
  description des talents du client. Un build illégal se dit tel, avec les erreurs de l'outil.
- Effet d'un talent : `forever_lookup(kind="talent", name=<nom anglais ou clé>, class_name=<classe>)` : arbre,
  palier, prérequis, description du client (valeurs par rang non décodées pour ces classes : dis-le).
- Palier communautaire (probable) ou légalité non décidable (nœud hors grille) : répète ce que dit l'outil.

## Hors de ce skill
- PvP d'une classe (contrôles, défensifs, affrontement) : skill `forever-pvp`.
- Dégâts, rotations et leveling des autres classes : « je ne sais pas » + tranche de la classe.
