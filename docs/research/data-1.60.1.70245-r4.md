# 1.60.1.70245, révision 4 : origine des arbres de talents touchés par les correctifs (DON17)

Révision demandée par l'utilisateur le 2026-10-07, après la fusion de T08e : réécrire les règles `correctif_serveur`
d'`origins.json` avec la règle de la décision 208 (DON17), pour fermer l'angle mort relevé en fin de tranche (règles
de r3 écrites avant DON17).

## Chemin suivi

- Candidate : `forever decode --version 1.60.1.70245 --hotfixes --dbcache <cache>/dbcache/70245/DBCache.bin`, hors
  ligne (tables de wago et dispositions de WoWDBDefs du cache). Même `DBCache.bin` que r3 (sha256 `0a2ef77e28dd…`,
  poussée la plus haute 112457) : mêmes correctifs appliqués.
- Installation en révision dans une copie de préparation, puis report à la main, comme `forever update` : aucun
  refus, report de 152 valeurs écrites à la main sans écart (gardées 152, réappliquées 0, remplacées 0, perdues 0).
- Entrées des moteurs (`mage_build`, `mage_leveling`, `pvp_dr`) identiques ; aucune valeur `correctif_serveur` perdue.

## Changements

Aucune valeur de jeu ne change (`classes.json` identique hors métadonnées : seule la date de lecture du
`DBCache.bin` des entités annotées change).

Règles `correctif_serveur` de `classes.json` (poussée 112347) :

| Avant (r3) | Après (r4) |
| --- | --- |
| 25 talents du Guerrier nommés par position (`/classes/Warrior/trees/1/talents/<i>`, `/trees/2/talents/<i>`, `/trees/0/talents/14`) | Listes entières de Fury et de Protection (`/classes/Warrior/trees/1/talents`, `/trees/2/talents`), talent 14 d'Armes inchangé |
| `tree_checks` d'origine `client` | `/classes/Warrior/tree_checks/1` et `/2` en `correctif_serveur` |
| 24 sorts du Guerrier | inchangés |

Effet : une version nouvelle installée sans le `DBCache.bin` de son build (décision 207) qui perdrait la refonte des
arbres du Guerrier, même sans toucher un sort, garde l'attente « correctifs du serveur non relus ».

`verify --data` vert avant le commit ; CI de la branche `data/1.60.1.70245-r4` sous Ubuntu et Windows avant la
fusion.
