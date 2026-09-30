# Protocole de mesure des rendements décroissants en PvP (pour PV2)

PV1 (bloc C) modélise les rendements décroissants avec les règles du serveur de Classic, toutes `suppose`
(`forever/data/1.60.1.70124/pvp_rules.json`, registre K1). La **catégorie** de chaque contrôle vient du client
(`SpellCategories.DiminishType`, certain, `classes.json`) ; les **paliers**, la **fenêtre de remise à zéro** et son
point de départ, et le **plafond de durée** sur un joueur restent à mesurer dans mes journaux de combat de champ de
bataille. Ce document dit quoi relever pour passer K1 et K3 à `valide-journal`. Aucun chiffre de jeu ici.

## Ce qu'il faut relever

Dans `WoWCombatLog-*.txt` (format 22, bloc avancé), pour une unité **joueur** (`Player-…`) cible d'un contrôle :

1. `SPELL_AURA_APPLIED` d'un sort de contrôle (identifiant retrouvé dans `classes.json`, `pvp.control`), avec
   l'instant, le lanceur et la cible ;
2. le `SPELL_AURA_REMOVED` du même sort sur la même cible : la durée observée est l'écart entre les deux ;
3. la catégorie du sort (`control.diminish`) et sa durée de base dans le client (`duration_s`, `pvp_duration_s`),
   au rang lancé (rang lu par l'identifiant du sort).

## Ce qu'il faut écarter

- Les retraits anticipés : `SPELL_AURA_BROKEN`, `SPELL_AURA_BROKEN_SPELL`, `SPELL_DISPEL` sur la cible, dégâts reçus
  quand le contrôle rompt aux dégâts (`control.breaks_on_damage`), rupture par un bijou ou un racial (sorts de
  `pvp_items.json` et de `races.json` lancés par la cible entre la pose et le retrait).
- Les sorts sans catégorie (`diminish` à 0) pour les paliers ; ils servent au plafond seulement.
- Les poses sur un PNJ (GUID `Creature-…`) : les rendements contre les PNJ ne sont pas modélisés.
- Les sessions dont la version du client est inconnue ou différente de la version installée
  (`client_builds.split_by_version`, décision 135).

## Mesures

- **Paliers** (K1) : pour une même cible et une même catégorie, durée observée de la *k*-ième application
  rapprochée, rapportée à la durée de base ; comparer au multiplicateur `steps` de `pvp_rules.json`. Une durée nulle
  ou un `SPELL_MISSED` de type `IMMUNE` après le dernier palier mesure l'immunité.
- **Fenêtre** (K1) : écart entre la fin (ou la pose) d'une application et la pose suivante qui repart au premier
  palier ; relever les deux écarts pour trancher `window_from` (fin de l'effet ou application) et la largeur (fixe
  ou comprise entre deux bornes).
- **Plafond** (K3) : durée observée d'un contrôle dont la durée de base dépasse `pvp_duration_cap_s`, première
  application seulement.
- **Racines et silences** : vérifier si l'immunité arrive dès la deuxième application (wiki de fans de Forever),
  contre la règle de Classic.

## Seuil

Une mesure ne compte qu'avec `n` ≥ `tolerance.n_min` de l'entrée du registre (décision 2) ; tant que `n` est
insuffisant, l'entrée reste `teste` et les valeurs `suppose`. Chaque preuve cite le journal, la ligne et la version
du client (`docs/MECHANICS_REGISTRY.yaml`, champ des preuves).
