# data: 1.60.1.70374 r6 → r7

Candidate : `~/AppData/Local/Temp/claude/C--Users-rapha-Documents-wow-forever/e023bd1e-0fc5-48fe-8864-2e5448fc288b/scratchpad/cand-r7` (données bd05b862fa7b).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 69 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 2 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 2 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"2891df083903"` | `"744ed85ced1c"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"3e060fc95bad"` | `"4a0a9a03c5ba"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |

## Règles et valeurs écrites à la main

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| origins.json | * | `"e0d7caaddad0"` | `"5e9c7cddfa9c"` | rules | règles de la tranche (origins.json du dépôt, lu par forever decode) | certain |
| mechanics.json | * | `"8cca0c06db9b"` | `"f6ce8d81ca1c"` | rules | valeurs écrites à la main de la tranche (mechanics.json du dépôt, hérité par forever decode) | probable |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 6 ; source observation ; certitude certain)

## Champs ajoutés

- spells.json : source (15)
- talents.json : source (54)

Provenance · version 1.60.1.70374 r6 · données dc4b60dedda6 · générée 2026-10-19T06:29:23Z · fraîcheur fresh · certitude certain · registre 76/147 · hypothèses : candidate ~/AppData/Local/Temp/claude/C--Users-rapha-Documents-wow-forever/e023bd1e-0fc5-48fe-8864-2e5448fc288b/scratchpad/cand-r7 (données bd05b862fa7b) sur la version 1.60.1.70374 r6

## Contenu des règles installées

- `mechanics.json` : clé `values.route.start_zones` ajoutée (table race → zone et sous-zone de départ donnée par
  l'utilisateur le 2026-10-16, décision 283, certitude `probable`). Elle était déjà dans le dépôt (commit `0c3416e`,
  manifeste réécrit à la main) ; cette révision la journalise (décision 284). `values.route.filters` (bloc 1a) n'a
  pas changé.
- `origins.json` : règle d'origine `manuel` de `/values/route.start_zones`.
- Hors règles, sans valeur de jeu changée : `quest_rewards.json` (2 quêtes vues de plus dans le dernier
  `questcache.wdb` archivé du build 70374) et `classes.json` (version de Talents Forever citée dans les notes du
  Chasseur, 0.38.2 → 0.38.6).
