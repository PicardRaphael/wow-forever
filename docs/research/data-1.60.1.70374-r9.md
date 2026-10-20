# data: 1.60.1.70374 r8 → r9

Candidate : `~/AppData/Local/Temp/claude/C--Users-rapha-Documents-wow-forever/e023bd1e-0fc5-48fe-8864-2e5448fc288b/scratchpad/cand-r9` (données 793298201276).

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
| règles de lecture ou d'origine, valeurs écrites à la main (decode_rules.json, origins.json, mechanics.json du dépôt) | 2 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"e49cb0fbb03f"` | `"3e99fc9256bd"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |
| races.json | * | `"0ca45dd19953"` | `"0cb62fe0bf9f"` | replaced_file | Client 1.60.1.70374 : fichier décodé par forever decode (candidate) | certain |

## Règles et valeurs écrites à la main

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| decode_rules.json | * | `"de795d5e3452"` | `"d984c8a55319"` | rules | règles de la tranche (decode_rules.json du dépôt, lu par forever decode) | certain |
| origins.json | * | `"759273c8ac60"` | `"4b0bcbfe8976"` | rules | règles de la tranche (origins.json du dépôt, lu par forever decode) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 8 ; source observation ; certitude certain)

## Champs ajoutés

- spells.json : source (15)
- talents.json : source (54)

Provenance · version 1.60.1.70374 r8 · données 20e8c3403bb4 · générée 2026-10-20T12:59:18Z · fraîcheur fresh · certitude certain · registre 76/147 · hypothèses : candidate ~/AppData/Local/Temp/claude/C--Users-rapha-Documents-wow-forever/e023bd1e-0fc5-48fe-8864-2e5448fc288b/scratchpad/cand-r9 (données 793298201276) sur la version 1.60.1.70374 r8

## Contenu des règles installées
- `decode_rules.json` : `rank_variables.wintersChill` selon la forme de l'infobulle (4 variables avant 70450, 3
  après) ; `target_auras.winters_chill` avec son aura de repli 271 (Cone of Cold) et sa sorte ; `talent_models`
  (Arcane Blast, Missile Barrage, Fire Power, Winter's Chill) ; `racial_values` crit (Ruthless, Savage), haste (Wind
  Blessed), eureka_* (Eureka!) ; `spells` et `new_spells` (Frost Blast, Arcane Wrath) ; `frozen_mult` (Ice Lance lu
  dans le talent iceLance) ; `effects.aura_decrease_speed`.
- `origins.json` : multiplicateur d'Ice Lance d'origine `client` (plus `manuel`) ; champs des sorts nouveaux
  `client`, règle anticipée (valeurs à venir avec 70450) ; nouvelles clés des règles de lecture en `parametre`.
- Fichiers décodés remplacés, aucune valeur des moteurs changée tant que le bloc B ne les lit pas : `races.json`
  (Gnome : Eureka! 15 s, recharge 120 s, coût −10 %, dégâts +10 % ; Skyborne : hâte de Wind Blessed 1 %),
  `classes.json` (version de Talents Forever citée dans les notes du Chasseur).
