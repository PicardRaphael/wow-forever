# data: 1.60.1.70888 r6 → r7

Candidate : `<cache>/candidates/1.60.1.70888` (données ffb2142ffa84).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 2 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 3 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 0 |
| règle de lecture dépassée (talent gardé, à relire, certitude suppose, hors des calculs) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"bfda32b2b264"` | `"d693ad4c548e"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |
| pets.json | * | `"b387f915b4d1"` | `"cf4787da250e"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"0c17515f8ccf"` | `"eff5b26b2cec"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 6 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (2)

Provenance · version 1.60.1.70888 r6 · données 87f896634ce7 · générée 2026-11-11T15:53:49Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.70888 (données ffb2142ffa84) sur la version 1.60.1.70888 r6

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
