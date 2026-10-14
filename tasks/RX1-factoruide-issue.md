# Issue pour Factoruide (RX1, bloc G) — envoyée le 2026-10-14 sur accord : https://github.com/brouznouf/factoruide/issues/13

Dépôt : https://github.com/brouznouf/factoruide (code MIT, lu à `f7da6da`). Texte en anglais, sans chiffre de jeu
recopié de nos données (l'auteur relira ses propres sources).

---

**Title:** Quest XP and lower-level mob XP on WoW Forever: two differences with the client and in-game measurements

Hi, thanks for Factoruide and for the MIT licence: we read its planner to write our own route search.
While comparing our routes with yours, we found two places where Forever seems to differ from the Classic rules
the planner uses:

1. **Quest XP.** For quests without an XP value in the database, the planner takes the `QuestXP` row of the quest
   level with a fixed difficulty column. The Forever client's quest cache gives each quest its own difficulty
   index; reading it gives the exact reward the client shows. Quests reworked by Forever also often have a
   different reward than their Classic version, so the database value is stale for them.
2. **XP of a mob below the player's level.** The planner computes it from the player's level. Our measurements on
   Forever (XP gains logged in game, several levels and mob levels) match a base taken at the mob's level instead.

We can share how we read the quest cache (`questcache.wdb`, local file) and the measurement method if useful.
We also noticed the quest log size comment says Forever allows a larger log than Classic Era; do you have a source
for it? We could not confirm it yet.

---

Notes internes (non envoyées) : points 1 et 2 = décision 249 et T04d ; journal de quêtes = question RTE2.
