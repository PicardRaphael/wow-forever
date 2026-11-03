# data: 1.60.1.70707 r2 → r3

Candidate : `<cache>/candidates/1.60.1.70707` (données 5e112a58dcc4).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 2 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 2 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"7d0310f3a9c2"` | `"00e386634327"` | replaced_file | Client 1.60.1.70707 : fichier décodé par forever decode (candidate) | certain |
| races.json | * | `"be29be2fd9d4"` | `"a462da211240"` | replaced_file | Client 1.60.1.70707 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 2 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (2)

Provenance · version 1.60.1.70707 r2 · données db6f386df442 · générée 2026-11-03T14:10:46Z · fraîcheur stale · certitude certain · registre 76/148 · hypothèses : candidate <cache>/candidates/1.60.1.70707 (données 5e112a58dcc4) sur la version 1.60.1.70707 r2

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
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.70707 garde la priorité
