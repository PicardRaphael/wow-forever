# data: 1.60.1.70959 r1 → r2

Candidate : `<cache>/candidates/1.60.1.70959` (données df0b65889eef).

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
| classes.json | * | `"eeb46f07fe70"` | `"e7729c05365a"` | replaced_file | Client 1.60.1.70959 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"6a90d87a9129"` | `"e3416213c7da"` | replaced_file | Client 1.60.1.70959 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 1 ; source observation ; certitude certain)

## Champs ajoutés

- spells.json : source (16)
- talents.json : source (53)

Provenance · version 1.60.1.70959 r1 · données 529368acb3b6 · générée 2026-11-20T08:37:02Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.70959 (données df0b65889eef) sur la version 1.60.1.70959 r1

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
| Hunter | dropped_nodes | 105003 reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.28.20261116 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4f8aa5a9b366) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) à la rangée 4, colonne 4 ; absent de l'arbre en jeu : relevé en jeu de l'utilisateur du 2026-10-08 (fenêtre des talents du Chasseur, arbre Marksmanship : Improved Stings affiché, Improved Serpent Sting absent) |
| Hunter | parked_nodes | improvedSerpentSting talents_forever | Talents Forever 0.38.28.20261116 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4f8aa5a9b366) | Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) |
| Hunter | parked_nodes | improvedSerpentSting reason | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.28.20261116 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4f8aa5a9b366) à la rangée 4, colonne 4 : question ouverte à créer | garé hors du canevas (PosY 39300 : dix fois la grille), non confirmé par Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) à la rangée 4, colonne 4 : question ouverte à créer |
| Hunter | parked_nodes | improvedSerpentSting question | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.28.20261116 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4f8aa5a9b366) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). | Hunter : Improved Serpent Sting (improvedSerpentSting, nœud 105003) est-il dans l'arbre en jeu ? Le client le garde hors du canevas (PosY 39300, dix fois la grille ; rangée 4, colonne 4 une fois corrigé) et Talents Forever 0.38.28.20261119 (Data.lua build 1.60.1.70755, généré le 2026-11-15, empreinte 4233cc4fa1c1) ne le confirme pas. Test : arbre de la classe en jeu ; réponse dans decode_rules.json (observed_absent ou observed_positions). |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.70959 garde la priorité
