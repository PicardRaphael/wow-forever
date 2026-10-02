# data: 1.60.1.70170 r1 → r2

Mesure du premier journal du client 1.60.1.70170, `WoWCombatLog-100226_080035.txt`, par `forever measures refresh`
(simulation montrée à l'utilisateur, accord du 2026-10-02). Le journal est attribué à 70170 par session
(`client_builds.json`, décision 167) ; les journaux écrits sous 70009 et 70124 sont lus mais jamais écrits dans les
données de 70170 (décision 135). Le journal était encore en cours d'écriture (session de jeu ouverte) : la mesure est
l'état du fichier à l'écriture, empreinte dans `revisions.json` ; un passage suivant le relèvera comme « modifié ».

| Fichier | Changement |
| --- | --- |
| monsters.json | 30 PNJ ajoutés (mesurés), 21 conservés (journaux du 2026-09-27 disparus du dossier), aucun retiré |
| monsters.json | `hp_by_level` : 44 niveaux changés (tableau) |
| monsters.json | `questie_correction` : 13 niveaux au lieu de 7, pente 0.0248 → 0.0238, genou 7.95 → 7.44 |
| monsters.json | `curve_excluded` : Thistle Bear (2163), Grizzled Thistle Bear (2165), Dark Strand Enforcer (3727), Wildthorn Stalker (3819), avec leur raison |
| origins.json | règle `/curve_excluded` (origine `parametre` : choix de calcul de l'agrégat) |
| sources.json | source de `monsters.json`, révision 2 |
| revisions.json | révision 2 : commande, journal et son empreinte, chaque valeur changée |

## PNJ hors norme (décision de l'utilisateur)
Toujours mesurés un par un dans `npcs`, écartés de la médiane par niveau et de l'ajustement de la correction : les
ours (Thistle Bear 299 PV au niveau 11, Grizzled Thistle Bear 534 et 591 aux niveaux 16 et 17, au-dessus des PNJ
normaux de ces niveaux) et les deux PNJ à 642 PV au niveau 20 (629 pour les autres). Effet : niveau 20 à 629 `certain`
(valeur commune), niveau 21 rendu à Questie corrigé (seul Wildthorn Stalker y était mesuré).

## PV par niveau

| Niveau | Avant | Après |
| --- | --- | --- |
| 8 | 156 | 158 |
| 9 | 181 | 180 |
| 21 | 703 | 702 |
| 22 | 773 | 746 |
| 23 | 847 | 846 |
| 24 | 928 | 926 |
| 26 | 1139 | 1135 |
| 27 | 1237 | 1231 |
| 28 | 1342 | 1335 |
| 29 | 1446 | 1438 |
| 30 | 1550 | 1540 |
| 31 | 1738 | 1726 |
| 32 | 1855 | 1841 |
| 33 | 1980 | 1964 |
| 34 | 2105 | 2088 |
| 35 | 2242 | 2222 |
| 36 | 2491 | 2468 |
| 37 | 2643 | 2617 |
| 38 | 2799 | 2771 |
| 39 | 2970 | 2939 |
| 40 | 3145 | 3110 |
| 41 | 3461 | 3422 |
| 42 | 3654 | 3611 |
| 43 | 3849 | 3802 |
| 44 | 4049 | 3999 |
| 45 | 4254 | 4199 |
| 46 | 4661 | 4599 |
| 47 | 4897 | 4831 |
| 48 | 5137 | 5065 |
| 49 | 5392 | 5316 |
| 50 | 5655 | 5572 |
| 51 | 6159 | 6068 |
| 52 | 6449 | 6351 |
| 53 | 6750 | 6646 |
| 54 | 7052 | 6941 |
| 55 | 7363 | 7245 |
| 56 | 6505 | 6399 |
| 57 | 8329 | 8192 |
| 58 | 8364 | 8224 |
| 59 | 8722 | 8573 |
| 60 | 7550 | 7420 |
| 61 | 7861 | 7724 |
| 62 | 10228 | 10046 |
| 63 | 13590 | 13346 |

Niveaux 1 à 22 : mesure si le niveau est mesuré, sinon Questie corrigé (`probable` dans la plage) ; au-delà, Questie
corrigé par la droite (`suppose`).
