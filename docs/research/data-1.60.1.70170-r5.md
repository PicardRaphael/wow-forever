# data: 1.60.1.70170 r4 → r5

Mesure des journaux du 2026-10-02 sous le client 1.60.1.70170, par `forever measures refresh` (simulation montrée à
l'utilisateur, accords du 2026-10-06), en session et avant l'installation de 1.60.1.70235 (`monsters.json` passe à
la version suivante quand on l'installe). Première écriture corrigée avant la poussée : règle des PNJ nommés de quête
(décision 189).

- `WoWCombatLog-100226_080035.txt` est le journal de la révision 2, qui a grossi : l'empreinte de la r2 est celle
  de ses 21 372 premières lignes (5 936 426 octets, jusqu'à 12:08:07) ; il en compte 28 335 (7 817 941 octets).
- `WoWCombatLog-100226_162842.txt` est une autre session du même jour, sous 70170.
- Journaux écrits sous 70009, 70124, 70205 et 70235 : lus mais jamais écrits dans 70170 (décision 135).

| Fichier | Changement |
| --- | --- |
| monsters.json | 16 PNJ ajoutés, 5 changés (mesurés), 67 au total |
| monsters.json | `hp_by_level` : 43 niveaux changés (tableau) |
| monsters.json | `questie_correction` : 16 niveaux mesurés (1 à 24) au lieu de 13, pente 0.0238 → 0.0299, genou 7.44 → 8.45 |
| monsters.json | `curve_excluded` : 2 PNJ hors norme et 8 PNJ nommés de quête ajoutés (ci-dessous) |
| sources.json | source de `monsters.json`, révision 5 |
| revisions.json | révision 5 : commandes, journaux et leurs empreintes, chaque valeur changée |

## PNJ écartés de la courbe (toujours mesurés un par un dans `npcs`)

- **Hors norme** (précédent de la révision 2, décision 168) : Ashenvale Bear (860 et 928 PV aux niveaux 21 et 22 :
  famille des ours), Wrathtail Priestess (642 au niveau 20, comme les deux PNJ à 642 de la r2).
- **PNJ nommés de quête** (règle de l'utilisateur du 2026-10-06, décision 189, au-dessus comme en dessous) : Ilkrud
  Magthrull (1 269 au niveau 24), Vorsha the Lasher (1 462 au 22), Sarilus Foulborne et Muglash (927 au 25), Talen et
  Therylune (473 au 17), Gamon (272 au 12), Teo Hammerstorm (absent de Questie).
- **Candidats proposés, non écartés** (au plus un point d'apparition dans Questie) : Burning Blade Toxicologist
  (345 au niveau 14) et Burning Blade Crusher (307 au 13), PNJ d'événement dont les PV sont ceux de la courbe : ils
  restent dans la courbe (décision de l'utilisateur).

Effet : plus aucun PNJ normal mesuré au niveau 25 ; la plage mesurée s'arrête au niveau 24 (rapport 1,48), d'où une
correction plus pentue et des niveaux 25 à 63 plus hauts que dans la r4 (`suppose`).

## PV par niveau

| Niveau | r4 | r5 | Certitude |
| --- | --- | --- | --- |
| 8 | 158 | 156 | probable |
| 21 | 702 | 691 | probable |
| 23 | 846 | 803 | certain |
| 24 | 926 | 863 | probable |
| 25 | 927 | 1064 | suppose |
| 26 | 1135 | 1200 | suppose |
| 27 | 1231 | 1306 | suppose |
| 28 | 1335 | 1419 | suppose |
| 29 | 1438 | 1533 | suppose |
| 30 | 1540 | 1647 | suppose |
| 31 | 1726 | 1851 | suppose |
| 32 | 1841 | 1980 | suppose |
| 33 | 1964 | 2117 | suppose |
| 34 | 2088 | 2256 | suppose |
| 35 | 2222 | 2407 | suppose |
| 36 | 2468 | 2678 | suppose |
| 37 | 2617 | 2847 | suppose |
| 38 | 2771 | 3021 | suppose |
| 39 | 2939 | 3210 | suppose |
| 40 | 3110 | 3404 | suppose |
| 41 | 3422 | 3752 | suppose |
| 42 | 3611 | 3967 | suppose |
| 43 | 3802 | 4185 | suppose |
| 44 | 3999 | 4409 | suppose |
| 45 | 4199 | 4639 | suppose |
| 46 | 4599 | 5089 | suppose |
| 47 | 4831 | 5354 | suppose |
| 48 | 5065 | 5623 | suppose |
| 49 | 5316 | 5910 | suppose |
| 50 | 5572 | 6205 | suppose |
| 51 | 6068 | 6767 | suppose |
| 52 | 6351 | 7093 | suppose |
| 53 | 6646 | 7433 | suppose |
| 54 | 6941 | 7773 | suppose |
| 55 | 7245 | 8125 | suppose |
| 56 | 6399 | 7186 | suppose |
| 57 | 8192 | 9211 | suppose |
| 58 | 8224 | 9259 | suppose |
| 59 | 8573 | 9664 | suppose |
| 60 | 7420 | 8374 | suppose |
| 61 | 7724 | 8727 | suppose |
| 62 | 10046 | 11364 | suppose |
| 63 | 13346 | 15114 | suppose |
