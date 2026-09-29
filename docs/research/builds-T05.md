# Builds du Mage par contexte : résultats de la fin de T05

Calculés le 2026-09-29 par `uv run forever build <contexte> --level N --preset complet --json` (graine 12345, race Orc, fiche de base par niveau, données 1.60.1.70009, branche `t05`). Préréglage complet : faisceau 3, anticipation 4, 4 finalistes, Monte Carlo à n = 200 ; stabilité sur 5 graines ; sensibilité aux sept hypothèses incertaines. Donjon et raid : scénarios provisoires (`build.scenarios`). PvP : profil du seed, déterministe. Tout build au-delà du niveau 20 n'est pas vérifiable en jeu avant la sortie.

## Synthèse

Écart de l'alternative : avantage du build (positif : le build fait mieux), intervalle à 95 %, dans l'unité de la métrique (leveling : secondes par monstre ; donjon et raid : dégâts par seconde ; PvP : points du profil).

| Contexte | Niveau | Arcanes/Feu/Givre | Monte Carlo | Analytique | Avantage sur l'alternative | Retenu | Stabilité | Sensibilité | Calcul |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| leveling | 20 | 0/0/11 | 34,74 | 35,37 | 0,45 [-0,83 ; 1,73] (égalité) | build (analytique) | stable (build) | tient | 39 s |
| leveling | 40 | 0/0/31 | 51,72 | 49,89 | 0,66 [-0,93 ; 2,24] (égalité) | build (analytique) | stable (build) | tient | 159 s |
| leveling | 60 | 0/0/51 | 43,66 | 47,01 | 0,67 [-1,03 ; 2,38] (égalité) | alternative (analytique) | stable (alternative) | tient | 283 s |
| dungeon | 20 | 10/0/1 | 40,70 | 51,00 | 4,37 [3,76 ; 4,98] | build (monte_carlo) | stable (build) | mob_hp | 7 s |
| dungeon | 40 | 31/0/0 | 144,93 | 161,96 | 1,27 [-1,76 ; 4,30] (égalité) | build (analytique) | stable (build) | regen_stacking | 28 s |
| dungeon | 60 | 30/3/18 | 314,62 | 359,53 | 27,40 [18,79 ; 36,02] | build (monte_carlo) | stable (build) | tient | 75 s |
| raid | 20 | 11/0/0 | 6,18 | 6,36 | -0,12 [-0,30 ; 0,06] (égalité) | build (analytique) | instable (4/5 build) | tient | 5 s |
| raid | 40 | 28/3/0 | 40,38 | 38,53 | 0,00 [0,00 ; 0,00] (égalité) | build (analytique) | stable (build) | tient | 25 s |
| raid | 60 | 46/5/0 | 79,92 | 75,58 | 0,00 [0,00 ; 0,00] (égalité) | build (analytique) | stable (build) | tient | 62 s |
| pvp-bg | 20 | 0/0/11 | — | 50,17 | 11,04 [11,04 ; 11,04] | build (profil) | stable (build) | tient | 3 s |
| pvp-bg | 40 | 31/0/0 | — | 69,32 | 0,35 [0,35 ; 0,35] | build (profil) | stable (build) | tient | 16 s |
| pvp-bg | 60 | 15/3/33 | — | 118,14 | 2,05 [2,05 ; 2,05] | build (profil) | stable (build) | tient | 31 s |
| pvp-world | 20 | 0/0/11 | — | 41,14 | 8,07 [8,07 ; 8,07] | build (profil) | stable (build) | tient | 3 s |
| pvp-world | 40 | 31/0/0 | — | 65,88 | 6,04 [6,04 ; 6,04] | build (profil) | stable (build) | tient | 16 s |
| pvp-world | 60 | 29/3/19 | — | 121,02 | 1,30 [1,30 ; 1,30] | build (profil) | stable (build) | tient | 31 s |

## Lecture

- **Leveling : Givre à tous les niveaux** (Improved Frostbolt, Elemental Precision, Frostbite, Ice Lance, puis Shatter, Ice Shards, Winter's Chill), en accord avec la tendance de la communauté (`docs/research/community-builds-mage.md`, comparaison du bloc J). Au niveau 60, l'alternative (Incineration 1 à la place d'un rang d'Arctic Reach) fait jeu égal ; plusieurs points finissent sur des talents sans effet modélisé (Frost Warding, Improved Blizzard, Ice Block : angle mort C9).
- **Donjon et raid : Arcanes, `ab_stacks` 1, décharge Arcane Missiles**, parce que la mana borne tout : avec la fiche de base, sans Évocation ni potion (B10), la réserve s'épuise en une vingtaine de secondes en rotation arcane ; le build choisit donc peu de cumuls d'Arcane Blast. L'angle mort de l'Évocation a une borne haute de 86 à 144 % de la métrique : **ces classements de donjon et de raid sont fragiles** tant que la mana (Évocation, potions, gemmes, équipement réel) n'est pas modélisée.
- Plusieurs builds de fin de partie placent des points sur des talents sans effet dans nos modèles (Wand Specialization, Magic Absorption, Arcane Shielding, Improved Counterspell) : ce sont des égalités (écart nul avec l'alternative au raid 40 et 60), pas des recommandations ; les raisons du rapport le montrent (valeur marginale nulle) et l'angle mort C9 le signale.
- Stabilité : un seul cas instable (raid niveau 20 : 4 graines sur 5 pour le build, écart dans le bruit). Sensibilité : deux bascules, au donjon 20 (PV des monstres du seed) et au donjon 40 (cumul de régénération au maximum) ; ailleurs, les sept hypothèses tiennent.
- PvP : profil du seed (EST) sans duel ; les builds de niveau 40 sont Arcanes purs, ceux de 60 hybrides Givre-Arcanes. Les poids du monde ouvert sont supposés (question ouverte).
- Écart analytique / Monte Carlo : faible en leveling (−4 à +8 %), faible en raid (−5 à +3 %), plus fort en donjon (+12 à +25 % à l'analytique : fin de mana et sorts de zone) ; la décision revient au Monte Carlo.

## Détail

### leveling niveau 20
- Talents (Arcanes/Feu/Givre 0/0/11) : improvedFrostbolt 5, elementalPrecision 2, frostbite 3, iceLance 1
- Choix : leveling : frost, frost
- Métrique (temps par monstre, s) : Monte Carlo 34,74, analytique 35,37
- Alternative la plus proche : elementalPrecision 2→1, iceShards 0→1 ; avantage du build 0,45 [-0,83 ; 1,73] (égalité) ; retenu : build (analytique)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : aucun
- Certitude : suppose ; vérifiable en jeu : oui

### leveling niveau 40
- Talents (Arcanes/Feu/Givre 0/0/31) : improvedFrostbolt 5, elementalPrecision 2, iceShards 5, frostbite 3, piercingIce 3, frostChanneling 3, iceLance 1, shatter 3, fingersOfFrost 1, wintersChill 5
- Choix : leveling : frost, mage
- Métrique (temps par monstre, s) : Monte Carlo 51,72, analytique 49,89
- Alternative la plus proche : elementalPrecision 2→3, wintersChill 5→4 ; avantage du build 0,66 [-0,93 ; 2,24] (égalité) ; retenu : build (analytique)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : aucun
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### leveling niveau 60
- Talents (Arcanes/Feu/Givre 0/0/51) : frostWarding 2, improvedFrostbolt 5, elementalPrecision 5, iceShards 5, permafrost 3, improvedFrostNova 2, frostbite 3, piercingIce 3, frostChanneling 3, iceLance 1, improvedBlizzard 3, arcticReach 2, iceBlock 1, shatter 3, improvedConeOfCold 3, fingersOfFrost 2, wintersChill 5
- Choix : leveling : frost, mage
- Métrique (temps par monstre, s) : Monte Carlo 43,66, analytique 47,01
- Alternative la plus proche : incineration 0→1, arcticReach 2→1 ; avantage du build 0,67 [-1,03 ; 2,38] (égalité) ; retenu : alternative (analytique)
- Stabilité : stable (alternative) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : C9 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### dungeon niveau 20
- Talents (Arcanes/Feu/Givre 10/0/1) : wandSpecialization 2, arcaneFocus 3, arcaneConcentration 5, elementalPrecision 1
- Choix : dungeon_boss : frost, frost ; dungeon_pack : aoe, frost, aoe_filler flamestrike
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 40,70, analytique 51,00
- Alternative la plus proche : wandSpecialization 2→0, arcaneFocus 3→0, arcaneConcentration 5→0, elementalPrecision 1→5, iceShards 0→5, frostChanneling 0→1 ; avantage du build 4,37 [3,76 ; 4,98] ; retenu : build (monte_carlo)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : mob_hp bascule
- Angles morts : B10 ≤ 144,2 %, C7 non chiffré, D1 non chiffré, H9 non chiffré
- Certitude : suppose ; vérifiable en jeu : oui

### dungeon niveau 40
- Talents (Arcanes/Feu/Givre 31/0/0) : wandSpecialization 2, arcaneFocus 5, improvedChanneling 1, arcaneConcentration 5, arcaneImpact 3, arcaneBlast 1, arcaneMeditation 3, missileBarrage 1, presenceOfMind 1, arcaneMind 5, arcaneInstability 3, arcanePower 1
- Choix : dungeon_boss : arcane, mage, ab_stacks 1, ab_dump arcane_missiles ; dungeon_pack : aoe, mage, aoe_filler blizzard
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 144,93, analytique 161,96
- Alternative la plus proche : wandSpecialization 2→0, arcaneFocus 5→0, improvedChanneling 1→0, arcaneConcentration 5→0, arcaneImpact 3→0, arcaneBlast 1→0, arcaneMeditation 3→0, missileBarrage 1→0, presenceOfMind 1→0, arcaneMind 5→0, arcaneInstability 3→0, arcanePower 1→0, improvedFrostbolt 0→3, elementalPrecision 0→4, iceShards 0→5, piercingIce 0→3, frostChanneling 0→3, iceLance 0→1, shatter 0→3, improvedConeOfCold 0→3, fingersOfFrost 0→2, wintersChill 0→4 ; avantage du build 1,27 [-1,76 ; 4,30] (égalité) ; retenu : build (analytique)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : regen_stacking bascule
- Angles morts : B10 ≤ 100,9 %, B18 ≤ 1,9 %, C7 non chiffré, C9 non chiffré, D1 non chiffré, H9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### dungeon niveau 60
- Talents (Arcanes/Feu/Givre 30/3/18) : arcaneFocus 5, improvedChanneling 4, arcaneConcentration 5, arcaneImpact 3, arcaneBlast 1, arcaneMeditation 3, missileBarrage 1, arcaneMind 5, arcaneInstability 3, incineration 3, frostWarding 2, elementalPrecision 5, iceShards 5, piercingIce 3, frostChanneling 3
- Choix : dungeon_boss : arcane, mage, ab_stacks 1, ab_dump arcane_missiles ; dungeon_pack : aoe, mage, aoe_filler blizzard
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 314,62, analytique 359,53
- Alternative la plus proche : improvedChanneling 4→5, arcaneSubtlety 0→2, magicAbsorption 0→2, arcaneResilience 0→2, arcaneGeometry 0→2, arcaneShielding 0→2, improvedCounterspell 0→2, presenceOfMind 0→1, frostWarding 2→0, elementalPrecision 5→4, iceShards 5→0, piercingIce 3→0, frostChanneling 3→0 ; avantage du build 27,40 [18,79 ; 36,02] ; retenu : build (monte_carlo)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : B10 ≤ 86,3 %, B18 ≤ 1,9 %, C7 non chiffré, C9 non chiffré, D1 non chiffré, H9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### raid niveau 20
- Talents (Arcanes/Feu/Givre 11/0/0) : arcaneFocus 5, arcaneConcentration 5, arcaneBlast 1
- Choix : raid_boss : arcane, frost, ab_stacks 1, ab_dump arcane_missiles
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 6,18, analytique 6,36
- Alternative la plus proche : arcaneFocus 5→0, arcaneConcentration 5→0, arcaneBlast 1→0, elementalPrecision 0→5, iceShards 0→5, frostChanneling 0→1 ; avantage du build -0,12 [-0,30 ; 0,06] (égalité) ; retenu : build (analytique)
- Stabilité : instable (4/5 build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : A12 non chiffré, A13 non chiffré, A14 non chiffré, B10 ≤ 144,2 %, D1 non chiffré, H9 non chiffré
- Certitude : suppose ; vérifiable en jeu : oui

### raid niveau 40
- Talents (Arcanes/Feu/Givre 28/3/0) : arcaneFocus 5, improvedChanneling 2, arcaneConcentration 5, arcaneImpact 3, arcaneBlast 1, arcaneMeditation 3, missileBarrage 1, arcaneMind 5, arcaneInstability 3, incineration 3
- Choix : raid_boss : arcane, mage, ab_stacks 1, ab_dump arcane_missiles
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 40,38, analytique 38,53
- Alternative la plus proche : wandSpecialization 0→2, improvedChanneling 2→0 ; avantage du build 0,00 [0,00 ; 0,00] (égalité) ; retenu : build (analytique)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : A12 non chiffré, A13 non chiffré, A14 non chiffré, B10 ≤ 100,9 %, C9 non chiffré, D1 non chiffré, H9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### raid niveau 60
- Talents (Arcanes/Feu/Givre 46/5/0) : wandSpecialization 2, arcaneFocus 5, improvedChanneling 5, arcaneSubtlety 2, magicAbsorption 2, arcaneConcentration 5, arcaneResilience 2, arcaneGeometry 2, arcaneImpact 3, arcaneBlast 1, arcaneShielding 2, improvedCounterspell 2, arcaneMeditation 3, missileBarrage 1, presenceOfMind 1, arcaneMind 5, arcaneInstability 3, wakeOfFire 2, incineration 3
- Choix : raid_boss : arcane, mage, ab_stacks 1, ab_dump arcane_missiles
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 79,92, analytique 75,58
- Alternative la plus proche : arcaneGeometry 2→0, arcaneShielding 2→0, improvedCounterspell 2→0, presenceOfMind 1→0, improvedFireball 0→5, ignite 0→2 ; avantage du build 0,00 [0,00 ; 0,00] (égalité) ; retenu : build (analytique)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : A12 non chiffré, A13 non chiffré, A14 non chiffré, B10 ≤ 86,3 %, B18 ≤ 1,7 %, B19 ≤ 1,6 %, C9 non chiffré, D1 non chiffré, H9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### pvp-bg niveau 20
- Talents (Arcanes/Feu/Givre 0/0/11) : frostWarding 2, elementalPrecision 3, permafrost 2, improvedFrostNova 2, frostbite 2
- Choix : profil PvP (pas de rotation)
- Métrique (score PvP, points) : Monte Carlo —, analytique 50,17
- Alternative la plus proche : wakeOfFire 0→2, incineration 0→3, impact 0→3, elementalPrecision 3→1, permafrost 2→0, improvedFrostNova 2→0, frostbite 2→0 ; avantage du build 11,04 [11,04 ; 11,04] ; retenu : build (profil)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : B19 ≤ 2,6 %, C9 non chiffré
- Certitude : suppose ; vérifiable en jeu : oui

### pvp-bg niveau 40
- Talents (Arcanes/Feu/Givre 31/0/0) : wandSpecialization 2, arcaneFocus 5, improvedChanneling 5, arcaneSubtlety 2, magicAbsorption 1, arcaneResilience 2, arcaneImpact 3, arcaneBlast 1, presenceOfMind 1, arcaneMind 5, arcaneInstability 3, arcanePower 1
- Choix : profil PvP (pas de rotation)
- Métrique (score PvP, points) : Monte Carlo —, analytique 69,32
- Alternative la plus proche : wandSpecialization 2→0, arcaneFocus 5→0, improvedChanneling 5→0, arcaneSubtlety 2→0, magicAbsorption 1→0, arcaneResilience 2→0, arcaneImpact 3→0, arcaneBlast 1→0, presenceOfMind 1→0, arcaneMind 5→0, arcaneInstability 3→0, arcanePower 1→0, frostWarding 0→2, improvedFrostbolt 0→3, elementalPrecision 0→3, iceShards 0→5, permafrost 0→3, improvedFrostNova 0→2, piercingIce 0→3, iceLance 0→1, iceBlock 0→1, shatter 0→3, improvedConeOfCold 0→3, coldSnap 0→1, iceBarrier 0→1 ; avantage du build 0,35 [0,35 ; 0,35] ; retenu : build (profil)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : B18 ≤ 1,9 %, C9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### pvp-bg niveau 60
- Talents (Arcanes/Feu/Givre 15/3/33) : arcaneFocus 4, improvedChanneling 5, arcaneResilience 2, arcaneImpact 3, arcaneBlast 1, incineration 3, frostWarding 2, improvedFrostbolt 5, elementalPrecision 3, iceShards 5, permafrost 3, improvedFrostNova 2, piercingIce 3, iceLance 1, iceBlock 1, shatter 3, improvedConeOfCold 3, coldSnap 1, iceBarrier 1
- Choix : profil PvP (pas de rotation)
- Métrique (score PvP, points) : Monte Carlo —, analytique 118,14
- Alternative la plus proche : arcaneFocus 4→3, improvedChanneling 5→2, arcaneConcentration 0→5, arcaneMeditation 0→3, missileBarrage 0→1, presenceOfMind 0→1, arcaneMind 0→5, arcaneInstability 0→3, improvedFrostbolt 5→0, iceShards 5→4, shatter 3→0, improvedConeOfCold 3→0, coldSnap 1→0, iceBarrier 1→0 ; avantage du build 2,05 [2,05 ; 2,05] ; retenu : build (profil)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : B18 ≤ 1,9 %, C9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### pvp-world niveau 20
- Talents (Arcanes/Feu/Givre 0/0/11) : frostWarding 2, elementalPrecision 3, permafrost 2, frostbite 3, iceLance 1
- Choix : profil PvP (pas de rotation)
- Métrique (score PvP, points) : Monte Carlo —, analytique 41,14
- Alternative la plus proche : wandSpecialization 0→2, arcaneFocus 0→5, improvedChanneling 0→1, arcaneResilience 0→2, arcaneBlast 0→1, frostWarding 2→0, elementalPrecision 3→0, permafrost 2→0, frostbite 3→0, iceLance 1→0 ; avantage du build 8,07 [8,07 ; 8,07] ; retenu : build (profil)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : C9 non chiffré
- Certitude : suppose ; vérifiable en jeu : oui

### pvp-world niveau 40
- Talents (Arcanes/Feu/Givre 31/0/0) : wandSpecialization 2, arcaneFocus 5, improvedChanneling 5, arcaneSubtlety 2, magicAbsorption 1, arcaneResilience 2, arcaneImpact 3, arcaneBlast 1, presenceOfMind 1, arcaneMind 5, arcaneInstability 3, arcanePower 1
- Choix : profil PvP (pas de rotation)
- Métrique (score PvP, points) : Monte Carlo —, analytique 65,88
- Alternative la plus proche : wandSpecialization 2→0, arcaneFocus 5→0, improvedChanneling 5→0, arcaneSubtlety 2→0, magicAbsorption 1→0, arcaneResilience 2→0, arcaneImpact 3→0, arcaneBlast 1→0, presenceOfMind 1→0, arcaneMind 5→0, arcaneInstability 3→0, arcanePower 1→0, frostWarding 0→2, improvedFrostbolt 0→3, elementalPrecision 0→3, iceShards 0→5, permafrost 0→3, improvedFrostNova 0→2, piercingIce 0→3, iceLance 0→1, iceBlock 0→1, shatter 0→3, improvedConeOfCold 0→3, coldSnap 0→1, iceBarrier 0→1 ; avantage du build 6,04 [6,04 ; 6,04] ; retenu : build (profil)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : B18 ≤ 1,9 %, C9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### pvp-world niveau 60
- Talents (Arcanes/Feu/Givre 29/3/19) : arcaneFocus 3, improvedChanneling 2, arcaneConcentration 5, arcaneResilience 2, arcaneImpact 3, arcaneBlast 1, arcaneMeditation 3, missileBarrage 1, presenceOfMind 1, arcaneMind 5, arcaneInstability 3, incineration 3, frostWarding 2, elementalPrecision 3, iceShards 4, permafrost 3, improvedFrostNova 2, piercingIce 3, iceLance 1, iceBlock 1
- Choix : profil PvP (pas de rotation)
- Métrique (score PvP, points) : Monte Carlo —, analytique 121,02
- Alternative la plus proche : arcaneSubtlety 0→2, magicAbsorption 0→2, arcaneMeditation 3→0, missileBarrage 1→0, improvedFireball 0→2, ignite 0→5, iceShards 4→0, piercingIce 3→1, iceBlock 1→0 ; avantage du build 1,30 [1,30 ; 1,30] ; retenu : build (profil)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : les sept hypothèses tiennent
- Angles morts : B18 ≤ 1,8 %, C9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)
