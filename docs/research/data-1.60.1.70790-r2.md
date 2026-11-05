# data: 1.60.1.70790 r1 → r2

Candidate : `<cache>/candidates/1.60.1.70790` (données 66eb8a814319).

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
| classes.json | * | `"65a5c48b4c96"` | `"8b4c1da13e1b"` | replaced_file | Client 1.60.1.70790 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"b79c9d9a04ab"` | `"d935abb692b1"` | replaced_file | Client 1.60.1.70790 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 1 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (2)

Provenance · version 1.60.1.70790 r1 · données 2bc45f0f3497 · générée 2026-11-05T14:28:03Z · fraîcheur fresh · certitude certain · registre 76/148 · hypothèses : candidate <cache>/candidates/1.60.1.70790 (données 66eb8a814319) sur la version 1.60.1.70790 r1

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
| Hunter | dropped_nodes | 105003 reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.15 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte a01f7e5eca58) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.16.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte bf4ba19fe238) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) |
| Hunter | parked_nodes | improvedSerpentSting talents_forever | Talents Forever 0.38.15 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte a01f7e5eca58) | Talents Forever 0.38.16.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte bf4ba19fe238) |
| Hunter | parked_nodes | improvedSerpentSting reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.15 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte a01f7e5eca58) à la rangée 4, colonne 4 : question ouverte à créer | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.16.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte bf4ba19fe238) à la rangée 4, colonne 4 : question ouverte à créer |
| Hunter | parked_nodes | improvedSerpentSting question | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.15 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte a01f7e5eca58) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.16.20261105 (Data.lua build 1.60.1.70755, généré le 2026-11-04, empreinte bf4ba19fe238) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.70790 garde la priorité
