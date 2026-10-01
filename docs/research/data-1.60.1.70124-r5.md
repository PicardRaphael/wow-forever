# data: 1.60.1.70124 r4 → r5

Candidate : `<cache>/candidates/1.60.1.70124` (données 3c7220a7cb76).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 0 |
| fichier ajouté (décodé du client) | 1 |
| fichier remplacé (décodé du client) | 0 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| pets.json | * | — | `"8fa536c74d27"` | added_file | Client 1.60.1.70124 : fichier décodé par forever decode (candidate) | certain |

## CH0 : familiers du Chasseur (accord de l'utilisateur du 2026-10-01)

- **Accès réseau** (D1, un accord par accès, `forever fetch --version 1.60.1.70124`) : `CreatureFamily` (enUS, frFR),
  `UiMap` (enUS, frFR), `Creature` (enUS, frFR : premier essai expiré au délai de 30 s, relancé une fois avec
  `--timeout 300` sur accord), `CreatureDifficulty`, `ItemPetFood` (enUS, frFR), `SpellTargetRestrictions`. Aucun
  autre appel.
- **Tables utilisées** (`decode_rules.json` `pet_tables`) : `CreatureFamily` (familles, masque de régime, lignes de
  compétence, noms français), `ItemPetFood` (noms des régimes), `UiMap` (cartes, parents, continents, noms
  français), plus les tables de sorts déjà en cache.
- **Tables téléchargées mais inutilisables** : `Creature` et `CreatureDifficulty` ne portent que 179 PNJ (mascottes
  de compagnie pour l'essentiel), aucun avec une famille, aucun drapeau d'apprivoisement lisible : le recoupement de
  la famille des bêtes par le client est impossible ; la famille reste celle de Forever Bestiary.
- **`SpellTargetRestrictions`** : Tame Beast porte le type de cible (bête) mais `MaxTargetLevel` nul : la marge
  d'apprivoisement n'est pas dans le client et reste un relevé de joueurs (`pet_rules.json`, `suppose`).
- **`pets.json`** : 19 familles, 34 capacités (22 de famille, 10 générales, 2 passifs de vitesse), 162 rangs, 60
  cartes, 8 régimes, une ligne orpheline. Écarts internes au client listés dans `observations` (ligne « Pet -
  Crocilisk » contre « Crocolisk » de `CreatureFamily`, seconde ligne « Pet - Bat » visée par aucune famille, sorts
  sans niveau ou sans rang écartés, premier rang au-dessus de 1 pour Lava Breath, Pet Hardiness et Slower Attack).
  Le Renard partage le passif de famille du Loup (même sort) ; Core Hound a `PetTalentType` non nul.
- **`pet_rules.json`** (ajouté à la main, hérité par les versions suivantes) : 14 règles et un bug signalé par des
  joueurs, tirés du guide de Forever Bestiary 0.5.0, chacune avec sa source, sa date, sa certitude (`suppose`) et
  son entrée du registre (L1 à L12).
- **Recoupement** client ↔ Forever Bestiary ↔ Questie : `docs/research/familiers-recoupement.md`
  (`forever pets crosscheck --markdown`).

## État du jeu

- plafond de la bêta : 20 (reporté de la révision 4 ; source plafond de niveau de la bêta de Forever (niveau 30 annoncé ensuite) : docs/research/community-builds-mage.md (recherche du 2026-09-28) ; tout build au-delà n'est pas vérifiable en jeu avant la sortie (décision 89) ; certitude probable)

Provenance · version 1.60.1.70124 r4 · données 638d9da1a356 · générée 2026-10-01T16:44:07Z · fraîcheur fresh · certitude certain · registre 52/125 · hypothèses : candidate <cache>/candidates/1.60.1.70124 (données 3c7220a7cb76) sur la version 1.60.1.70124 r4
