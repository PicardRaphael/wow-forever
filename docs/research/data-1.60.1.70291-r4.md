# data: 1.60.1.70291 r3 → r4 (mesures de 1.60.1.70245 reportées, décisions 221 et 222)

Accord de l'utilisateur du 2026-10-09 (attente `measures-1.60.1.70245-1ddb4bdae91a`, variante B), après la simulation et
le rejeu. Trois journaux écrits sous le client 1.60.1.70245 (WoWCombatLog-100726_130833, WoWCombatLog-100826_081058,
WoWCombatLog-100826_153741 : Dun Morogh, Coldridge, Ragefire Chasm) mesurés dans 1.60.1.70291 par
`forever measures refresh --accept-version 1.60.1.70245` : la note officielle du 08/10 (t/2360696/5, révision 1) ne
touche pas ces monstres (seuls Shadowvale et Bandarion Keep, en Tirisfal, changent de niveau). Trace : notes de
`monsters.json`, source de `sources.json`, `revisions.json` (révision 4, empreintes des journaux).

## Courbe des PV
Seuls les PNJ combattus par le joueur et non amis entrent dans la courbe (décision 222) ; 16 PNJ nommés écartés sur
accord (Mountaineer Naarh, Ironforge Protector et 14 PNJ de quête ou de zone de départ). Sans la règle générale, Dun
Morogh Mountaineer (garde ami de niveau 30, relevé à côté des combats) aurait porté le niveau 30 de 1555 à 2484.

Correction Questie : pente 0.025093148621598615 → 0.025354762196867386, ordonnée 0.7991893193790787 → 0.7959953788901166,
genou 8.002609941427439 → 8.046008064516117.

| Niveau | Avant (r3) | Après (r4) |
| --- | --- | --- |
| 25 | 1016 | 1018 |
| 26 | 1142 | 1145 |
| 27 | 1240 | 1244 |
| 28 | 1346 | 1349 |
| 29 | 1451 | 1455 |
| 30 | 1555 | 1560 |
| 31 | 1744 | 1750 |
| 32 | 1862 | 1868 |
| 33 | 1987 | 1994 |
| 34 | 2113 | 2121 |
| 35 | 2251 | 2259 |
| 36 | 2501 | 2510 |
| 37 | 2654 | 2664 |
| 38 | 2811 | 2822 |
| 39 | 2983 | 2995 |
| 40 | 3159 | 3171 |
| 41 | 3477 | 3491 |
| 42 | 3671 | 3686 |
| 43 | 3867 | 3884 |
| 44 | 4069 | 4087 |
| 45 | 4275 | 4294 |
| 46 | 4684 | 4706 |
| 47 | 4923 | 4945 |
| 48 | 5163 | 5188 |
| 49 | 5421 | 5447 |
| 50 | 5685 | 5712 |
| 51 | 6193 | 6223 |
| 52 | 6485 | 6517 |
| 53 | 6788 | 6822 |
| 54 | 7092 | 7128 |
| 55 | 7405 | 7443 |
| 56 | 6543 | 6577 |
| 57 | 8378 | 8422 |
| 58 | 8414 | 8459 |
| 59 | 8775 | 8822 |
| 60 | 7597 | 7638 |
| 61 | 7910 | 7953 |
| 62 | 10291 | 10348 |
| 63 | 13676 | 13752 |

## PNJ écartés de la courbe (nouveaux)
| PNJ | Nom | Raison |
| --- | --- | --- |
| 1131 | Winter Wolf | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1134 | Young Wendigo | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1135 | Wendigo | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1138 | Snow Tracker Wolf | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1161 | Stonesplinter Trogg | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1162 | Stonesplinter Scout | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1176 | Tunnel Rat Forager | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1190 | Mountain Boar | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1202 | Tunnel Rat Kobold | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1211 | Leper Gnome | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1260 | Great Father Arctikus | rang 4 dans Questie (rare) : écarté automatiquement de la courbe des PNJ normaux (communautaire (Classic Era, aucune correction Forever), Questie 11.38.0 Forever-v27) |
| 1266 | Tundra MacGrann | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 1271 | Old Icebeard | rang 1 dans Questie (élite) : écarté automatiquement de la courbe des PNJ normaux (communautaire (Classic Era, aucune correction Forever), Questie 11.38.0 Forever-v27) |
| 1329 | Mountaineer Naarh | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 1388 | Vagash | rang 1 dans Questie (élite) : écarté automatiquement de la courbe des PNJ normaux (communautaire (Classic Era, aucune correction Forever), Questie 11.38.0 Forever-v27) |
| 1412 | Squirrel | PNJ seulement vu à côté des combats, jamais combattu par le joueur dans les journaux : mesuré, écarté d'office de la courbe (décision 222) |
| 1961 | Mangeclaw | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 5612 | Gimrizz Shadowcog | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 6119 | Tog Rustsprocket | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 6124 | Captain Beld | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 6328 | Dannie Fizzwizzle | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 10556 | Lazy Peon | PNJ ami d'après la réaction du journal de combat (garde, PNJ de ville ou de quête) : mesuré, écarté d'office de la courbe (décision 222) |
| 10803 | Rifleman Wheeler | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 10804 | Rifleman Middlecamp | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 12319 | Burning Blade Toxicologist | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 12320 | Burning Blade Crusher | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 12427 | Mountaineer Dolf | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 13076 | Dun Morogh Mountaineer | PNJ ami d'après la réaction du journal de combat (garde, PNJ de ville ou de quête) : mesuré, écarté d'office de la courbe (décision 222) |
| 260157 | Elder Snow Leopard | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 271486 | Wendigo Shaman | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 271530 | Elder Wendigo | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |
| 274935 | Ironforge Protector | PNJ nommés ou hors norme signalés par la mesure (un point d'apparition dans Questie ou absents de Questie) : Mountaineer Naarh (niveau 30), Ironforge Protector (garde élite, niveau 55) et 14 PNJ de quête ou de zone de départ ; accord de l'utilisateur du 2026-10-09 |

## Rejeu
Rejeu des cas de leveling de T05 (personnage neuf, chemin depuis le niveau 10, décision 220), r3 (empreinte
da74bf6bf71d) contre variante B (fda10be3c665, mêmes valeurs que r4) : leveling 20 inchangé (Feu) ; leveling 30 :
Piercing Ice 3 au lieu de 2 et sans Ice Shards (Givre), 45,72 → 45,60 s par monstre ; leveling 40 et 60 : ordre des
talents changé, mêmes talents. XP par heure (Monte Carlo, sans talent, Orc) : niveaux 20 à 30 inchangés à 0,2 % près ;
niveau 40 : Givre −1,2 %, Feu −0,6 %.
