# T03 — Écarts client 1.60.1.70009 ↔ référence (à trancher)

Source : `forever diff 1.60.1.70009 <candidate>` sur les fixtures (tests `test_no_other_talent_difference`, `test_no_other_spell_difference`). Structure des 54 talents (clé, nom, arbre, palier, colonne, max, prérequis, ordre) : identique. 5 oracles FC-70009 : identiques. 95 rangs de sort sur 99 : identiques.

Pour chaque ligne : **B** = bogue du décodeur (je corrige le décodeur), **C** = vrai changement du client (entrée dans `confirmed_changes.json`).

## Groupe 1 — même variable, valeur différente (6 lignes)
Certitude de la référence : FC-69893 (rangs wowsims lus sur 69893).

| # | Talent | Champ | Client | Référence | Note |
| --- | --- | --- | --- | --- | --- |
| T13 | impact | ranks[2] | [7, 2] | [6] | courbe du client 3 / 7 / 10 |
| T14 | impact | ranks[3] | [10, 2] | [9] | idem |
| T16 | improvedScorch | ranks[2] | [67, 3, 30, 5] | [66] | courbe 33 / 67 / 100 |
| T18 | hotStreak | ranks[1] | [20, 25, 3] | [15, 25, 3] | `talents.json` porte déjà `duration_s: 20` et la note « durée de Hot Streak 20 s » : seul `ranks[0][0]` est resté à 15 |
| T23 | improvedBlizzard | ranks[2] | [25, 1.5] | [30] | courbe 15 / 25 / 40 |
| — | (les lignes T13, T14, T16, T23 ont aussi un écart de forme, groupe 2) | | | | |

## Groupe 2 — forme : sélection des variables (23 lignes)
Certitude de la référence : FC-69893. Mêmes valeurs du client ; wowsims a écrit en clair une constante que l'infobulle du client met en variable (ou l'inverse). Règle du plan : « toutes les variables de l'infobulle, dans l'ordre ».

| # | Talent | Rangs | Client (rang 1) | Référence (rang 1) | Cause |
| --- | --- | --- | --- | --- | --- |
| T1–T5 | arcaneConcentration | 1–5 | [2, 100] | [2] | « 100% » en clair chez wowsims (`$/10;12536s1`) |
| T6 | presenceOfMind | 1 | [] | [10] | l'infobulle du client écrit « 10 sec » en clair, aucune variable |
| T7–T11 | ignite | 1–5 | [8, 4] | [8] | « 4 sec » en clair (`$412538d`) |
| T12–T14 | impact | 1–3 | [3, 2] | [3] | « 2 sec » en clair (`$12355d`) |
| T15–T17 | improvedScorch | 1–3 | [33, 3, 30, 5] | [33] | « 3% … 30 sec … 5 » en clair (`$22959s1`, `$22959d`, `$22959u`) |
| T19–T21 | frostbite | 1–3 | [5, 5] | [5] | « 5 sec » en clair (`$12494d`) |
| T22–T24 | improvedBlizzard | 1–3 | [15, 1.5] | [15] | « 1.5 sec » en clair (`$12484d`) |
| T25–T29 | wintersChill | 1–5 | [20, 2, 15, 1] | [20, 1] | « 2% … 15 sec » en clair (`$12579s1`, `$12579d`), valeurs insérées au milieu |

Effet sur le moteur : `talent_value` lit les rangs par position. Parmi ces talents, seuls `ignite` et `arcaneConcentration` sont lus (`forever/engine/cast.py`), à l'indice 0, inchangé. `wintersChill` (indice 1 déplacé) et `presenceOfMind` (plus de valeur) ne sont lus nulle part dans `forever/engine/`.

Résolutions possibles :
- **A** : garder la règle du plan ; les 23 lignes deviennent des changements confirmés ; T08 adapte les indices s'il le faut.
- **B** : sélection des variables par talent dans `decode_rules.json` (donnée, pas code) pour reproduire la forme de la référence. Ne peut pas produire le `[10]` de Presence of Mind depuis un texte en clair : T6 resterait un changement confirmé.

## Groupe 3 — convention de niveau des sorts (9 lignes)
Certitude de la référence : `spells.json` certain (wowforevertalents.com), mais ces quatre rangs 1 viennent d'infobulles de talent.

| # | Sort | Champ | Client | Référence |
| --- | --- | --- | --- | --- |
| S1 | pyroblast | ranks[1].min | 100 | 95 |
| S2 | pyroblast | ranks[1].max | 132 | 125 |
| S3 | ice_lance | ranks[1].min | 28 | 26 |
| S4 | ice_lance | ranks[1].max | 33 | 30 |
| S5 | arcane_blast | ranks[1].min | 57 | 50 |
| S6 | arcane_blast | ranks[1].max | 66 | 58 |
| S7 | blast_wave | ranks[1].level | 30 | 36 |
| S8 | blast_wave | ranks[1].min | 153 | 148 |
| S9 | blast_wave | ranks[1].max | 185 | 178 |

Cause : tous les autres rangs de `spells.json` sont au niveau min(MaxLevel, 60) ; ces quatre rangs 1, issus d'un talent, ont été lus au niveau de base du sort. Évalué au niveau de base, le client redonne exactement la référence (mêmes chiffres que les oracles FC-70009 des talents). S7 : `SpellLevels.BaseLevel` 30 (MaxLevel 36) ; la référence met 36 au rang 1 comme au rang 2.

Résolutions possibles : garder `levels.spell_rank: max_capped` et confirmer S1–S9 ; ou une règle « rang de sort issu d'un talent évalué au niveau de base » (S1–S6, S8, S9 disparaissent ; S7 reste à trancher) — ce qui ratifie aussi la convention `levels` notée dans `sources.json`.

## Observations (pas des écarts)
- Mana relevé là où la référence a null : pyroblast r1 125, ice_lance r1 45, blast_wave r1 215 (Arcane Blast : coût en pourcentage, pas de mana fixe).
- `spellIds` : un seul sort par nœud dans le client ; 7 talents portent un autre sort que le premier identifiant wowsims (identifiants TBC/Wrath) : arcaneGeometry 11247 / 11100, arcaneBlast 400574 / 30451, missileBarrage 400588 / 44404, flameThrowing 11100 / 11078, hotStreak 400624 / 44445, iceLance 1312002 / 30455, fingersOfFrost 400647 / 44543.
