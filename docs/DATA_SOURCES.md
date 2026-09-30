# Sources de données

## Hiérarchie des sources (décisions 127 et 128)
1. **Données du client** (tables décodées, `DBCache.bin` et `Hotfix.log` pour les correctifs) : `certain`.
2. **Mes observations** : journaux de combat et relevés hors combat de ForeverLogger (`certain` pour ce qu'ils mesurent directement).
3. **Wowhead Forever et addons de données** (AtlasLoot, ForeverDungeonJournal, Questie, GearQuestForever, Auctionator) : `suppose` au mieux, source et version citées.
4. **Guides** (Icy Veins, forums, vidéos) : faits sourcés, `suppose`.

Une source plus haute l'emporte sur une plus basse ; un écart entre deux sources est toujours signalé, jamais tranché au hasard. Une donnée que seules les sources 3 et 4 portent (PV des monstres avant mesure, taux de butin, gains de réputation) reste `suppose` jusqu'à une observation réelle.

## Client Forever (vérité)
- Versions : `https://wago.tools/api/builds` (produit `wow_classic_beta`, versions `1.60.x` ; liste non triée : trier par `created_at`). Produit de lancement : inconnu, prévoir l'alerte `silent`.
- Tables : `https://wago.tools/db2/<Table>/csv?build=<version>` (enUS) ; autre locale : `&locale=frFR` (vérifié le 2026-09-27 sur `SpellName`). Liste des tables, colonnes utilisées et règles de lecture : `forever/data/<version>/decode_rules.json`, `forever/pipeline/tables.py`, inventaire `tasks/T03-inventaire.md`. `TraitTreeLoadout*` : HTTP 400 sur 1.60.1.70009 (inutile).
    - Talents : SkillLineXTraitTree (ligne de compétence → arbre), TraitNode, TraitNodeEntry, TraitNodeXTraitNodeEntry, TraitDefinition, TraitDefinitionEffectPoints (points par rang via CurvePoint), TraitEdge (prérequis), CurvePoint. Ignorer Talent et TalentTab (reliquats Classic). Valeurs d'un rang : variables de l'infobulle du sort du nœud (`Spell.Description_lang`).
    - Géométrie des arbres : onglets à PosX 1020 / 5020 / 9080, rangées à PosY 2130 + 600 par rangée, colonnes espacées de 600 ; quelques positions ont un zéro en trop ; si deux nœuds partagent un sort, le plus récent est le bon.
    - Sorts : SkillLineAbility (rangs par ligne de compétence), Spell (rang dans NameSubtext, infobulle), SpellName, SpellEffect (points de base, RealPointsPerLevel, variance, période, sort déclenché), SpellLevels, SpellMisc (attributs, index d'incantation et de durée), SpellCastTimes, SpellDuration, SpellPower, SpellCooldowns, SpellAuraOptions (cumuls, charges).
    - Objets : Item*, formules RandPropPoints, ItemDamage*, ItemArmor*.
- Hotfixes : `DBCache.bin` du client, à faire correspondre à la version, la région et la langue.
- Absent du client : PV des monstres, quêtes, positions des PNJ, taux de butin, stocks, listes d'entraîneurs.

## Voie autonome (si wago est indisponible)
- `db2tool` (wowsims) : lecture du client installé, superposition des hotfixes ; mode hors ligne sur fichiers extraits.
- wow.tools.local (TACTSharp, DBCD, WoWDBDefs) ; définitions de tables : WoWDBDefs.

## Données dérivées et simulateurs (MIT, garder le lien vers wowsims/classic)
- Arbres de talents au format wowsims : `gunba/wow-forever-sim` (`ui/core/talents/trees/mage.json`), rangs confirmés : `ElliotWood/Forever` (`assets/confirmed_talents.json`).
- Simulateur de référence : fork `ElliotWood/Forever` ; `SimOptions.ruleset` vaut `RulesetClassic` par défaut : toujours passer la règle Forever. Le dépôt amont `wowsims/forever` a été injoignable (404) : **épingler les commits et copier les arbres utilisés**.
- Base d'objets de référence : `alcaras/forever-ref` (calcul des stats par formules du client).
- Recoupements lisibles : ForeverChanges, WoW Forever Talents, Wowhead Forever.

## Wowhead Forever : contrôle, jamais vérité (décision 128)
- Rôle : contrôler les valeurs de sorts décodées du client (dégâts par rang, coûts, durées, recharges). La concordance conforte une valeur `probable` ou `suppose` (valeur calculée, rang lu sur un ancien build) ; elle n'ajoute rien à une valeur `certain` du client.
- Divergence client ↔ Wowhead : **alerte**, pas un arbitrage. Causes possibles : correctif serveur non appliqué par notre décodage, ou erreur de notre côté. L'agent vérifie dans l'ordre les correctifs du client (`Hotfix.log`, puis `Cache/ADB/<locale>/DBCache.bin`), puis mes journaux (valeur observée), et signale l'écart avec ce qu'il a trouvé ; la question va dans `docs/OPEN_QUESTIONS.md` si rien ne tranche.
- Accès : consultation ponctuelle par le sous-agent de recherche (`forever-web-researcher`), avec l'adresse de la page et la date de consultation. **Jamais d'aspiration automatique du site**, que ses conditions d'utilisation interdisent : aucun code du dépôt ne lit Wowhead. GearQuestForever, dont les fiches viennent de Wowhead, ne sert qu'au recoupement.

## Client installé (sources locales, sans réseau ; T04a)
Dossier du client : `FOREVER_WOW_DIR` (défaut `C:\Program Files (x86)\World of Warcraft\_classic_beta_`), lu en lecture seule.
- **Journaux de combat** `Logs/WoWCombatLog-*.txt` : format 22, bloc avancé à 19 champs (dont PV max, coût du sort, position, niveau) ; lecteur `forever/pipeline/combatlog.py`, mesures `forever/pipeline/measure.py` (`forever logs scan`, `forever logs measure`). L'en-tête ne donne que `1.60.1` (pas le build) : la provenance retient la version locale de même préfixe, avec une hypothèse. Source de premier rang pour les PV des monstres (`certain`). Warcraft Logs n'a pas de support Forever documenté.
- **Hotfix.log** : index des hotfixes appliqués au démarrage (push, table, RecID, validité), **sans valeur** ; utilisable en T08 comme index de changements. Les valeurs sont dans `Cache/ADB/<locale>/DBCache.bin` (en-tête `XFTH`, build en octets 4-7) : décodage en T08 (WoWDBDefs).
- **QuestCache.log** : journal de requêtes du cache de quêtes, **aucune donnée** ; le contenu est dans `Cache/WDB/<locale>/questcache.wdb` (`WQST`) et `creaturecache.wdb` (`WMOB`, sans PV) : format binaire non documenté, hors T04.
- **SavedVariables** `WTF/Account/<COMPTE>/SavedVariables/` : `ForeverLogger.lua` (`ForeverLoggerDB`, niveau et talents du personnage, `forever/pipeline/addon_sv.py`) ; lus sans exécuter de Lua (`forever/pipeline/lua_table.py`).
- **Carnet de Questie** (T04b, décision 3) : `SavedVariables/Questie.lua`, table `QuestieConfig.char.<Nom - Royaume>.journey` (événements `Level` : heure Unix, nouveau niveau). Données personnelles de l'utilisateur, lues localement seulement (`forever/pipeline/questie.py : read_journey`), jamais copiées au-delà d'un extrait anonymisé de fixture. Le fichier contient des chaînes compressées (octets quelconques) : lecture octet pour octet et balayage table par table ; Questie écrit parfois plusieurs blocs `char` pour un même GUID (« Unknown ») : réunis par GUID. Heures ramenées à l'heure locale du journal par le décalage d'un instantané ForeverLogger, sinon par le fuseau du système. Repli après ForeverLoggerDB pour le niveau du lanceur.

## Addons installés (sources communautaires)
- **Quêtes et zones de Questie** (T04c, décision 69) : `Database/Classic/classicQuestDB.lua` (`questKeys` : niveau requis, niveau, masques de races et de classes, `zoneOrSort`), `Database/Zones/data/dungeons.lua` (zone du donjon, identifiants alternatifs, zone parente), `Localization/lookups/lookupZones.lua` (noms **anglais**, aucune table française), seuils de couleur de `Modules/Libs/QuestieLib.lua`. Lus à l'exécution par `forever lookup zones` ; base Classic Era sans correction Forever, `suppose`, jamais copiée (fixture minimale dans `tests/fixtures/questie/`).
- **Questie** (`Interface/AddOns/Questie`, version lue dans `Questie_Camelot.toc`, ici 11.38.0 Forever-v27) : base **Classic Era sans correction Forever** (PNJ : PV min/max, niveaux, rang ; XP de quête). Lecture locale seulement (`forever/pipeline/questie.py`), jamais copiée : le dépôt ne garde que l'agrégat par niveau et les PNJ observés dans un journal avec la valeur Questie en regard (`monsters.json`). Certitude `suppose`, étiquette « communautaire », version de l'addon dans la provenance. **Licence amont à vérifier** avant tout élargissement. Relire quand la version change (veille, T08). Écart mesuré le 2026-09-27 : Questie sous-estime les PV de Forever à partir du niveau 10 environ (29 écarts sur 21 PNJ mesurés).
- **RestedXP (RXPGuides) : exclu en entier** (guides payants). EllesmereUI (interface) et Quest Master (copie exacte des bases de Questie, `tasks/inventaire-addons.md`) : non utilisés comme sources.

## Addons de données : première source communautaire (décision 123)
Ces addons compilent des données relevées par de nombreux joueurs, souvent plus complètes que mes propres observations. Règles communes :
- **Lecture locale seulement** (`Interface/AddOns` et `WTF/.../SavedVariables`), jamais par le réseau, jamais dans les tests (fixtures minimales dans `tests/fixtures/`).
- **Version de l'addon dans la provenance** de chaque valeur, avec l'empreinte de ses fichiers de données (décision 124).
- **Seuls des agrégats entrent dans le dépôt** (comptes, écarts, valeurs recoupées avec leur source), jamais les tables de l'addon.
- **Licences à vérifier avant tout usage élargi** (redistribution, données dans `forever/data/`).
- Certitude au mieux `suppose` ; une observation réelle l'emporte (décision 127).

| Addon | Version relevée (2026-09-30) | Apport | Licence | Usage |
|---|---|---|---|---|
| AtlasLoot Classic Forever | 1.1.3 annoncée, `.toc` : « Forever 1.60.1 » | Butin par boss (instance → boss → `npcID` → objets), taux Classic de `droprate.lua` | GPL-2 (installée) | DJ1, T10 ; valeur Classic de `GetForVersion` (premier argument) |
| ForeverDungeonJournal | 1.3.1 | Donjons, boss, butin, quêtes Forever et leur XP (base et réglée), textes français | aucune ; données de sites tiers (`SOURCES.txt`) | DJ1, T04d ; niveaux des boss hérités copiés de Classic (pas un recoupement de H1) |
| Questie Forever | 11.38.0 Forever-v27 | Quêtes, PNJ, récompenses ; `QuestieForeverDB` (quêtes Forever apprises en jeu) ; quêtes faites de mes personnages | à vérifier (CurseForge 334372) | Déjà lu (T04a à T04c) ; profil (T07), T04d |
| GearQuestForever | 0.2.19-beta | Fiches d'objets, infobulles Wowhead Forever, sources (boss, quête, marchand, métier) | aucune ; données Wowhead | **Recoupement seulement** (T10, T04d), jamais source d'une valeur |
| Auctionator | 339 | **Mes relevés de prix** (`AUCTIONATOR_PRICE_DATABASE`, CBOR), cache des prix marchands | All Rights Reserved ; `AGENTS.md` adressé aux agents d'IA | Lecture de mes propres SavedVariables par un décodeur maison, code de l'addon jamais lu ni repris (décision de l'utilisateur du 2026-09-30) ; profil (T07), prix avant l'API (EC1, T10) |

Détail des formats, comptes et recoupements : `tasks/inventaire-addons.md`.

### Versions des addons (décision 124)
Quand la version d'un addon de données change, le projet le détecte, relit ses données et signale ce qui a changé, comme pour une version du jeu. La chaîne `## Version` du `.toc` ne suffit pas (AtlasLoot 1.1.3 ne l'écrit nulle part) : la détection compare aussi l'**empreinte des fichiers de données** de l'addon à celle du dernier relevé. Commande simple `forever addons status` en DJ1 (version, empreinte, date du relevé, changé ou non, agrégats touchés) ; automatisation (relecture et note de changement à chaque veille) en T08.

## Observations de ForeverLogger (décision 127, DJ1)
ForeverLogger complète et vérifie les addons de données par mes observations réelles, **relevées hors combat**, sans abonnement au journal de combat ni fonction d'action (`docs/ADDON.md`) : objets et prix des marchands à l'ouverture d'un marchand, butin ramassé, gains de réputation ; chaque API sondée sous `pcall`. Une observation réelle l'emporte sur une donnée d'addon et passe la certitude à `certain` ; un écart entre les deux est signalé (valeur de l'addon et sa version en regard).

## Profil multi-sources (décision 125)
Le profil de mes personnages (hors du dépôt, décision 99) croise : ForeverLogger (niveau, talents, observations), les sauvegardes des autres addons (quêtes faites dans Questie, mes prix d'Auctionator), mes journaux de combat (personnages « à moi ») et, après le lancement, l'API Blizzard (fiche de personnage, équipement, honneur et rang PvP, classements) si elle couvre Forever. Chaque champ garde sa source et sa date ; en cas de désaccord, la valeur la plus récente l'emporte, et à date égale la plus directe (ordre fixé au plan de PV1) ; l'écart est signalé.

## Données manquantes et addons candidats (décision 131)
Quand l'agent constate qu'il lui manque une donnée pour répondre (angle mort, valeur supposée, domaine pas encore couvert, taux de Classic au lieu de Forever), il cherche sur CurseForge, Wago et la liste des addons Forever de foreverchanges.pro un addon qui embarque ou collecte cette donnée et **propose de l'installer** : donnée apportée, ce que ça change à la réponse, lien, version, date de mise à jour, licence, compatibilité Forever (`.toc` `_Camelot` ou interface 16001) et signalements de stabilité (un addon connu pour faire planter le jeu est écarté). **Il ne télécharge ni n'installe jamais rien** : l'utilisateur installe. Une fois l'addon installé, il l'inventorie en lecture seule (comme `tasks/inventaire-addons.md`, puis par `forever addons status` à partir de DJ1) et l'ajoute à cette page.

Liste tenue à chaque fin de tranche (tirée du registre et de `docs/OPEN_QUESTIONS.md`), regroupée par donnée. Statut du candidat : addon installé qui s'applique, « non cherché », ou « aucun trouvé (date) » après une recherche. Aucune recherche n'a encore été faite au 2026-09-30.

| Donnée manquante | Où elle manque | Candidat |
|---|---|---|
| PV des monstres de Forever hors des Tarides | H11, `hp_by_level` | Questie (base Classic, sous-estime) ; addon Forever : non cherché. Mesure : mes journaux |
| Taux de butin de Forever | DJ1, T10 | AtlasLoot (taux Classic seulement, `suppose`) ; addon Forever : non cherché |
| Butin des donjons et raids Forever (hors Hall of Thanes et Ruins of Lordaeron) | DJ1 | ForeverDungeonJournal, AtlasLoot (incomplets) |
| Niveaux des boss et plages de niveau des donjons Forever | DJ1, H1 | ForeverDungeonJournal, AtlasLoot (contradictoires) ; mesure : mes journaux |
| Quêtes propres à Forever et leur XP | T04d | `QuestieForeverDB` (sans XP), ForeverDungeonJournal (quêtes de donjon), GearQuestForever (noms sans ID) |
| Couleurs de quête de Forever (plage verte) | I7 | non cherché ; relevé possible par ForeverLogger |
| Prix de l'hôtel des ventes | EC1, T10, MT1 | Auctionator (mes relevés) ; API Blizzard après le lancement |
| Objets et prix des marchands | T10, MT1 | Auctionator (cache des prix marchands), GearQuestForever (sources) ; relevé ForeverLogger (DJ1) |
| Gains de réputation par source, récompenses par palier | RP1 | non cherché ; relevé ForeverLogger (DJ1) |
| Entraîneurs, sources de recettes, chance de gain | MT1 | AtlasLoot Crafting (Classic, TBC et Wrath mêlés) ; addon Forever : non cherché |
| Progression Legacy du compte | LG2, G5 | non cherché |
| Honneur, rang et classements PvP | PV2, LG2 | non cherché ; API Blizzard après le lancement |
| Rendements décroissants de Forever | PV2 | non cherché (un addon qui les suit en direct lirait le journal de combat, refusé aux addons sur Forever) ; mesure : mes journaux |
| Buffs mondiaux, de campement et de Legacy ; conditions de zone des flacons | D3, D5, E1 | non cherché |
| Armure et résistances des monstres | H2 | non cherché |
| Statistiques des objets de Forever | T10, F1 | GearQuestForever (recoupement seulement) ; source : tables du client |

## API Blizzard (décision 126, tranche EC1)
Gardée par le lancement et la vérification de la couverture de Forever. Tout ce que l'API couvre pour Forever : prix de l'hôtel des ventes ; fiches de personnages (niveau, équipement, talents si disponibles) ; PvP (honneur, rang, classements). Clés dans `.env` (ignoré par git, jamais lu par les tests). Le client futur vivra dans `forever/pipeline/bnet.py` (via `Deps.http_get`) et sera ajouté à la liste réseau de CLAUDE.md et de `tests/unit/test_network_boundary.py` ce jour-là, **après accord de l'utilisateur** pour chaque nouvel accès réseau. Aucun code avant EC1.
