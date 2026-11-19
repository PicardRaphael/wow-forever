# data: 1.60.1.70959 r9 → r1

Candidate : `<cache>/candidates/1.60.1.70959` (données b078c973345c).

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

- plafond de la bêta : 30 (reporté de la révision 9 ; source observation ; certitude certain)

## Certitudes

53 talent(s) : FC-70938 → FC-70959 :

wandSpecialization, improvedChanneling, missileBarrage, arcaneSubtlety, magicAbsorption, arcaneConcentration, arcaneResilience, arcaneGeometry, arcaneImpact, arcaneBlast, arcaneShielding, improvedCounterspell, arcaneMeditation, arcaneWrath, presenceOfMind, arcaneMind, arcaneInstability, arcanePower, incineration, accelerant, ignite, flameThrowing, impact, burningSoul, improvedFlamestrike, pyroblast, wakeOfFire, improvedScorch, improvedFireWard, hotStreak, masterOfElements, criticalMass, blastWave, firePower, combustion, frostWarding, improvedFrostbolt, precision, iceShards, frostbite, improvedFrostNova, permafrost, frostChanneling, improvedBlizzard, iceLance, arcticReach, iceBlock, shatter, improvedConeOfCold, coldSnap, fingersOfFrost, wintersChill, iceBarrier

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.70959 r1 · données 078e29bcbc14 · générée 2026-11-18T11:33:41Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.70959 (données b078c973345c) sur la version 1.60.1.70938 (nouvelle version 1.60.1.70959)

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : identiques
- pvp_dr : différentes

## Valeurs changées

fiches PvP : Shaman, 1 talent modifié.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| Shaman | talent Enhancement Maelstrom Weapon | desc | When you deal damage with a melee attack, you have a chance to reduce the cast time and Mana cost of your next Lightning Bolt spell by $m1%. Stacks up to $s3 times. Lasts $408505d. | When you deal damage with a melee attack, you have a ${($mws*$s2/60)*100}% chance (based on weapon speed) to reduce the cast time and Mana cost of your next Lightning Bolt spell by $m1%. Stacks up to $s3 times. Lasts $408505d. |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » : relevé écarté, le client 1.60.1.70959 fait foi ; ton observation datait de 1.60.1.70938
