# DON13 — nœuds des nouveaux talents du Guerrier, cinq témoins (T08d, 2026-10-06)

Lecture seule, sans réseau, avec le code du projet (`read_dbcache`, dispositions WoWDBDefs du commit épinglé
`d3722486`, qui a un bloc `1.60.1.70235` pour les dix tables utiles). Arbre du Guerrier : TraitTreeID 1117.
Agrégats et identifiants seulement : aucun contenu d'addon recopié.

| Talent | (a) `DBCache.bin` 70170 = r4 installée | (b) tables de wago 70235 seules | (c) `DBCache.bin` 70235 + tables 70235 | (d) Talents Forever 0.37.1 | (e) Forever Companion |
| --- | --- | --- | --- | --- | --- |
| Lingering Rage (sort 1323964) | nœud 110857, Fury r2 c2, 5 rangs | absent | nœud 110857 | nœud 113564 | Fury r2 c2, 5 rangs |
| Furious Precision (1323963) | nœud 105953, Fury r3 c1, 3 rangs | absent | nœud 105953 | nœud 113565 | Fury r3 c1, 3 rangs |
| Gore Drinker (1323967) | nœud 113569, Fury r6 c3, 2 rangs | absent | nœud 113569 | nœud 113566 | Fury r6 c3, 2 rangs |
| Iron Will (12962) | nœud 113570, Protection r1 c3, 5 rangs | nœud 110857, à une place de Fury | nœud 113570 | nœud 110857 | Protection r1 c3, 5 rangs |

Sources : (a) `<cache>/dbcache/70170/DBCache.bin` et `forever/data/1.60.1.70170/classes.json` (concordants) ;
(b) `<cache>/wago/1.60.1.70235/enUS/` (Trait*, SpellName) ; (c) archive `<cache>/dbcache/70235/DBCache.bin`
(sha256 `90a83962…`) et sa copie antérieure (`c38deba0…`), même résultat ; (d) `TalentsForeverBook/Data.lua`
(build déclaré 1.60.1.70170, généré le 2026-10-04, `codeVersion` 6) ; (e) `ForeverCompanion/Data/Talents.lua`
(`dataVersion` 79, 2026-10-05), sans nœud.

## Constats

- **Les tables de wago de 70235 ne portent pas la refonte** : 46 des 47 CSV enUS sont identiques octet pour octet à
  ceux de 70170 ; seul `PlayerExpectedStat.csv` change, par son en-tête (`HPPerStamina`, bloc I). Les nœuds
  113564 à 113570 et les sorts 1323963, 1323964 et 1323967 en sont absents.
- **La refonte vient seulement des correctifs du serveur** (poussée 112347) : le `DBCache.bin` de 70235 porte les
  mêmes 92 entrées Trait* que celui de 70170, octet pour octet. Aucune poussée postérieure (112369 à 112426) ne touche
  une table Trait* résolue ; un hachage de table de la poussée 112426 (`0xc842493a`) reste non résolu.
- **Talents Forever diverge sur les quatre nœuds** (noms, places, rangs, sorts et prérequis identiques) : 113564 à
  113566 suivent le dernier nœud des tables de base (113563) et ne sont connus d'aucune table ni d'aucun correctif ;
  Iron Will y garde 110857, que le client corrigé attribue à Lingering Rage.

## Conclusion proposée (règle du plan : le client du build joué fait foi, (b) recouvert par (c))

(c) fait foi : Lingering Rage 110857, Furious Precision 105953, Gore Drinker 113569, Iron Will 113570, soit
exactement la révision 4 de 70170 ; l'installation de 70235 ne change rien pour DON13. Règle pour FA1 : exporter les
nœuds du client corrigé, jamais ceux de Talents Forever, tant que l'addon décrit des nœuds que le client ignore.

Reste incertain : ce que l'export `/tf` encode (nœud, place ou table interne de l'addon) ; contrôle en jeu proposé,
jamais exigé : apprendre un des quatre talents, puis exporter le code par `/tf`.
