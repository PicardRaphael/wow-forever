# data: 1.60.1.70170 r3 → r4

Candidate : `<cache>/candidates/1.60.1.70170-t08c-v2` (données 9733ec20a0ac).

| Règle | Changements |
| --- | --- |
| changement confirmé (confirmed_changes.json) | 0 |
| valeur du client là où le dépôt avait null | 0 |
| certitude du talent | 0 |
| champ ajouté | 0 |
| champ retiré | 0 |
| métadonnée | 69 |
| fichier ajouté (décodé du client) | 0 |
| fichier remplacé (décodé du client) | 1 |
| fichier retiré (retired_files) | 0 |
| état du jeu (plafond de la bêta, meta.json game_state) | 0 |
| valeur d'un fichier décodé (spell_scaling.json, character_scaling.json) | 0 |
| hors règles (refusé) | 0 |

## Fichiers

| Fichier | Chemin | Avant | Après | Règle | Source | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| classes.json | * | `"fc9644dfd0cd"` | `"27ce2efac5a1"` | replaced_file | Client 1.60.1.70170 : fichier décodé par forever decode (candidate) | certain |

## État du jeu

- plafond de la bêta : 30 (reporté de la révision 3 ; source observation ; certitude certain)

## Champs ajoutés

- spells.json : source (15)
- talents.json : source (54)

## Motif (T08c)

Valeurs des correctifs du serveur du 2026-10-02, lues dans `Cache/ADB/enUS/DBCache.bin` du client 1.60.1.70170 (copie
gardée le 2026-10-05 avant que le client, passé en 70205, ne le remplace : 7 300 286 octets, sha256 `2f2a6ba10c82…`) et
décodées avec les dispositions de WoWDBDefs (commit `1d356b44c798`, toutes validées contre les CSV du build) :
poussées 112323, 112347 et 112349, 175 enregistrements appliqués dont 141 qui changent une valeur, 49 entités
touchées, 712 valeurs d'origine `correctif_serveur` (`origins.json`, poussées et date vue par le client :
2026-10-02 08:00). Détail : `sources.json`, bloc `hotfixes` ; `uv run forever hotfixes --values` ; décision 174.
Seul `classes.json` est remplacé ; les métadonnées (`source.read_at`) des talents et sorts du Mage suivent la date de
lecture de la candidate.

## Rejeu des builds de T05 : non nécessaire (preuve par les entrées)

Le moteur du Mage lit, pendant les rejeux de T05 (relevé instrumenté de `VersionData.read_json` et de la lecture des
sorts du Mage dans `classes.json`, un cas par contexte : leveling 20 et 30, donjon, raid, PvP champ de bataille et
monde ouvert au niveau 20), exactement : `character_scaling.json`, `decode_rules.json`, `leveling.json`,
`mechanics.json`, `meta.json`, `monsters.json`, `races.json`, `respec.json`, `spell_scaling.json`, `spells.json`,
`talents.json` et `classes.json` (partie `classes.Mage.spells` seulement). Comparaison par empreinte entre la
révision 3 (dernier commit) et la révision 4 installée :

```text
character_scaling.json : identique (sha256 6344e821e1b88dc7)
decode_rules.json : identique (sha256 a76fc0fdf642d836)
leveling.json : identique (sha256 a649d83137fb9dcf)
mechanics.json : identique (sha256 d714d34778fc004a)
meta.json : octets différents (5912993c25f5 -> c0c1d64aa8a4), 2 feuille(s) ; champs : ['carried_from', 'carried_to']
monsters.json : identique (sha256 497bf48c4b1fedfc)
races.json : identique (sha256 0e7be5b1c572bafb)
respec.json : identique (sha256 604a4f8a135a8197)
spell_scaling.json : identique (sha256 e3c862eef05241cf)
spells.json : octets différents (5b43bb3e4179 -> 7e55347f0423), 15 feuille(s) ; champs : ['read_at']
talents.json : octets différents (92452a4f3426 -> 2c8e420280da), 54 feuille(s) ; champs : ['read_at']
classes.json, classes.Mage : identique (sha256 canonique 4c956da05c8f53c4 / 4c956da05c8f53c4)
classes.json, classes.Mage.spells : identique
```

Les trois fichiers aux octets différents ne changent que des métadonnées que le moteur ne lit jamais :
`source.read_at` (date de lecture de la candidate) dans `talents.json` et `spells.json`, et `carried_from` et
`carried_to` (plafond reporté de la révision 3) dans `meta.json`, dont le moteur ne lit que
`game_state.beta_level_cap.value` (inchangé, 30). Mêmes entrées, mêmes sorties : les recommandations de T05 sont
inchangées sans rejeu (accord de l'utilisateur du 2026-10-05 ; le rejeu lancé plus tôt avait été arrêté par Claude
Code faute de mémoire).

## Contrôle du Guerrier face à la note officielle du 01/10

Aucun nœud du Guerrier non résolu, dispositions toutes validées. Retrouvé dans l'arbre décodé :
- Fureur : nouveaux talents Lingering Rage (rangée 2), Furious Precision (rangée 3, colonne 1, à la place de Boundless
  Rage), Gore Drinker (rangée 6, colonne 3, 2 rangs) ; Improved Cleave retiré ; Flurry exige Death Wish au lieu
  d'Enrage ; Improved Berserker Rage en rangée 5 ; Berserker Rage au niveau 30 ; descriptions de Booming Voice,
  Unbridled Wrath, Blood Craze, Raging Blows et Dual Wield Specialization corrigées.
- Protection : Iron Will (nouveau nœud 113570), Anticipation, Improved Bloodrage, Improved Revenge, Improved Disarm et
  Improved Shield Bash déplacés ; Toughness retiré.
- Dans les correctifs, absent de la note : Precision retiré ; Vanguard, Bastion et Focused Rage déplacés ; prérequis
  de Last Stand et de Bloodthirst retirés (arêtes supprimées) ; description de Piercing Howl.
- Hors des données décodées : dégâts de Whirlwind et Bloodthirst (moteur du Guerrier, GU1).

## Recoupement avec Talents Forever

`docs/research/guerrier-T08c-talents-forever.md` : Talents Forever 0.37.1 (données du 2026-10-04) porte la même
refonte (noms, rangées, colonnes, rangs, sorts) ; quatre identifiants de nœud diffèrent (Lingering Rage, Furious
Precision, Gore Drinker, Iron Will) : question DON13, tranchée à l'installation de 1.60.1.70205.

Provenance · version 1.60.1.70170 r3 · données e7a5c1156df9 · générée 2026-10-05T15:43:58Z · fraîcheur fresh · certitude certain · registre 54/129 · hypothèses : candidate <cache>/candidates/1.60.1.70170-t08c-v2 (données 9733ec20a0ac) sur la version 1.60.1.70170 r3
