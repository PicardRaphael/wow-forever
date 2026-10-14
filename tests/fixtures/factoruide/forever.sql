-- Fixture RX1 : schéma réduit de la base Forever de Factoruide (brouznouf/factoruide@f7da6da, data/forever.sqlite.zst),
-- colonnes lues seulement ; identifiants, noms et niveaux inventés.
CREATE TABLE import_run (source TEXT PRIMARY KEY, imported_at TEXT NOT NULL, detail TEXT);
CREATE TABLE m_quest (id INT, name TEXT, level INT, min_level INT, races_mask INT, classes_mask INT, sources, status TEXT, in_client INTEGER, xp INTEGER);
CREATE TABLE m_quest_relation (quest_id INT, role TEXT, entity_type TEXT, entity_id INT, sources);
INSERT INTO import_run VALUES ('questie', '2026-10-13 19:36:08', 'fixture');
INSERT INTO import_run VALUES ('att', '2026-10-13 19:36:15', 'fixture');
INSERT INTO m_quest VALUES (990010, 'Fixture Errand', 5, 3, NULL, NULL, 'wowhead,questie', 'available', 1, NULL);
INSERT INTO m_quest VALUES (990022, 'Fixture Almanac, Vol. 1', NULL, NULL, NULL, NULL, 'wowhead,att', 'available', 1, NULL);
INSERT INTO m_quest VALUES (990070, 'Fixture Unseen', 12, 10, NULL, NULL, 'wowhead,att', 'available', 1, NULL);
INSERT INTO m_quest VALUES (990071, 'Fixture Removed', 20, 18, NULL, NULL, 'vmangos', 'removed', 0, NULL);
INSERT INTO m_quest VALUES (990072, 'Fixture Incomplete', 22, 20, NULL, NULL, 'wowhead', 'incomplete', 1, NULL);
INSERT INTO m_quest_relation VALUES (990070, 'start', 'npc', 990800, 'wowhead');
