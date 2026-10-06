# data: 1.60.1.70170 r5 → r6

Correction Questie → Forever recalculée par **Theil-Sen pondéré** (décision 190, question MON6), sur les mêmes
mesures que la révision 5 (mêmes journaux, mêmes PNJ écartés). Accord de l'utilisateur du 2026-10-06 après le rejeu
des builds de T05 (`docs/research/builds-T05.md`, section « Rejeu T08d, révision 6 »).

| Fichier | Changement |
| --- | --- |
| monsters.json | `questie_correction` : méthode Theil-Sen pondéré ; pente 0.0299 → 0.0251, ordonnée 0.747 → 0.799, genou 8.45 → 8.00 (16 niveaux mesurés, 1 à 24) |
| monsters.json | `hp_by_level` : 39 niveaux non mesurés recalculés (tableau) ; niveaux mesurés inchangés |
| monsters.json | `inversions` : toujours 56 et 60 (valeurs recalculées) |
| sources.json | révision 6 |
| revisions.json | révision 6 : chaque valeur changée |

Pourquoi : la droite des moindres carrés donnait le même poids à chaque niveau, et un seul PNJ faisait varier la
pente de 0,0261 à 0,0323 ; Theil-Sen pondéré donne 0,0248 en r4 et 0,0251 en r5, et retirer un PNJ ne la fait varier
que de 0,0250 à 0,0262 (`docs/modeling-decisions.md`, section « Correction Questie »).

## PV par niveau

| Niveau | r5 | r6 | Certitude |
| --- | --- | --- | --- |
| 25 | 1064 | 1016 | suppose |
| 26 | 1200 | 1142 | suppose |
| 27 | 1306 | 1240 | suppose |
| 28 | 1419 | 1346 | suppose |
| 29 | 1533 | 1451 | suppose |
| 30 | 1647 | 1555 | suppose |
| 31 | 1851 | 1744 | suppose |
| 32 | 1980 | 1862 | suppose |
| 33 | 2117 | 1987 | suppose |
| 34 | 2256 | 2113 | suppose |
| 35 | 2407 | 2251 | suppose |
| 36 | 2678 | 2501 | suppose |
| 37 | 2847 | 2654 | suppose |
| 38 | 3021 | 2811 | suppose |
| 39 | 3210 | 2983 | suppose |
| 40 | 3404 | 3159 | suppose |
| 41 | 3752 | 3477 | suppose |
| 42 | 3967 | 3671 | suppose |
| 43 | 4185 | 3867 | suppose |
| 44 | 4409 | 4069 | suppose |
| 45 | 4639 | 4275 | suppose |
| 46 | 5089 | 4684 | suppose |
| 47 | 5354 | 4923 | suppose |
| 48 | 5623 | 5163 | suppose |
| 49 | 5910 | 5421 | suppose |
| 50 | 6205 | 5685 | suppose |
| 51 | 6767 | 6193 | suppose |
| 52 | 7093 | 6485 | suppose |
| 53 | 7433 | 6788 | suppose |
| 54 | 7773 | 7092 | suppose |
| 55 | 8125 | 7405 | suppose |
| 56 | 7186 | 6543 | suppose |
| 57 | 9211 | 8378 | suppose |
| 58 | 9259 | 8414 | suppose |
| 59 | 9664 | 8775 | suppose |
| 60 | 8374 | 7597 | suppose |
| 61 | 8727 | 7910 | suppose |
| 62 | 11364 | 10291 | suppose |
| 63 | 15114 | 13676 | suppose |
