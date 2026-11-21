# data: 1.60.1.71037 r2 → r1

Candidate : `<cache>/candidates/1.60.1.71037` (données eb830eeb31a6).

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

53 talent(s) : FC-70959 → FC-71037 :

wandSpecialization, improvedChanneling, missileBarrage, arcaneSubtlety, magicAbsorption, arcaneConcentration, arcaneResilience, arcaneGeometry, arcaneImpact, arcaneBlast, arcaneShielding, improvedCounterspell, arcaneMeditation, arcaneWrath, presenceOfMind, arcaneMind, arcaneInstability, arcanePower, incineration, accelerant, ignite, flameThrowing, impact, burningSoul, improvedFlamestrike, pyroblast, wakeOfFire, improvedScorch, improvedFireWard, hotStreak, masterOfElements, criticalMass, blastWave, firePower, combustion, frostWarding, improvedFrostbolt, precision, iceShards, frostbite, improvedFrostNova, permafrost, frostChanneling, improvedBlizzard, iceLance, arcticReach, iceBlock, shatter, improvedConeOfCold, coldSnap, fingersOfFrost, wintersChill, iceBarrier

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.71037 r1 · données 3c9910f23881 · générée 2026-11-21T08:07:34Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.71037 (données eb830eeb31a6) sur la version 1.60.1.70959 (nouvelle version 1.60.1.71037)

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : différentes
- pvp_dr : différentes

## Valeurs changées

mage_leveling : xp_bonuses.json, 1 autre valeur changée.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| xp_bonuses.json | food | n°8 spell | 1248377 | 1248381 |
| xp_bonuses.json | food | n°12 item | 6290 | 5525 |
| xp_bonuses.json | food | n°12 name | Brilliant Smallfish | Boiled Clams |
| xp_bonuses.json | food | n°12 spell | 1249500 | 1248377 |
| xp_bonuses.json | food | n°12 buff_spell | 1249519 | 1248406 |
| xp_bonuses.json | food | n°13 item | 6888 | 6290 |
| xp_bonuses.json | food | n°13 name | Herb Baked Egg | Brilliant Smallfish |
| xp_bonuses.json | food | n°13 spell | 1248377 | 1249500 |
| xp_bonuses.json | food | n°13 buff_spell | 1248406 | 1249519 |
| xp_bonuses.json | food | n°14 item | 6890 | 6888 |
| xp_bonuses.json | food | n°14 name | Smoked Bear Meat | Herb Baked Egg |
| xp_bonuses.json | food | n°14 spell | 1248380 | 1248377 |
| xp_bonuses.json | food | n°14 buff_spell | 1248422 | 1248406 |
| xp_bonuses.json | food | n°15 item | 12224 | 6890 |
| xp_bonuses.json | food | n°15 name | Crispy Bat Wing | Smoked Bear Meat |
| xp_bonuses.json | food | n°15 spell | 1248379 | 1248380 |
| xp_bonuses.json | food | n°15 buff_spell | 1248421 | 1248422 |
| xp_bonuses.json | food | n°16 item | 249865 | 12224 |
| xp_bonuses.json | food | n°16 name | Peace Tea | Crispy Bat Wing |
| xp_bonuses.json | food | n°16 spell | 1249920 | 1248379 |
| xp_bonuses.json | food | n°16 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°16 buff_spell | 1249927 | 1248421 |
| xp_bonuses.json | food | n°17 item | 249871 | 249865 |
| xp_bonuses.json | food | n°17 name | Venomous Smoothie | Peace Tea |
| xp_bonuses.json | food | n°17 spell | 1249914 | 1249920 |
| xp_bonuses.json | food | n°17 buff_spell | 1249926 | 1249927 |
| xp_bonuses.json | food | n°18 item | 250079 | 249871 |
| xp_bonuses.json | food | n°18 name | Tasty Raptor Bites | Venomous Smoothie |
| xp_bonuses.json | food | n°18 spell | 1248379 | 1249914 |
| xp_bonuses.json | food | n°18 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°18 buff_spell | 1248421 | 1249926 |
| xp_bonuses.json | food | n°19 item | 287973 | 250079 |
| xp_bonuses.json | food | n°19 name | Tender Wolf Steak | Tasty Raptor Bites |
| xp_bonuses.json | food | n°19 spell | 1248395 | 1248379 |
| xp_bonuses.json | food | n°19 buff_spell | 1248420 | 1248421 |
| xp_bonuses.json | food | n°20 item | 287974 | 287973 |
| xp_bonuses.json | food | n°20 name | Grilled Squid | Tender Wolf Steak |
| xp_bonuses.json | food | n°20 spell | 1249522 | 1248395 |
| xp_bonuses.json | food | n°20 buff_spell | 1249523 | 1248420 |
| xp_bonuses.json | food | n°21 item | 724 | 287974 |
| xp_bonuses.json | food | n°21 name | Goretusk Liver Pie | Grilled Squid |
| xp_bonuses.json | food | n°21 required_level | 5 | 1 |
| xp_bonuses.json | food | n°21 spell | 1248384 | 1249522 |
| xp_bonuses.json | food | n°21 buff_spell | 1248422 | 1249523 |
| xp_bonuses.json | food | n°22 item | 733 | 724 |
| xp_bonuses.json | food | n°22 name | Westfall Stew | Goretusk Liver Pie |
| xp_bonuses.json | food | n°22 spell | 1248687 | 1248384 |
| xp_bonuses.json | food | n°22 buff_spell | null | 1248422 |
| xp_bonuses.json | food | n°22 buff_name | null | Well Fed |
| xp_bonuses.json | food | n°22 buff_duration_ms | null | 900000 |
| xp_bonuses.json | food | n°23 item | 1082 | 733 |
| xp_bonuses.json | food | n°23 name | Redridge Goulash | Westfall Stew |
| xp_bonuses.json | food | n°23 spell | 1248383 | 1248687 |
| xp_bonuses.json | food | n°23 buff_spell | 1248421 | null |
| xp_bonuses.json | food | n°23 buff_name | Well Fed | null |
| xp_bonuses.json | food | n°23 buff_duration_ms | 900000 | null |
| xp_bonuses.json | food | n°24 item | 2683 | 1082 |
| xp_bonuses.json | food | n°24 name | Crab Cake | Redridge Goulash |
| xp_bonuses.json | food | n°25 item | 2684 | 2683 |
| xp_bonuses.json | food | n°25 name | Coyote Steak | Crab Cake |
| xp_bonuses.json | food | n°25 spell | 1248382 | 1248383 |
| xp_bonuses.json | food | n°25 buff_spell | 1248420 | 1248421 |
| xp_bonuses.json | food | n°26 item | 2687 | 2684 |
| xp_bonuses.json | food | n°26 name | Dry Pork Ribs | Coyote Steak |
| xp_bonuses.json | food | n°26 spell | 1248384 | 1248382 |
| xp_bonuses.json | food | n°26 buff_spell | 1248422 | 1248420 |
| xp_bonuses.json | food | n°27 item | 3220 | 2687 |
| xp_bonuses.json | food | n°27 name | Blood Sausage | Dry Pork Ribs |
| xp_bonuses.json | food | n°28 item | 3662 | 3220 |
| xp_bonuses.json | food | n°28 name | Crocolisk Steak | Blood Sausage |
| xp_bonuses.json | food | n°28 spell | 1248382 | 1248384 |
| xp_bonuses.json | food | n°28 buff_spell | 1248420 | 1248422 |
| xp_bonuses.json | food | n°29 item | 3726 | 3662 |
| xp_bonuses.json | food | n°29 name | Big Bear Steak | Crocolisk Steak |
| xp_bonuses.json | food | n°29 spell | 1248384 | 1248382 |
| xp_bonuses.json | food | n°29 buff_spell | 1248422 | 1248420 |
| xp_bonuses.json | food | n°30 item | 4592 | 3726 |
| xp_bonuses.json | food | n°30 name | Longjaw Mud Snapper | Big Bear Steak |
| xp_bonuses.json | food | n°30 spell | 1249506 | 1248384 |
| xp_bonuses.json | food | n°30 buff_spell | 1249519 | 1248422 |
| xp_bonuses.json | food | n°31 item | 5095 | 4592 |
| xp_bonuses.json | food | n°31 name | Rainbow Fin Albacore | Longjaw Mud Snapper |
| xp_bonuses.json | food | n°31 spell | 1249501 | 1249506 |
| xp_bonuses.json | food | n°31 buff_spell | 1249520 | 1249519 |
| xp_bonuses.json | food | n°32 item | 5476 | 5095 |
| xp_bonuses.json | food | n°32 name | Fillet of Frenzy | Rainbow Fin Albacore |
| xp_bonuses.json | food | n°32 spell | 1249505 | 1249501 |
| xp_bonuses.json | food | n°32 buff_spell | 1249521 | 1249520 |
| xp_bonuses.json | food | n°33 item | 5479 | 5476 |
| xp_bonuses.json | food | n°33 name | Crispy Lizard Tail | Fillet of Frenzy |
| xp_bonuses.json | food | n°33 spell | 1248381 | 1249505 |
| xp_bonuses.json | food | n°33 buff_spell | 1248406 | 1249521 |
| xp_bonuses.json | food | n°34 item | 6316 | 5479 |
| xp_bonuses.json | food | n°34 name | Loch Frenzy Delight | Crispy Lizard Tail |
| xp_bonuses.json | food | n°34 spell | 1249502 | 1248381 |
| xp_bonuses.json | food | n°34 buff_spell | 1249521 | 1248406 |
| xp_bonuses.json | food | n°35 item | 12213 | 5526 |
| xp_bonuses.json | food | n°35 name | Carrion Surprise | Clam Chowder |
| xp_bonuses.json | food | n°36 item | 249866 | 6316 |
| xp_bonuses.json | food | n°36 name | Royal Tea | Loch Frenzy Delight |
| xp_bonuses.json | food | n°36 spell | 1249921 | 1249502 |
| xp_bonuses.json | food | n°36 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°36 buff_spell | 1249927 | 1249521 |
| xp_bonuses.json | food | n°37 item | 249872 | 12213 |
| xp_bonuses.json | food | n°37 name | Slimy Smoothie | Carrion Surprise |
| xp_bonuses.json | food | n°37 spell | 1249915 | 1248381 |
| xp_bonuses.json | food | n°37 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°37 buff_spell | 1249926 | 1248406 |
| xp_bonuses.json | food | n°38 item | 250077 | 249866 |
| xp_bonuses.json | food | n°38 name | Twice-Spiced Raptor Slice | Royal Tea |
| xp_bonuses.json | food | n°38 spell | 1248383 | 1249921 |
| xp_bonuses.json | food | n°38 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°38 buff_spell | 1248421 | 1249927 |
| xp_bonuses.json | food | n°39 item | 250080 | 249872 |
| xp_bonuses.json | food | n°39 name | Breakfast Omelette | Slimy Smoothie |
| xp_bonuses.json | food | n°39 spell | 1248381 | 1249915 |
| xp_bonuses.json | food | n°39 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°39 buff_spell | 1248406 | 1249926 |
| xp_bonuses.json | food | n°40 item | 263509 | 250077 |
| xp_bonuses.json | food | n°40 name | Skywall Souffle | Twice-Spiced Raptor Slice |
| xp_bonuses.json | food | n°40 spell | 1248377 | 1248383 |
| xp_bonuses.json | food | n°40 buff_spell | 1248406 | 1248421 |
| xp_bonuses.json | food | n°41 item | 263512 | 250080 |
| xp_bonuses.json | food | n°41 name | Pincer Bites | Breakfast Omelette |
| xp_bonuses.json | food | n°41 spell | 1248379 | 1248381 |
| xp_bonuses.json | food | n°41 buff_spell | 1248421 | 1248406 |
| xp_bonuses.json | food | n°42 item | 268912 | 263509 |
| xp_bonuses.json | food | n°42 name | Expiring Crab Cake | Skywall Souffle |
| xp_bonuses.json | food | n°42 spell | 1248381 | 1248377 |
| xp_bonuses.json | food | n°43 item | 268913 | 263512 |
| xp_bonuses.json | food | n°43 name | Expiring Crocolisk Steak | Pincer Bites |
| xp_bonuses.json | food | n°43 spell | 1248381 | 1248379 |
| xp_bonuses.json | food | n°43 buff_spell | 1248406 | 1248421 |
| xp_bonuses.json | food | n°44 item | 21072 | 268912 |
| xp_bonuses.json | food | n°44 name | Smoked Sagefish | Expiring Crab Cake |
| xp_bonuses.json | food | n°44 required_level | 10 | 5 |
| xp_bonuses.json | food | n°44 spell | 1249504 | 1248381 |
| xp_bonuses.json | food | n°44 buff_spell | 1249520 | 1248406 |
| xp_bonuses.json | food | n°45 item | 1017 | 268913 |
| xp_bonuses.json | food | n°45 name | Seasoned Wolf Kabob | Expiring Crocolisk Steak |
| xp_bonuses.json | food | n°45 required_level | 15 | 5 |
| xp_bonuses.json | food | n°45 spell | 1248387 | 1248381 |
| xp_bonuses.json | food | n°45 buff_spell | 1248420 | 1248406 |
| xp_bonuses.json | food | n°46 item | 2685 | 21072 |
| xp_bonuses.json | food | n°46 name | Succulent Pork Ribs | Smoked Sagefish |
| xp_bonuses.json | food | n°46 required_level | 15 | 10 |
| xp_bonuses.json | food | n°46 spell | 1248389 | 1249504 |
| xp_bonuses.json | food | n°46 buff_spell | 1248422 | 1249520 |
| xp_bonuses.json | food | n°47 item | 3664 | 1017 |
| xp_bonuses.json | food | n°47 name | Crocolisk Gumbo | Seasoned Wolf Kabob |
| xp_bonuses.json | food | n°48 item | 3665 | 2685 |
| xp_bonuses.json | food | n°48 name | Curiously Tasty Omelet | Succulent Pork Ribs |
| xp_bonuses.json | food | n°48 spell | 1248386 | 1248389 |
| xp_bonuses.json | food | n°48 buff_spell | 1248406 | 1248422 |
| xp_bonuses.json | food | n°49 item | 3666 | 3664 |
| xp_bonuses.json | food | n°49 name | Gooey Spider Cake | Crocolisk Gumbo |
| xp_bonuses.json | food | n°49 spell | 1248386 | 1248387 |
| xp_bonuses.json | food | n°49 buff_spell | 1248406 | 1248420 |
| xp_bonuses.json | food | n°50 item | 3727 | 3665 |
| xp_bonuses.json | food | n°50 name | Hot Lion Chops | Curiously Tasty Omelet |
| xp_bonuses.json | food | n°50 spell | 1248387 | 1248386 |
| xp_bonuses.json | food | n°50 buff_spell | 1248420 | 1248406 |
| xp_bonuses.json | food | n°51 item | 3729 | 3666 |
| xp_bonuses.json | food | n°51 name | Soothing Turtle Bisque | Gooey Spider Cake |
| xp_bonuses.json | food | n°52 item | 4593 | 3727 |
| xp_bonuses.json | food | n°52 name | Bristle Whisker Catfish | Hot Lion Chops |
| xp_bonuses.json | food | n°52 spell | 1249508 | 1248387 |
| xp_bonuses.json | food | n°52 buff_spell | 1249521 | 1248420 |
| xp_bonuses.json | food | n°53 item | 5480 | 3729 |
| xp_bonuses.json | food | n°53 name | Lean Venison | Soothing Turtle Bisque |
| xp_bonuses.json | food | n°53 spell | 1248389 | 1248386 |
| xp_bonuses.json | food | n°53 buff_spell | 1248422 | 1248406 |
| xp_bonuses.json | food | n°54 item | 12209 | 4593 |
| xp_bonuses.json | food | n°54 name | Lean Wolf Steak | Bristle Whisker Catfish |
| xp_bonuses.json | food | n°54 spell | 1248387 | 1249508 |
| xp_bonuses.json | food | n°54 buff_spell | 1248420 | 1249521 |
| xp_bonuses.json | food | n°55 item | 12210 | 5480 |
| xp_bonuses.json | food | n°55 name | Roast Raptor | Lean Venison |
| xp_bonuses.json | food | n°55 spell | 1248388 | 1248389 |
| xp_bonuses.json | food | n°55 buff_spell | 1248421 | 1248422 |
| xp_bonuses.json | food | n°56 item | 12214 | 5527 |
| xp_bonuses.json | food | n°56 name | Mystery Stew | Goblin Deviled Clams |
| xp_bonuses.json | food | n°57 item | 249867 | 12209 |
| xp_bonuses.json | food | n°57 name | Root Tea | Lean Wolf Steak |
| xp_bonuses.json | food | n°57 spell | 1249922 | 1248387 |
| xp_bonuses.json | food | n°57 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°57 buff_spell | 1249927 | 1248420 |
| xp_bonuses.json | food | n°58 item | 249873 | 12210 |
| xp_bonuses.json | food | n°58 name | Mrrggl Smrrthle | Roast Raptor |
| xp_bonuses.json | food | n°58 spell | 1249916 | 1248388 |
| xp_bonuses.json | food | n°58 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°58 buff_spell | 1249926 | 1248421 |
| xp_bonuses.json | food | n°59 item | 3728 | 12214 |
| xp_bonuses.json | food | n°59 name | Tasty Lion Steak | Mystery Stew |
| xp_bonuses.json | food | n°59 required_level | 25 | 15 |
| xp_bonuses.json | food | n°59 spell | 1248391 | 1248386 |
| xp_bonuses.json | food | n°59 buff_spell | 1248420 | 1248406 |
| xp_bonuses.json | food | n°60 item | 4457 | 249867 |
| xp_bonuses.json | food | n°60 name | Barbecued Buzzard Wing | Root Tea |
| xp_bonuses.json | food | n°60 required_level | 25 | 15 |
| xp_bonuses.json | food | n°60 spell | 1248392 | 1249922 |
| xp_bonuses.json | food | n°60 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°60 buff_spell | 1248421 | 1249927 |
| xp_bonuses.json | food | n°61 item | 4594 | 249873 |
| xp_bonuses.json | food | n°61 name | Rockscale Cod | Mrrggl Smrrthle |
| xp_bonuses.json | food | n°61 required_level | 25 | 15 |
| xp_bonuses.json | food | n°61 spell | 1249511 | 1249916 |
| xp_bonuses.json | food | n°61 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°61 buff_spell | 1249521 | 1249926 |
| xp_bonuses.json | food | n°62 item | 6038 | 3728 |
| xp_bonuses.json | food | n°62 name | Giant Clam Scorcho | Tasty Lion Steak |
| xp_bonuses.json | food | n°62 spell | 1248390 | 1248391 |
| xp_bonuses.json | food | n°62 buff_spell | 1248406 | 1248420 |
| xp_bonuses.json | food | n°63 item | 8364 | 4457 |
| xp_bonuses.json | food | n°63 name | Mithril Head Trout | Barbecued Buzzard Wing |
| xp_bonuses.json | food | n°63 spell | 1249509 | 1248392 |
| xp_bonuses.json | food | n°63 buff_spell | 1249519 | 1248421 |
| xp_bonuses.json | food | n°64 item | 10841 | 4594 |
| xp_bonuses.json | food | n°64 name | Goldthorn Tea | Rockscale Cod |
| xp_bonuses.json | food | n°64 spell | 1249906 | 1249511 |
| xp_bonuses.json | food | n°64 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°64 buff_spell | null | 1249521 |
| xp_bonuses.json | food | n°64 buff_name | null | Well Fed |
| xp_bonuses.json | food | n°64 buff_duration_ms | null | 900000 |
| xp_bonuses.json | food | n°65 item | 12215 | 6038 |
| xp_bonuses.json | food | n°65 name | Heavy Kodo Stew | Giant Clam Scorcho |
| xp_bonuses.json | food | n°66 item | 12216 | 8364 |
| xp_bonuses.json | food | n°66 name | Spiced Chili Crab | Mithril Head Trout |
| xp_bonuses.json | food | n°66 spell | 1248392 | 1249509 |
| xp_bonuses.json | food | n°66 buff_spell | 1248421 | 1249519 |
| xp_bonuses.json | food | n°67 item | 13851 | 10841 |
| xp_bonuses.json | food | n°67 name | Hot Wolf Ribs | Goldthorn Tea |
| xp_bonuses.json | food | n°67 spell | 1248391 | 1249906 |
| xp_bonuses.json | food | n°67 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°67 buff_spell | 1248420 | null |
| xp_bonuses.json | food | n°67 buff_name | Well Fed | null |
| xp_bonuses.json | food | n°67 buff_duration_ms | 900000 | null |
| xp_bonuses.json | food | n°68 item | 20074 | 12215 |
| xp_bonuses.json | food | n°68 name | Heavy Crocolisk Stew | Heavy Kodo Stew |
| xp_bonuses.json | food | n°68 spell | 1248391 | 1248390 |
| xp_bonuses.json | food | n°68 buff_spell | 1248420 | 1248406 |
| xp_bonuses.json | food | n°69 item | 249868 | 12216 |
| xp_bonuses.json | food | n°69 name | Triage Tea | Spiced Chili Crab |
| xp_bonuses.json | food | n°69 spell | 1249923 | 1248392 |
| xp_bonuses.json | food | n°69 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°69 buff_spell | 1249927 | 1248421 |
| xp_bonuses.json | food | n°70 item | 249874 | 13851 |
| xp_bonuses.json | food | n°70 name | Calcified Smoothie | Hot Wolf Ribs |
| xp_bonuses.json | food | n°70 spell | 1249917 | 1248391 |
| xp_bonuses.json | food | n°70 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°70 buff_spell | 1249926 | 1248420 |
| xp_bonuses.json | food | n°71 item | 250073 | 20074 |
| xp_bonuses.json | food | n°71 name | Raging Raptor Ribs | Heavy Crocolisk Stew |
| xp_bonuses.json | food | n°71 spell | 1248392 | 1248391 |
| xp_bonuses.json | food | n°71 buff_spell | 1248421 | 1248420 |
| xp_bonuses.json | food | n°72 item | 250074 | 249868 |
| xp_bonuses.json | food | n°72 name | Bear Brisket | Triage Tea |
| xp_bonuses.json | food | n°72 spell | 1248393 | 1249923 |
| xp_bonuses.json | food | n°72 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°72 buff_spell | 1248422 | 1249927 |
| xp_bonuses.json | food | n°73 item | 250078 | 249874 |
| xp_bonuses.json | food | n°73 name | Giant Scrambled Eggs | Calcified Smoothie |
| xp_bonuses.json | food | n°73 spell | 1248390 | 1249917 |
| xp_bonuses.json | food | n°73 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°73 buff_spell | 1248406 | 1249926 |
| xp_bonuses.json | food | n°74 item | 274971 | 250073 |
| xp_bonuses.json | food | n°74 name | Briny Seafood Stew | Raging Raptor Ribs |
| xp_bonuses.json | food | n°74 spell | 1249510 | 1248392 |
| xp_bonuses.json | food | n°74 buff_spell | 1249520 | 1248421 |
| xp_bonuses.json | food | n°75 item | 274976 | 250074 |
| xp_bonuses.json | food | n°75 name | Plain Ol' Paletusk | Bear Brisket |
| xp_bonuses.json | food | n°76 item | 21217 | 250078 |
| xp_bonuses.json | food | n°76 name | Sagefish Delight | Giant Scrambled Eggs |
| xp_bonuses.json | food | n°76 required_level | 30 | 25 |
| xp_bonuses.json | food | n°76 spell | 1249507 | 1248390 |
| xp_bonuses.json | food | n°76 buff_spell | 1249520 | 1248406 |
| xp_bonuses.json | food | n°77 item | 6887 | 274971 |
| xp_bonuses.json | food | n°77 name | Spotted Yellowtail | Briny Seafood Stew |
| xp_bonuses.json | food | n°77 required_level | 35 | 25 |
| xp_bonuses.json | food | n°77 spell | 1249513 | 1249510 |
| xp_bonuses.json | food | n°78 item | 12212 | 274976 |
| xp_bonuses.json | food | n°78 name | Jungle Stew | Plain Ol' Paletusk |
| xp_bonuses.json | food | n°78 required_level | 35 | 25 |
| xp_bonuses.json | food | n°78 spell | 1248395 | 1248393 |
| xp_bonuses.json | food | n°78 buff_spell | 1248420 | 1248422 |
| xp_bonuses.json | food | n°79 item | 12218 | 21217 |
| xp_bonuses.json | food | n°79 name | Monster Omelet | Sagefish Delight |
| xp_bonuses.json | food | n°79 required_level | 35 | 30 |
| xp_bonuses.json | food | n°79 spell | 1248394 | 1249507 |
| xp_bonuses.json | food | n°79 buff_spell | 1248406 | 1249520 |
| xp_bonuses.json | food | n°80 item | 13927 | 6887 |
| xp_bonuses.json | food | n°80 name | Cooked Glossy Mightfish | Spotted Yellowtail |
| xp_bonuses.json | food | n°80 spell | 1249512 | 1249513 |
| xp_bonuses.json | food | n°80 buff_spell | 1249519 | 1249520 |
| xp_bonuses.json | food | n°81 item | 13928 | 12212 |
| xp_bonuses.json | food | n°81 name | Grilled Squid | Jungle Stew |
| xp_bonuses.json | food | n°81 spell | 1249522 | 1248395 |
| xp_bonuses.json | food | n°81 buff_spell | 1249523 | 1248420 |
| xp_bonuses.json | food | n°82 item | 13929 | 12218 |
| xp_bonuses.json | food | n°82 name | Hot Smoked Bass | Monster Omelet |
| xp_bonuses.json | food | n°82 spell | 1249522 | 1248394 |
| xp_bonuses.json | food | n°82 buff_spell | 1249523 | 1248406 |
| xp_bonuses.json | food | n°83 item | 13930 | 13927 |
| xp_bonuses.json | food | n°83 name | Filet of Redgill | Cooked Glossy Mightfish |
| xp_bonuses.json | food | n°83 spell | 1249514 | 1249512 |
| xp_bonuses.json | food | n°83 buff_spell | 1249521 | 1249519 |
| xp_bonuses.json | food | n°84 item | 13931 | 13928 |
| xp_bonuses.json | food | n°84 name | Nightfin Soup | Grilled Squid |
| xp_bonuses.json | food | n°84 spell | 1249513 | 1249522 |
| xp_bonuses.json | food | n°84 buff_spell | 1249520 | 1249523 |
| xp_bonuses.json | food | n°85 item | 13932 | 13929 |
| xp_bonuses.json | food | n°85 name | Poached Sunscale Salmon | Hot Smoked Bass |
| xp_bonuses.json | food | n°85 spell | 1249515 | 1249522 |
| xp_bonuses.json | food | n°85 buff_spell | 1249519 | 1249523 |
| xp_bonuses.json | food | n°86 item | 17222 | 13930 |
| xp_bonuses.json | food | n°86 name | Spider Sausage | Filet of Redgill |
| xp_bonuses.json | food | n°86 spell | 1248394 | 1249514 |
| xp_bonuses.json | food | n°86 buff_spell | 1248406 | 1249521 |
| xp_bonuses.json | food | n°87 item | 18045 | 13931 |
| xp_bonuses.json | food | n°87 name | Tender Wolf Steak | Nightfin Soup |
| xp_bonuses.json | food | n°87 spell | 1248395 | 1249513 |
| xp_bonuses.json | food | n°87 buff_spell | 1248420 | 1249520 |
| xp_bonuses.json | food | n°88 item | 18254 | 13932 |
| xp_bonuses.json | food | n°88 name | Runn Tum Tuber Surprise | Poached Sunscale Salmon |
| xp_bonuses.json | food | n°88 spell | 1248396 | 1249515 |
| xp_bonuses.json | food | n°88 buff_spell | 1248421 | 1249519 |
| xp_bonuses.json | food | n°89 item | 249869 | 16766 |
| xp_bonuses.json | food | n°89 name | Sunny Tea | Undermine Clam Chowder |
| xp_bonuses.json | food | n°89 spell | 1249924 | 1248394 |
| xp_bonuses.json | food | n°89 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°89 buff_spell | 1249927 | 1248406 |
| xp_bonuses.json | food | n°90 item | 249875 | 17222 |
| xp_bonuses.json | food | n°90 name | Spicy Smoothie | Spider Sausage |
| xp_bonuses.json | food | n°90 spell | 1249918 | 1248394 |
| xp_bonuses.json | food | n°90 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°90 buff_spell | 1249926 | 1248406 |
| xp_bonuses.json | food | n°91 item | 250065 | 18045 |
| xp_bonuses.json | food | n°91 name | Savory Stag Sliders | Tender Wolf Steak |
| xp_bonuses.json | food | n°91 spell | 1248397 | 1248395 |
| xp_bonuses.json | food | n°91 buff_spell | 1248422 | 1248420 |
| xp_bonuses.json | food | n°92 item | 250076 | 18254 |
| xp_bonuses.json | food | n°92 name | Raptor Rouladen | Runn Tum Tuber Surprise |
| xp_bonuses.json | food | n°93 item | 286152 | 249869 |
| xp_bonuses.json | food | n°93 name | Plated Armorfish | Sunny Tea |
| xp_bonuses.json | food | n°93 spell | 1319311 | 1249924 |
| xp_bonuses.json | food | n°93 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°93 buff_spell | 1319310 | 1249927 |
| xp_bonuses.json | food | n°94 item | 8957 | 249875 |
| xp_bonuses.json | food | n°94 name | Spinefin Halibut | Spicy Smoothie |
| xp_bonuses.json | food | n°94 required_level | 45 | 35 |
| xp_bonuses.json | food | n°94 spell | 1249514 | 1249918 |
| xp_bonuses.json | food | n°94 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°94 buff_spell | 1249521 | 1249926 |
| xp_bonuses.json | food | n°95 item | 13933 | 250065 |
| xp_bonuses.json | food | n°95 name | Lobster Stew | Savory Stag Sliders |
| xp_bonuses.json | food | n°95 required_level | 45 | 35 |
| xp_bonuses.json | food | n°95 spell | 1249516 | 1248397 |
| xp_bonuses.json | food | n°95 buff_spell | 1249520 | 1248422 |
| xp_bonuses.json | food | n°96 item | 13934 | 250076 |
| xp_bonuses.json | food | n°96 name | Mightfish Steak | Raptor Rouladen |
| xp_bonuses.json | food | n°96 required_level | 45 | 35 |
| xp_bonuses.json | food | n°96 spell | 1249515 | 1248396 |
| xp_bonuses.json | food | n°96 buff_spell | 1249519 | 1248421 |
| xp_bonuses.json | food | n°97 item | 13935 | 286152 |
| xp_bonuses.json | food | n°97 name | Baked Salmon | Plated Armorfish |
| xp_bonuses.json | food | n°97 required_level | 45 | 35 |
| xp_bonuses.json | food | n°97 spell | 1249516 | 1319311 |
| xp_bonuses.json | food | n°97 buff_spell | 1249520 | 1319310 |
| xp_bonuses.json | food | n°98 item | 20452 | 8957 |
| xp_bonuses.json | food | n°98 name | Smoked Desert Dumplings | Spinefin Halibut |
| xp_bonuses.json | food | n°98 spell | 1248401 | 1249514 |
| xp_bonuses.json | food | n°98 buff_spell | 1248422 | 1249521 |
| xp_bonuses.json | food | n°99 item | 249870 | 13933 |
| xp_bonuses.json | food | n°99 name | Sage's Tea | Lobster Stew |
| xp_bonuses.json | food | n°99 spell | 1249925 | 1249516 |
| xp_bonuses.json | food | n°99 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°99 buff_spell | 1249927 | 1249520 |
| xp_bonuses.json | food | n°100 item | 249876 | 13934 |
| xp_bonuses.json | food | n°100 name | Wicked Smoothie | Mightfish Steak |
| xp_bonuses.json | food | n°100 spell | 1249919 | 1249515 |
| xp_bonuses.json | food | n°100 kind | Nutritious Drink | Nutritious Food |
| xp_bonuses.json | food | n°100 buff_spell | 1249926 | 1249519 |
| xp_bonuses.json | food | n°101 item | 250066 | 13935 |
| xp_bonuses.json | food | n°101 name | Soaring Pamplona | Baked Salmon |
| xp_bonuses.json | food | n°101 spell | 1248400 | 1249516 |
| xp_bonuses.json | food | n°101 buff_spell | 1248421 | 1249520 |
| xp_bonuses.json | food | n°102 item | 250067 | 20452 |
| xp_bonuses.json | food | n°102 name | Bat Hachee | Smoked Desert Dumplings |
| xp_bonuses.json | food | n°102 spell | 1248400 | 1248401 |
| xp_bonuses.json | food | n°102 buff_spell | 1248421 | 1248422 |
| xp_bonuses.json | food | n°103 item | 250068 | 249870 |
| xp_bonuses.json | food | n°103 name | Savory Turtle Stew | Sage's Tea |
| xp_bonuses.json | food | n°103 spell | 1248398 | 1249925 |
| xp_bonuses.json | food | n°103 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°103 buff_spell | 1248406 | 1249927 |
| xp_bonuses.json | food | n°104 item | 250069 | 249876 |
| xp_bonuses.json | food | n°104 name | Flank au Poivre | Wicked Smoothie |
| xp_bonuses.json | food | n°104 spell | 1248399 | 1249919 |
| xp_bonuses.json | food | n°104 kind | Nutritious Food | Nutritious Drink |
| xp_bonuses.json | food | n°104 buff_spell | 1248420 | 1249926 |
| xp_bonuses.json | food | n°105 item | 250070 | 250066 |
| xp_bonuses.json | food | n°105 name | Bear Bruscitti | Soaring Pamplona |
| xp_bonuses.json | food | n°105 spell | 1248401 | 1248400 |
| xp_bonuses.json | food | n°105 buff_spell | 1248422 | 1248421 |
| xp_bonuses.json | food | n°106 item | 250071 | 250067 |
| xp_bonuses.json | food | n°106 name | Steaming Stag Steak | Bat Hachee |
| xp_bonuses.json | food | n°106 spell | 1248401 | 1248400 |
| xp_bonuses.json | food | n°106 buff_spell | 1248422 | 1248421 |
| xp_bonuses.json | food | n°107 item | 250072 | 250068 |
| xp_bonuses.json | food | n°107 name | Swiftstrike Steak | Savory Turtle Stew |
| xp_bonuses.json | food | n°107 spell | 1248399 | 1248398 |
| xp_bonuses.json | food | n°107 buff_spell | 1248420 | 1248406 |
| xp_bonuses.json | food | n°108 item | 250075 | 250069 |
| xp_bonuses.json | food | n°108 name | Prehistoric Pulled Raptor | Flank au Poivre |
| xp_bonuses.json | food | n°108 spell | 1248400 | 1248399 |
| xp_bonuses.json | food | n°108 buff_spell | 1248421 | 1248420 |
| xp_bonuses.json | food | n°109 item | 267341 | 250070 |
| xp_bonuses.json | food | n°109 name | Sweetpaw Jam | Bear Bruscitti |
| xp_bonuses.json | food | n°109 required_level | 55 | 45 |
| xp_bonuses.json | food | n°109 spell | 1294006 | 1248401 |
| xp_bonuses.json | food | n°109 buff_spell | null | 1248422 |
| xp_bonuses.json | food | n°109 buff_name | null | Well Fed |
| xp_bonuses.json | food | n°109 buff_duration_ms | null | 900000 |
| xp_bonuses.json | food | n°110 | null | {"item": 250071, "name": "Steaming Stag Steak", "required_level": 45, "spell": 1248401, "kind": "Nutritious Food", "buff_spell": 1248422, "buff_name": "Well Fed", "buff_duration_ms": 900000, "xp_aura": 1243969} |
| xp_bonuses.json | food | n°111 | null | {"item": 250072, "name": "Swiftstrike Steak", "required_level": 45, "spell": 1248399, "kind": "Nutritious Food", "buff_spell": 1248420, "buff_name": "Well Fed", "buff_duration_ms": 900000, "xp_aura": 1243969} |
| xp_bonuses.json | food | n°112 | null | {"item": 250075, "name": "Prehistoric Pulled Raptor", "required_level": 45, "spell": 1248400, "kind": "Nutritious Food", "buff_spell": 1248421, "buff_name": "Well Fed", "buff_duration_ms": 900000, "xp_aura": 1243969} |
| xp_bonuses.json | food | n°113 | null | {"item": 250081, "name": "Clam Linguine", "required_level": 45, "spell": 1248398, "kind": "Nutritious Food", "buff_spell": 1248406, "buff_name": "Well Fed", "buff_duration_ms": 900000, "xp_aura": 1243969} |
| xp_bonuses.json | food | n°114 | null | {"item": 267341, "name": "Sweetpaw Jam", "required_level": 55, "spell": 1294006, "kind": "Nutritious Food", "buff_spell": null, "buff_name": null, "buff_duration_ms": null, "xp_aura": 1243969} |

fiches PvP : Hunter, 2 autres valeurs changées ; Priest, 1 talent modifié.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| Hunter | dropped_nodes | 105003 reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) |
| Hunter | parked_nodes | improvedSerpentSting talents_forever | Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) | Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) |
| Hunter | parked_nodes | improvedSerpentSting reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) à la rangée 4, colonne 4 : question ouverte à créer | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) à la rangée 4, colonne 4 : question ouverte à créer |
| Hunter | parked_nodes | improvedSerpentSting question | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). |
| Priest | talent Shadow Magic Vampiric Embrace | desc | Afflicts your target with Shadow energy that causes all party members to be healed for $s1% of any Shadow spell damage you deal for $d. | Afflicts your target with Shadow energy that causes all party members to be healed for $s1% of any Shadow spell damage you deal for $d. You receive $s2% increased healing on yourself from this effect. |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » : relevé écarté, le client 1.60.1.71037 fait foi ; ton observation datait de 1.60.1.70959
- moteurs aux entrées changées : mage_leveling
