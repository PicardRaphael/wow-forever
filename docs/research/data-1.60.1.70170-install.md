# data: 1.60.1.70170 r6 → r1

Candidate : `<cache>/candidates/1.60.1.70170` (données 2656aa73e8e7).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 6 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 54 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 69 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 0 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 1 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| hors règles (refusé) | 0 |

## Valeurs changées

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| talents.json | hotStreak.former_names | — | `["Hot Streak"]` | confirmed | client 1.60.1.70170, tables Trait* et Spell* (wago.tools) ; E1, renommage du client 1.60.1.70170 (même nœud 105786, sort 400624, aura 400625 aux effets identiques) ; clé du dépôt hotStreak gardée (tasks/70170-ecarts.md, décision de l'utilisateur du 2026-10-02) | certain |
| talents.json | hotStreak.name | `"Hot Streak"` | `"Heating Up"` | confirmed | client 1.60.1.70170, tables Trait* et Spell* (wago.tools) ; E1, renommage du client 1.60.1.70170 (même nœud 105786, sort 400624, aura 400625 aux effets identiques) ; clé du dépôt hotStreak gardée (tasks/70170-ecarts.md, décision de l'utilisateur du 2026-10-02) | certain |
| talents.json | hotStreak.name_fr | `"Bonne série"` | `"Heating Up"` | confirmed | client 1.60.1.70170, tables Trait* et Spell* (wago.tools) ; E1, renommage du client 1.60.1.70170 (même nœud 105786, sort 400624, aura 400625 aux effets identiques) ; clé du dépôt hotStreak gardée (tasks/70170-ecarts.md, décision de l'utilisateur du 2026-10-02) | certain |
| talents.json | hotStreak.desc | `"Your non-periodic critical strikes with Fireball, Frostfire Bolt, Fire Blast, …` | `"Non-periodic critical strikes with Fireball, Frostfire Bolt, Fire Blast, and S…` | confirmed | client 1.60.1.70170, tables Trait* et Spell* (wago.tools) ; E1, renommage du client 1.60.1.70170 (même nœud 105786, sort 400624, aura 400625 aux effets identiques) ; clé du dépôt hotStreak gardée (tasks/70170-ecarts.md, décision de l'utilisateur du 2026-10-02) | certain |
| talents.json | combustion.ranks[1] | `[10, 4]` | `[10, 3]` | confirmed | client 1.60.1.70170, tables Trait* et Spell* (wago.tools) ; E2, SpellAuraOptions.ProcCharges du sort 11129 : 4 -> 3 dans le client 1.60.1.70170 (tasks/70170-ecarts.md, décision de l'utilisateur du 2026-10-02) | certain |
| talents.json | combustion.tooltip_values[1] | `[10, 4]` | `[10, 3]` | confirmed | client 1.60.1.70170, tables Trait* et Spell* (wago.tools) ; E3, même variable de l'infobulle que E2 (tasks/70170-ecarts.md, décision de l'utilisateur du 2026-10-02) | certain |

## État du jeu

- plafond de la bêta : 30 (donné à l'installation ; source observation ; certitude certain)

## Certitudes

54 talent(s) : FC-70124 → FC-70170 :

wandSpecialization, arcaneFocus, improvedChanneling, arcaneSubtlety, magicAbsorption, arcaneConcentration, arcaneResilience, arcaneGeometry, arcaneImpact, arcaneBlast, arcaneShielding, improvedCounterspell, arcaneMeditation, missileBarrage, presenceOfMind, arcaneMind, arcaneInstability, arcanePower, wakeOfFire, incineration, improvedFireball, ignite, flameThrowing, impact, burningSoul, improvedFlamestrike, pyroblast, improvedScorch, improvedFireWard, hotStreak, masterOfElements, criticalMass, blastWave, firePower, combustion, frostWarding, improvedFrostbolt, elementalPrecision, iceShards, permafrost, improvedFrostNova, frostbite, piercingIce, frostChanneling, iceLance, improvedBlizzard, arcticReach, iceBlock, shatter, improvedConeOfCold, coldSnap, fingersOfFrost, wintersChill, iceBarrier

## Champs ajoutés

- spells.json : source (15)
- talents.json : source (54)

Provenance · version 1.60.1.70170 r1 · données b8e8094026ea · générée 2026-10-02T08:19:30Z · fraîcheur stale · certitude certain · registre 53/126 · hypothèses : candidate <cache>/candidates/1.60.1.70170 (données 2656aa73e8e7) sur la version 1.60.1.70124 (nouvelle version 1.60.1.70170)
