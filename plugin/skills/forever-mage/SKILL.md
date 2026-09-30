---
name: forever-mage
description: "Mage de WoW Forever : sorts (dégâts, rangs, coût, temps d'incantation), talents (effet à un rang, prérequis, palier), meilleur build par contexte (leveling, donjon, raid, PvP), rotations Givre, Feu et Arcanes, mécaniques du Mage (Ignite, Hot Streak, Arcane Blast, Winter's Chill, Clearcasting). Déclencher pour « que fait le talent X », « meilleur build Mage », « Givre ou Feu », « combien fait Frostbolt ». Pas pour d'autres classes (non couvertes), ni WoW retail ou WoW Classic hors Forever, ni la programmation."
---

# Mage (WoW Forever)

Race et niveau du joueur : `forever_player_profile` (section « Données du joueur » de `format-reponse.md`) ;
comparer deux builds : section « Comparer deux options ».

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé » (outils forever introuvables :
message fixe, rien de mémoire), forme de la réponse, règle « je ne sais pas ». Aucun chiffre de mémoire : tout vient
des outils ci-dessous.

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
- `forever_build(context, level, race, current, respecs)` ; `context` : `leveling`, `dungeon`, `raid`, `pvp-bg` ou
  `pvp-world`.
- Réponse courte : talents conseillés et rotation (`choices`), puis l'écart avec l'alternative la plus proche
  (`alternative`) si le joueur hésite entre deux builds.
- Donne toujours `certainty` et `verifiable_in_game` ; au-delà du plafond de la bêta, le build n'est pas vérifiable
  en jeu.
- Donjon et raid : scénarios provisoires, mana des combats longs non modélisée (tranche T05b) : écris-le en
  « Attention ». Raid complet : tranche T09.
- PvP : le build sort de `forever_build` ; classes adverses, contrôles et affrontements : skill `forever-pvp` ;
  profil PvP du Mage avec rendements décroissants et bijou : tranche PV2.
- `sensitivity` et `stability` : seulement si le joueur demande le détail ou si une hypothèse retourne le choix.
- Preset `complet` ou comparaison de plusieurs contextes : sous-agent `forever-sim-runner`.

## Mécaniques
- `forever_explain_mechanic(mechanic_id=<identifiant ou mots de la description>)` : description, statut, formule
  symbolique, paramètres chiffrés de la version, certitude.
- Statut `absent` : la mécanique n'est pas modélisée ; réponds « je ne sais pas » pour son effet chiffré et cite
  l'entrée du registre.

## Hors de ce skill
- Temps par monstre, XP/h, zone à mon niveau : skill `forever-leveling`.
- Autres classes : section « Classe pas encore calculée » du routeur (tranches de classe PA1 à DR1).
- Équipement (T10), consommables (T11) : « je ne sais pas » + tranche.
