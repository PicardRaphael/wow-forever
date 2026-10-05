# Arbres de talents : forever face à Talents Forever (T08c)

Généré par `uv run python scripts/compare_talents_forever.py` (lecture locale, agrégats et écarts seulement ; rien de l'addon n'est recopié).

- Talents Forever : `Data.lua` build 1.60.1.70170, généré le 2026-10-04 (codes v6).
- forever : candidate 1.60.1.70170 avec les correctifs du serveur (poussées 112323, 112347, 112349), décodée le 2026-10-05.
- Champs comparés par nœud : nom, arbre, rangée, colonne, rangs, sort, prérequis.

| Classe | Talents forever | Talents TF | Identiques | Écarts (nœuds) | Seulement forever | Seulement TF |
| --- | --- | --- | --- | --- | --- | --- |
| DRUID | 52 | 52 | 52 | 0 | 0 | 0 |
| HUNTER | 51 | 50 | 49 | 1 | 1 | 0 |
| MAGE | 54 | 54 | 54 | 0 | 0 | 0 |
| PALADIN | 50 | 50 | 50 | 0 | 0 | 0 |
| PRIEST | 53 | 53 | 35 | 18 | 0 | 0 |
| ROGUE | 53 | 53 | 53 | 0 | 0 | 0 |
| SHAMAN | 50 | 50 | 34 | 16 | 0 | 0 |
| WARLOCK | 52 | 52 | 50 | 2 | 0 | 0 |
| WARRIOR | 52 | 52 | 48 | 1 | 3 | 3 |

Référence : version installée 1.60.1.70170 r3 (avant les correctifs du serveur) :

- HUNTER : 49 identiques, 1 nœud(s) en écart, 1 seulement forever, 0 seulement TF
- PRIEST : 35 identiques, 18 nœud(s) en écart, 0 seulement forever, 0 seulement TF
- SHAMAN : 34 identiques, 16 nœud(s) en écart, 0 seulement forever, 0 seulement TF
- WARLOCK : 50 identiques, 2 nœud(s) en écart, 0 seulement forever, 0 seulement TF
- WARRIOR : 36 identiques, 13 nœud(s) en écart, 4 seulement forever, 3 seulement TF

## Écarts

### HUNTER

- Nœuds seulement dans forever : 105003
- Champs en écart : prereq 1

| Nœud | Champ | forever | Talents Forever |
| --- | --- | --- | --- |
| 104964 | prereq | None | 104970 |

### PRIEST

- Champs en écart : tree 18

| Nœud | Champ | forever | Talents Forever |
| --- | --- | --- | --- |
| 105817 | tree | Shadow Magic | Shadow |
| 105818 | tree | Shadow Magic | Shadow |
| 105819 | tree | Shadow Magic | Shadow |
| 105820 | tree | Shadow Magic | Shadow |
| 105821 | tree | Shadow Magic | Shadow |
| 105823 | tree | Shadow Magic | Shadow |
| 105824 | tree | Shadow Magic | Shadow |
| 105825 | tree | Shadow Magic | Shadow |
| 105826 | tree | Shadow Magic | Shadow |
| 105827 | tree | Shadow Magic | Shadow |
| 105828 | tree | Shadow Magic | Shadow |
| 105829 | tree | Shadow Magic | Shadow |
| 105830 | tree | Shadow Magic | Shadow |
| 105831 | tree | Shadow Magic | Shadow |
| 105832 | tree | Shadow Magic | Shadow |
| 105833 | tree | Shadow Magic | Shadow |
| 110851 | tree | Shadow Magic | Shadow |
| 110854 | tree | Shadow Magic | Shadow |

### SHAMAN

- Champs en écart : tree 16

| Nœud | Champ | forever | Talents Forever |
| --- | --- | --- | --- |
| 104758 | tree | Elemental Combat | Elemental |
| 104759 | tree | Elemental Combat | Elemental |
| 104760 | tree | Elemental Combat | Elemental |
| 104761 | tree | Elemental Combat | Elemental |
| 104762 | tree | Elemental Combat | Elemental |
| 104763 | tree | Elemental Combat | Elemental |
| 104764 | tree | Elemental Combat | Elemental |
| 104765 | tree | Elemental Combat | Elemental |
| 104766 | tree | Elemental Combat | Elemental |
| 104767 | tree | Elemental Combat | Elemental |
| 104768 | tree | Elemental Combat | Elemental |
| 104769 | tree | Elemental Combat | Elemental |
| 104770 | tree | Elemental Combat | Elemental |
| 104771 | tree | Elemental Combat | Elemental |
| 104772 | tree | Elemental Combat | Elemental |
| 104773 | tree | Elemental Combat | Elemental |

### WARLOCK

- Champs en écart : tier 2

| Nœud | Champ | forever | Talents Forever |
| --- | --- | --- | --- |
| 105916 | tier | None | 3 |
| 105921 | tier | None | 1 |

### WARRIOR

- Nœuds seulement dans forever : 105953, 113569, 113570
- Nœuds seulement dans Talents Forever : 113564, 113565, 113566
- Même talent (nom, arbre, rangée, colonne, rangs, sort), autre nœud : Furious Precision (forever 105953, TF 113565), Lingering Rage (forever 110857, TF 113564), Gore Drinker (forever 113569, TF 113566), Iron Will (forever 113570, TF 110857)
- Champs en écart : col 1, name 1, spell 1, tier 1, tree 1

| Nœud | Champ | forever | Talents Forever |
| --- | --- | --- | --- |
| 110857 | name | Lingering Rage | Iron Will |
| 110857 | tree | Fury | Protection |
| 110857 | tier | 2 | 1 |
| 110857 | col | 2 | 3 |
| 110857 | spell | 1323964 | 12962 |
