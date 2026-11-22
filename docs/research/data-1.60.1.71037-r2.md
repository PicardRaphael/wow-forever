# data: 1.60.1.71037 r1 → r2

Candidate : `<cache>/candidates/1.60.1.71037` (données bf6f5c82791a).

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
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 0 |
| règle de lecture dépassée (talent gardé, à relire, certitude suppose, hors des calculs) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"6e7e6efae9af"` | `"c881cbf4e171"` | replaced_file | Client 1.60.1.71037 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"b56655e2fd9b"` | `"9064139ebcdc"` | replaced_file | Client 1.60.1.71037 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 1 ; source observation ; certitude certain)

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.71037 r1 · données 46c1ff824023 · générée 2026-11-22T11:05:28Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.71037 (données bf6f5c82791a) sur la version 1.60.1.71037 r1

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : identiques
- pvp_dr : différentes

## Valeurs changées

fiches PvP : Hunter, 2 autres valeurs changées.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| Hunter | dropped_nodes | 105003 reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.31.20261121 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte abfd62c6a7ab) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) |
| Hunter | parked_nodes | improvedSerpentSting talents_forever | Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) | Talents Forever 0.38.31.20261121 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte abfd62c6a7ab) |
| Hunter | parked_nodes | improvedSerpentSting reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) à la rangée 4, colonne 4 : question ouverte à créer | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.31.20261121 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte abfd62c6a7ab) à la rangée 4, colonne 4 : question ouverte à créer |
| Hunter | parked_nodes | improvedSerpentSting question | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.30.20261120 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte ef435d859bf8) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.31.20261121 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte abfd62c6a7ab) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.71037 garde la priorité
