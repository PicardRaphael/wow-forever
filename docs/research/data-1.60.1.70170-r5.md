# data: 1.60.1.70170 r4 → r5

Mesure des journaux du 2026-10-02 sous le client 1.60.1.70170, par `forever measures refresh` (simulation montrée à
l'utilisateur, accord du 2026-10-06), en session et avant l'installation de 1.60.1.70235 (`monsters.json` passe à
la version suivante quand on l'installe).

- `WoWCombatLog-100226_080035.txt` est le journal de la révision 2, qui a grossi : l'empreinte de la r2 est celle
  de ses 21 372 premières lignes (5 936 426 octets, jusqu'à 12:08:07) ; il en compte 28 335 (7 817 941 octets).
- `WoWCombatLog-100226_162842.txt` est une autre session du même jour, sous 70170.
- Journaux écrits sous 70009, 70124, 70205 et 70235 : lus mais jamais écrits dans 70170 (décision 135).

| Fichier | Changement |
| --- | --- |
| monsters.json | 16 PNJ ajoutés, 5 changés (mesurés), 67 au total |
| monsters.json | `hp_by_level` : 41 niveaux changés (tableau) |
| monsters.json | `questie_correction` : 17 niveaux au lieu de 13, pente 0.02381 → 0.02509, genou 7.44 → 7.46 |
| monsters.json | `curve_excluded` : + Ilkrud Magthrull (3664), Ashenvale Bear (3809), Wrathtail Priestess (3944) |
| sources.json | source de `monsters.json`, révision 5 |
| revisions.json | révision 5 : commande, journaux et leurs empreintes, chaque valeur changée |

## PNJ hors norme (décision de l'utilisateur du 2026-10-06, même précédent que la révision 2)

Tous au rang normal dans Questie : l'écartement automatique par rang (T08d, bloc J) n'en écarte aucun. Mesurés un
par un dans `npcs`, écartés de la médiane par niveau et de l'ajustement : Ilkrud Magthrull (1 269 PV au niveau 24,
863 pour les autres PNJ), Ashenvale Bear (860 et 928 aux niveaux 21 et 22, comme les ours de la r2), Wrathtail
Priestess (642 au niveau 20, comme les deux PNJ à 642 de la r2). Vorsha the Lasher (1 462 au niveau 22) est gardé.

Effet sur la pente de la correction (calculé sur les PNJ de la r5) : 0.02610 sans écart supplémentaire ; Ilkrud
Magthrull seul la porte à 0.02507 ; les deux autres n'y changent presque rien ; écarter aussi Vorsha la remonterait
à 0.02611 (rapport du niveau 22 : 1.30 → 1.385).

## PV par niveau

| Niveau | r4 | r5 | Certitude |
| --- | --- | --- | --- |
| 21 | 702 | 691 | probable |
| 23 | 846 | 803 | certain |
| 24 | 926 | 863 | probable |
| 26 | 1135 | 1153 | suppose |
| 27 | 1231 | 1252 | suppose |
| 28 | 1335 | 1358 | suppose |
| 29 | 1438 | 1463 | suppose |
| 30 | 1540 | 1569 | suppose |
| 31 | 1726 | 1759 | suppose |
| 32 | 1841 | 1877 | suppose |
| 33 | 1964 | 2003 | suppose |
| 34 | 2088 | 2131 | suppose |
| 35 | 2222 | 2269 | suppose |
| 36 | 2468 | 2521 | suppose |
| 37 | 2617 | 2674 | suppose |
| 38 | 2771 | 2833 | suppose |
| 39 | 2939 | 3006 | suppose |
| 40 | 3110 | 3182 | suppose |
| 41 | 3422 | 3502 | suppose |
| 42 | 3611 | 3698 | suppose |
| 43 | 3802 | 3895 | suppose |
| 44 | 3999 | 4098 | suppose |
| 45 | 4199 | 4305 | suppose |
| 46 | 4599 | 4717 | suppose |
| 47 | 4831 | 4956 | suppose |
| 48 | 5065 | 5198 | suppose |
| 49 | 5316 | 5457 | suppose |
| 50 | 5572 | 5722 | suppose |
| 51 | 6068 | 6233 | suppose |
| 52 | 6351 | 6526 | suppose |
| 53 | 6646 | 6830 | suppose |
| 54 | 6941 | 7136 | suppose |
| 55 | 7245 | 7451 | suppose |
| 56 | 6399 | 6582 | suppose |
| 57 | 8192 | 8429 | suppose |
| 58 | 8224 | 8464 | suppose |
| 59 | 8573 | 8826 | suppose |
| 60 | 7420 | 7640 | suppose |
| 61 | 7724 | 7955 | suppose |
| 62 | 10046 | 10349 | suppose |
| 63 | 13346 | 13752 | suppose |
