---
name: forever-donjons
description: "Donjons de WoW Forever, toutes les classes : liste des donjons à mon niveau (plage, niveau du client, nouveau ou fermé), fiche d'un donjon (entrée, boss et leur niveau, butin avec taux et source, objets utilisables par ma classe), quêtes du donjon et leurs prérequis à faire d'abord, où trouver tel objet (boss, donjon, taux), écarts entre addons. Déclencher pour « que lâche le dernier boss des Mortemines », « quel donjon à mon niveau », « quêtes à prendre avant Gnomeregan », « où trouver tel objet ». Pas pour les raids, ni WoW retail ni WoW Classic hors Forever, ni la programmation."
---

# Donjons (WoW Forever)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé », forme de la réponse, règle
« je ne sais pas ». Aucun chiffre de mémoire : niveaux, taux, XP et durées viennent des outils, recopiés tels quels.

## Noms du client

Cite chaque donjon, boss, objet et quête **tel qu'il apparaît dans le client du joueur** (`game_locale` de
`forever_player_profile` ; en anglais pour `enUS`), avec le nom français entre parenthèses seulement quand l'outil le
rend ; le reste de la réponse en français.

## Outils
- `forever_lookup(kind="dungeons", level, faction)` : donjons dont la plage retenue contient le niveau ; pour chacun
  la plage et sa source (`levels_source`), le niveau de contenu du client (`client_level`), `new`, `closed`, le
  nombre de boss, de quêtes et d'écarts entre sources.
- `forever_lookup(kind="dungeon", name, class_name, level)` : fiche d'un donjon (`name` : nom anglais, identifiant
  d'instance ou clé d'aile comme `189:graveyard`). Champs : `fields.levels` (valeur, source, certitude, `others`),
  `fields.client_level`, `fields.access_level`, `fields.entrance` ; `bosses` (nom, PNJ, `level` avec sa source,
  `loot` : objet, `rate` en fraction, `rate_source`, `classic`, `certainty`, `observed`, `usable`, `level_ok`) ;
  `quests` (XP et `xp_source`, niveau de prise `min_level`, donneur) ; `first_steps` (quêtes à faire d'abord, hors
  du donjon, dans l'ordre) ; `access` (clés et objets d'accès) ; `runs` (passages relevés) ; `discrepancies`.
- `forever_lookup(kind="dungeon_item", name=<identifiant de l'objet>)` : où le trouver (donjon, boss, taux, source,
  version de la source).
- Rentabilité d'un donjon, premier passage avec ses quêtes, niveau où le faire :
  `forever_sim_leveling(kind="objectives", level, class_name, faction)` (`dungeons`, `dungeon_advice`) ; skill
  `forever-leveling`.

## Lire la fiche
- **Taux** : `rate` est une fraction ; donne-le en pourcentage, avec sa source. `rate` à `null` : « taux inconnu »,
  jamais estimé. `classic` vrai : taux repris de WoW Classic (boss inchangé), dis-le. `rate_source` = `relevé` :
  taux mesuré sur les passages du joueur (`observed` : lâchés et victoires), `certain`, à citer en premier.
- **Écarts** : quand `others` ou `discrepancies` montrent des valeurs différentes (plages, niveau d'un boss, boss
  absent du client, donjon dit fermé par un addon et ouvert par la note officielle), cite les valeurs et leurs
  sources ; ne tranche jamais toi-même. Le client prime quand il les donne (rencontres) ; la note officielle passe
  avant les addons.
- **Niveau d'un boss** : `journal` (relevé dans un journal de combat) est `certain` ; `independent` compte les
  sources indépendantes (une valeur recopiée d'un addon à l'autre compte une fois).
- **Objets pour moi** : avec `class_name` et `level`, `usable` (classes permises du client) et `level_ok` (niveau
  requis) ; `null` si l'objet n'est pas connu. La maîtrise d'armure et d'armes n'est pas vérifiée : dis-le.
- **Prérequis** : `first_steps` donne les quêtes à faire avant, dans l'ordre ; cite le donneur et le lieu de chaque
  quête du donjon quand `giver` est rendu.

## Ce qui n'est pas couvert
- Raids et stratégies de boss : dis « je ne sais pas » (plan d'équipement complet : T10, préparation de raid : T11).
  Valeur d'un objet pour ton personnage et « est-ce une amélioration » : skill `forever-builds` (`forever_gear`).
- Une source extérieure (Wowhead Forever, guide) passe par le sous-agent `forever-web-researcher`, étiquetée comme
  telle, certitude au mieux `suppose`.
