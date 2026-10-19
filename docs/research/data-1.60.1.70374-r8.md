# data: 1.60.1.70374 r7 → r8

Candidate : `~/AppData/Local/Temp/claude/C--Users-rapha-Documents-wow-forever/e023bd1e-0fc5-48fe-8864-2e5448fc288b/scratchpad/cand-r8` (données 5d5dfecb6a2c).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 1 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 1 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 2 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"e49cb0fbb03f"` | `"744ed85ced1c"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |

## Règles et valeurs écrites à la main

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| origins.json | * | `"5e9c7cddfa9c"` | `"759273c8ac60"` | rules | règles de la tranche (origins.json du dépôt, lu par forever decode) | certain |
| mechanics.json | * | `"f6ce8d81ca1c"` | `"193de98cbd78"` | rules | valeurs écrites à la main de la tranche (mechanics.json du dépôt, hérité par forever decode) | probable |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 7 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (1)

Provenance · version 1.60.1.70374 r7 · données f5b5f2ce7610 · générée 2026-10-19T06:38:48Z · fraîcheur fresh · certitude certain · registre 76/147 · hypothèses : candidate ~/AppData/Local/Temp/claude/C--Users-rapha-Documents-wow-forever/e023bd1e-0fc5-48fe-8864-2e5448fc288b/scratchpad/cand-r8 (données 5d5dfecb6a2c) sur la version 1.60.1.70374 r7

## Contenu des règles installées

- `mechanics.json` : clé `values.route.cities` ajoutée : cartes de zone des six capitales (1453 Stormwind City,
  1454 Orgrimmar, 1455 Ironforge, 1456 Thunder Bluff, 1457 Darnassus, 1458 Undercity), certitude `probable`,
  registre C6 ; RTE8.
- `origins.json` : règle d'origine `manuel` de `/values/route.cities`.
- `classes.json` : clés de talents renommées rétablies par l'installation (comme à chaque révision), aucune valeur
  changée.
