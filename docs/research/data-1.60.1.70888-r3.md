# data: 1.60.1.70888 r2 → r3

Candidate : `<cache>/candidates/1.60.1.70888` (données 3db3cb84f9ec).

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
| classes.json | * | `"d7f97e779914"` | `"684db0293dee"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |
| pets.json | * | `"2c0be80e80bf"` | `"9f6e0f6ccd3a"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |
| quest_rewards.json | * | `"77f0e950f79c"` | `"1e268400ec62"` | replaced_file | Client 1.60.1.70888 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 2 ; source observation ; certitude certain)

## Champs ajoutés

- talents.json : source (2)

Provenance · version 1.60.1.70888 r2 · données 4958d44e2e8b · générée 2026-11-11T11:20:41Z · fraîcheur fresh · certitude certain · registre 80/152 · hypothèses : candidate <cache>/candidates/1.60.1.70888 (données 3db3cb84f9ec) sur la version 1.60.1.70888 r2

## Report à la main

- gardé : 174
- réappliqué : 0
- remplacé : 0
- perdu : 0

## Entrées des moteurs

- mage_leveling : identiques
- pvp_dr : différentes

## Valeurs changées

fiches PvP : Warlock, 2 talents modifiés.

| Classe | Entité | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| Warlock | talent Affliction Soul Siphon | desc | Increases the damage done or health drained by your Drain Life, Drain Soul, and Wrack spells by $s1% per each of your Corruption, Siphon Life, and Bane of Agony effects active on the target, up to a maximum increase of ${$m1*3}%. | Increases the damage done or health drained by your Drain Life, Drain Soul, and Wrack spells by $s1% per each of your other Affliction effects active on the target, up to a maximum increase of ${$m1*3}%. |
| Warlock | talent Affliction Wrack | desc | Tears the target apart from within for $d, inflicting $s1 Shadow damage every $t sec. While channeling, your Siphon Life, Corruption, and Bane of Agony effects on the target deal their periodic damage $s2% faster. | Tears the target apart from within, inflicting $s1 Shadow damage every $t sec and increasing the damage they take from your other Shadow damage over time effects by $s2% for $d. |


## Correctifs du serveur

Porte : lire ; correctifs du serveur lus avec la candidate.

Règle d'automatisme : écrire (décision 295 : installée d'elle-même, annulable).
- écart signalé : Paladin : position relevée pour un talent inconnu du client « improvedSealOfFury » ; ton observation de 1.60.1.70888 garde la priorité
