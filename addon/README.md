# Addons de forever-core

Règles, canaux de données et feuille de route : [`docs/ADDON.md`](../docs/ADDON.md).

## ForeverLogger (0.2.0)
Active le journal de combat avancé à chaque connexion et note le contexte du personnage pour `forever`. N'agit jamais dans le jeu et ne lit pas le journal de combat (interdit sur Forever) : l'analyse se fait hors du jeu, sur `Logs/WoWCombatLog-*.txt`.

### Installation
```
uv run python scripts/install_addon.py --dry-run     # affiche la copie prévue
uv run python scripts/install_addon.py               # copie addon/ForeverLogger dans Interface/AddOns
```
Dossier du client : `--wow-dir`, sinon `FOREVER_WOW_DIR`, sinon `C:\Program Files (x86)\World of Warcraft\_classic_beta_`. L'ancien dossier est renommé `ForeverLogger.bak-<date>`. Si Windows refuse l'écriture dans `Program Files (x86)`, relancer la commande dans un terminal administrateur. Puis relancer le jeu ou taper `/reload`.

### Contenu de `ForeverLoggerDB`
Fichier `WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua`, écrit par le client au `/reload`, à la déconnexion et à la sortie.
```
ForeverLoggerDB = {
  schema = 1,
  characters = {
    ["<GUID du personnage>"] = {
      name, realm, class, race,
      snapshots = { { reason = "connexion" | "niveau" | "talents", time, localtime, level,
                      talents = { [nodeID] = rang }, spell_bonus = { [école] = … }, spell_crit = { [école] = … } }, … },
      xp = { { time, localtime, level, text }, … },
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
- Lecture : `uv run forever logs measure <journal> --addon-sv <SavedVariables>/ForeverLogger.lua` (niveau du lanceur pour les touchés et ratés).
