# data: 1.60.1.70374 r3 → r4

Candidate : `<cache>/candidates/1.60.1.70374` (données 9190d1dc5663).

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
| règles de lecture ou d'origine nouvelles (decode_rules.json, origins.json du dépôt, lues par forever decode) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"508668e65d09"` | `"c003e8f0ba5c"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"8da2ad6a78a4"` | `"49e9a795c4d1"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 3 ; source observation ; certitude certain)

## Champs ajoutés

- spells.json : source (15)
- talents.json : source (54)

Provenance · version 1.60.1.70374 r3 · données 426ab7462efe · générée 2026-10-15T07:58:08Z · fraîcheur fresh · certitude certain · registre 75/146 · hypothèses : candidate <cache>/candidates/1.60.1.70374 (données 9190d1dc5663) sur la version 1.60.1.70374 r3

## Report à la main

- gardé : 172
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_build : identiques
- mage_leveling : identiques
- pvp_dr : différentes

## Valeurs changées

fiches PvP : Hunter, 2 autres valeurs changées.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| Hunter | dropped_nodes | 105003 reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.1 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte 976540e388aa) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.2 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte c59092d8bd77) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) |
| Hunter | parked_nodes | improvedSerpentSting talents_forever | Talents Forever 0.38.1 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte 976540e388aa) | Talents Forever 0.38.2 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte c59092d8bd77) |
| Hunter | parked_nodes | improvedSerpentSting reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.1 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte 976540e388aa) à la rangée 4, colonne 4 : question ouverte à créer | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.2 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte c59092d8bd77) à la rangée 4, colonne 4 : question ouverte à créer |
| Hunter | parked_nodes | improvedSerpentSting question | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.1 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte 976540e388aa) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.2 (Data.lua build 1.60.1.70291, généré le 2026-10-08, empreinte c59092d8bd77) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (tenue).
