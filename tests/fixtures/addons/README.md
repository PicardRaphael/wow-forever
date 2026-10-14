# Addons synthétiques (T08d, bloc D)

Fichiers écrits pour les tests, sans contenu tiers : ni code ni données d'un addon réel. Les noms de dossier
reprennent ceux des addons suivis pour exercer `forever/addons.py` ; les valeurs (versions, noms, nombres) sont
inventées et ne sont pas des valeurs de jeu.

- `TalentsForeverBook/` : `Data.lua` minimal (`build`, `generated`, `codeVersion`, un arbre d'un talent).
- `ForeverCompanion/` : `.toc` sans licence, `Data/Meta.lua` (`dataVersion`, `updated`) et `Data/Bis.lua`.
- `EllesmereUI/`, `EllesmereUI_Extra/` : addon d'interface (jamais lu hors du `.toc`).
- `ForeverCompletionist/` : dossier sans `.toc` (pas un addon).
- `SomeDataAddon/` : addon inconnu, avec `X-License` et une table globale.

## `quests/` (T04d, bloc D)
- Dossier du client réduit (`Interface/AddOns`, `WTF/Account/COMPTE/SavedVariables`), extrait des addons installés le
  2026-10-13 par `uv run python scripts/extract_quest_fixtures.py addons` ; ne pas éditer à la main.
- Questie 11.38.0 Forever-v27 : en-tête `questKeys` et quêtes 7, 15, 783, 790, 804 (deux quêtes nommées « Sarkoth »,
  Durotar : nom ambigu pour GearQuest), 825, 5722 à 5725, 5728, 5761 et 7677 (quête Classic d'Elwynn Forest absente
  de Completo, zone couverte par Completo : statut `absente des sources Forever`), leurs PNJ, leur XP Classic, leurs
  corrections (`classicQuestFixes.lua`, entrées de ces quêtes) et `areaIdToUiMapId.lua` entier.
- Naowh Forever 1.1.11 : Completo (zones Elwynn Forest, Alterac Mountains et Durotar ; quêtes, prérequis et la chaîne
  783 → 7 → 15), Journeys (points de rendu et camps), Dungeon Journal (Ragefire Chasm, The Hall of Thanes).
- Forever Guide 1.33.0 (donjons rfc et thanes, quêtes et leurs PNJ) ; ForeverDungeonJournal 1.6.2 (XP de repli,
  bloc « Hall of Thanes » de `Dungeons.lua`, dont 96395 au texte « 3,570 XP » contre 1050 en repli) ;
  GearQuestForever 0.5.4-beta (deux objets : « From The Wreckage.... » et « Sarkoth »).
- `QuestieForeverDB` (SavedVariable de Questie) : deux quêtes apprises en jeu (96607, 886), champs `questId`,
  `title`, `level`, `mapID` seulement (aucun horodatage, aucun nom de personnage).
- `xp_bonuses/` (T04f, bloc E) : extraits structurels de `NaowhForever_Discovery/Data/SleepingBag.lua` (1.1.11) et de `FojjiCore_DungeonJournal/Data/Guides.lua` (3.3.5, clé `sleepingbag`) : forme, objets, cartes, positions, quêtes et camps gardés ; conseils et textes remplacés (« tip », « text »).

## `quests_rx1/` (RX1, bloc A)
- Fichiers écrits à la main d'après la **structure** des fichiers installés le 2026-10-14 que nos lecteurs ignoraient
  (Naowh Discovery `Data/Books.lua`, Forever Guide `ChainData.lua`, Dungeon Journal de Naowh `Data/QuestChains.lua`,
  ForeverDungeonJournal `Data/QuestChains.lua` et `Data/QuestMaps.lua`, `QuestieConfig.char[…].complete` et entrées
  sans titre de `QuestieForeverDB`) ; identifiants (990000 et plus), noms, niveaux et positions **inventés** ; aucun
  nom de personnage réel.
- `../factoruide/forever.sql` : schéma réduit de la base de Factoruide (`m_quest`, `m_quest_relation`,
  `import_run`), cinq quêtes inventées ; la base SQLite est bâtie par le test dans `tmp_path`.
