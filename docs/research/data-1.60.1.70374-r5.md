# data: 1.60.1.70374 r4 → r5

Candidate : `<cache>/candidates/1.60.1.70374` (données 94a88505c16e).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 1 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 2 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine nouvelles (decode_rules.json, origins.json du dépôt, lues par forever decode) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"2891df083903"` | `"c003e8f0ba5c"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"49e9a795c4d1"` | `"3b8a4bec451b"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 4 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (1)

Provenance · version 1.60.1.70374 r4 · données 026f29bc25bd · générée 2026-10-15T09:14:30Z · fraîcheur fresh · certitude certain · registre 75/146 · hypothèses : candidate <cache>/candidates/1.60.1.70374 (données 94a88505c16e) sur la version 1.60.1.70374 r4

## Report à la main

- gardé : 172
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_build : identiques
- mage_leveling : identiques
- pvp_dr : identiques

## Valeurs changées

Aucune valeur changée dans les entrées des moteurs.

## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (tenue).
