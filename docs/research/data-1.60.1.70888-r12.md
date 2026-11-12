# data: 1.60.1.70888 r11 → r12

Candidate : `<cache>/candidates/1.60.1.70888` (données 3beb80f7e559).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 2 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 4 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 0 |
| règle de lecture dépassée (talent gardé, à relire, certitude suppose, hors des calculs) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"8f7d5c2e52a7"` | `"88891edfb39b"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |
| pvp_items.json | * | `"78a42882354c"` | `"32ef46e5d7ce"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |
| pets.json | * | `"53f6b8705e5b"` | `"39f606b9af4c"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"d56bb34917f8"` | `"1a101684d577"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 11 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (2)

Provenance · version 1.60.1.70888 r11 · données 24d09eb30e58 · générée 2026-11-12T08:18:55Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.70888 (données 3beb80f7e559) sur la version 1.60.1.70888 r11

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : identiques
- pvp_dr : identiques

## Valeurs changées

Aucune valeur changée dans les entrées des moteurs.

## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.70888 garde la priorité
