# data: 1.60.1.70707 r1 → r2

Candidate : `<cache>/candidates/1.60.1.70707` (données 84e4c62b2fde).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 69 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 4 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"089c11c95122"` | `"6e649c3d8bd1"` | replaced_file | Client 1.60.1.70707 : fichier décodé par forever decode (candidate) | certain |
| races.json | * | `"0294bc88a9ad"` | `"be29be2fd9d4"` | replaced_file | Client 1.60.1.70707 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"15a9c55a2d53"` | `"6d78bde9620d"` | replaced_file | Client 1.60.1.70707 : fichier décodé par forever decode (candidate) | certain |
| xp_bonuses.json | * | `"63ca323d26eb"` | `"439b79034174"` | replaced_file | Client 1.60.1.70707 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 1 ; source observation ; certitude certain)

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.70707 r1 · données 64f834880b15 · générée 2026-11-03T13:13:47Z · fraîcheur fresh · certitude certain · registre 76/148 · hypothèses : candidate <cache>/candidates/1.60.1.70707 (données 84e4c62b2fde) sur la version 1.60.1.70707 r1

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
| races.json | races | Orc racials 20576 name | Command | Ordre |
| races.json | races | Orc racials 21563 name | Command | Ordre |
| races.json | races | Orc racials 20575 name | Command | Ordre |
| races.json | races | Dwarf racials 1259719 name | Artisan's Precision | Earth Fury |
| xp_bonuses.json | auras | 1328127 name | Elixir of Endless Experience | Élixir d’expérience infinie |
| xp_bonuses.json | auras | 1328127 description | Increases experience gained by $s1% for $d. | Gains d’expérience augmentés de $s1 % pendant $d. |
| xp_bonuses.json | auras | 1328127 items n°1 name | Elixir of Endless Experience | Élixir d’expérience infinie |

fiches PvP : races.json, 1 autre valeur changée ; Druid, 2 sorts ajoutés ou retirés, 5 talents et 2 sorts modifiés ; Mage, 1 talent modifié ; Paladin, 3 sorts ajoutés ou retirés, 14 talents et 1 sort modifiés ; Priest, 1 talent modifié ; Warlock, 1 talent modifié.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| races.json | races | Orc racials 20576 name | Command | Ordre |
| races.json | races | Orc racials 21563 name | Command | Ordre |
| races.json | races | Orc racials 20575 name | Command | Ordre |
| races.json | races | Dwarf racials 1259719 name | Artisan's Precision | Earth Fury |
| Druid | talent Balance Moonkin Form | desc | Shapeshift into Moonkin Form, increasing Omen of Clarity's chance to trigger by $s5%, Armor contribution from items by $24905s1%, and all party or raid members within $24907a1 yards have their Critical Strike chance increased by $24907s1%. Also protects the caster from Polymorph effects and prevents the use of healing spells.    The act of shapeshifting frees the caster of Polymorph and Movement Impairing effects. | Shapeshift into Moonkin Form, increasing Omen of Clarity's chance to trigger by $s5%, Armor contribution from items by $24905s1%, and all party or raid members within $24907a1 yards have their spell Critical Strike chance increased by $24907s1%.  Also protects the caster from Polymorph effects and prevents the use of healing spells.    The act of shapeshifting frees the caster of Polymorph and Movement Impairing effects. |
| Druid | talent Feral Combat Lacérer | name | Lacerate | Lacérer |
| Druid | talent Feral Combat Lacérer | desc | Lacerates the enemy target, making them bleed for $o1 damage over $d plus $s2% weapon damage per existing application of Lacerate on the target. Causes a high amount of threat. This effect stacks up to $u times on the same target. | Lacère la cible, ce qui la fait saigner et lui inflige $o1 $lpoint:points; de dégâts en $d, plus $s2 % des dégâts de l’arme par application existante de Lacérer sur la cible. Génère un niveau de menace très élevé. Cet effet se cumule jusqu’à $u fois sur la même cible. |
| Druid | talent Feral Combat Lacérer | former_names | null | ["Lacerate"] |
| Druid | talent Feral Combat Lacérer | client_key | null | lacRer |
| Druid | talent Feral Combat Leader of the Pack | desc | While in Cat Form, Bear Form, or Dire Bear Form, the Leader of the Pack increases the Critical Strike chance of all party or raid members within $24932a1 yards by $24932s1%. | While in Cat Form, Bear Form, or Dire Bear Form, the Leader of the Pack increases the melee and ranged Critical Strike chance of all party or raid members within $24932a1 yards by $24932s1%. |
| Druid | talent Restoration Naturalist | desc | Reduces the cast time of your Healing Touch and Wild Growth spells by $/1000;S1 sec and increases all damage you deal by $m2%. | Reduces the cast time of your Healing Touch spell by $/1000;S1 sec and increases all damage you deal by $m2%. |
| Druid | talent Restoration Swiftmend | desc | Instantly heals a target with your active Rejuvenation or Regrowth effect for an amount equal to the full duration of the periodic effect of the consumed spell. | Instantly heals a target with an active Rejuvenation or Regrowth effect for an amount equal to the full duration of the periodic effect of one of those spells. |
| Druid | sort Ferocious Bite | rang 1 spell_id | 1328618 | 22568 |
| Druid | sort Ferocious Bite | rang 1 level | 24 | 32 |
| Druid | sort Ferocious Bite | rang 2 spell_id | 22568 | 22827 |
| Druid | sort Ferocious Bite | rang 2 level | 32 | 40 |
| Druid | sort Ferocious Bite | rang 3 spell_id | 22827 | 22828 |
| Druid | sort Ferocious Bite | rang 3 level | 40 | 48 |
| Druid | sort Ferocious Bite | rang 4 spell_id | 22828 | 22829 |
| Druid | sort Ferocious Bite | rang 4 level | 48 | 56 |
| Druid | sort Ferocious Bite | rang 5 spell_id | 22829 | 31018 |
| Druid | sort Ferocious Bite | rang 5 level | 56 | 60 |
| Druid | sort Ferocious Bite | rang 6 | {"spell_id": 31018, "rank": 6, "level": 60, "cast_s": 0, "cooldown_s": null, "gcd_s": 1, "duration_s": null, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 5}, "school": 1, "cost": {"power_type": 3, "amount": 35, "pct": 0}, "mechanic": 0, "diminish": 0, "dispel_type": 0} | null |
| Druid | sort Lacerate | talent | {"node_id": 104949, "key": "lacerate"} | null |
| Druid | sort Lacerate | rang 1 spell_id | 1328617 | 414644 |
| Druid | sort Lacerate | rang 1 level | 25 | 42 |
| Druid | sort Lacerate | rang 2 spell_id | 1328616 | 1235826 |
| Druid | sort Lacerate | rang 2 level | 34 | 50 |
| Druid | sort Lacerate | rang 3 spell_id | 414644 | 1235827 |
| Druid | sort Lacerate | rang 3 level | 42 | 58 |
| Druid | sort Lacerate | rang 4 | {"spell_id": 1235826, "rank": 4, "level": 50, "cast_s": 0, "cooldown_s": null, "gcd_s": 1.5, "duration_s": 15, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 5}, "school": 1, "cost": {"power_type": 1, "amount": 150, "pct": 0}, "mechanic": 15, "diminish": 0, "dispel_type": 0} | null |
| Druid | sort Lacerate | rang 5 | {"spell_id": 1235827, "rank": 5, "level": 58, "cast_s": 0, "cooldown_s": null, "gcd_s": 1.5, "duration_s": 15, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 5}, "school": 1, "cost": {"power_type": 1, "amount": 150, "pct": 0}, "mechanic": 15, "diminish": 0, "dispel_type": 0} | null |
| Druid | sort Lacérer | sort | absent | ajouté |
| Druid | sort Morsure féroce | sort | absent | ajouté |
| Mage | talent Frost Arctic Reach | desc | Increases the range of your Frostbolt, Frost Blast, Ice Lance, and Blizzard spells and the radius of your Frost Nova and Cone of Cold spells by $s1%. | Increases the range of your Frostbolt, Frost Blast, and Blizzard spells and the radius of your Frost Nova and Cone of Cold spells by $s1%. |
| Paladin | talent Holy Divine Precision | desc | Improves your chance to hit with Holy spells by $s1%, and reduces the duration of Silence effects on you by $s2%. | Improves your chance to hit with Holy spells by $s1%. |
| Paladin | talent Holy Serment de lumière | name | Oath of Light | Serment de lumière |
| Paladin | talent Holy Serment de lumière | desc | Swear an Oath to protect target ally for $d, increasing the healing of your Holy Light on them by up to $s1, your Flash of Light by up to $s2, and your Holy Shock by up to $s3. Only one Oath of Light may be sworn by the Paladin at any one time. | Vous jurez de protéger une cible alliée pendant $d, ce qui augmente les soins qui lui sont procurés par votre sort Lumière sacrée de $s1 $lpoint:points; maximum, par votre sort Éclair lumineux de $s2 $lpoint:points; maximum et par votre sort Horion sacré de $s3 $lpoint:points; maximum. Un seul serment de lumière peut être prononcé par le paladin ou la paladine à la fois. |
| Paladin | talent Holy Serment de lumière | former_names | null | ["Oath of Light"] |
| Paladin | talent Holy Serment de lumière | client_key | null | sermentDeLumiRe |
| Paladin | talent Holy Lumière illimitée | name | Boundless Light | Lumière illimitée |
| Paladin | talent Holy Lumière illimitée | desc | Increases the critical strike chance of your Holy Shock spell by $s1% when cast on allies not affected by your Oath of Light. | Augmente de $s1 % les chances de coup critique de votre sort Horion sacré lorsqu’il est lancé sur des cibles alliées qui ne bénéficient pas de votre Serment de lumière. |
| Paladin | talent Holy Lumière illimitée | former_names | null | ["Boundless Light"] |
| Paladin | talent Holy Lumière illimitée | client_key | null | lumiReIllimitE |
| Paladin | talent Holy Holy Power | desc | Increases the critical strike healing bonus of your Holy spells by $s1%. | Increases the critical strike chance of your Holy Shock and Holy Strike spells by $m2%, and all other spells by $m1%. |
| Paladin | talent Holy Light's Vigil | desc | Applies Light's Vigil to a friendly target for $1310909d. The caster's next Holy Shock on the target incurs no cooldown and heals the target and their party for $1310912s1. Only one Vigil per Paladin may be active in each party. | Applies Light's Vigil to the target for $1310909d. Your next Holy Shock cast on them triggers no cooldown and causes enemy targets to suffer $1310914s1 Holy damage and refund $s2% of Light's Vigil's Mana cost, or allied targets to heal their party for $1310912s1. You may only have one Light's Vigil active per party. |
| Paladin | talent Protection Sacred Duty | desc | Reduces the cooldown of your Divine Shield, Divine Protection, and Templar's Bulwark spells by ${$m2/-1000} sec, and reduces the duration of Forbearance by ${$m1/-1000} sec. | Increases your total Stamina by $s1% and reduces the cooldown of your Divine Shield, Divine Protection, and Templar's Bulwark spells by ${$m2/-1000} sec. |
| Paladin | talent Protection Swift Judgement | desc | Unleash the energy of a Seal spell upon an enemy. Does not consume the Seal. Refer to individual Seals for Judgement effect. Does not share a cooldown with your Judgement ability. | Finishes the remaining cooldown on your Judgement ability and reduces the Mana cost of your next Judgement by $s1%. |
| Paladin | talent Protection Stoïcisme | name | Stoicism | Stoïcisme |
| Paladin | talent Protection Stoïcisme | desc | Reduces the duration of Stun and Charm effects on you by $s1%. | Réduit de $s1 % la durée des effets d’étourdissement et de charme qui vous sont infligés. |
| Paladin | talent Protection Stoïcisme | former_names | null | ["Stoicism"] |
| Paladin | talent Protection Stoïcisme | client_key | null | stoCisme |
| Paladin | talent Protection Serment du bouclier | name | Shieldsworn | Serment du bouclier |
| Paladin | talent Protection Serment du bouclier | former_names | null | ["Shieldsworn"] |
| Paladin | talent Protection Serment du bouclier | client_key | null | sermentDuBouclier |
| Paladin | talent Retribution Conviction | desc | Improves your chance to get a critical strike with all spells and attacks by $m1%. | Improves your chance to get a critical strike with melee attacks by $s1%. |
| Paladin | talent Retribution Vindication | desc | Gives your damaging melee attacks a chance to reduce the target's Attack Power by ${$m1/-3*$440667m1} for $440667d. | Gives your damaging melee attacks a chance to reduce the target's Attack Power by ${$m1/-3*$440667m1}, and increase your Attack Power by $m1% for $440667d. |
| Paladin | talent Retribution Two-Handed Weapon Specialization | desc | Increases the physical damage you deal by $s1%, and reduces all threat you generate by $m2% while a two-handed melee weapon is equipped. | Increases the damage you deal with two-handed melee weapons by $s1%. |
| Paladin | talent Retribution Champion of the Light | desc | Increases your spell damage by up to $m1% of your Intellect, and reduces the cast time of your Hammer of Wrath by ${$m2/-1000}.1 sec. | Increases your spell damage by up to $m1% of your Intellect. |
| Paladin | talent Retribution Twist of Light | name | Unsealed Wrath | Twist of Light |
| Paladin | talent Retribution Twist of Light | desc | Your melee attacks store a copy of your active Seal for $1311701d, stacking up to $1311701u times. Landing an attack with a different Seal consumes all stacks, giving the stored Seal its normal chance to activate once per stack. | Reduces the Mana cost of your Seal spells by $s1%, and when you replace your Seal of Command, Seal of Righteousness, Seal of Fury, or Seal of Justice with a different Seal, you gain an Echo of that Seal. Your next melee attack applies the replaced Seal's effects, consuming the Echo. |
| Paladin | talent Retribution Twist of Light | former_names n°2 | null | Unsealed Wrath |
| Paladin | sort Holy Shield | rang 4 | {"spell_id": 1239570, "rank": 4, "level": null, "cast_s": 0, "cooldown_s": null, "gcd_s": null, "duration_s": 10, "pvp_duration_s": null, "range_yd": {"min": 0, "max": 0}, "school": 2, "cost": null, "mechanic": 0, "diminish": 0, "dispel_type": 0} | null |
| Paladin | sort Oath of Light | sort | présent | retiré |
| Paladin | sort Bouclier sacré | sort | absent | ajouté |
| Paladin | sort Serment de lumière | sort | absent | ajouté |
| Priest | talent Discipline Renewed Hope | desc | Your heals from Flash Heal, Lesser Heal, Heal, Greater Heal, and Penance gain $m1% increased critical strike chance when cast on targets with Weakened Soul, and reduce the remaining duration of Weakened Soul on their target by ${$m2/-1000} sec. | Your heals from Flash Heal, Binding Heal, Lesser Heal, Heal, Greater Heal, and Penance gain $m1% increased critical strike chance when cast on targets with Weakened Soul, and reduce the remaining duration of Weakened Soul on their target by ${$m2/-1000} sec. |
| Warlock | talent Affliction Improved Drains | desc | Increases Health drained, damage done, or Mana drained by your Drain Life, Drain Soul, and Drain Mana spells by $m1%. | Increases health drained or damage done by your Drain Life, Drain Soul, and Wrack spells by $m1%. |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.70707 garde la priorité
- sort Oath of Light (Paladin) retiré par la version 1.60.1.70707
- moteurs aux entrées changées : mage_leveling
