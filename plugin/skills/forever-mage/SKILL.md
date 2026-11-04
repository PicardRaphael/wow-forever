---
name: forever-mage
description: "Mage de WoW Forever : sorts (dégâts, rangs, coût, temps d'incantation), talents (effet à un rang, prérequis, palier), build du Mage (builds populaires de Talents Forever vérifiés sur le client, wowsims au niveau 60), rotations Givre, Feu et Arcanes, mécaniques du Mage (Ignite, Hot Streak, Arcane Blast, Winter's Chill, Clearcasting). Déclencher pour « que fait le talent X », « meilleur build Mage », « Givre ou Feu », « combien fait Frostbolt ». Pas pour d'autres classes (non couvertes), ni WoW retail ou WoW Classic hors Forever, ni la programmation."
---

# Mage (WoW Forever)

Race et niveau du joueur : `forever_player_profile` (section « Données du joueur » de `format-reponse.md`) ;
comparer deux options : section « Comparer deux options ».

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé » (outils forever introuvables :
message fixe, rien de mémoire), forme de la réponse, règle « je ne sais pas ». Aucun chiffre de mémoire : tout vient
des outils ci-dessous.

## Noms du client

Le joueur lit les noms dans son client : sa langue est `game_locale`, rendue par `forever_player_profile`. Cite
chaque sort, talent, capacité, objet et zone **tel qu'il apparaît dans son client** (en anglais pour `enUS`), suivi du
nom français entre parenthèses quand l'outil le rend (`name_fr`, `name.fr`) ; le reste de la réponse reste en
français. Sans `game_locale` connue, cite le nom anglais du client et le nom français entre parenthèses.

## Sorts
- `forever_lookup(kind="spell", name=<nom anglais>, rank=<rang>)` ; sans `rank`, tous les rangs.
- Nom donné en français : traduis-le en nom anglais du client (par exemple « Éclair de givre » → Frostbolt). Nom
  inconnu : l'erreur propose des noms proches, reprends-en un.
- Sort utilitaire (Blink, Polymorph, armures…) : pas dans `kind="spell"` ; son rôle PvP (durée, recharge, catégorie)
  est dans la fiche `forever_lookup(kind="pvp", name="Mage")` (skill `forever-pvp`).

## Talents
- `forever_lookup(kind="talent", name=<nom anglais ou clé>, rank=<rang>)` : arbre, palier, points exigés dans
  l'arbre, prérequis, description aux valeurs du rang, sort appris, source des valeurs (`source`) et durée corrigée
  (`duration_s`) quand elle existe.
- Certitude `probable` : valeurs lues sur un build antérieur du client (hypothèse de la provenance), à dire.

## Builds
- Le build du Mage n'est plus calculé (décision 299) : comme pour les autres classes, il vient des builds populaires
  de Talents Forever, vérifiés sur les données du client ; détail dans le skill `forever-builds`.
- `forever_lookup(kind="tf_popular", name="Mage")` : builds par spécialisation, lien, `import` et légalité ; talents
  actuels connus (profil, contexte du jeu) : ajoute `current=<clé=rang,…>` et donne `closest` tel quel. Certitude
  supposé (choix de joueurs), date `asOf` citée.
- Contrôle : `forever_lookup(kind="build_check", name="Mage", level, talents)` ; guide de Forever Companion :
  `forever_lookup(kind="class_guide", name="Mage", level)`.
- Ordre des talents, prochain talent, respec, « meilleur build » par contexte (leveling, donjon, raid, PvP) : plus
  calculés ; dis-le. Les builds populaires ne sont pas classés par contexte ; l'ordre de prise du code Naowh est
  généré par palier et prérequis, pas optimisé.
- Givre ou Feu, meilleure race au niveau 60 : `forever_simulate` (wowsims/forever, skill `forever-builds`) ;
  MythicSim en recoupement (`engine="both"`, deux colonnes et leur écart, moteur, commit et date cités) ; un
  build du 60 se cherche par `action="builds"` (décision 301). Sous le
  60 : temps par monstre et XP/h par rotation avec `forever_sim_leveling` (moteur gelé, skill `forever-leveling`).
- PvP : classes adverses, contrôles et affrontements : skill `forever-pvp`.

## Mécaniques
- `forever_explain_mechanic(mechanic_id=<identifiant ou mots de la description>)` : description, statut, formule
  symbolique, paramètres chiffrés de la version, certitude.
- Statut `absent` : la mécanique n'est pas modélisée ; réponds « je ne sais pas » pour son effet chiffré et cite
  l'entrée du registre.

## Hors de ce skill
- Temps par monstre, XP/h, zone à mon niveau : skill `forever-leveling`.
- Autres classes : section « Classe pas encore calculée sous le 60 » du routeur (au 60 : wowsims/forever ; dessous : SIM2).
- Équipement (T10), consommables (T11) : « je ne sais pas » + tranche.
