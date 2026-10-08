# data: 1.60.1.70245 r5 → r6

## Relevés en jeu du 2026-10-08 (décision 210)

Révision demandée par l'utilisateur le 2026-10-08 après ses relevés en jeu (certitude certain), choix des règles le
même jour :

- **CLS3** : Improved Serpent Sting absent de l'arbre du Chasseur (Marksmanship affiche Improved Stings, nœud 110870,
  déjà décodé). Le nœud 105003 du client est rangé à l'ordonnée 39300 (dix fois la grille) ; la règle du zéro en trop
  le replaçait en rangée 4. Écarté par `observed_absent` (`decode_rules.json`) : `dropped_nodes` du Chasseur, raison
  « absent de l'arbre en jeu » et source.
- **DON5** : Intimidation exige Bestial Swiftness. Le client porte deux arêtes suffisantes en sens contraires entre
  Intimidation et Bestial Wrath ; celle de Bestial Wrath vers Intimidation est circulaire (Bestial Wrath n'a
  qu'Intimidation pour prérequis) et est écartée (`circular_sufficient_edges`, `dropped_edges` du Chasseur).
  Intimidation garde un seul prérequis (`prereq` renseigné).
- **CLS1** : Improved Life Tap (Affliction, rangée 1, colonne 1) et Amplify Curse (rangée 3, colonne 3) placés par
  `observed_positions` ; colonnes concordantes avec le client ; `tier_community` et `unresolved` retirés, plus aucun
  nœud non résolu.
- Champ nouveau `dropped_edges` dans chaque classe (vide hors Chasseur).

## Nœuds garés hors du canevas (décision 211)

Demande de l'utilisateur du 2026-10-08 : la règle du zéro en trop ne replace plus jamais un nœud en silence. Un nœud
dont une coordonnée vaut dix fois une valeur de la grille n'est replacé à la position corrigée que si Talents Forever
installé le porte au même arbre, même sort, même rangée et même colonne (position `probable`) ; sinon il est garé,
écarté (`dropped_nodes`), listé dans `parked_nodes` avec la question à ouvrir dans `docs/OPEN_QUESTIONS.md`, jusqu'à
un relevé en jeu (`observed_absent`, `observed_positions`). Règle `parked_nodes` de `decode_rules.json` ; sans elle
(versions antérieures), l'ancienne règle s'applique, pour que leurs décodages restent reproductibles.

- Seul cas des neuf arbres : Improved Serpent Sting (Chasseur, nœud 105003, ordonnée 39300). Talents Forever 0.37.1
  ne le porte pas : **garé** ; le relevé en jeu du 2026-10-08 (`observed_absent`) répond à la question, qui n'est
  donc pas rouverte (CLS3 résolue). Raison de son écart : garé, puis absent de l'arbre en jeu.
- Champ nouveau `parked_nodes` dans chaque classe (vide hors Chasseur) ; note du fichier mise à jour.
- `talents.json` (moteurs du Mage) : un talent sur un nœud garé arrête le décodage (`check_mage_not_parked`) ; aucun
  nœud garé dans l'arbre du Mage.

## Chemin suivi

- Faite d'abord en r5 et r6 sur une branche partie de r4 ; la veille a installé entre-temps sa r5 (6 correctifs du
  serveur, `DBCache.bin` du 2026-10-08) sur `main`. Les deux installations de la branche ont été abandonnées et
  refaites ici en une seule révision sur la r5 de la veille (seules les règles de `decode_rules.json` et leurs
  origines dans `origins.json` ont été reportées à la main).
- Candidate : `forever decode --version 1.60.1.70245 --hotfixes --dbcache <copie de DBCache.bin, sha256
  6bf9bc559c0c…, poussée la plus haute 112486> --out <cache>/candidates/1.60.1.70245-fa1-r6`, hors ligne, le même
  `DBCache.bin` que la r5 de la veille (aucun correctif perdu). Talents Forever 0.37.1 lu sur disque (empreinte de
  `Data.lua` `4f5f53571fb7`). Aucun correctif du serveur de ce `DBCache.bin` ne touche les nœuds, entrées, définitions
  et arêtes en cause (Improved Serpent Sting, Improved Stings, Intimidation, Bestial Swiftness, Bestial Wrath,
  Improved Life Tap, Amplify Curse).
- Installation d'essai dans une copie de préparation : aucun refus ; valeurs écrites à la main : gardées 153,
  réappliquées 0, remplacées 0, perdues 0 ; renommage du Mage (`hotStreak`, clé du client `heatingUp`) réappliqué par
  `forever install`.
- `classes.json` ne change que pour le Chasseur et le Démoniste, les champs nouveaux `dropped_edges` et `parked_nodes`
  de chaque classe, la note des positions hors grille et des dates de lecture du `DBCache.bin` (Guerrier).
- Entrées des moteurs : `mage_build` et `mage_leveling` **identiques** (aucun moteur qui calcule n'est touché) ;
  `pvp_dr` différent sur `classes.json`, fiches recopiées du client, sans rejeu. Le contrôle de légalité
  (`forever/engine/talents.py`, code inchangé) refuse désormais Intimidation sans Bestial Swiftness.
- Puis `forever install --yes` (r6), `forever manifest --update`.

Candidate : `<cache>/candidates/1.60.1.70245-fa1-r6` (données 52eb13a6b993).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 1 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 1 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"36cc712408dc"` | `"fbeb64903546"` | replaced_file | Client 1.60.1.70245 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 5 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (1)

Provenance · version 1.60.1.70245 r5 · données 7e05c843de4b · générée 2026-10-08T08:02:17Z · fraîcheur fresh · certitude certain · registre 54/129 · hypothèses : candidate <cache>/candidates/1.60.1.70245-fa1-r6 (données 52eb13a6b993) sur la version 1.60.1.70245 r5
