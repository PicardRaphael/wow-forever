---
name: addon-forever
description: Savoir-faire Lua et addons de WoW Forever pour le développement dans ce dépôt (addon/, ForeverLogger, ForeverBridge, pont de P06a, P06b, EX1). À charger avant d'écrire ou de relire du Lua d'addon, un .toc, le client simulé des tests (lupa) ou le protocole du pont.
---
# Addons de WoW Forever (développement)

Ce skill sert au développement dans `addon/` et `forever/bridge/` ; il ne fait pas partie du plugin. Les règles du dépôt
priment : `CLAUDE.md` (section « Addon »), `docs/ADDON.md`, décisions 194 à 196 et 212.

## Quand le charger
- Tout travail dans `addon/` (ForeverLogger, ForeverBridge, futurs addons), dans `forever/bridge/`, dans
  `scripts/check_addon.py` ou dans les tests `lupa` (`tests/unit/test_bridge_addon_lua.py`, `tests/fixtures/bridge/`).
- Tranches P06a, P06b, EX1 et toute sonde en jeu (`docs/ADDON.md` §7).

## Règles du dépôt (contrôlées)
- `uv run python scripts/check_addon.py` et `tests/unit/test_addon_rules.py` : SavedVariable initialisée dans le
  gestionnaire d'`ADDON_LOADED`, **jamais d'alias local au niveau du fichier** ; `pcall` autour de chaque
  `RegisterEvent` ; aucune fonction d'action (`CastSpell*`, `UseAction`, `RunMacro*`, `CreateMacro`,
  `SendChatMessage`) ; aucun `ReloadUI`, `EnableKeyboard`, `SetPropagateKeyboardInput` (décision 212) ; aucun
  abonnement à `COMBAT_LOG_EVENT*`.
- Dessin (`SetColorTexture` et pixels) : **ForeverBridge seulement** (décision 194) ; ForeverLogger ne dessine rien.
- Aucun chiffre de jeu dans `addon/` (`scripts/check_game_numbers.py` lit `.lua` et `.toc`) : dans les commentaires,
  éviter un nombre suivi d'une unité de jeu (secondes, points, pourcentages…) ; les constantes du protocole s'écrivent
  dans le code.
- Code repris de wow-ai : notice MIT complète en tête du fichier (liste fermée de `tests/unit/test_bridge_license.py`).

## Pièges de l'API et du Lua du client
- **Lua 5.1** : nombres en double (pas d'entiers 64 bits, exacts jusqu'à 2^53) ; ni `os` ni `io` ; `bit` est fourni
  par le jeu mais **absent de Lua 5.1 nu** (le codec n'en dépend pas, arithmétique pure) ; pas d'`utf8` (`strlenutf8`
  seulement) ; `#` et `string.sub` comptent des **octets** (couper un texte UTF-8 au bon endroit).
- **Valeurs secrètes** : `issecretvalue(v)` avant tout usage ; `UnitHealth`, `UnitPower` secrets même hors combat ;
  `UnitClass`, `UnitRace` peuvent l'être (restriction d'identité) : `pcall` et clé absente si secrète.
- **Fonctions protégées** : `ReloadUI` exige un événement matériel (le joueur tape `/reload`) ; rien de protégé en
  combat (`InCombatLockdown()`).
- **API retirées** : `GetSpellInfo`, `GetItemInfo`, `GetTalentInfo`… : utiliser `C_Spell`, `C_Item`,
  `C_Traits`, `C_ClassTalents`, `C_AddOns`.
- **Fichiers vus au lancement seulement** (sonde en jeu A du 2026-10-09) : un fichier ajouté pendant que le client
  tourne n'est pas vu (addons, sons) avant un redémarrage complet ; le code Lua d'un addon est relu au `/reload` et au
  `LoadAddOn` (un addon chargé à la demande lit son fichier modifié) ; sons, polices et textures déjà chargés restent
  en cache pour tout le processus.
- **`PlaySoundFile`** rend `willPlay, handle` ; **sur Forever, un fichier vide présent au lancement « jouera »** :
  le drapeau son de wow-ai ne marche pas ; seul un fichier absent au lancement « ne jouera pas ». Le retour du pont
  passe par la consultation de la réserve à intervalles (décision 212) ; les sons ne servent qu'au diagnostic
  `/fv diag`.
- **`LoadOnDemand`** : un addon se charge une fois par session d'interface (`/reload` les décharge tous) ;
  `C_AddOns.LoadAddOn` rend `loaded, reason` ; ne jamais l'appeler dans le gestionnaire d'`ADDON_LOADED`.
- **Pixel parfait** : `GetPhysicalScreenSize()` ; échelle `768 / hauteur physique` sur un cadre qui ignore l'échelle
  de son parent (`SetIgnoreParentScale(true)`, appelé une fois hors combat) ; strate `TOOLTIP`.
- **Textes affichés** : `|` ouvre une séquence d'interface (`|c`, `|H`, `|T`) : le doubler (`||`) dans un texte
  venu de l'extérieur.
- **Événements** : un événement inconnu du client lève une erreur au `RegisterEvent` (d'où le `pcall`).

## Tests sous `lupa.lua51`
- `lupa` est une dépendance de développement ; `from lupa import lua51` exécute le vrai Lua de l'addon dans Lua 5.1.
- Client simulé `tests/fixtures/bridge/wow_stub.lua`, **écrit de zéro** pour nos seules API (cadres, textures,
  commandes `/`, minuteries, `PlaySoundFile`, `C_AddOns`) ; les fonctions interdites y sont des pièges qui
  enregistrent tout appel.
- Lire les cellules de la bande dans les textures simulées, puis les décoder par `forever.bridge.codec` : le codec Lua
  et le codec Python doivent rendre les mêmes cellules.
- Les tests n'utilisent ni réseau, ni jeu, ni écran ; ils écrivent dans `tmp_path`.

## Sources
- API : https://warcraft.wiki.gg (pages `API_*`, `TOC_format`, `Secret_Values`, `Lua_functions`) ; code de Blizzard :
  https://github.com/Gethe/wow-ui-source (par exemple `PixelUtil.lua`).
- wow-ai (MIT, commit 3756eb5a) : https://github.com/chelinho139/wow-ai, résumé dans `tasks/P06a-plan.md`.
- `docs/research/addon-forever.md` (rapport du 2026-09-27) et `docs/ADDON.md`.
