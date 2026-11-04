# data: 1.60.1.70755 r2 → r1

Candidate : `<cache>/candidates/1.60.1.70755` (données a1f189445908).

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

- plafond de la bêta : 30 (reporté de la révision 2 ; source observation ; certitude certain)

## Certitudes

53 talent(s) : FC-70707 → FC-70755 :

wandSpecialization, improvedChanneling, missileBarrage, arcaneSubtlety, magicAbsorption, arcaneConcentration, arcaneResilience, arcaneGeometry, arcaneImpact, arcaneBlast, arcaneShielding, improvedCounterspell, arcaneMeditation, arcaneWrath, presenceOfMind, arcaneMind, arcaneInstability, arcanePower, incineration, accelerant, ignite, flameThrowing, impact, burningSoul, improvedFlamestrike, pyroblast, wakeOfFire, improvedScorch, improvedFireWard, hotStreak, masterOfElements, criticalMass, blastWave, firePower, combustion, frostWarding, improvedFrostbolt, precision, iceShards, frostbite, improvedFrostNova, permafrost, frostChanneling, improvedBlizzard, iceLance, arcticReach, iceBlock, shatter, improvedConeOfCold, coldSnap, fingersOfFrost, wintersChill, iceBarrier

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.70755 r1 · données db6f386df442 · générée 2026-11-04T09:27:10Z · fraîcheur stale · certitude certain · registre 76/148 · hypothèses : candidate <cache>/candidates/1.60.1.70755 (données a1f189445908) sur la version 1.60.1.70707 (nouvelle version 1.60.1.70755)

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : différentes
- pvp_dr : différentes

## Valeurs changées

mage_leveling : character_scaling.json, 1 autre valeur changée ; races.json, 1 autre valeur changée.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| character_scaling.json | talents | points_per_tier Rogue | null | 5 |
| races.json | races | Orc racials 20576 name | Ordre | Command |
| races.json | races | Orc racials 20576 name_fr |  | Ordre |
| races.json | races | Orc racials 20576 passive | false | true |
| races.json | races | Orc racials 21563 name | Ordre | Command |
| races.json | races | Orc racials 21563 name_fr |  | Ordre |
| races.json | races | Orc racials 20575 name | Ordre | Command |
| races.json | races | Orc racials 20575 name_fr |  | Ordre |
| races.json | races | Orc racials 20575 passive | false | true |
| races.json | races | Orc racials 20575 effects n°2 | null | {"effect": 6, "aura": 108, "base_points": 5, "misc": 0, "mechanic": 0} |
| races.json | races | Dwarf racials 1259719 name | Earth Fury | Artisan's Precision |
| races.json | races | Dwarf racials 1259719 name_fr | Fureur terrestre | Précision artisanale |
| races.json | races | High Order Skyborne racials 1259705 name_fr | Read Leyline | Lecture des lignes telluriques |

fiches PvP : races.json, 1 autre valeur changée ; Druid, 3 sorts ajoutés ou retirés, 7 talents et 2 sorts modifiés ; Mage, 1 talent modifié ; Paladin, 3 sorts ajoutés ou retirés, 15 talents et 8 sorts modifiés ; Priest, 1 sort ajouté ou retiré, 2 talents modifiés ; Rogue, 11 talents ajoutés ou retirés, 7 sorts ajoutés ou retirés, 24 talents et 5 sorts modifiés ; Shaman, 2 talents ajoutés ou retirés, 1 sort ajouté ou retiré, 2 talents et 5 sorts modifiés ; Warlock, 1 talent modifié ; Warrior, 1 talent ajouté ou retiré, 1 sort ajouté ou retiré, 7 talents et 1 sort modifiés.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| races.json | races | Orc racials 20576 name | Ordre | Command |
| races.json | races | Orc racials 20576 name_fr |  | Ordre |
| races.json | races | Orc racials 20576 passive | false | true |
| races.json | races | Orc racials 21563 name | Ordre | Command |
| races.json | races | Orc racials 21563 name_fr |  | Ordre |
| races.json | races | Orc racials 20575 name | Ordre | Command |
| races.json | races | Orc racials 20575 name_fr |  | Ordre |
| races.json | races | Orc racials 20575 passive | false | true |
| races.json | races | Orc racials 20575 effects n°2 | null | {"effect": 6, "aura": 108, "base_points": 5, "misc": 0, "mechanic": 0} |
| races.json | races | Dwarf racials 1259719 name | Earth Fury | Artisan's Precision |
| races.json | races | Dwarf racials 1259719 name_fr | Fureur terrestre | Précision artisanale |
| races.json | races | High Order Skyborne racials 1259705 name_fr | Read Leyline | Lecture des lignes telluriques |
| Druid | talent Balance Moonkin Form | desc | Shapeshift into Moonkin Form, increasing Omen of Clarity's chance to trigger by $s5%, Armor contribution from items by $24905s1%, and all party or raid members within $24907a1 yards have their spell Critical Strike chance increased by $24907s1%.  Also protects the caster from Polymorph effects and prevents the use of healing spells.    The act of shapeshifting frees the caster of Polymorph and Movement Impairing effects. | Shapeshift into Moonkin Form, increasing Omen of Clarity's chance to trigger by $s5%, Armor contribution from items by $24905s1%, and all party or raid members within $24907a1 yards have their Critical Strike chance increased by $24907s1%. Also protects the caster from Polymorph effects and prevents the use of healing spells.    The act of shapeshifting frees the caster of Polymorph and Movement Impairing effects. |
| Druid | talent Feral Combat Lacerate | name | Lacérer | Lacerate |
| Druid | talent Feral Combat Lacerate | name_fr |  | Lacérer |
| Druid | talent Feral Combat Lacerate | desc | Lacère la cible, ce qui la fait saigner et lui inflige $o1 $lpoint:points; de dégâts en $d, plus $s2 % des dégâts de l’arme par application existante de Lacérer sur la cible. Génère un niveau de menace très élevé. Cet effet se cumule jusqu’à $u fois sur la même cible. | Lacerates the enemy target, making them bleed for $o1 damage over $d plus $s2% weapon damage per existing application of Lacerate on the target. Causes a high amount of threat. This effect stacks up to $u times on the same target. |
| Druid | talent Feral Combat Lacerate | former_names n°2 | null | Lacérer |
| Druid | talent Feral Combat Predatory Discipline | name_fr |  | Predatory Discipline |
| Druid | talent Feral Combat Leader of the Pack | desc | While in Cat Form, Bear Form, or Dire Bear Form, the Leader of the Pack increases the melee and ranged Critical Strike chance of all party or raid members within $24932a1 yards by $24932s1%. | While in Cat Form, Bear Form, or Dire Bear Form, the Leader of the Pack increases the Critical Strike chance of all party or raid members within $24932a1 yards by $24932s1%. |
| Druid | talent Restoration Naturalist | desc | Reduces the cast time of your Healing Touch spell by $/1000;S1 sec and increases all damage you deal by $m2%. | Reduces the cast time of your Healing Touch and Wild Growth spells by $/1000;S1 sec and increases all damage you deal by $m2%. |
| Druid | talent Restoration Bloom | name_fr |  | Bloom |
| Druid | talent Restoration Swiftmend | desc | Instantly heals a target with an active Rejuvenation or Regrowth effect for an amount equal to the full duration of the periodic effect of one of those spells. | Instantly heals a target with your active Rejuvenation or Regrowth effect for an amount equal to the full duration of the periodic effect of the consumed spell. |
| Druid | sort Ferocious Bite | rang 1 spell_id | 22568 | 1328618 |
| Druid | sort Ferocious Bite | rang 1 level | 32 | 24 |
| Druid | sort Ferocious Bite | rang 2 spell_id | 22827 | 22568 |
| Druid | sort Ferocious Bite | rang 2 level | 40 | 32 |
| Druid | sort Ferocious Bite | rang 3 spell_id | 22828 | 22827 |
| Druid | sort Ferocious Bite | rang 3 level | 48 | 40 |
| Druid | sort Ferocious Bite | rang 4 spell_id | 22829 | 22828 |
| Druid | sort Ferocious Bite | rang 4 level | 56 | 48 |
| Druid | sort Ferocious Bite | rang 5 spell_id | 31018 | 22829 |
| Druid | sort Ferocious Bite | rang 5 level | 60 | 56 |
| Druid | sort Ferocious Bite | rang 6 | null | {"spell_id": 31018, "rank": 6, "level": 60, "cast_s": 0, "cooldown_s": null, "gcd_s": 1, "duration_s": null, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 5}, "school": 1, "cost": {"power_type": 3, "amount": 35, "pct": 0}, "mechanic": 0, "diminish": 0, "dispel_type": 0} |
| Druid | sort Lacerate | talent | null | {"node_id": 104949, "key": "lacerate"} |
| Druid | sort Lacerate | rang 1 spell_id | 414644 | 1328617 |
| Druid | sort Lacerate | rang 1 level | 42 | 25 |
| Druid | sort Lacerate | rang 2 spell_id | 1235826 | 1328616 |
| Druid | sort Lacerate | rang 2 level | 50 | 34 |
| Druid | sort Lacerate | rang 3 spell_id | 1235827 | 414644 |
| Druid | sort Lacerate | rang 3 level | 58 | 42 |
| Druid | sort Lacerate | rang 4 | null | {"spell_id": 1235826, "rank": 4, "level": 50, "cast_s": 0, "cooldown_s": null, "gcd_s": 1.5, "duration_s": 15, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 5}, "school": 1, "cost": {"power_type": 1, "amount": 150, "pct": 0}, "mechanic": 15, "diminish": 0, "dispel_type": 0} |
| Druid | sort Lacerate | rang 5 | null | {"spell_id": 1235827, "rank": 5, "level": 58, "cast_s": 0, "cooldown_s": null, "gcd_s": 1.5, "duration_s": 15, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 5}, "school": 1, "cost": {"power_type": 1, "amount": 150, "pct": 0}, "mechanic": 15, "diminish": 0, "dispel_type": 0} |
| Druid | sort Lacérer | sort | présent | retiré |
| Druid | sort Morsure féroce | sort | présent | retiré |
| Druid | sort Poised | sort | absent | ajouté |
| Mage | talent Frost Arctic Reach | desc | Increases the range of your Frostbolt, Frost Blast, and Blizzard spells and the radius of your Frost Nova and Cone of Cold spells by $s1%. | Increases the range of your Frostbolt, Frost Blast, Ice Lance, and Blizzard spells and the radius of your Frost Nova and Cone of Cold spells by $s1%. |
| Paladin | talent Holy Divine Precision | desc | Improves your chance to hit with Holy spells by $s1%. | Improves your chance to hit with Holy spells by $s1%, and reduces the duration of Silence effects on you by $s2%. |
| Paladin | talent Holy Oath of Light | name | Serment de lumière | Oath of Light |
| Paladin | talent Holy Oath of Light | name_fr |  | Serment de lumière |
| Paladin | talent Holy Oath of Light | desc | Vous jurez de protéger une cible alliée pendant $d, ce qui augmente les soins qui lui sont procurés par votre sort Lumière sacrée de $s1 $lpoint:points; maximum, par votre sort Éclair lumineux de $s2 $lpoint:points; maximum et par votre sort Horion sacré de $s3 $lpoint:points; maximum. Un seul serment de lumière peut être prononcé par le paladin ou la paladine à la fois. | Swear an Oath to protect target ally for $d, increasing the healing of your Holy Light on them by up to $s1, your Flash of Light by up to $s2, and your Holy Shock by up to $s3. Only one Oath of Light may be sworn by the Paladin at any one time. |
| Paladin | talent Holy Oath of Light | former_names n°2 | null | Serment de lumière |
| Paladin | talent Holy Boundless Light | name | Lumière illimitée | Boundless Light |
| Paladin | talent Holy Boundless Light | name_fr |  | Lumière illimitée |
| Paladin | talent Holy Boundless Light | desc | Augmente de $s1 % les chances de coup critique de votre sort Horion sacré lorsqu’il est lancé sur des cibles alliées qui ne bénéficient pas de votre Serment de lumière. | Increases the critical strike chance of your Holy Shock spell by $s1% when cast on allies not affected by your Oath of Light. |
| Paladin | talent Holy Boundless Light | former_names n°2 | null | Lumière illimitée |
| Paladin | talent Holy Holy Power | desc | Increases the critical strike chance of your Holy Shock and Holy Strike spells by $m2%, and all other spells by $m1%. | Increases the critical strike healing bonus of your Holy spells by $s1%. |
| Paladin | talent Holy Light's Vigil | desc | Applies Light's Vigil to the target for $1310909d. Your next Holy Shock cast on them triggers no cooldown and causes enemy targets to suffer $1310914s1 Holy damage and refund $s2% of Light's Vigil's Mana cost, or allied targets to heal their party for $1310912s1. You may only have one Light's Vigil active per party. | Applies Light's Vigil to a friendly target for $1310909d. The caster's next Holy Shock on the target incurs no cooldown and heals the target and their party for $1310912s1. Only one Vigil per Paladin may be active in each party. |
| Paladin | talent Protection Sacred Duty | desc | Increases your total Stamina by $s1% and reduces the cooldown of your Divine Shield, Divine Protection, and Templar's Bulwark spells by ${$m2/-1000} sec. | Reduces the cooldown of your Divine Shield, Divine Protection, and Templar's Bulwark spells by ${$m2/-1000} sec, and reduces the duration of Forbearance by ${$m1/-1000} sec. |
| Paladin | talent Protection Swift Judgement | desc | Finishes the remaining cooldown on your Judgement ability and reduces the Mana cost of your next Judgement by $s1%. | Unleash the energy of a Seal spell upon an enemy. Does not consume the Seal. Refer to individual Seals for Judgement effect. Does not share a cooldown with your Judgement ability. |
| Paladin | talent Protection Stoicism | name | Stoïcisme | Stoicism |
| Paladin | talent Protection Stoicism | name_fr |  | Stoïcisme |
| Paladin | talent Protection Stoicism | desc | Réduit de $s1 % la durée des effets d’étourdissement et de charme qui vous sont infligés. | Reduces the duration of Stun and Charm effects on you by $s1%. |
| Paladin | talent Protection Stoicism | former_names n°2 | null | Stoïcisme |
| Paladin | talent Protection Shieldsworn | name | Serment du bouclier | Shieldsworn |
| Paladin | talent Protection Shieldsworn | name_fr |  | Serment du bouclier |
| Paladin | talent Protection Shieldsworn | former_names n°2 | null | Serment du bouclier |
| Paladin | talent Retribution Conviction | desc | Improves your chance to get a critical strike with melee attacks by $s1%. | Improves your chance to get a critical strike with all spells and attacks by $m1%. |
| Paladin | talent Retribution Vindication | desc | Gives your damaging melee attacks a chance to reduce the target's Attack Power by ${$m1/-3*$440667m1}, and increase your Attack Power by $m1% for $440667d. | Gives your damaging melee attacks a chance to reduce the target's Attack Power by ${$m1/-3*$440667m1} for $440667d. |
| Paladin | talent Retribution Two-Handed Weapon Specialization | desc | Increases the damage you deal with two-handed melee weapons by $s1%. | Increases the physical damage you deal by $s1%, and reduces all threat you generate by $m2% while a two-handed melee weapon is equipped. |
| Paladin | talent Retribution Turn Evil | name_fr |  | Turn Evil |
| Paladin | talent Retribution Champion of the Light | desc | Increases your spell damage by up to $m1% of your Intellect. | Increases your spell damage by up to $m1% of your Intellect, and reduces the cast time of your Hammer of Wrath by ${$m2/-1000}.1 sec. |
| Paladin | talent Retribution Unsealed Wrath | name | Twist of Light | Unsealed Wrath |
| Paladin | talent Retribution Unsealed Wrath | name_fr | Effet de lumière | Courroux descellé |
| Paladin | talent Retribution Unsealed Wrath | desc | Reduces the Mana cost of your Seal spells by $s1%, and when you replace your Seal of Command, Seal of Righteousness, Seal of Fury, or Seal of Justice with a different Seal, you gain an Echo of that Seal. Your next melee attack applies the replaced Seal's effects, consuming the Echo. | Your melee attacks store a copy of your active Seal for $1311701d, stacking up to $1311701u times. Landing an attack with a different Seal consumes all stacks, giving the stored Seal its normal chance to activate once per stack. |
| Paladin | sort sort 1038 | name_fr | Salut |  |
| Paladin | sort sort 1038 | rang 1 level | 26 | null |
| Paladin | sort sort 1038 | rang 1 gcd_s | 1.5 | null |
| Paladin | sort sort 1038 | rang 1 duration_s | 3600 | null |
| Paladin | sort sort 1038 | rang 1 range_yd | {"min": 0, "max": 30} | null |
| Paladin | sort sort 1038 | rang 1 school | 2 | 0 |
| Paladin | sort sort 1038 | rang 1 cost | {"power_type": 0, "amount": 0, "pct": 8} | null |
| Paladin | sort sort 1038 | rang 1 dispel_type | 1 | 0 |
| Paladin | sort sort 19977 | name_fr | Bénédiction de lumière |  |
| Paladin | sort sort 19977 | rang 1 level | 40 | null |
| Paladin | sort sort 19977 | rang 1 gcd_s | 1.5 | null |
| Paladin | sort sort 19977 | rang 1 duration_s | 3600 | null |
| Paladin | sort sort 19977 | rang 1 range_yd | {"min": 0, "max": 30} | null |
| Paladin | sort sort 19977 | rang 1 school | 2 | 0 |
| Paladin | sort sort 19977 | rang 1 cost | {"power_type": 0, "amount": 85, "pct": 0} | null |
| Paladin | sort sort 19977 | rang 1 dispel_type | 1 | 0 |
| Paladin | sort sort 19978 | name_fr | Bénédiction de lumière |  |
| Paladin | sort sort 19978 | rang 1 level | 50 | null |
| Paladin | sort sort 19978 | rang 1 gcd_s | 1.5 | null |
| Paladin | sort sort 19978 | rang 1 duration_s | 3600 | null |
| Paladin | sort sort 19978 | rang 1 range_yd | {"min": 0, "max": 30} | null |
| Paladin | sort sort 19978 | rang 1 school | 2 | 0 |
| Paladin | sort sort 19978 | rang 1 cost | {"power_type": 0, "amount": 110, "pct": 0} | null |
| Paladin | sort sort 19978 | rang 1 dispel_type | 1 | 0 |
| Paladin | sort sort 19979 | name_fr | Bénédiction de lumière |  |
| Paladin | sort sort 19979 | rang 1 level | 60 | null |
| Paladin | sort sort 19979 | rang 1 gcd_s | 1.5 | null |
| Paladin | sort sort 19979 | rang 1 duration_s | 3600 | null |
| Paladin | sort sort 19979 | rang 1 range_yd | {"min": 0, "max": 30} | null |
| Paladin | sort sort 19979 | rang 1 school | 2 | 0 |
| Paladin | sort sort 19979 | rang 1 cost | {"power_type": 0, "amount": 135, "pct": 0} | null |
| Paladin | sort sort 19979 | rang 1 dispel_type | 1 | 0 |
| Paladin | sort Holy Shield | rang 4 | null | {"spell_id": 1239570, "rank": 4, "level": 60, "cast_s": 0, "cooldown_s": 10, "gcd_s": 1.5, "duration_s": 10, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 0}, "school": 2, "cost": {"power_type": 0, "amount": 240, "pct": 0}, "mechanic": 0, "diminish": 0, "dispel_type": 1} |
| Paladin | sort sort 25890 | name_fr | Bénédiction de lumière supérieure |  |
| Paladin | sort sort 25890 | rang 1 level | 60 | null |
| Paladin | sort sort 25890 | rang 1 gcd_s | 1.5 | null |
| Paladin | sort sort 25890 | rang 1 duration_s | 3600 | null |
| Paladin | sort sort 25890 | rang 1 range_yd | {"min": 0, "max": 40} | null |
| Paladin | sort sort 25890 | rang 1 school | 2 | 0 |
| Paladin | sort sort 25890 | rang 1 cost | {"power_type": 0, "amount": 260, "pct": 0} | null |
| Paladin | sort sort 25890 | rang 1 dispel_type | 1 | 0 |
| Paladin | sort sort 25895 | name_fr | Salut collectif |  |
| Paladin | sort sort 25895 | rang 1 level | 60 | null |
| Paladin | sort sort 25895 | rang 1 gcd_s | 1.5 | null |
| Paladin | sort sort 25895 | rang 1 duration_s | 3600 | null |
| Paladin | sort sort 25895 | rang 1 range_yd | {"min": 0, "max": 40} | null |
| Paladin | sort sort 25895 | rang 1 school | 2 | 0 |
| Paladin | sort sort 25895 | rang 1 cost | {"power_type": 0, "amount": 0, "pct": 16} | null |
| Paladin | sort sort 25895 | rang 1 dispel_type | 1 | 0 |
| Paladin | sort Bouclier sacré | sort | présent | retiré |
| Paladin | sort sort 1325499 | name_fr | Révocation |  |
| Paladin | sort sort 1325499 | rang 1 level | 26 | null |
| Paladin | sort sort 1325499 | rang 1 gcd_s | 1.5 | null |
| Paladin | sort sort 1325499 | rang 1 range_yd | {"min": 0, "max": 40} | null |
| Paladin | sort sort 1325499 | rang 1 school | 2 | 0 |
| Paladin | sort sort 1325499 | rang 1 dispel_type | 1 | 0 |
| Paladin | sort Serment de lumière | sort | présent | retiré |
| Paladin | sort Oath of Light | sort | absent | ajouté |
| Priest | talent Discipline Renewed Hope | desc | Your heals from Flash Heal, Binding Heal, Lesser Heal, Heal, Greater Heal, and Penance gain $m1% increased critical strike chance when cast on targets with Weakened Soul, and reduce the remaining duration of Weakened Soul on their target by ${$m2/-1000} sec. | Your heals from Flash Heal, Lesser Heal, Heal, Greater Heal, and Penance gain $m1% increased critical strike chance when cast on targets with Weakened Soul, and reduce the remaining duration of Weakened Soul on their target by ${$m2/-1000} sec. |
| Priest | talent Holy Holy Binding | name_fr |  | Holy Binding |
| Priest | sort Binding Heal | sort | présent | retiré |
| Rogue | talent Assassination Murder | talent | présent | retiré |
| Rogue | talent Assassination Relentless Strikes | node_id | 105759 | 113633 |
| Rogue | talent Assassination Relentless Strikes | tier | 3 | 5 |
| Rogue | talent Assassination Relentless Strikes | max | 1 | 5 |
| Rogue | talent Assassination Improved Expose Armor | tier | 3 | 2 |
| Rogue | talent Assassination Lethality | max | 5 | 2 |
| Rogue | talent Assassination Vigor | node_id | 105718 | 105720 |
| Rogue | talent Assassination Vigor | tier | 5 | 3 |
| Rogue | talent Assassination Mutilate | tier | 5 | 7 |
| Rogue | talent Assassination Mutilate | desc | Instantly attacks with both weapons for $1310706s2% weapon damage plus an additional ${$1310706m1*$1310706m2/100} with each weapon. Damage increased by $m4% against Poisoned targets. Awards $m1 Combo $LPoint:Points;. | Instantly attacks with both weapons for $399960s2% weapon damage plus an additional ${$399960m1*$399960m2/100} with each weapon. Damage increased by $m4% against Poisoned targets. Awards $m1 Combo $LPoint:Points;. |
| Rogue | talent Assassination Mutilate | spell_id | 1310707 | 399956 |
| Rogue | talent Assassination Mutilate | prereq | null | {"node_id": 105712, "tier": 5, "col": 2} |
| Rogue | talent Assassination Mutilate | prereqs 105712 | null | {"node_id": 105712, "tier": 5, "col": 2, "kind": "sufficient"} |
| Rogue | talent Assassination Seal Fate | max | 5 | 3 |
| Rogue | talent Assassination Venom | talent | présent | retiré |
| Rogue | talent Combat Improved Sprint | tier | 3 | 2 |
| Rogue | talent Combat Dual Wield Specialization | node_id | 105740 | 113635 |
| Rogue | talent Combat Dual Wield Specialization | tier | 4 | 5 |
| Rogue | talent Combat Dual Wield Specialization | col | 3 | 1 |
| Rogue | talent Combat Dual Wield Specialization | max | 5 | 2 |
| Rogue | talent Combat Dual Wield Specialization | prereq | {"node_id": 105737, "tier": 2, "col": 3} | null |
| Rogue | talent Combat Dual Wield Specialization | prereqs 105737 | {"node_id": 105737, "tier": 2, "col": 3, "kind": "sufficient"} | null |
| Rogue | talent Combat Weapon Expertise | tier | 6 | 4 |
| Rogue | talent Combat Weapon Expertise | col | 2 | 3 |
| Rogue | talent Combat Weapon Expertise | prereq node_id | 105728 | 105737 |
| Rogue | talent Combat Weapon Expertise | prereq tier | 5 | 2 |
| Rogue | talent Combat Weapon Expertise | prereq col | 2 | 3 |
| Rogue | talent Combat Weapon Expertise | prereqs 105728 | {"node_id": 105728, "tier": 5, "col": 2, "kind": "sufficient"} | null |
| Rogue | talent Combat Weapon Expertise | prereqs 105737 | null | {"node_id": 105737, "tier": 2, "col": 3, "kind": "sufficient"} |
| Rogue | talent Combat Aggression | tier | 6 | 4 |
| Rogue | talent Combat Aggression | col | 3 | 4 |
| Rogue | talent Combat Adrenaline Rush | prereq | null | {"node_id": 105728, "tier": 5, "col": 2} |
| Rogue | talent Combat Adrenaline Rush | prereqs 105728 | null | {"node_id": 105728, "tier": 5, "col": 2, "kind": "sufficient"} |
| Rogue | talent Subtlety Camouflage | tier | 1 | 2 |
| Rogue | talent Subtlety Camouflage | col | 1 | 2 |
| Rogue | talent Subtlety Camouflage | max | 5 | 3 |
| Rogue | talent Subtlety Opportunity | max | 2 | 5 |
| Rogue | talent Subtlety Setup | tier | 2 | 1 |
| Rogue | talent Subtlety Elusiveness | tier | 2 | 4 |
| Rogue | talent Subtlety Elusiveness | col | 2 | 1 |
| Rogue | talent Subtlety Dirty Tricks | col | 3 | 4 |
| Rogue | talent Subtlety Improved Ambush | col | 4 | 3 |
| Rogue | talent Subtlety Ghostly Strike | tier | 3 | 4 |
| Rogue | talent Subtlety Improved Distract | talent | présent | retiré |
| Rogue | talent Subtlety Heightened Senses | tier | 4 | 5 |
| Rogue | talent Subtlety Premeditation | tier | 4 | 3 |
| Rogue | talent Subtlety Serrated Blades | tier | 4 | 3 |
| Rogue | talent Subtlety Dirty Deeds | tier | 5 | 2 |
| Rogue | talent Subtlety Hemorrhage | prereq tier | 4 | 3 |
| Rogue | talent Subtlety Hemorrhage | prereqs 105752 tier | 4 | 3 |
| Rogue | talent Subtlety Quietus | tier | 6 | 4 |
| Rogue | talent Subtlety Quietus | col | 1 | 4 |
| Rogue | talent Subtlety Quietus | max | 5 | 2 |
| Rogue | talent Subtlety Quietus | prereq node_id | 105745 | 105757 |
| Rogue | talent Subtlety Quietus | prereq tier | 5 | 2 |
| Rogue | talent Subtlety Quietus | prereq col | 1 | 4 |
| Rogue | talent Subtlety Quietus | prereqs 105745 | {"node_id": 105745, "tier": 5, "col": 1, "kind": "sufficient"} | null |
| Rogue | talent Subtlety Quietus | prereqs 105757 | null | {"node_id": 105757, "tier": 2, "col": 4, "kind": "sufficient"} |
| Rogue | talent Subtlety Cutthroat | talent | présent | retiré |
| Rogue | talent Subtlety Thousand Cuts | talent | présent | retiré |
| Rogue | talent Assassination Blood Splatter | talent | absent | ajouté |
| Rogue | talent Assassination Toxine | talent | absent | ajouté |
| Rogue | talent Combat Sang-froid | talent | absent | ajouté |
| Rogue | talent Combat Flash of Steel | talent | absent | ajouté |
| Rogue | talent Subtlety Boot Knife | talent | absent | ajouté |
| Rogue | talent Subtlety Death Mark | talent | absent | ajouté |
| Rogue | sort Dual Wield Specialization | talent node_id | 105740 | 113635 |
| Rogue | sort Murder | talent | {"node_id": 105720, "key": "murder"} | null |
| Rogue | sort Relentless Strikes | talent node_id | 105759 | 113633 |
| Rogue | sort Vigor | talent node_id | 105718 | 105720 |
| Rogue | sort Mutilate | rang 1 spell_id | 1310707 | 399956 |
| Rogue | sort Mutilate | rang 1 rank | 1 | 2 |
| Rogue | sort Mutilate | rang 1 level | 30 | 40 |
| Rogue | sort Mutilate | rang 2 spell_id | 399956 | 1241582 |
| Rogue | sort Mutilate | rang 2 rank | 2 | 3 |
| Rogue | sort Mutilate | rang 2 level | 40 | 50 |
| Rogue | sort Mutilate | rang 3 spell_id | 1241582 | 1241584 |
| Rogue | sort Mutilate | rang 3 rank | 3 | 4 |
| Rogue | sort Mutilate | rang 3 level | 50 | 60 |
| Rogue | sort Mutilate | rang 4 | {"spell_id": 1241584, "rank": 4, "level": 60, "cast_s": 0, "cooldown_s": null, "gcd_s": 1, "duration_s": null, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 5}, "school": 1, "cost": {"power_type": 3, "amount": 60, "pct": 0}, "mechanic": 0, "diminish": 0, "dispel_type": 0} | null |
| Rogue | sort Venom | sort | présent | retiré |
| Rogue | sort Coup de Grace | sort | présent | retiré |
| Rogue | sort sort 1310709 | sort | absent | ajouté |
| Rogue | sort Death Mark | sort | absent | ajouté |
| Rogue | sort Poised | sort | absent | ajouté |
| Rogue | sort Surin | sort | absent | ajouté |
| Rogue | sort Toxine | sort | absent | ajouté |
| Rogue | tree_checks | n°1 counts 253 | 16 | 15 |
| Rogue | tree_checks | n°3 counts 39 | 14 | 15 |
| Shaman | talent Elemental Combat Lava Burst | talent | présent | retiré |
| Shaman | talent Enhancement Improved Ghost Wolf | tier | 2 | 4 |
| Shaman | talent Enhancement Improved Ghost Wolf | col | 3 | 4 |
| Shaman | talent Enhancement Improved Lightning Shield | col | 4 | 3 |
| Shaman | talent Elemental Combat Call of Thunder | talent | absent | ajouté |
| Shaman | sort Chain Lightning | rang 1 cast_s | 2 | 2.5 |
| Shaman | sort Chain Lightning | rang 1 cost amount | 145 | 245 |
| Shaman | sort Chain Lightning | rang 2 cast_s | 2 | 2.5 |
| Shaman | sort Chain Lightning | rang 2 cost amount | 200 | 360 |
| Shaman | sort Chain Lightning | rang 3 cast_s | 2 | 2.5 |
| Shaman | sort Chain Lightning | rang 3 cost amount | 250 | 425 |
| Shaman | sort Chain Lightning | rang 4 cast_s | 2 | 2.5 |
| Shaman | sort Chain Lightning | rang 4 cost amount | 315 | 495 |
| Shaman | sort Call of Thunder | talent | null | {"node_id": 104760, "key": "callOfThunder"} |
| Shaman | sort Stormstrike | rang 1 cooldown_s | 8 | 6 |
| Shaman | sort Lava Burst | sort | présent | retiré |
| Shaman | sort Riptide | rang 1 cooldown_s | 6 | 12 |
| Shaman | sort Riptide | rang 1 cost amount | 245 | 150 |
| Shaman | sort Riptide | rang 2 cooldown_s | 6 | 12 |
| Shaman | sort Riptide | rang 2 cost amount | 300 | 180 |
| Shaman | sort Riptide | rang 3 cooldown_s | 6 | 12 |
| Shaman | sort Riptide | rang 3 cost amount | 385 | 230 |
| Shaman | sort Totemic Projection | rang 1 cooldown_s | 60 | 30 |
| Warlock | talent Affliction Improved Drains | desc | Increases health drained or damage done by your Drain Life, Drain Soul, and Wrack spells by $m1%. | Increases Health drained, damage done, or Mana drained by your Drain Life, Drain Soul, and Drain Mana spells by $m1%. |
| Warrior | talent Arms Improved Tactical Mastery | max | 5 | 3 |
| Warrior | talent Arms Bloodthrill | max | 5 | 2 |
| Warrior | talent Fury Raging Blows | tier | 4 | 6 |
| Warrior | talent Fury Raging Blows | col | 2 | 1 |
| Warrior | talent Fury Raging Blows | max | 1 | 2 |
| Warrior | talent Fury Enrage | tier | 4 | 3 |
| Warrior | talent Fury Enrage | col | 3 | 4 |
| Warrior | talent Fury Flurry | col | 2 | 3 |
| Warrior | talent Fury Flurry | max | 5 | 3 |
| Warrior | talent Fury Flurry | prereq | {"node_id": 105927, "tier": 5, "col": 2} | null |
| Warrior | talent Fury Flurry | prereqs 105927 | {"node_id": 105927, "tier": 5, "col": 2, "kind": "sufficient"} | null |
| Warrior | talent Fury Gore Drinker | tier | 6 | 5 |
| Warrior | talent Fury Gore Drinker | prereq node_id | 105931 | 105934 |
| Warrior | talent Fury Gore Drinker | prereq tier | 4 | 3 |
| Warrior | talent Fury Gore Drinker | prereqs 105931 | {"node_id": 105931, "tier": 4, "col": 3, "kind": "sufficient"} | null |
| Warrior | talent Fury Gore Drinker | prereqs 105934 | null | {"node_id": 105934, "tier": 3, "col": 3, "kind": "sufficient"} |
| Warrior | talent Fury Bloodthirst | prereq | null | {"node_id": 105927, "tier": 5, "col": 2} |
| Warrior | talent Fury Bloodthirst | prereqs 105927 | null | {"node_id": 105927, "tier": 5, "col": 2, "kind": "sufficient"} |
| Warrior | talent Fury Frappes téméraires | talent | absent | ajouté |
| Warrior | sort Slam | rang 1 cooldown_s | 18 | 15 |
| Warrior | sort Slam | rang 2 cooldown_s | 18 | 15 |
| Warrior | sort Slam | rang 3 cooldown_s | 18 | 15 |
| Warrior | sort Slam | rang 4 cooldown_s | 18 | 15 |
| Warrior | sort Slam | rang 5 cooldown_s | 18 | 15 |
| Warrior | sort Frappes téméraires | sort | absent | ajouté |
| Warrior | tree_checks | n°2 counts 256 | 13 | 14 |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » : relevé écarté, le client 1.60.1.70755 fait foi ; ton observation datait de 1.60.1.70707
- sort Lacérer (Druid) retiré par la version 1.60.1.70755
- sort Morsure féroce (Druid) retiré par la version 1.60.1.70755
- sort Bouclier sacré (Paladin) retiré par la version 1.60.1.70755
- sort Serment de lumière (Paladin) retiré par la version 1.60.1.70755
- sort Binding Heal (Priest) retiré par la version 1.60.1.70755
- sort Coup de Grace (Rogue) retiré par la version 1.60.1.70755
- sort Venom (Rogue) retiré par la version 1.60.1.70755
- sort Lava Burst (Shaman) retiré par la version 1.60.1.70755
- moteurs aux entrées changées : mage_leveling
