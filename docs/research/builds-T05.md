# Builds du Mage par contexte : résultats de la fin de T05

Calculés le 2026-09-29 par `uv run forever build <contexte> --level N --preset complet --json` (graine 12345, race Orc, fiche de base par niveau, données 1.60.1.70009, branche `t05`). Préréglage complet : faisceau 3, anticipation 4, 4 finalistes, Monte Carlo à n = 200 ; stabilité sur 5 graines ; sensibilité aux sept hypothèses incertaines. Donjon et raid : scénarios provisoires (`build.scenarios`). PvP : profil du seed, déterministe. Tout build au-delà du niveau 20 n'est pas vérifiable en jeu avant la sortie.

## Synthèse

Correction du 2026-09-29 (T06b) : analytique du donjon 40 et 60 rendu tel que le calcule le code de fin de T05
(164,28 et 364,67 ; le document donnait 161,96 et 359,53). Ce document a été écrit au commit `29c2e47` ; vingt minutes
plus tard, le commit `7c96d77` (suites de la relecture de T05) a corrigé `context_analytic`
(`forever/optimize/endgame.py`) : la durée d'un scénario y est la durée effective (dégâts ÷ dégâts par seconde, comme
au Monte Carlo), et non plus la durée prévue du scénario, plus longue quand la mana s'épuise ou que les monstres meurent
avant la fin. Seuls les deux donjons à fin de mana bougent ; builds, Monte Carlo, alternatives et verdicts sont
inchangés (vérifié par le rejeu `r1` ci-dessous et par le calcul aux commits `c8977e1` et `7c96d77`).

Écart de l'alternative : avantage du build (positif : le build fait mieux), intervalle à 95 %, dans l'unité de la métrique (leveling : secondes par monstre ; donjon et raid : dégâts par seconde ; PvP : points du profil).

| Contexte | Niveau | Arcanes/Feu/Givre | Monte Carlo | Analytique | Avantage sur l'alternative | Retenu | Stabilité | Sensibilité | Calcul |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| leveling | 20 | 0/0/11 | 34,74 | 35,37 | 0,45 [-0,83 ; 1,73] (égalité) | build (analytique) | stable (build) | tient | 39 s |
| leveling | 40 | 0/0/31 | 51,72 | 49,89 | 0,66 [-0,93 ; 2,24] (égalité) | build (analytique) | stable (build) | tient | 159 s |
| leveling | 60 | 0/0/51 | 43,66 | 47,01 | 0,67 [-1,03 ; 2,38] (égalité) | alternative (analytique) | stable (alternative) | tient | 283 s |
| dungeon | 20 | 10/0/1 | 40,70 | 51,00 | 4,37 [3,76 ; 4,98] | build (monte_carlo) | stable (build) | mob_hp | 7 s |
| dungeon | 40 | 31/0/0 | 144,93 | 164,28 | 1,27 [-1,76 ; 4,30] (égalité) | build (analytique) | stable (build) | regen_stacking | 28 s |
| dungeon | 60 | 30/3/18 | 314,62 | 364,67 | 27,40 [18,79 ; 36,02] | build (monte_carlo) | stable (build) | tient | 75 s |
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
- Écart analytique / Monte Carlo : faible en leveling (−4 à +8 %), faible en raid (−5 à +3 %), plus fort en donjon (+13 à +25 % à l'analytique : fin de mana et sorts de zone) ; la décision revient au Monte Carlo.

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
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 144,93, analytique 164,28
- Alternative la plus proche : wandSpecialization 2→0, arcaneFocus 5→0, improvedChanneling 1→0, arcaneConcentration 5→0, arcaneImpact 3→0, arcaneBlast 1→0, arcaneMeditation 3→0, missileBarrage 1→0, presenceOfMind 1→0, arcaneMind 5→0, arcaneInstability 3→0, arcanePower 1→0, improvedFrostbolt 0→3, elementalPrecision 0→4, iceShards 0→5, piercingIce 0→3, frostChanneling 0→3, iceLance 0→1, shatter 0→3, improvedConeOfCold 0→3, fingersOfFrost 0→2, wintersChill 0→4 ; avantage du build 1,27 [-1,76 ; 4,30] (égalité) ; retenu : build (analytique)
- Stabilité : stable (build) sur les graines [12345, 12346, 12347, 12348, 12349] ; sensibilité : regen_stacking bascule
- Angles morts : B10 ≤ 100,9 %, B18 ≤ 1,9 %, C7 non chiffré, C9 non chiffré, D1 non chiffré, H9 non chiffré, I8 non chiffré
- Certitude : suppose ; vérifiable en jeu : non (au-delà du plafond de la bêta)

### dungeon niveau 60
- Talents (Arcanes/Feu/Givre 30/3/18) : arcaneFocus 5, improvedChanneling 4, arcaneConcentration 5, arcaneImpact 3, arcaneBlast 1, arcaneMeditation 3, missileBarrage 1, arcaneMind 5, arcaneInstability 3, incineration 3, frostWarding 2, elementalPrecision 5, iceShards 5, piercingIce 3, frostChanneling 3
- Choix : dungeon_boss : arcane, mage, ab_stacks 1, ab_dump arcane_missiles ; dungeon_pack : aoe, mage, aoe_filler blizzard
- Métrique (dégâts par seconde, dégâts/s) : Monte Carlo 314,62, analytique 364,67
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

## Rejeu 1.60.1.70245 révision 2 (PV des monstres du journal du 2026-10-07)

Rejoué le 2026-10-07 par `scripts/replay_builds.py run m70245-r2` (préréglage complet, graine 12345, race Orc),
comparé à `m70245-avant` (données de la révision 1, même jour). Seul changement des données : `monsters.json`
(`docs/research/data-1.60.1.70245-r2.md`) : 33 PNJ ajoutés et 7 changés, élites, PNJ nommés de quête et démons de
quête écartés de la courbe ; **aucune valeur de la courbe des PV par niveau ni de la correction Questie ne change**.

**Les 16 cas sont identiques** : talents, ordre des talents, alternative, stabilité, sensibilité et mesures (Monte
Carlo et analytique) au chiffre près ; `compare` : « aucune recommandation changée ».

Simulation montrée avant l'accord (première tentative, sans écartement, journal encore ouvert) : talents finaux
identiques, ordre changé en leveling 40 (niveaux 31 à 37) et 60 (niveaux 31 à 37, 54 et 56), chaque fois entre
talents non départagés ; l'écartement de Polly et des PNJ nommés ramène la courbe à celle de la révision 1.

## Rejeu T08d, révision 6 (correction Questie par Theil-Sen pondéré)

Rejoué le 2026-10-06 par `scripts/replay_builds.py run 70170-r6` (préréglage complet, graine 12345, race Orc) sur la
révision 6 préparée dans une copie des données avant l'écriture, comparé à `70170-r5`. Seul changement : la
correction Questie (`docs/research/data-1.60.1.70170-r6.md`). Raison commune : PV plus bas au-delà du niveau 24
(niveau 30 : 1 647 → 1 555 ; niveau 40 : 3 404 → 3 159 ; niveau 60 : 8 374 → 7 597), temps par monstre en baisse
d'environ 2,5 à 3,7 s.

**Treize cas inchangés, trois changés** (montrés à l'utilisateur et acceptés avant l'écriture) :

| Cas | Changement | Avant (r5) | Après (r6) |
| --- | --- | --- | --- |
| leveling 30 | build : Ice Shards 1 → 0, Shatter 2 → 3 ; ordre des niveaux 27 à 29 | 49,3 s par monstre (analytique) | 46,7 s ; égalité avec l'alternative (écart −1,27 s [−2,91 ; 0,37]), stable 5/5 |
| leveling 40 | build : Elemental Precision 3 → 4, Winter's Chill 4 → 3 (retour au build de la r3) ; ordre des niveaux 27 à 39 | 53,3 s | 50,8 s ; égalité (écart 0,39 s [−1,29 ; 2,06]), stable 5/5 |
| leveling 60 | ordre des talents (niveaux 27 à 56), build final inchangé | 50,9 s, stable 5/5 | 47,2 s ; égalité (écart −0,36 s [−2,09 ; 1,37]), stable 4/5 |

## Rejeu T08d (1.60.1.70170 révision 5, PV des monstres des journaux du 2026-10-02)

Rejoué le 2026-10-06 par `scripts/replay_builds.py run 70170-r5` (préréglage complet, graine 12345, race Orc),
comparé à `70170-r3` (la r4 ne change que l'arbre du Guerrier et des métadonnées : entrées des moteurs du Mage
identiques). Seul changement des données : `monsters.json` (`docs/research/data-1.60.1.70170-r5.md`). Raison commune :
PV plus bas aux niveaux 21, 23 et 24 (691, 803, 863 mesurés), plus hauts de 25 à 63 (correction plus pentue après
l'écartement des PNJ nommés, décision 189) ; le temps par monstre monte d'environ 3 à 5 s au-delà du niveau 25.

**Treize cas inchangés, trois changés** (montrés à l'utilisateur avant la poussée) :

| Cas | Changement | Avant (r3) | Après (r5) |
| --- | --- | --- | --- |
| leveling 30 | ordre des talents (niveaux 21 à 28), build final inchangé | Frost Channeling aux niveaux 21 à 23 | Piercing Ice aux niveaux 21 à 23, Frost Channeling aux niveaux 24, 26 et 27 |
| leveling 40 | build : Elemental Precision 4 → 3, Winter's Chill 3 → 4 ; ordre des niveaux 21 à 40 | 50,14 s par monstre (analytique) | 53,30 s ; l'ancien build est maintenant à égalité statistique (écart 0,23 s [-1,36 ; 1,82]), stable 5/5 |
| leveling 60 | ordre des talents (niveaux 21 à 60), build final inchangé | Ice Block au niveau 60, Frost Warding aux niveaux 50 et 51 | Ice Block au niveau 50, Frost Warding aux niveaux 56 et 57, Improved Blizzard au niveau 60 |

Chaque choix changé est une égalité statistique (intervalle de confiance à 95 % qui contient 0) : l'ordre bascule
sur de petits écarts de PV. Explication probable, non vérifiée par ablation : les combats plus longs avantagent
Winter's Chill, dont les cumuls servent davantage sur la durée.

## Rejeu 1.60.1.70170 révision 2 (PV des monstres du premier journal, 2026-10-02)

Rejoué le 2026-10-02 par `scripts/replay_builds.py run 70170-r2` (préréglage complet, graine 12345, race Orc),
comparé à `70170-r1`. Seul changement des données : `monsters.json` (PV par niveau et correction Questie recalculés
sur le journal `WoWCombatLog-100226_080035`, PNJ hors norme écartés de la courbe ; `docs/research/data-1.60.1.70170-r2.md`).
Raison commune : les PV des monstres des niveaux 21 à 63 (correction moins pentue, niveau 22 mesuré à 746 au lieu de
773 estimés).

**Treize cas inchangés, trois changés** (montrés à l'utilisateur avant le commit) :

| Cas | Changement | Avant (r1) | Après (r2) |
| --- | --- | --- | --- |
| leveling 30 | recommandation : Elemental Precision 2 → 1, Frost Channeling 2 → 3 | build retenu par le Monte Carlo, instable (1/5), sensible aux PV des monstres et au coefficient d'Ice Lance | alternative retenue par l'analytique (égalité, écart 0,37 s [-1,05 ; 1,80] sur 46 s par monstre), stable (5/5), aucune sensibilité |
| leveling 40 | ordre des talents (niveaux 21 à 24), build final inchangé | Piercing Ice aux niveaux 21 et 22, Frost Channeling aux niveaux 23 et 24 | Frost Channeling aux niveaux 21 à 23, Piercing Ice au niveau 24 |
| leveling 60 | même ordre que leveling 40, build final inchangé | idem | idem |

Chaque choix des niveaux 21 à 24 est une égalité statistique (`non_departage` ou `anticipation`) : l'ordre bascule
sur de petits écarts de PV. Le build de leveling au niveau 30 devient stable, mais il reste à une égalité près de
l'ancienne recommandation.

## Rejeu 1.60.1.70170 (installation du 2026-10-02)

Rejoué le 2026-10-02 par `scripts/replay_builds.py run 70170-r1` (préréglage complet, graine 12345, race Orc ; données
1.60.1.70170 révision 1, empreinte f2d021a89e1f), comparé au passage `70124-r6` (empreinte ef5603c56de6) produit juste
avant l'installation sur 1.60.1.70124 révision 6. Le plafond de la bêta passe à 30
(observé en jeu par l'utilisateur le 2026-10-01) : le rejeu joue désormais aussi le leveling au niveau 30 (16 cas).

**Aucune recommandation changée** (`compare 70124-r6 70170-r1`), métriques identiques dans les 16 cas. Raisons :
Heating Up garde les valeurs de Hot Streak (20 s, 25 % par cumul, 3 cumuls, même aura 400625) ; Combustion (3 charges
au lieu de 4) n'est pas modélisée hors de la borne de l'angle mort B18, et aucun build retenu ne la prend ; les sorts
du Mage ne changent pas. Seul changement : `leveling-30` devient vérifiable en jeu (niveau ≤ plafond).

| Cas | Arcanes/Feu/Givre | Monte Carlo | Analytique | Avantage sur l'alternative | Retenu | Stabilité | Sensibilité |
| --- | --- | --- | --- | --- | --- | --- | --- |
| leveling 30 (nouveau) | 0/0/21 | 46,44 | 46,66 | 1,71 [0,12 ; 3,30] | build (monte_carlo) | instable (1/5 build) | mob_hp, ice_lance_coef |

Le build de leveling au niveau 30 est **instable** (une graine sur cinq le retient) et bascule avec les PV des monstres
et le coefficient d'Ice Lance (E4) : deux hypothèses à mesurer en jeu avant de s'y fier.

## Rejeu T08b (1.60.1.70124 révision 4)

Rejoué le 2026-10-01 par `scripts/replay_builds.py run T08b` (préréglage complet, graine 12345, race Orc) sur la
révision 4 : ratios du personnage lus dans le client en mode forever (`character_scaling.json`), utilitaires du Mage
lus dans `classes.json`. Comparaison `compare PV1 T08b` ; raison de chaque changement par **ablation**
(`--ratios seed:<nom>` : la valeur du client remise à son estimation, une à la fois, passages `T08b-sans-<nom>`).
Seules trois valeurs du client diffèrent des estimations : critique par Intelligence (`int_per_crit`), mana de base
(`base_mana`), utilitaires (`utility`) ; XP par niveau, constante d'armure, règles des talents, Ignite et Winter's
Chill décodés sont identiques aux estimations (contrôlé avant le rejeu).

**Onze cas inchangés, quatre changés** (montrés à l'utilisateur avant le commit de la révision 4, accord du même jour) :

| Cas | Changement | Raison (ablation qui rend la recommandation de PV1) | Écart avec l'alternative (T08b) |
| --- | --- | --- | --- |
| leveling 40 | Elemental Precision 2 → 4, Winter's Chill 5 → 3 ; ordre des niveaux 21 à 31 | critique par Intelligence | égalité au seul niveau 40 (non significatif) ; le build suit le meilleur chemin cumulé de 10 à 40 |
| leveling 60 | mêmes talents ; ordre des niveaux 21 à 31 | critique par Intelligence | inchangé (non significatif) |
| donjon 20 | Arcane Focus 3 → 5, Arcane Blast 0 → 1, Wand Specialization 2 → 0, Elemental Precision 1 → 0 ; boss en rotation Arcanes (un cumul, Arcane Missiles), paquets en Blizzard ; dégâts par seconde plus bas | mana de base (plus basse au niveau 20 que la droite estimée) | significatif |
| raid 20 | même build ; décision au Monte Carlo et stabilité sur 5 graines sur 5 | mana de base | l'alternative devient significativement moins bonne |

Les chiffres de chaque cas sont dans `<cache>/builds/T08b/` et `<cache>/builds/T08b-sans-*/` (`table.md`). Les écarts
des 55 builds de la communauté sont recalculés (fixture `tests/fixtures/community/mage_builds.json`) : ils
concordent désormais avec notre référence pour 2 builds (8 avant la révision 4).

## Rejeu T08a (1.60.1.70124)

Rejoué le 2026-09-30 par `scripts/replay_builds.py run T08a` (mêmes réglages : préréglage complet, graine 12345,
race Orc), sur les données de 1.60.1.70124 révision 1 (empreinte `b57929e561ea`), après
`forever install --new-version`.

**Aucune recommandation changée, et aucune mesure changée non plus** : les quinze lignes du tableau (contexte,
niveau, répartition des points, Monte Carlo, analytique, avantage, retenu, stabilité, sensibilité) sont identiques
à celles du rejeu `r2-departage` de T06b, la durée de calcul mise à part, qui dépend de la machine.

C'était attendu : les 22 tables du client sont identiques entre 1.60.1.70009 et 1.60.1.70124
(`docs/research/data-1.60.1.70124.md`), `forever diff` entre les deux versions installées ne rend « aucun
changement », et l'optimiseur reçoit donc exactement les mêmes entrées.

**Limite de l'outil, relevée à cette occasion et corrigée** : `scripts/replay_builds.py compare <avant> <après>`
rendait « aucune recommandation changée » quand l'étiquette `<avant>` n'existait pas dans le cache, sans rien
signaler. La comparaison ci-dessus a donc été faite ligne à ligne contre le tableau de la section suivante, pas
avec `compare`. Le script refuse désormais une étiquette absente ou vide, en nommant le dossier cherché, les
passages disponibles et la commande qui produit celui qui manque (`tests/unit/test_replay_builds_labels.py`).

## Rejeu T06b (révision 2)

Rejoué le 2026-09-29 par `scripts/replay_builds.py` (mêmes réglages que ci-dessus : préréglage complet, graine 12345,
race Orc), en trois passages, chacun rendu dans `<cache>/builds/<passage>/` :

1. `r1` : données de la révision 1 (empreinte `bc8ce3e99480`) et règles de T05 ; mêmes talents, choix, alternatives,
   métriques et verdicts que le tableau ci-dessus (analytique du donjon corrigé, voir la note de la synthèse : écart
   du document venu du commit `7c96d77`, pas de T06b).
   Durée totale : environ 15 min (leveling 60 : 356 s).
2. `r2-donnees` : révision 2 installée (`forever install`, `revisions.json`), règles de T05. **Aucune recommandation
   changée.** Seules bougent des mesures : leveling 20, Monte Carlo 34,74 → 34,90 s et analytique 35,37 → 35,48 s
   (coût d'Ice Lance rang 1 lu dans le client, 45, au lieu de l'estimation 41,25 : ligne `ice_lance.ranks[1].mana`
   de `revisions.json`) ; PvP champ de bataille 20, avantage 11,04 → 10,84 (Ice Lance rang 1 : 28-33 au lieu de 26-30,
   `ice_lance.ranks[1].min`/`max`).
3. `r2-departage` : révision 2 et départage de T06b (décision 100), présélection du faisceau corrigée après la
   relecture (à score égal, talent modélisé d'abord). **Seul l'ordre du leveling 60 change** ; le build final,
   l'alternative, les métriques et les verdicts restent les mêmes. Entre les niveaux 41 et 60, les points sans effet
   modélisé (Frost Warding, Ice Block, Improved Blizzard : angle mort C9) passent après les talents modélisés à
   égalité (`decided_by` : `modelise` aux niveaux 48, 49, 54, 57), puis sont pris quand il ne reste que des
   égalités (`non_departage`) ; aucune étape ne prend un non modélisé à égalité avec un modélisé (contrôlé sur les
   trois chemins). Limite : Improved Cone of Cold compte comme modélisé alors qu'il n'agit pas en leveling (question
   ouverte I5, contexte du départage).

Décisions des étapes de l'ordre (`r2-departage`) : leveling 20 : 5 non départagées, 4 au Monte Carlo, 2 gardées par
l'anticipation ; 40 : 19, 6, 6 ; 60 : 29 non départagées, 7 départagées en faveur d'un talent modélisé, 7 au Monte
Carlo, 8 par l'anticipation. La plupart des étapes du leveling ne sont donc **pas départagées par le calcul** à
n = 200 : l'ordre y reste une proposition parmi des choix équivalents.

| Contexte | Niveau | Arcanes/Feu/Givre | Monte Carlo | Analytique | Avantage sur l'alternative | Retenu | Stabilité | Sensibilité | Calcul |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| leveling | 20 | 0/0/11 | 34,90 | 35,48 | 0,45 [-0,82 ; 1,71] (égalité) | build (analytique) | stable (build) | tient | 42 s |
| leveling | 40 | 0/0/31 | 51,72 | 49,89 | 0,66 [-0,93 ; 2,24] (égalité) | build (analytique) | stable (build) | tient | 180 s |
| leveling | 60 | 0/0/51 | 43,66 | 47,01 | 0,67 [-1,03 ; 2,38] (égalité) | alternative (analytique) | stable (alternative) | tient | 333 s |
| dungeon | 20 | 10/0/1 | 40,70 | 51,00 | 4,37 [3,76 ; 4,98] | build (monte_carlo) | stable (build) | mob_hp | 7 s |
| dungeon | 40 | 31/0/0 | 144,93 | 164,28 | 1,27 [-1,76 ; 4,30] (égalité) | build (analytique) | stable (build) | regen_stacking | 34 s |
| dungeon | 60 | 30/3/18 | 314,62 | 364,67 | 27,40 [18,79 ; 36,02] | build (monte_carlo) | stable (build) | tient | 87 s |
| raid | 20 | 11/0/0 | 6,18 | 6,36 | -0,12 [-0,30 ; 0,06] (égalité) | build (analytique) | instable (4/5 build) | tient | 5 s |
| raid | 40 | 28/3/0 | 40,38 | 38,53 | 0,00 [0,00 ; 0,00] (égalité) | build (analytique) | stable (build) | tient | 28 s |
| raid | 60 | 46/5/0 | 79,92 | 75,58 | 0,00 [0,00 ; 0,00] (égalité) | build (analytique) | stable (build) | tient | 69 s |
| pvp-bg | 20 | 0/0/11 | — | 50,17 | 10,84 [10,84 ; 10,84] | build (profil) | stable (build) | tient | 2 s |
| pvp-bg | 40 | 31/0/0 | — | 69,32 | 0,35 [0,35 ; 0,35] | build (profil) | stable (build) | tient | 17 s |
| pvp-bg | 60 | 15/3/33 | — | 118,14 | 2,05 [2,05 ; 2,05] | build (profil) | stable (build) | tient | 33 s |
| pvp-world | 20 | 0/0/11 | — | 41,14 | 8,07 [8,07 ; 8,07] | build (profil) | stable (build) | tient | 3 s |
| pvp-world | 40 | 31/0/0 | — | 65,88 | 6,04 [6,04 ; 6,04] | build (profil) | stable (build) | tient | 18 s |
| pvp-world | 60 | 29/3/19 | — | 121,02 | 1,30 [1,30 ; 1,30] | build (profil) | stable (build) | tient | 33 s |
