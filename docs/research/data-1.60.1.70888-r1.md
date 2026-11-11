# data: 1.60.1.70888 r13 → r1

Candidate : `<cache>/candidates/1.60.1.70888` (données 8c6697efeffe).

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

- plafond de la bêta : 30 (reporté de la révision 13 ; source observation ; certitude certain)

## Certitudes

53 talent(s) : FC-70862 → FC-70888 :

wandSpecialization, improvedChanneling, missileBarrage, arcaneSubtlety, magicAbsorption, arcaneConcentration, arcaneResilience, arcaneGeometry, arcaneImpact, arcaneBlast, arcaneShielding, improvedCounterspell, arcaneMeditation, arcaneWrath, presenceOfMind, arcaneMind, arcaneInstability, arcanePower, incineration, accelerant, ignite, flameThrowing, impact, burningSoul, improvedFlamestrike, pyroblast, wakeOfFire, improvedScorch, improvedFireWard, hotStreak, masterOfElements, criticalMass, blastWave, firePower, combustion, frostWarding, improvedFrostbolt, precision, iceShards, frostbite, improvedFrostNova, permafrost, frostChanneling, improvedBlizzard, iceLance, arcticReach, iceBlock, shatter, improvedConeOfCold, coldSnap, fingersOfFrost, wintersChill, iceBarrier

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.70888 r1 · données 5f5a4c1c9bab · générée 2026-11-11T07:37:48Z · fraîcheur stale · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.70888 (données 8c6697efeffe) sur la version 1.60.1.70862 (nouvelle version 1.60.1.70888)

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : identiques
- pvp_dr : différentes

## Valeurs changées

fiches PvP : Hunter, 2 sorts modifiés ; Warlock, 2 talents et 1 sort modifiés.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| Hunter | sort Arcane Shot | rang 1 cost amount | 25 | 0 |
| Hunter | sort Arcane Shot | rang 1 cost pct | 0 | 11 |
| Hunter | sort Arcane Shot | rang 2 cost amount | 35 | 0 |
| Hunter | sort Arcane Shot | rang 2 cost pct | 0 | 11 |
| Hunter | sort Arcane Shot | rang 3 cost amount | 50 | 0 |
| Hunter | sort Arcane Shot | rang 3 cost pct | 0 | 11 |
| Hunter | sort Arcane Shot | rang 4 cost amount | 80 | 0 |
| Hunter | sort Arcane Shot | rang 4 cost pct | 0 | 11 |
| Hunter | sort Arcane Shot | rang 5 cost amount | 105 | 0 |
| Hunter | sort Arcane Shot | rang 5 cost pct | 0 | 11 |
| Hunter | sort Arcane Shot | rang 6 cost amount | 135 | 0 |
| Hunter | sort Arcane Shot | rang 6 cost pct | 0 | 11 |
| Hunter | sort Arcane Shot | rang 7 cost amount | 160 | 0 |
| Hunter | sort Arcane Shot | rang 7 cost pct | 0 | 11 |
| Hunter | sort Arcane Shot | rang 8 cost amount | 190 | 0 |
| Hunter | sort Arcane Shot | rang 8 cost pct | 0 | 11 |
| Hunter | sort Summon Hawk | rang 1 cost amount | 80 | 0 |
| Hunter | sort Summon Hawk | rang 1 cost pct | 0 | 11 |
| Hunter | sort Summon Hawk | rang 2 cost amount | 105 | 0 |
| Hunter | sort Summon Hawk | rang 2 cost pct | 0 | 11 |
| Hunter | sort Summon Hawk | rang 3 cost amount | 135 | 0 |
| Hunter | sort Summon Hawk | rang 3 cost pct | 0 | 11 |
| Hunter | sort Summon Hawk | rang 4 cost amount | 190 | 0 |
| Hunter | sort Summon Hawk | rang 4 cost pct | 0 | 11 |
| Hunter | dropped_nodes | 105003 reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.21.20261109 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.22.20261110 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) |
| Hunter | parked_nodes | improvedSerpentSting talents_forever | Talents Forever 0.38.21.20261109 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) | Talents Forever 0.38.22.20261110 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) |
| Hunter | parked_nodes | improvedSerpentSting reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.21.20261109 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 : question ouverte à créer | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.22.20261110 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) à la rangée 4, colonne 4 : question ouverte à créer |
| Hunter | parked_nodes | improvedSerpentSting question | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.21.20261109 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.22.20261110 (Data.lua build 1.60.1.70755, généré le 2026-11-05, empreinte fecfe730eb45) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). |
| Warlock | talent Affliction Soul Siphon | desc | Increases the damage done or health drained by your Drain Life, Drain Soul, and Wrack spells by $s1% per each of your other Affliction effects active on the target, up to a maximum increase of ${$m1*3}%. | Increases the damage done or health drained by your Drain Life, Drain Soul, and Wrack spells by $s1% per each of your Corruption, Siphon Life, and Bane of Agony effects active on the target, up to a maximum increase of ${$m1*3}%. |
| Warlock | talent Affliction Wrack | desc | Tears the target apart from within, inflicting $s1 Shadow damage every $t sec and increasing the damage they take from your other Shadow damage over time effects by $s2% for $d. | Tears the target apart from within for $d, inflicting $s1 Shadow damage every $t sec. While channeling, your Siphon Life, Corruption, and Bane of Agony effects on the target deal their periodic damage $s2% faster. |
| Warlock | sort Bane of Havoc | rang 1 gcd_s | null | 1.5 |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » : relevé écarté, le client 1.60.1.70888 fait foi ; ton observation datait de 1.60.1.70862
