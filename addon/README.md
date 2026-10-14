# Addons de forever-core

Règles, canaux de données et feuille de route : [`docs/ADDON.md`](../docs/ADDON.md).

## ForeverBridge (0.1.0)
Fenêtre de chat de forever dans le jeu (`/fv`) : question, réponse courte avec sa provenance, état des données,
boutons des tranches faites. Seul addon de forever-core qui dessine : une petite bande de couleurs en haut à gauche,
le temps d'un envoi. Aucune action de jeu, rien dans la discussion générale (sauf `/fv diag`), aucune ouverture
automatique. Installation et pont : `uv run forever bridge install`, puis `uv run forever bridge start`, ou une
fois pour toutes `uv run forever bridge autostart install` (pont lancé à chaque ouverture de session Windows ;
`docs/USAGE.md`, « Chat en jeu »). Contient du code adapté de wow-ai (licence MIT, crédits dans `docs/ADDON.md`).
P06b (décision 235) : liens insérés par Maj+clic (accroches `hooksecurefunc`) envoyés avec leur infobulle, messages
longs en parties montrées tour à tour, zone « Coller /simc » (export SimulationCraft collé, lu par le pont), bouton
« Mettre à jour », panneau « À valider » (attentes de `forever update`, écarts avec le profil ; Valider et Refuser
demandent un second clic), onglets « Jeu » et « Addons » (historiques séparés). `ForeverBridgeDB` gagne
`history_addons`, `paste` (position de la zone de collage), `help_shown` et `update_seen`.

## ForeverLogger (0.4.0)
Active le journal de combat avancé à chaque connexion et note le contexte du personnage pour `forever`. N'agit jamais dans le jeu et ne lit pas le journal de combat (interdit sur Forever) : l'analyse se fait hors du jeu, sur `Logs/WoWCombatLog-*.txt`.

### Installation
```
uv run python scripts/install_addon.py --dry-run     # affiche la copie prévue
uv run python scripts/install_addon.py               # copie addon/ForeverLogger dans Interface/AddOns
```
Dossier du client : `--wow-dir`, sinon l'installation choisie par `forever wow list` (version finale adoptée, sinon la bêta ; LN1). L'ancien dossier est déplacé dans le cache du projet (`<cache>/addons/backups/ForeverLogger.bak-<date>`, jamais dans le dossier des addons) ; `--backups-only` y range les `ForeverLogger.bak-*` laissés par les anciennes installations. Si Windows refuse l'écriture dans `Program Files (x86)`, relancer la commande dans un terminal administrateur. Puis relancer le jeu ou taper `/reload`.

### Contenu de `ForeverLoggerDB`
Fichier `WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua`, écrit par le client au `/reload`, à la déconnexion et à la sortie.
```
ForeverLoggerDB = {
  schema = 2,  -- 2 depuis 0.4.0 (T04d) ; les anciennes listes gardent leur forme
  seq,          -- compteur commun des entrées numérotées (ordre entre gains, états et quêtes)
  errors = { [événement] = { count, last } },  -- erreurs des gestionnaires, jamais remontées au joueur
  characters = {
    ["<GUID du personnage>"] = {
      name, realm, class, race,
      snapshots = { { reason = "connexion" | "niveau" | "talents", time, localtime, level,
                      talents = { [nodeID] = rang }, spell_bonus = { [école] = … }, spell_crit = { [école] = … } }, … },
      xp = { { time, localtime, level, text,
                -- T04d (0.4.0) :
                seq, amount, kind = "monster" | "other" | "unknown", monster,
                target = { name, level, classification, npc, creature_type,
                           source = "target" | "nameplate" | "recent" },  -- monstre tué, s'il est visible
                seen_levels = { … },  -- sinon, niveaux vus pour ce nom depuis l'entrée dans la zone
                state = { xp, max, rested, rest_state }, resting,
                instance = { inside, type, name, id }, group = { size, raid, levels = { … } }, map }, … },
      xp_states = { { seq, reason = "connexion" | "niveau" | "xp" | "repos", time, localtime, level,
                      xp, max, rested, rest_state, resting }, … },
      quests = { { event = "accepted" | "turned_in", seq, quest_id, title, quest_level, xp_reward, money_reward,
                   time, localtime, level, state = {…}, resting, map, instance = {…}, group = {…} }, … },
      -- CH0 (0.3.0), hors combat seulement :
      pet_snapshots = { { reason = "connexion" | "familier" | "fenetre" | "apres-combat", time, localtime, level,
                          pet = { family, name, level, health_max, armor = {…}, attack_speed, attack_power = {…},
                                  loyalty, happiness = {…}, training_points = {…}, diet = {…} },
                          hunter = { stamina = {…}, armor = {…}, attack_power = {…}, ranged_attack_power = {…},
                                     crit, ranged_crit } }, … },
      training = { { time, localtime, skill_line, family, pet_level,
                     entries = { { name, rank, type, cost, level }, … } }, … },
    },
  },
}
```
- `time` : heure du serveur (`GetServerTime`) ; `localtime` : heure locale au format des journaux (`%m/%d/%Y %H:%M:%S`), pour la jointure avec `WoWCombatLog-*.txt`.
- Un champ absent signifie une API indisponible, en erreur ou une valeur secrète. `{…}` : retours multiples de l'API gardés par position (un trou pour une valeur secrète).
- Familier (CH0) : `uv run forever pets measure --addon-sv <SavedVariables>/ForeverLogger.lua` compare la fenêtre Beast Training et le régime au client et forme les rapports d'héritage (protocole : `docs/research/familiers-protocole.md`).
- `/flog` : résumé de la session (gains relevés, XP et repos, dernier gain et niveau du monstre, dernière quête rendue, erreurs) ; sert à vérifier l'addon pendant une sonde (`docs/ADDON.md`, section 7, étape 21).
- Lecture : `uv run forever logs measure <journal> --addon-sv <SavedVariables>/ForeverLogger.lua` (niveau du lanceur pour les touchés et ratés).
