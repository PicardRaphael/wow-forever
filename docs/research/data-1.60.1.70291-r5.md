# data: 1.60.1.70291 r4 → r5 (PNJ hors norme écartés de la courbe, décision 223)

Accord de l'utilisateur du 2026-10-09 : règle automatique, seuil de 15 %, au moins 3 PNJ au niveau, référence concordante
(deux tiers des autres PNJ à moins du seuil de leur médiane) ; paramètres dans `mechanics.json`
(`monsters.curve_outlier`, origine paramètre). Seuil choisi d'après les mesures de r4 : 122 PNJ sur 137 exactement à la
médiane des autres PNJ de leur niveau, ours et Sunscale Lashtail entre 19,6 et 20,1 %, faux écarts de 8,9 % au plus.
Mesure relancée sur les mêmes journaux qu'en révision 4 ; chaque ligne de `monsters.json` garde désormais son état de
combat (`fought`).

## PNJ écartés de la courbe
| PNJ | Nom | Niveaux | Raison |
| --- | --- | --- | --- |
| 721 | Rabbit | 1 | hors norme : 1 PV au niveau 1, -97,6 % de la médiane des autres PNJ du niveau (42) ; mesuré, écarté de la courbe (décision 223) |
| 1128 | Young Black Bear | 5, 6 | hors norme : 122 PV au niveau 5, +19,6 % de la médiane des autres PNJ du niveau (102) ; mesuré, écarté de la courbe (décision 223) |
| 1186 | Elder Black Bear | 11, 12 | hors norme : 287 PV au niveau 11, +20,1 % de la médiane des autres PNJ du niveau (239) ; mesuré, écarté de la courbe (décision 223) |
| 1196 | Ice Claw Bear | 7, 8 | hors norme : 164 PV au niveau 7, +19,7 % de la médiane des autres PNJ du niveau (137) ; mesuré, écarté de la courbe (décision 223) |
| 3254 | Sunscale Lashtail | 11, 12, 13 | hors norme : 191 PV au niveau 11, -20,1 % de la médiane des autres PNJ du niveau (239) ; mesuré, écarté de la courbe (décision 223) |
| 5951 | Hare | 1 | hors norme : 8 PV au niveau 1, -81,0 % de la médiane des autres PNJ du niveau (42) ; mesuré, écarté de la courbe (décision 223) |

## Courbe
Niveau 1 : 8 → 42 PV (les bestioles Rabbit et Hare ne tirent plus la médiane vers le bas) ; niveaux 5, 6, 7, 8, 11, 12 et
13 : même valeur, certitude probable → certain ; correction Questie inchangée.

## Rejeu
Cas de leveling 20 et 30 (personnage neuf, décision 220) : talents, choix, ordre et métrique identiques à la révision 4
(aucune entrée des moteurs ne change au-delà du niveau 1, que les chemins depuis le niveau 10 n'utilisent pas).

## Question ouverte
MON7 : multiplicateur de PV par famille de monstres (ours à +20 et +25 %, Sunscale Lashtail à −20 %).
