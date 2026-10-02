# 1.60.1.70170 — écarts de talents à trancher avant l'installation

Source : `forever diff 1.60.1.70124 <candidate>` et `forever install <candidate> --new-version --dry-run` (refus :
4 écarts hors des règles de fusion), candidate décodée le 2026-10-02 depuis les tables de wago.tools
(`forever fetch --version 1.60.1.70170`, 61 fichiers, accord réseau de l'utilisateur du 2026-10-02).

Pour chaque ligne : **C** = vrai changement du client (entrée dans `confirmed_changes.json`, nature `client`),
**B** = bogue du décodeur (corriger le décodeur).

| # | Talent | Changement | 70124 | 70170 | Preuve dans le client | Proposition |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | hotStreak → heatingUp | renommage | « Hot Streak », clé `hotStreak` | « Heating Up », clé `heatingUp` | même nœud (`TraitNode` 105786, palier 4, colonne 3), même sort du talent (400624), même aura (400625) aux effets identiques (`SpellEffect` 1045825 aura 108 −25, 1337783 aura 4 −3) ; seuls `SpellName` et l'infobulle changent | C |
| E2 | combustion | `ranks[1]` (2e valeur) | 4 | 3 | `SpellAuraOptions.ProcCharges` du sort 11129 : 4 → 3 (critiques non périodiques avant la fin de l'effet) | C |
| E3 | combustion | `tooltip_values[1]` (2e valeur) | 4 | 3 | même variable (`$n` de l'infobulle) | C |

Valeurs de Heating Up : 20 s, 25 % de réduction de l'incantation de Pyroblast par cumul, 3 cumuls, identiques à
Hot Streak. Texte du client 70170 : « reduce the cast time of your **next** Pyroblast cast within 20 sec ». Le modèle
consomme déjà les cumuls au Pyroblast qui suit (`forever/sim/leveling_mc.py`, « cumuls consommés par Pyroblast ») :
le renommage ne change pas la règle modélisée (registre B15).

## Ce que l'installation demande en plus
- `forever install` refuse toujours un talent retiré, un talent ajouté et tout changement de `tooltip_values`, même
  listés dans `confirmed_changes.json` (`forever/pipeline/install.py`, `_Merge.talents`) : la règle de fusion doit
  accepter un renommage confirmé et un changement de `tooltip_values` confirmé (tests d'abord).
- Selon la décision sur la clé (ci-dessous), le moteur, les fixtures de builds communautaires et les tests qui
  nomment `hotStreak` suivent ou non.

## Décision sur la clé du talent renommé
- **Garder la clé du dépôt `hotStreak`** : nom affiché « Heating Up », alias `heatingUp` pour la recherche ; aucun
  changement du moteur, des builds enregistrés ni des fixtures ; `classes.json` (décodé) porte `heatingUp`.
- **Prendre la clé du client `heatingUp`** : moteur, explications du registre, fixtures de builds communautaires et
  tests suivent ; le mode seed garde `hotStreak` (copie figée).

## Décisions de l'utilisateur (2026-10-02)
- E1, E2, E3 : **C**, changements du client, inscrits dans `confirmed_changes.json` (copie de 1.60.1.70170,
  `applied_in_revision` 1 ; lus à l'installation dans celui de 1.60.1.70124, rendu ensuite à son état committé).
- Clé : **`hotStreak` gardée**. Nom « Heating Up », ancien nom dans `former_names` (la recherche trouve les deux),
  clé du client dans `source.client_key` ; l'arbre du Mage de `classes.json` prend aussi `hotStreak` (l'import du
  profil traduit les nœuds par ce fichier).
