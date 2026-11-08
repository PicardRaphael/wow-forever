# data: 1.60.1.70862 r11 → r1

Candidate : `<cache>/candidates/1.60.1.70862` (données 19b43b210b07).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 53 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 69 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 0 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 0 |
| règle de lecture dépassée (talent gardé, à relire, certitude suppose, hors des calculs) | 0 |
| hors règles (refusé) | 0 |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 11 ; source observation ; certitude certain)

## Certitudes

53 talent(s) : FC-70790 → FC-70862 :

wandSpecialization, improvedChanneling, missileBarrage, arcaneSubtlety, magicAbsorption, arcaneConcentration, arcaneResilience, arcaneGeometry, arcaneImpact, arcaneBlast, arcaneShielding, improvedCounterspell, arcaneMeditation, arcaneWrath, presenceOfMind, arcaneMind, arcaneInstability, arcanePower, incineration, accelerant, ignite, flameThrowing, impact, burningSoul, improvedFlamestrike, pyroblast, wakeOfFire, improvedScorch, improvedFireWard, hotStreak, masterOfElements, criticalMass, blastWave, firePower, combustion, frostWarding, improvedFrostbolt, precision, iceShards, frostbite, improvedFrostNova, permafrost, frostChanneling, improvedBlizzard, iceLance, arcticReach, iceBlock, shatter, improvedConeOfCold, coldSnap, fingersOfFrost, wintersChill, iceBarrier

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.70862 r1 · données af004b0824d8 · générée 2026-11-08T16:18:58Z · fraîcheur stale · certitude certain · registre 78/150 · hypothèses : candidate <cache>/candidates/1.60.1.70862 (données 19b43b210b07) sur la version 1.60.1.70790 (nouvelle version 1.60.1.70862)

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : différentes
- pvp_dr : différentes

## Valeurs changées

mage_leveling : races.json, 1 autre valeur changée ; xp_bonuses.json, 1 autre valeur changée.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| races.json | races | Orc racials 20575 effects n°2 base_points | 5 | 0 |
| xp_bonuses.json | auras | 1328127 name | Élixir d’expérience infinie | Elixir of Endless Experience |
| xp_bonuses.json | auras | 1328127 description | Gains d’expérience augmentés de $s1 % pendant $d. | Increases experience gained by $s1% for $d. |
| xp_bonuses.json | auras | 1328127 items n°1 name | Élixir d’expérience infinie | Elixir of Endless Experience |

fiches PvP : races.json, 1 autre valeur changée ; Hunter, 2 autres valeurs changées ; Rogue, 1 sort modifié ; Warrior, 1 talent modifié.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| races.json | races | Orc racials 20575 effects n°2 base_points | 5 | 0 |
| Hunter | dropped_nodes | 105003 reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.18.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.19.20261106 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) |
| Hunter | parked_nodes | improvedSerpentSting talents_forever | Talents Forever 0.38.18.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) | Talents Forever 0.38.19.20261106 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) |
| Hunter | parked_nodes | improvedSerpentSting reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.18.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 : question ouverte à créer | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.19.20261106 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 : question ouverte à créer |
| Hunter | parked_nodes | improvedSerpentSting question | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.18.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.19.20261106 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). |
| Rogue | sort Shank | rang 1 rank | null | 1 |
| Rogue | sort Shank | rang 2 rank | null | 2 |
| Warrior | talent Fury Gore Drinker | desc | Your Enrage, Berserker Rage, Bloodrage, Death Wish, and Bloodthirst abilities cause your next $m1 melee attacks to restore ${$s2}.1% of your maximum Health. | Your Enrage, Berserker Rage, Bloodrage, Death Wish, Reckless Swings, and Bloodthirst abilities cause your next $m1 melee attacks to restore ${$s2}.1% of your maximum Health. |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » : relevé écarté, le client 1.60.1.70862 fait foi ; ton observation datait de 1.60.1.70790
- moteurs aux entrées changées : mage_leveling
