# data: 1.60.1.70938 r7 → r8

Candidate : `<cache>/candidates/1.60.1.70938` (données ceb221a70f39).

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
| règle de lecture dépassée (talent gardé, à relire, certitude suppose, hors des calculs) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"69b60a773f3d"` | `"06c932501065"` | replaced_file | Client 1.60.1.70938 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"a682283231d2"` | `"5d1252323866"` | replaced_file | Client 1.60.1.70938 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 7 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (2)

Provenance · version 1.60.1.70938 r7 · données 4ddbd99483f3 · générée 2026-11-16T16:18:07Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.70938 (données ceb221a70f39) sur la version 1.60.1.70938 r7

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : identiques
- pvp_dr : différentes

## Valeurs changées

fiches PvP : Warrior, 1 sort modifié.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| Warrior | sort Berserker Rage | pvp cc_break mechanics n°3 | null | 30 |
| Warrior | sort Berserker Rage | pvp cc_break mechanic_names n°3 | null | sapped |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.70938 garde la priorité
