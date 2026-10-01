# Familiers du Chasseur : recoupement client ↔ Forever Bestiary ↔ Questie

Rapport généré par `forever pets crosscheck --markdown` : ne pas éditer à la main. Le client fait foi ;
chaque écart est listé avec ses deux valeurs et leurs sources, jamais tranché.

- Client : client 1.60.1.70124 (pets.json)
- Addon : Forever Bestiary 0.5.0 (base du 2026-09-25, client 1.60.1.69913 ; carte communautaire du 2026-09-29)
- Questie : Questie 11.38.0 (base Classic Era)
- Familles : 19 dans le client, 18 dans l'addon, 18 comparées ; capacités de l'addon : 25 ; bêtes de l'addon : 606 (dont 552 dans Questie)
- Écarts : 29 ; PNJ dont Questie ne donne que le continent (non comptés) : 32

## Entrées du client jamais vues en jeu

- core-hound : famille du client absente de Forever Bestiary : jamais vue en jeu selon ses relevés

## Écarts internes au client (pets.json, observations du décodage)

- crocolisk : la ligne de compétence 212 s'appelle « Pet - Crocilisk », CreatureFamily écrit « Crocolisk » (écart interne au client)
- ligne 3015 « Pet - Bat » : aucune famille de CreatureFamily ne la vise (ligne orpheline, rendue à part)
- sort 6280 « Pet Hardiness » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6311 « Pet Aggression » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6314 « Pet Aggression » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6315 « Pet Aggression » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6316 « Pet Aggression » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6317 « Pet Aggression » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6328 « Pet Recovery » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6331 « Pet Recovery » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6332 « Pet Recovery » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6333 « Pet Recovery » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6334 « Pet Recovery » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6443 « Pet Resistance » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6444 « Pet Resistance » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6445 « Pet Resistance » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6446 « Pet Resistance » sans ligne SpellLevels (lignes [270]) : non rendu
- sort 6447 « Pet Resistance » sans ligne SpellLevels (lignes [270]) : non rendu
- lava-breath : premier rang du client 2 (aucun rang 1)
- pet-hardiness : premier rang du client 2 (aucun rang 1)
- slower-attack : premier rang du client 2 (aucun rang 1)
- sort 19577 « Intimidation » sans rang dans les lignes [270] : non rendu
- sort 24394 « Intimidation » sans rang dans les lignes [270] : non rendu
- sort 1278934 « Summoning » sans rang dans les lignes [653, 3015] : non rendu

## Familles du client absentes de l'addon (1)

| Sujet | Champ | client | addon |
| --- | --- | --- | --- |
| core-hound | — | Core Hound | — |

## Plage de niveau d'un PNJ différente de Questie (20)

| Sujet | Champ | questie | addon |
| --- | --- | --- | --- |
| 1129 | niveau | 6, 6 | 6, 7 |
| 11739 | niveau | 57, 59 | 57, 58 |
| 1184 | niveau | 18, 18 | 13, 14 |
| 14268 | niveau | 16, 16 | 15, 16 |
| 14283 | niveau | 53, 54 | 53, 63 |
| 1780 | niveau | 12, 13 | 12, 12 |
| 2070 | niveau | 16, 17 | 10, 11 |
| 2232 | niveau | 13, 14 | 12, 14 |
| 2729 | niveau | 38, 40 | 39, 40 |
| 2956 | niveau | 6, 8 | 6, 7 |
| 3634 | niveau | 15, 16 | 15, 17 |
| 3862 | niveau | 18, 18 | 18, 19 |
| 4304 | niveau | 33, 33 | 33, 34 |
| 5272 | niveau | 44, 44 | 44, 45 |
| 6013 | niveau | 37, 37 | 35, 37 |
| 6369 | niveau | 50, 50 | 50, 52 |
| 6585 | niveau | 53, 53 | 52, 53 |
| 7443 | niveau | 54, 56 | 55, 56 |
| 7455 | niveau | 55, 56 | 54, 56 |
| 9695 | niveau | 54, 54 | 54, 55 |

## Zone d'un PNJ différente de Questie (8)

| Sujet | Champ | questie | addon |
| --- | --- | --- | --- |
| 2408 | zone | Alterac Mountains | Hillsbrad Foothills |
| 3630 | zone | The Barrens | Wailing Caverns |
| 3631 | zone | The Barrens | Wailing Caverns |
| 3632 | zone | The Barrens | Wailing Caverns |
| 3633 | zone | The Barrens | Wailing Caverns |
| 3634 | zone | The Barrens | Wailing Caverns |
| 5291 | zone | Sunken Temple | The Temple of Atal'Hakkar |
| 5708 | zone | Sunken Temple | The Temple of Atal'Hakkar |
