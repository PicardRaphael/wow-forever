# data: 1.60.1.70009 r1 → r2

Candidate : `<cache>/candidates/1.60.1.70009` (données 2b344940521e).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 15 |
| valeur du client là où le dépôt avait null | 3 |
| certitude du talent | 49 |
| champ ajouté | 177 |
| champ retiré | 1 |
| métadonnée | 0 |
| hors règles (refusé) | 0 |

## Valeurs changées

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| talents.json | presenceOfMind.ranks[1] | `[10]` | `[]` | confirmed | client 1.60.1.70009, tables Trait* et Spell* (wago.tools) ; l'infobulle du client écrit « 10 sec » en clair, sans variable | certain |
| talents.json | impact.ranks[2] | `[6]` | `[7]` | confirmed | client 1.60.1.70009, tables Trait* et Spell* (wago.tools) ; courbe du client 3 / 7 / 10 (arrondi de 10 × rang / 3) ; aucun décalage de lecture ailleurs (tasks/T03-ecarts.md) | certain |
| talents.json | impact.ranks[3] | `[9]` | `[10]` | confirmed | client 1.60.1.70009, tables Trait* et Spell* (wago.tools) ; courbe du client 3 / 7 / 10 (arrondi de 10 × rang / 3) | certain |
| talents.json | improvedScorch.ranks[2] | `[66]` | `[67]` | confirmed | client 1.60.1.70009, tables Trait* et Spell* (wago.tools) ; courbe du client 33 / 67 / 100 | certain |
| talents.json | hotStreak.ranks[1] | `[15, 25, 3]` | `[20, 25, 3]` | confirmed | client 1.60.1.70009, tables Trait* et Spell* (wago.tools) ; durée de Hot Streak 20 s, déjà notée dans talents.json (duration_s, notes) | certain |
| talents.json | hotStreak.duration_s | `20` | — | removed_field | client 1.60.1.70009, tables Trait* et Spell* (wago.tools) | certain |
| talents.json | improvedBlizzard.ranks[2] | `[30]` | `[25]` | confirmed | client 1.60.1.70009, tables Trait* et Spell* (wago.tools) ; courbe du client 15 / 25 / 40 | certain |
| spells.json | pyroblast.ranks[1].min | `95` | `100` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | pyroblast.ranks[1].max | `125` | `132` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | pyroblast.ranks[1].mana | — | `125` | observation | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) | certain |
| spells.json | ice_lance.ranks[1].min | `26` | `28` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | ice_lance.ranks[1].max | `30` | `33` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | ice_lance.ranks[1].mana | — | `45` | observation | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) | certain |
| spells.json | arcane_blast.ranks[1].min | `50` | `57` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | arcane_blast.ranks[1].max | `58` | `66` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | blast_wave.ranks[1].level | `36` | `30` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; niveau appris : SpellLevels.BaseLevel 30 (MaxLevel 36) ; la référence donne 36 aux rangs 1 et 2 | certain |
| spells.json | blast_wave.ranks[1].min | `148` | `153` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | blast_wave.ranks[1].max | `178` | `185` | confirmed | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) ; rang 1 issu d'un talent : référence lue au niveau de base du sort ; décodage au niveau min(MaxLevel, 60) comme les 95 autres rangs | certain |
| spells.json | blast_wave.ranks[1].mana | — | `215` | observation | client 1.60.1.70009, tables Spell*, SpellLevels, SpellPower et SkillLineAbility (wago.tools) | certain |

## Certitudes

49 talent(s) : FC-69893 → FC-70009 :

wandSpecialization, arcaneFocus, improvedChanneling, arcaneSubtlety, magicAbsorption, arcaneConcentration, arcaneResilience, arcaneGeometry, arcaneImpact, arcaneShielding, improvedCounterspell, arcaneMeditation, missileBarrage, presenceOfMind, arcaneMind, arcaneInstability, arcanePower, wakeOfFire, incineration, improvedFireball, ignite, flameThrowing, impact, burningSoul, improvedFlamestrike, improvedScorch, improvedFireWard, hotStreak, masterOfElements, criticalMass, firePower, combustion, frostWarding, improvedFrostbolt, elementalPrecision, iceShards, permafrost, improvedFrostNova, frostbite, piercingIce, frostChanneling, improvedBlizzard, arcticReach, iceBlock, shatter, improvedConeOfCold, coldSnap, fingersOfFrost, wintersChill

## Champs ajoutés

- spells.json : source (15)
- talents.json : name_fr (54)
- talents.json : source (54)
- talents.json : tooltip_values (54)

Provenance · version 1.60.1.70009 r1 · données 3a15c9a67ba0 · générée 2026-09-29T15:35:46Z · fraîcheur fresh · certitude certain · registre 37/108 · hypothèses : candidate <cache>/candidates/1.60.1.70009 (données 2b344940521e) sur la version 1.60.1.70009 r1
