# T04 — Sources locales du client, mesures sur journaux, puis leveling : plan

> Plan rédigé le 2026-09-27 (session de cadrage en arrière-plan). **Décisions 1 à 8 acceptées par l'utilisateur le 2026-09-27** (T04a maintenant, T04b ensuite), avec des ajouts sur l'addon : règles de l'API Forever, `docs/ADDON.md`, feuille de route ForeverAssist, garde-fous dans CLAUDE.md (section « Addon »). Exécution : `/tranche T04` dans une nouvelle session.

## Contexte
T02 a porté le moteur, T03 la chaîne qui lit les tables du client (wago). Le simulateur de leveling du seed (`seed/forever-mage/scripts/sim_leveling.py`) repose sur des PV de monstres **estimés** (`leveling.json.mob_model.hp_anchors`, certitude EST) et sur des règles Classic supposées inchangées (A3, B1, H1 en `suppose`). L'utilisateur demande d'intégrer **d'abord** trois sources locales, sans réseau, pour mesurer ce qui manque au client : les journaux de combat (`WoWCombatLog-*.txt`), la base de l'addon Questie et un addon maison (ForeverLogger) ; puis de construire la table des monstres du simulateur, de fournir des preuves `valide-journal` au registre, et de prévoir le calcul des dégâts au niveau du personnage.

## Constats (relevés le 2026-09-27 dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_`, lecture seule)

### Journal de combat réel (`Logs/WoWCombatLog-092726_145346.txt`, 194 lignes, 46 Ko, 1 min 38 s, Durotar)
- En-tête : `COMBAT_LOG_VERSION,22,ADVANCED_LOG_ENABLED,1,BUILD_VERSION,1.60.1,PROJECT_ID,18`. **Le numéro de build (70009) n'y figure pas** : la provenance doit le prendre ailleurs (hypothèse affichée).
- Horodatage `9/27/2026 14:53:46.0812` (année présente, séparateur deux espaces ; format dépendant de la locale du client). Champs CSV avec guillemets ; noms en UTF-8 (coréen, chinois).
- Bloc avancé présent sur `SPELL_CAST_SUCCESS`, `SPELL_DAMAGE`, `SPELL_PERIODIC_DAMAGE`, `SPELL_ENERGIZE`, `DAMAGE_SHIELD` (après le préfixe de sort), `SWING_DAMAGE`, `SWING_DAMAGE_LANDED`, `ENVIRONMENTAL_DAMAGE` : **19 champs** — GUID décrit, GUID du maître, PV courants, **PV max**, puissance d'attaque, puissance des sorts, armure, absorption, **deux champs inconnus**, type de ressource, ressource courante, ressource max, **coût du sort**, **position X, Y**, uiMapID, orientation, **niveau**. Le client en Retail n'a que 17 champs : les deux inconnus restent bruts.
- **L'unité décrite n'est pas fixe par événement** : source pour `SPELL_CAST_SUCCESS` et `SWING_DAMAGE`, destination pour `SPELL_DAMAGE`, `SWING_DAMAGE_LANDED`, `DAMAGE_SHIELD`, `ENVIRONMENTAL_DAMAGE`. Le parseur se fie au GUID décrit (champ explicite), jamais à une hypothèse.
- Dernier champ = **niveau pour une créature** : sanglier 3099 niveau 6 → 120 PV (deux individus), niveau 7 → 137 PV, lièvre 5951 niveau 1 → 8 PV. Pour un **joueur**, ce n'est probablement pas le niveau : Jen affiche `7` en lançant Frostbolt 837 (rang 3, `BaseLevel` 14 dans les fixtures) avec 347 PV et 763 mana → sans doute le niveau d'objet. **À vérifier** (décision 5).
- Suffixe de dégâts : montant, montant d'origine, excès, école, résisté, bloqué, absorbé, critique, écrasant, glancing (10 champs) ; `SPELL_*` ajoute `ST` / `AOE`. Fireball critique : 87 pour 58 d'origine (× 1,5). Montant et montant d'origine diffèrent parfois d'une unité hors critique (53 / 52) : sens à établir.
- **Joueur qui journalise** : drapeau d'affiliation « à moi » (`0x511` pour Jen ; `0x518` pour les autres). Le journal contient aussi les actions des joueurs voisins.
- Mesures déjà possibles pour Jen : coût relevé = `spells.json` (Frostbolt r3 50, Fireball r3 65, Arcane Explosion r1 75, Fire Blast r2 75 ; mana 763 → 713 → 663) ; intervalles entre sorts instantanés 1,503 s, 1,516 s, 1,590 s et un `SPELL_CAST_FAILED « Not yet recovered »` 0,02 s après un lancer (compatible avec B1, n = 3) ; aucun `SPELL_MISSED` (A3 non mesurable), aucun boss (H1 non mesurable) ; incantations START → SUCCESS : Frostbolt 2,074 et 1,982 s (table 2,2), Fireball 2,443 et 2,472 s (table 2,5) — talents de Jen inconnus.
- Un second journal `WoWCombatLog-092726_150346.txt` existe mais est vide.

### Hotfix.log et QuestCache.log (réponse à la question de l'utilisateur)
- **Hotfix.log** : journal d'application des hotfixes au démarrage (`ClientAvailableHotfixes: region 70`, `ApplyingHotfixes from Cache`), une ligne par enregistrement : identifiant de push, table, RecID, `VALIDATION_RESULT_VALID|INVALID`. **Aucune valeur.** Tables touchées : objets (Item, ItemSparse, ItemSearchName, TradeSkillItem, ModifiedCraftingItem, TransmogHoliday ≈ 4 350 chacune), **CurvePoint 144, Curve 72**, lumières, **CreatureDifficulty 3**, SpellScript 2, GameObjects 4, AreaTable 1 ; **aucune table Spell\* de valeurs**. Utilisable en T08 comme **index de changements** (quelles lignes, quel push), pas comme source de valeurs : les valeurs sont dans `Cache/ADB/<locale>/DBCache.bin` (en-tête `XFTH`, version 9, build 70009 en octets 4-7 little-endian, entrées `XFTH` par enregistrement ; décodage des lignes par les définitions WoWDBDefs).
    - Conséquence pour T03 : CurvePoint porte les points par rang de talent décodés en T03 ; des lignes hotfixées peuvent différer de wago. À ajouter aux questions ouvertes.
- **QuestCache.log** : journal de requêtes du cache de quêtes (identifiant de quête, raison `QuestLog`, `IsComplete`, `GetLevel`, addon demandeur `RXPGuides`, `EllesmereUINameplates`, `Deny`). **Aucune donnée de quête** : pas une source. Le contenu envoyé par le serveur (niveau, texte, objectifs, récompenses) est dans `Cache/WDB/<locale>/questcache.wdb` (en-tête `WQST`, build 70009) ; `creaturecache.wdb` (`WMOB`) contient les fiches de créatures (nom, type, multiplicateurs de PV) mais pas les PV. Format binaire non documenté par WoWDBDefs : **hors T04**, à noter comme source de premier rang pour les quêtes (T04b ou plus tard).

### Addons installés (`Interface/AddOns`, 31 dossiers)
| Addon | Version (`## Version`) | Licence | Données | Usage T04 |
| --- | --- | --- | --- | --- |
| Questie (`Questie_Camelot.toc`, Interface 16001) | 11.38.0, titre « Forever-v27 » | aucun fichier de licence installé ; à vérifier en amont (CurseForge 334372, wago `qv634BKb`, lignée cmangos) | PNJ 10 119, quêtes 4 244, objets de monde 6 645, objets 14 889, XP de quête (`xpDB-classic.lua`) ; tables Lua dans des chaînes `[[return {…}]]` | **Lecteur local** |
| ForeverDungeonJournal | 1.2.0 | aucune | donjons, `BOSS_LEVELS`, quêtes 96xxx avec XP (sites tiers) | Noté (recoupement H1), non ingéré |
| GearQuestForever | 0.2.14-beta | aucune | fiches d'objets extraites de Wowhead Forever | Noté (T10), non ingéré |
| EllesmereUIForeverEssentials | 9.3 | propriétaire | durées de vol (build 69913) | Non |
| RXPGuides (RestedXP) | v4.11.11 | CC BY-NC-SA 4.0 | guides, `DB/forever/*` | **Exclu en entier** (guides payants, règle de l'utilisateur) |
| Auctionator, ForeverMapFix, EllesmereUI* | — | — | interface, tuiles de carte | Non |
| ForeverLogger | aucune | aucune | aucune ; `.toc` **corrompu** (deux blocs collés, ligne `ForeverLogger.lua## Interface: XXXXX`), pas de SavedVariables | À ranger dans le dépôt |

- Questie sur Forever : `ForeverCompat.lua` pose `QUESTIE_FOREVER_CLIENT` ; `IsForever ⇒ IsClassic, IsEra` ; charge la **base Classic Era sans aucune correction Forever** (blocs SoD et Anniversary inactifs). Les quêtes propres à Forever (96xxx) sont absentes de la base et capturées en jeu dans la SavedVariable `QuestieForeverDB` (≈ 118 quêtes : niveau, objectifs, carte).
- Schéma PNJ (`npcKeys`) : name, minLevelHealth, maxLevelHealth, minLevel, maxLevel, rank, spawns `{[zoneID]={{x,y}…}}`, waypoints, zoneID, questStarts, questEnds, factionID, friendlyToFaction, subName, npcFlags. Exemples : `[3099] = {'Dire Mottled Boar',120,137,6,7,0,{[14]=…},nil,14,…}`, `[5951] = {'Hare',8,8,1,1,0,…}`, `[3111] = {'Razormane Quilboar',120,137,6,7,0,…}`.
- **Recoupement** : les trois PNJ mesurés dans le journal ont exactement les PV de Questie (120 au niveau 6, 137 au niveau 7, 8 au niveau 1). Le modèle actuel du seed interpole 121,2 et 140,4.

### Données de sort pour le niveau du personnage
- Fixtures T03 (`tests/fixtures/wago/1.60.1.70009/enUS/`) : `SpellEffect` a `EffectBasePointsF`, `EffectRealPointsPerLevel`, `Variance` ; `SpellLevels` a `BaseLevel`, `SpellLevel`, `MaxLevel`. Exemple Frostbolt 837 : 46 points au niveau 14, + 0,9 par niveau jusqu'à 18, variance 0,111 ; à 18 : 49,6 × (1 ± 0,0556) → 47-52 = `spells.json`. Arcane Explosion 1449 : 32 + 0,4/niveau de 14 à 19 → 32-36.

## Décisions (acceptées le 2026-09-27)
| # | Décision | Retenu | Alternative écartée |
| --- | --- | --- | --- |
| 1 | Découpage de la tranche | **T04a** (cette exécution) : parseur de journaux, lecteur Questie, table des monstres, points de base par niveau, preuves du registre, addon et script d'installation, documentation. **T04b** (session suivante) : portage du simulateur MC et analytique, `forever_sim_leveling`, `forever chart leveling`, 3 tests du seed, remontées du registre (B6, B7, B13, C1, C5, H2, I1, I6, J2, A18, B11, C2). La feuille de route est mise à jour en conséquence. | Tout en une tranche (dépasse 1 à 3 sessions) |
| 2 | PV des monstres dans le simulateur | Paramètre `mob_source` : `measured` (défaut) lit `monsters.json` (journal, puis Questie par niveau), `seed` garde `hp_anchors` pour les tests de parité et de calibrage du seed. La provenance affiche la source et sa certitude. | Remplacer `hp_anchors` (casse « reproduit le seed à ±1 % ») ; garder l'estimation par défaut |
| 3 | Questie : licence et redistribution | Lecture locale seulement (`forever/pipeline/questie.py`, sans réseau) des fichiers `Database/Classic/*.lua` (source, pas le binaire compilé des SavedVariables). Dans le dépôt : un **agrégat par niveau** (médiane des PV des PNJ normaux, `rank` 0) et les PNJ **observés dans un journal** avec leur valeur Questie en regard ; **jamais la base brute**. Fixture de test : extrait minimal (3 PNJ + 2 leurres). Certitude : mesure de journal `certain` ; Questie seul `suppose`, étiqueté « communautaire (Classic Era, aucune correction Forever), Questie <version> ». Licence amont à vérifier avant tout élargissement (question ouverte). | Copier la base Questie dans `forever/data/` ; lire les SavedVariables compilées |
| 4 | Lecture des tables Lua | Analyseur pur Python du sous-ensemble généré (chaînes `'…'` et `"…"` avec échappements, nombres, `nil`, `true`/`false`, `{}` imbriquées, clés `[n]=` et `nom=`), aucune dépendance. | `lupa` (dépendance, exécute du Lua) |
| 5 | Niveau et talents du joueur | Étendre ForeverLogger avec une SavedVariable `ForeverLoggerDB` : à la connexion, au gain de niveau et au changement de talents, instantané {GUID, nom, royaume, niveau, classe, race, heure serveur, talents si l'API répond (sous `pcall`), bonus de dégâts des sorts, critique} ; gains d'XP (`CHAT_MSG_COMBAT_XP_GAIN`) horodatés. Lu par `forever/pipeline/addon_sv.py`, joint aux journaux par GUID et heure. Recoupe l'import d'addon prévu en T07 (même lecteur). Le sens du dernier champ du bloc avancé pour un joueur est vérifié avec ce niveau. | Addon inchangé (A3 et H1 impossibles sans le niveau du lanceur) ; saisie manuelle du niveau |
| 6 | Définition de `valide-journal` | Nouveau champ `preuves` du registre : liste de {`journal` (fixture sous `tests/fixtures/combatlog/`), `date`, `mesure`, `n`, `test`}. `registry.validate` exige pour `valide-journal` au moins une preuve dont la fixture et le test existent, et `n` ≥ `tolerance.n_min` de l'entrée. Le statut ne dit rien de la certitude : A3, B1, H1 ne passent en `probable` qu'avec une preuve valide. | Statut libre sans contrôle ; preuve dans une note |
| 7 | Stockage des points de base par niveau | Champ additif `scaling` par rang dans les sorts décodés (candidate T03) : {`spell_id`, `base_level`, `spell_level`, `max_level`, effets [{`index`, `base_points`, `points_per_level`, `variance`}]}. Pour 70009 : nouveau fichier `forever/data/1.60.1.70009/spell_scaling.json`, produit par `forever decode` sur les fixtures (FC, haché, `sources.json`), `spells.json` inchangé (décision 39). Moteur : `rank_values_at_level(gd, spell, rank, level)`. Le simulateur (T04b) choisit par `spell_level` : `character` (défaut) ou `rank` (parité seed). | Réécrire `ranks` de `spells.json` ; calcul hors du moteur |
| 8 | Fixtures de journaux et vie privée | Extraction hors ligne (`scripts/extract_combatlog_fixture.py`) : les autres joueurs deviennent `Joueur1-Royaume`, `Joueur2-…` et des GUID `Player-0000-0000000N` stables ; le joueur « à moi » devient `Moi-Royaume` ; créatures intactes. Nombre de lignes et d'événements conservés. | Journal brut dans le dépôt (noms de tiers) ; fixtures synthétiques |

Décisions techniques (sans arbitrage attendu) :
- **Aucun réseau** : journaux, Questie, SavedVariables et DBCache se lisent sur disque. Dossier du client : `FOREVER_WOW_DIR` (défaut `C:\Program Files (x86)\World of Warcraft\_classic_beta_`) dans `forever/config.py` (`Deps.wow_dir`). Tests : fixtures seulement. `test_network_boundary.py` inchangé.
- **Formats de fichier dans le code, chiffres de jeu dans les données** : la disposition des champs du journal (noms de préfixes et suffixes, 19 champs du bloc avancé) est un format, comme les colonnes CSV de `tables.py`. Aucun seuil de jeu dans `forever/pipeline/`.
- **Version du journal** : seules `COMBAT_LOG_VERSION 22` et `ADVANCED_LOG_ENABLED 1` sont acceptées (`unsupported_log`, code 3) ; un événement inconnu est gardé brut et compté, jamais interprété. Une ligne mal formée lève `data_schema` avec fichier et numéro de ligne.
- **Provenance des mesures** : `game_version` = version locale dont le préfixe correspond à `BUILD_VERSION` du journal, avec l'hypothèse « build du journal non précisé (1.60.1) » ; source = nom du journal et sa date ; certitude `certain` pour une valeur lue (PV max, coût), `probable` pour une statistique sous le seuil `n_min`.
- **Monstres** : PV max d'un PNJ à un niveau = valeur unique observée ; deux valeurs différentes au même niveau → conflit listé, jamais moyenné. PNJ normaux seulement dans l'agrégat (rang 0 ; élites et rares à part).
- **ForeverLogger** : `.toc` réparé (`## Interface: 16001`, `## Title`, `## Notes`, `## Version: 0.2.0`, `## Author`, `## SavedVariables: ForeverLoggerDB`) ; commentaires et messages en français.

## Addon (règles mesurées sur le client Forever, ajout de l'utilisateur)
Forever utilise l'API Retail 12.1.5 (interface 16001, suffixe de TOC `_Camelot` reconnu) ; les valeurs de combat y sont secrètes.
- `ForeverLoggerDB` s'initialise dans `ADDON_LOADED` (nom de l'addon vérifié) ; **jamais d'alias local au niveau du fichier** (les SavedVariables sont chargées après l'exécution du fichier : un alias pointerait vers une table perdue).
- `pcall` autour de chaque `RegisterEvent` et de chaque API incertaine : talents via `C_Traits`, bonus de dégâts des sorts, critique ; une valeur secrète ou une erreur donne un champ absent, jamais une erreur visible.
- **Aucune fonction d'action** : ni `CastSpell*`, ni `UseAction`, ni `SendChatMessage` automatique, ni macro.
- Sur Forever, un addon **ne peut pas s'abonner au journal de combat** : l'addon ne lit ni n'analyse aucun combat ; l'analyse se fait toujours hors du jeu, sur `WoWCombatLog-*.txt`.
- Aucun chiffre de jeu dans `addon/` (`scripts/check_game_numbers.py` étendu à `addon/`).
- Test statique `tests/unit/test_addon_rules.py` (Python, lecture des `.lua` et `.toc`) : initialisation dans `ADDON_LOADED`, aucun alias local de `ForeverLoggerDB` hors d'une fonction, chaque `RegisterEvent` sous `pcall`, aucune fonction interdite (`CastSpell`, `CastSpellByName`, `CastSpellByID`, `UseAction`, `SendChatMessage`, `RunMacro`, `RunMacroText`), aucun abonnement à `COMBAT_LOG_EVENT_UNFILTERED`, `## Interface: 16001`.

### `docs/ADDON.md` (nouveau)
Source de rédaction : `docs/research/addon-forever.md` (ajouté au dépôt par l'utilisateur avant l'exécution) ; toute affirmation de `docs/ADDON.md` sur l'API Forever en vient ou est marquée à vérifier. Si le fichier manque à l'exécution, s'arrêter et le demander.
- API : Retail 12.1.5, interface 16001, suffixe `_Camelot` ; valeurs de combat secrètes ; pas d'abonnement au journal de combat.
- **Lignes rouges** : pas d'automatisation, pas de lecture d'écran ni de pixels, pas d'entrées simulées.
- **Canaux de données** : aller = fichier Lua généré par `forever` (dans le dossier de l'addon) puis `/reload` ; retour = SavedVariables lues par `forever` hors du jeu ; journaux de combat analysés après le combat.
- Règles de code (section précédente) et procédure d'installation (`scripts/install_addon.py`).
- **ForeverAssist**, addon d'affichage, en trois versions : **V1** affiche des données exportées par `forever` (fichier Lua généré, par exemple ordre de talents, table des monstres de la zone) ; **V2** renvoie le contexte du personnage par SavedVariables (niveau, talents, zone, quêtes) ; **V3** compagnon de bureau qui analyse les journaux après le combat (`forever logs measure`) et prépare le fichier de V1.

### Feuille de route et CLAUDE.md
- `docs/ROADMAP.md` : T04 découpée en T04a / T04b ; lignes ForeverAssist V1 (après T04b), V2 (proposée avec T07, qui lit déjà les SavedVariables), V3 (proposée après T08) ; chacune avec fait, hors périmètre, critères de fin.
- `CLAUDE.md` : nouvelle section « Addon » avec les garde-fous ci-dessus (ADDON_LOADED sans alias de fichier, `pcall` sur `RegisterEvent` et les API incertaines, aucune fonction d'action, analyse du journal toujours hors du jeu) et le renvoi vers `docs/ADDON.md`.

### Installation, API Blizzard, DBCache
- **Script d'installation** : `scripts/install_addon.py` (`uv run`) copie `addon/ForeverLogger/` vers `<wow_dir>/Interface/AddOns/ForeverLogger/` ; `--wow-dir`, `--dry-run` ; refuse une destination qui n'est pas un dossier `Interface/AddOns` ; remplace uniquement le dossier `ForeverLogger` (ancien contenu renommé `ForeverLogger.bak-<date>`).
- **API Blizzard** : documentée seulement en T04 (`docs/DATA_SOURCES.md`) ; clés dans `.env` (déjà ignoré par git, jamais lu par les tests) ; client futur dans `forever/pipeline/bnet.py` via `Deps.http_get`, ajouté à la liste réseau de CLAUDE.md et de `test_network_boundary.py` le jour où la couverture de Forever est confirmée (au lancement).
- **DBCache.bin** : documenté pour T08 (lecture de l'en-tête et correspondance version, région, locale) ; aucun décodage en T04.

## Existant réutilisé
- `forever/config.py::Deps` (ajout de `wow_dir`), `forever/errors.py` (`DataSchemaError`, codes), `forever/provenance.py`, `forever/cli.py::_emit` / `_emit_error`.
- `forever/pipeline/tables.py` (schémas déclarés, style d'erreur), `forever/pipeline/decode.py::decode_spells` (ajout de `scaling`), `forever/pipeline/sources.py` (candidates), `scripts/extract_wago_fixtures.py` (modèle du script d'extraction).
- `forever/manifest.py::write_manifest`, `forever/store.py`, `forever/gamedata.py::build_game_data` (lecture de `spell_scaling.json` et `monsters.json`).
- `forever/registry.py` (`STATUSES` a déjà `valide-journal` ; `validate`, `COVERED_STATUSES`).
- `tests/conftest.py` : `make_deps`, `data_copy`, `write_manifest(data_copy)` après modification.
- Seed : `sim_leveling.py::mob_hp` (interpolation des ancres, gardée pour `mob_source="seed"`).

## Fichiers
```
addon/ForeverLogger/ForeverLogger.toc, ForeverLogger.lua      addon réparé + instantanés ForeverLoggerDB
addon/README.md                                                 installation, contenu de ForeverLoggerDB
scripts/install_addon.py                                        copie vers le dossier AddOns
scripts/extract_combatlog_fixture.py                            anonymisation hors ligne (décision 8)
scripts/extract_questie_fixture.py                              extrait de PNJ hors ligne
forever/pipeline/combatlog.py      lecture : en-tête, événements, unités, bloc avancé, suffixes
forever/pipeline/measure.py        mesures : PV des monstres, coûts, intervalles, critiques, touchés/ratés
forever/pipeline/lua_table.py      analyseur de tables Lua littérales
forever/pipeline/questie.py        lecteur Questie (version du .toc, PNJ, XP de quête)
forever/pipeline/addon_sv.py       lecteur de ForeverLoggerDB
forever/pipeline/monsters.py       construction de la table des monstres (candidate)
forever/pipeline/decode.py         + scaling par rang
forever/engine/spells.py           + rank_values_at_level
forever/registry.py                + champ preuves, contrôle de valide-journal
forever/config.py, errors.py       + wow_dir, UnsupportedLogError (unsupported_log, code 3)
forever/cli.py                     + logs scan, logs measure, questie info, monsters build
forever/data/1.60.1.70009/spell_scaling.json, monsters.json    + sources.json, manifest.json régénéré
tests/fixtures/combatlog/WoWCombatLog-092726_145346.anon.txt (+ README.md : date, origine, anonymisation)
tests/fixtures/combatlog/synthetic/*.txt    cas limites (version 21, ligne tronquée, événement inconnu, conflit de PV)
tests/fixtures/questie/11.38.0/Questie_Camelot.toc, classicNpcDB.lua (extrait), xpDB-classic.lua (extrait)
tests/fixtures/addon/ForeverLoggerDB.lua    SavedVariable d'exemple (niveau connu du personnage)
tests/unit/test_combatlog.py, test_measure.py, test_lua_table.py, test_questie.py, test_addon_sv.py,
tests/unit/test_monsters.py, test_spell_scaling.py, test_install_addon.py, test_addon_rules.py, test_logs_cli.py
Tests modifiés : test_registry.py (preuves), test_contract.py (+ 4 commandes), test_manifest.py et
                 test_data_import.py (+ 2 fichiers), test_decode_spells.py (scaling)
scripts/check_game_numbers.py      + dossier addon/
docs/ADDON.md (nouveau), docs/DATA_SOURCES.md, ARCHITECTURE.md, DECISIONS.md (42 et suivantes), OPEN_QUESTIONS.md,
docs/ROADMAP.md (T04a/T04b, ForeverAssist V1 à V3), CLAUDE.md (section « Addon »),
docs/MECHANICS_REGISTRY.yaml (preuves, A3, B1, H1 selon les mesures)
```

## Interfaces
```python
# forever/pipeline/combatlog.py
class LogHeader(NamedTuple): version: int; advanced: bool; build: str; project_id: int
class Unit(NamedTuple): guid: str; name: str | None; flags: int; raid_flags: int
    # propriétés : kind ("Player", "Creature", "Pet", "GameObject", "Vehicle"), npc_id (champ 6 du GUID), is_mine (flags & 0x1)
class Advanced(NamedTuple):
    guid: str; owner: str; hp: int; max_hp: int; attack_power: int; spell_power: int; armor: int; absorb: int
    unknown_a: int; unknown_b: int; power_type: int; power: int; max_power: int; power_cost: int
    x: float; y: float; ui_map_id: int; facing: float; level: int
class Event(NamedTuple):
    line: int; time: datetime; name: str; source: Unit | None; dest: Unit | None
    spell: tuple[int, str, int] | None; advanced: Advanced | None; suffix: Mapping[str, object]; raw: tuple[str, ...]
def read_log(path: Path) -> tuple[LogHeader, Iterator[Event]]      # unsupported_log, data_schema
def scan_logs(directory: Path) -> list[LogSummary]                  # nom, en-tête, début, fin, lignes, joueurs « à moi »

# forever/pipeline/measure.py
class MonsterObservation(TypedDict): npc_id: int; name: str; level: int; max_hp: int; guids: int; ui_map_id: int; log: str
def monster_hp(events) -> tuple[list[MonsterObservation], list[Conflict]]
def spell_costs(events, caster: str) -> dict[int, set[int]]          # sort → coûts relevés
def gcd_intervals(events, caster: str) -> list[float]                # entre deux SUCCESS sans START (instantanés)
def cast_times(events, caster: str) -> dict[int, list[float]]        # START → SUCCESS
def crit_ratios(events, caster: str) -> list[tuple[int, float]]      # montant / montant d'origine si critique
def hit_tally(events, caster: str, caster_level: int | None) -> dict[tuple[str, int], HitCount]  # (école, écart)

# forever/pipeline/lua_table.py
def parse_lua_value(text: str) -> object       # dict (clés int ou str), list, str, int, float, bool, None ; ValueError situé

# forever/pipeline/questie.py
class QuestieInfo(NamedTuple): version: str; title: str; interface: int; npc_count: int; quest_count: int
def read_questie(addon_dir: Path) -> QuestieDB  # npcs(), npc(id), quest_xp(id) ; valeurs étiquetées communautaires

# forever/pipeline/monsters.py
def build_monsters(observations, questie: QuestieDB | None, version: str) -> dict[str, object]
    # {"npcs": {id: {name, zone_id, rank, levels: {n: {max_hp, certainty, source, questie_hp}}}},
    #  "hp_by_level": {n: {value, certainty, source, n_npcs}}, "conflicts": [...], "questie_version": ...}

# forever/engine/spells.py
def rank_values_at_level(gd: GameData, spell: str, rank: int, level: int) -> RankValues  # Registre : A20 (et entrée ajoutée)
```

### CLI (texte français, `--json`, provenance sur chaque sortie, aucun réseau)
| Commande | Codes |
| --- | --- |
| `forever logs scan [--dir D]` | 0 ; 4 dossier absent |
| `forever logs measure FICHIER\|DOSSIER [--addon-sv F]` | 0 ; 3 `unsupported_log` / `data_schema` |
| `forever questie info [--dir D]` | 0 ; 4 addon absent |
| `forever monsters build --logs D [--questie D] [--out D] [--force]` | 0 ; 2 `candidate_exists` |

## Tests attendus (valeurs tirées des fixtures)
- `test_combatlog.py` : en-tête (22, avancé, `1.60.1`, 18) ; 193 événements ; comptes par événement identiques au journal réel (`SPELL_AURA_APPLIED` 44, `SPELL_CAST_SUCCESS` 40, `SPELL_CAST_START` 29, `SWING_DAMAGE` 12, `SPELL_DAMAGE` 9, `UNIT_DIED` 4, …) ; bloc avancé à 19 champs ; GUID décrit = destination sur `SPELL_DAMAGE`, source sur `SWING_DAMAGE` ; `npc_id` 3099 extrait du GUID ; joueur « à moi » unique ; version 21 → `unsupported_log` ; ligne tronquée → `data_schema` avec numéro de ligne ; événement inconnu gardé brut.
- `test_measure.py` : PV (3099, 6) = 120 sur 2 individus, (3099, 7) = 137, (5951, 1) = 8 ; aucun conflit ; conflit synthétique signalé ; coûts {837: 50, 145: 65, 1449: 75, 2137: 75} ; intervalles de GCD [1.503, 1.516, 1.590] (à 1 ms) ; critique Fireball 87 / 58 = 1,5 ; incantations Frostbolt [2.074, 1.982], Fireball [2.443, 2.472] ; `hit_tally` sans niveau du lanceur → vide avec hypothèse.
- `test_lua_table.py` : chaînes à guillemets simples et doubles et échappements, nombres négatifs et décimaux, `nil` dans une liste, clés `[14]=`, erreur localisée.
- `test_questie.py` : version `11.38.0` et titre « Forever-v27 » lus dans le `.toc` Camelot ; PNJ 3099 = (Dire Mottled Boar, 120, 137, 6, 7, rang 0, zone 14) ; 5951 = (Hare, 8, 8, 1, 1) ; XP de quête 788 = (2, 170) ; certitude `suppose`, source « communautaire ».
- `test_monsters.py` : 3099 niveau 6 : `max_hp` 120 `certain` (journal) et `questie_hp` 120 ; niveau 7 : 137 ; interpolation Questie PV niveau → niveau ; un PNJ Questie seul reste `suppose` ; écart journal ↔ Questie listé.
- `test_addon_sv.py` : lecture de `ForeverLoggerDB` d'exemple ; jointure GUID → niveau du lanceur ; `hit_tally` groupé par écart.
- `test_spell_scaling.py` : Frostbolt r3 (837) : niveau 14 → 43-49, niveau 18 et au-delà → 47-52 (= `spells.json`) ; Arcane Explosion r1 → 32-36 à 19 ; `decode` sur fixtures reproduit `spell_scaling.json`.
- `test_registry.py` : `valide-journal` sans preuve refusé ; fixture ou test inexistant refusé ; `n` < `n_min` refusé ; preuve valide acceptée.
- `test_install_addon.py` : copie dans un faux dossier `Interface/AddOns` (tmp), sauvegarde de l'ancien, `--dry-run` n'écrit rien, destination invalide refusée ; `.toc` sans ligne fusionnée et `## Interface: 16001`.
- `test_addon_rules.py` : `addon/ForeverLogger/` respecte les règles de la section Addon ; chaque règle a un cas négatif (fixture Lua fautive sous `tests/fixtures/addon/bad/` : alias de fichier, `RegisterEvent` nu, `CastSpellByName`, `COMBAT_LOG_EVENT_UNFILTERED`) refusé avec un message qui nomme le fichier et la ligne.
- `test_logs_cli.py` + `test_contract.py` : 4 commandes, code 0, provenance complète, `forever/data/` inchangé, aucun appel réseau (`http_get` qui lève).

## Étapes
0. **Vérification sur le vrai journal** (fait pendant le cadrage, voir Constats) ; en exécution : extraire la fixture anonymisée, figer la disposition des champs dans les tests.
1. Tests rouges (skill `/tranche`), commit `T04: tests`.
2. `combatlog.py` puis `measure.py` (journal d'abord, comme demandé).
3. `lua_table.py`, `questie.py`, fixture Questie ; puis `monsters.py` et `monsters.json` (observations du journal + agrégat par niveau, sources et certitudes).
4. `decode` : `scaling` ; `spell_scaling.json` ; `rank_values_at_level`.
5. Registre : champ `preuves`, contrôle de `valide-journal` ; ajouter les preuves disponibles (B1 : intervalles, n = 3, sous `n_min` → reste `teste` avec la preuve jointe ; coûts relevés en note de B11). A3 et H1 : protocole de collecte (ci-dessous), promotion seulement si un journal de campagne est fourni.
6. Addon : ranger, réparer, `ForeverLoggerDB` selon les règles de la section Addon, `test_addon_rules.py`, `install_addon.py`, `check_game_numbers.py` étendu ; `addon_sv.py`.
7. Documentation : `docs/ADDON.md` ; `ROADMAP.md` (T04a/T04b, ForeverAssist V1 à V3) ; `CLAUDE.md` (section « Addon ») ; `DATA_SOURCES.md` (client local : journaux, Hotfix.log, DBCache.bin pour T08, caches WDB ; addons de quêtes installés, source communautaire, licence à vérifier, version de l'addon comme provenance, relecture quand la version change (branchement sur la veille en T08) ; RestedXP exclu ; API Blizzard : clés dans `.env`, couverture de Forever à vérifier au lancement, client futur dans `forever/pipeline/`), `ARCHITECTURE.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `ROADMAP.md`.
8. `/verifier`, commit, résumé.

### Protocole de collecte (à jouer par l'utilisateur, ForeverLogger installé)
- **B1** : sur un mannequin ou des monstres faciles, 50 sorts instantanés enchaînés sans pause (Fire Blast, Arcane Explosion, Frost Nova hors recharge) → intervalles minimaux.
- **A3** : leveling ordinaire au Frostbolt ; il faut plusieurs centaines de lancers par écart de niveau (0, +1, +2, +3) pour distinguer des taux de raté voisins ; noter les talents de toucher (instantané de l'addon).
- **H1** : un boss de donjon (par exemple Ragefire Chasm) → niveau du boss dans le bloc avancé, recoupé avec `BOSS_LEVELS` de ForeverDungeonJournal (non ingéré).
- **Monstres** : tout journal de leveling enrichit la table (`forever monsters build`).

## Hors périmètre
- Simulateurs, MCP `forever_sim_leveling`, graphique, tests du seed, remontées du registre de la feuille de route (T04b).
- Décodage de `DBCache.bin` et application des hotfixes (T08) ; veille sur la version de Questie (T08).
- Caches `questcache.wdb` et `creaturecache.wdb` (format binaire à rétro-documenter).
- Client de l'API Blizzard (au lancement) ; tout accès réseau nouveau.
- Données de ForeverDungeonJournal, GearQuestForever, EllesmereUI (notées) ; RXPGuides (exclu).
- Quêtes propres à Forever (`QuestieForeverDB`) : lecture possible par `lua_table`, ingestion en T04b avec le modèle d'XP.
- ForeverAssist (V1 à V3) : seulement planifié dans `docs/ADDON.md` et `ROADMAP.md`, aucun code.

## Risques
- **Un seul journal court, sans raté ni boss** : A3 et H1 ne peuvent pas passer `valide-journal` sans campagne ; critère de fin formulé en conséquence.
- **Dernier champ joueur** (niveau d'objet ?) et **deux champs inconnus** du bloc avancé : parseur tolérant, valeurs brutes, question ouverte.
- **API de talents sur Forever** (moteur mainline, traits) : l'instantané de talents peut échouer ; `pcall` et champ absent plutôt qu'erreur.
- **Licence Questie** non confirmée : l'agrégat et les PNJ observés seulement dans le dépôt ; retrait facile si la licence l'interdit.
- **Questie = Classic Era** : les PV peuvent différer dans Forever ; seuls les PNJ mesurés sont `certain`.
- **Écriture dans `Program Files (x86)`** : droits possibles ; le script échoue proprement et indique la commande à lancer en administrateur.
- **Hotfixes CurvePoint** : les rangs de talent décodés en T03 peuvent différer du jeu en ligne (question ouverte, T08).

## Critères de fin (T04a)
- `forever logs measure` sur la fixture renvoie les PV, coûts, intervalles et critiques ci-dessus, avec provenance, code 0, sans réseau.
- `forever monsters build` sur les fixtures produit une table où 3099 (niveaux 6 et 7) et 5951 sont `certain` et égaux à Questie ; `monsters.json` et `spell_scaling.json` installés dans 1.60.1.70009 avec manifeste à jour.
- `rank_values_at_level` reproduit `spells.json` au niveau min(MaxLevel, 60).
- Le registre refuse un `valide-journal` sans preuve ; B1 porte la preuve du journal (n = 3).
- `uv run scripts/install_addon.py --dry-run` affiche la copie prévue ; le `.toc` est réparé ; `test_addon_rules.py` vert.
- `docs/ADDON.md` existe ; `ROADMAP.md` porte T04a/T04b et ForeverAssist V1 à V3 ; `CLAUDE.md` porte les garde-fous de l'addon.
- `uv run tasks.py verify` vert.

## Questions ouvertes à ajouter
- Deux champs inconnus du bloc avancé (entre absorption et type de ressource) ; dernier champ pour un joueur (niveau d'objet ?).
- Montant et montant d'origine différents d'une unité hors critique.
- Durées d'incantation mesurées inférieures à la table (Frostbolt 2,07 / 1,98 s pour 2,2) : talents, file d'attente de sort ou horodatage serveur.
- Hotfixes CurvePoint (144) et Curve (72) : écarts possibles avec le décodage T03 ; CreatureDifficulty (3) : PV de créatures corrigés.
- Questie : licence amont ; base Classic Era valable pour Forever au-delà des 3 PNJ recoupés.
- Build absent de l'en-tête du journal (`1.60.1` seulement).

## Écarts à l'exécution (2026-09-27)
- Incantations START → SUCCESS : la fixture en contient **trois** pour Frostbolt (1,916, 2,074, 1,982 s), le plan en citait deux ; les tests suivent la fixture. Intervalles entre instantanés : ordre chronologique [1,516, 1,503, 1,590], fenêtre d'enchaînement passée en paramètre (`--max-gap`, 3 s par défaut dans `forever/config.py`).
- Cas réels du second journal (devenu non vide pendant la session, 10 713 lignes) : ressources multiples `3|4` dans le bloc avancé, `SPELL_ABSORBED` à disposition variable, totems et gardiens invoqués (exclus des PV) ; fixtures synthétiques et tests ajoutés.
- `monsters.json` construit sur les deux journaux réels du 2026-09-27 et Questie 11.38.0 : 21 PNJ mesurés, 0 conflit, 29 écarts avec Questie (reconstruit après relecture : un niveau tiré d'un seul PNJ est `probable`).
- Nouvelle entrée de registre **G7** (points de base par niveau) ; B1 porte la preuve du journal (n = 3, `tolerance.n_min` 50) et reste `teste`.
- `forever explain-mechanic` affiche les preuves de journal ; `forever logs measure` rapporte `player_level_field` (dernier champ du bloc avancé du joueur) à côté du niveau de `ForeverLoggerDB`.
- ForeverAssist V1 dépend aussi de T05 (ordre de talents), en plus de T04b.
