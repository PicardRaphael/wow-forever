---
name: forever-pvp
description: "PvP de WoW Forever, toutes classes : contrôles d'une classe (étourdissement, peur, métamorphose, silence…), leur catégorie de rendements décroissants, défensifs et immunités, ruptures de contrôle, interruptions, dissipations, mobilité, recharges offensives, raciaux et bijoux PvP ; fiche d'affrontement « comment jouer contre un Démoniste avec mon Mage ». Déclencher pour « contrôles du Voleur », « temps de recharge défensif du Paladin », « mon Mage contre un Démoniste », « rendements décroissants ». Pas pour WoW retail ni WoW Classic hors Forever, ni la programmation."
---

# PvP (WoW Forever, 9 classes)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé », forme de la réponse, règle
« je ne sais pas ». Aucun chiffre de mémoire : tout vient de `forever_lookup(kind="pvp")`.

## Fiche d'une classe
- `forever_lookup(kind="pvp", name=<classe>, level=<niveau>)` : contrôles (catégorie de rendements décroissants,
  durée, portée, recharge, rupture aux dégâts), défensifs et immunités, ruptures de contrôle, interruptions
  (verrouillage), dissipations, mobilité, recharges offensives, raciaux possibles, bijoux PvP.
- Listes paginées : `limit`, `offset`, `totals`, `next_offset`. `detail=true` rend le chemin de chaque valeur dans
  les données (`from`) et sa certitude : à demander quand le joueur veut vérifier une valeur.
- Niveau inconnu : rang le plus haut de chaque sort (écrit dans `missing`).

## Affrontement
- Question personnelle (« mon Mage contre un Démoniste ») : `forever_player_profile` d'abord (section « Données du
  joueur » de `format-reponse.md`), puis `forever_lookup(kind="pvp", name=<ma classe>, opponent=<classe adverse>,
  level=<niveau>, race=<race>, talents=<clé=rang,…>)`. L'outil ne lit jamais le profil : passe-lui classe, niveau,
  race et talents du profil.
- Réponse courte, dans cet ordre : ses menaces (`threats` : recharges offensives, contrôles, défensifs), mes
  réponses (`answers` : ruptures, bijou, raciaux, interruptions contre ses sorts à incantation, dissipations), ses
  réponses à mes contrôles (`their_answers`), fenêtres à surveiller (`windows` : ses recharges longues).
- Talents adverses inconnus : ses sorts de talent sont marqués « si talent » ; dis-le.

## Certitude
- Valeurs du client (durées, recharges, portées, catégorie de rendement) : certaines. Classement d'un sort
  (contrôle, défensif…) : probable. Noms des catégories et règles des rendements décroissants (paliers, fenêtre,
  plafond) : supposés, règles de WoW Classic en attendant les mesures de PV2. Donne la certitude la plus basse
  utilisée dans la réponse.
- Cite `missing` : ce qui manque (portée absente, catégorie inconnue, talents adverses, conditions d'emploi comme la
  posture ou le camouflage, sorts non classés comme les pièges et les totems). Jamais de valeur inventée pour combler.

## Limites (à dire quand le joueur demande un suivi en jeu)
- Aucun suivi en direct des recharges adverses dans un addon sur Forever : le journal de combat est refusé aux
  addons et les valeurs de combat y sont secrètes (`docs/research/addon-forever.md`). Seules des fiches fixes,
  consultées hors combat ou affichées en jeu par l'addon (tranche FA1p).
- Pas de dégâts ni de soins des autres classes (tranches de classe PA1 à DR1), pas de simulation de duel, pas de
  mesure des rendements décroissants dans mes journaux (PV2), pas d'analyse de mes combats (AN1).

## Hors de ce skill
- Build du Mage en PvP (`pvp-bg`, `pvp-world`) : skill `forever-mage` (`forever_build`).
- Build d'une autre classe : skill `forever-builds`.
