# data: 1.60.1.70124 r3 → r4

Candidate : `<cache>/candidates/1.60.1.70124` (données ef0975d18392).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 69 |
| fichier ajouté (décodé du client) | 1 |
| fichier remplacé (décodé du client) | 0 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 1 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 11 |
| hors règles (refusé) | 0 |

## Valeurs changées

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| spell_scaling.json | auras ignite · cumulative | — | `1` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras ignite · duration_ms | — | `4000` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras ignite · period_ms | — | `2000` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras ignite · spell_id | — | `412538` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras winters_chill · duration_ms | — | `15000` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras winters_chill · max_stacks | — | `5` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras winters_chill · pct_per_stack | — | `2` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras winters_chill · schools.0 | — | `"frost"` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras winters_chill · source_spell_id | — | `11180` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras winters_chill · spell_id | — | `12579` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |
| spell_scaling.json | auras winters_chill · talent | — | `"wintersChill"` | value | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| character_scaling.json | * | — | `"e26a43ce3c26"` | added_file | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 20 (reporté de la révision 3 ; source plafond de niveau de la bêta de Forever (niveau 30 annoncé ensuite) : docs/research/community-builds-mage.md (recherche du 2026-09-28) ; tout build au-delà n'est pas vérifiable en jeu avant la sortie (décision 89) ; certitude probable)

## Champs ajoutés

- spells.json : source (15)
- talents.json : source (54)

Provenance · version 1.60.1.70124 r3 · données 34fde12f701e · générée 2026-10-01T09:13:38Z · fraîcheur fresh · certitude certain · registre 41/113 · hypothèses : candidate <cache>/candidates/1.60.1.70124 (données ef0975d18392) sur la version 1.60.1.70124 r3
